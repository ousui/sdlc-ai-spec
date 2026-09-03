#!/usr/bin/env python3
"""Run complete CTX -> REQ -> DSN -> PLN -> IMP integration probes.

The supplied projects are immutable test inputs.  A probe uses only a disposable
checkout, creates real formal artifacts with the production handlers, performs
one bounded README edit, reads the completed IMP back, and restores the exact
initial Git workspace before returning.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import traceback
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
CTX_RUNTIME = ROOT / "skills/sdlc-000-ctx/scripts/runtime.py"
REQ_SCRIPTS = ROOT / "skills/sdlc-100-req/scripts"
DSN_SCRIPTS = ROOT / "skills/sdlc-200-dsn/scripts"
PLN_SCRIPTS = ROOT / "skills/sdlc-300-pln/scripts"
IMP_SCRIPTS = ROOT / "skills/sdlc-400-imp/scripts"
for candidate in (
    ROOT,
    ROOT / "packages",
    TOOLS,
    REQ_SCRIPTS,
    DSN_SCRIPTS,
    PLN_SCRIPTS,
    IMP_SCRIPTS,
):
    value = str(candidate)
    if value not in sys.path:
        sys.path.insert(0, value)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load module {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ctx_runtime = _load_module("external_imp_ctx_runtime", CTX_RUNTIME)
req_runtime = _load_module(
    "external_imp_req_runtime", REQ_SCRIPTS / "runtime_final.py"
)

import run_external_pln_integration as pln_fixture  # noqa: E402
from packages.sdlc_artifact_store import ArtifactStore, compute_sha256  # noqa: E402
from packages.sdlc_claim_provider import ClaimProvider  # noqa: E402
from packages.sdlc_lifecycle import LifecycleQueryService  # noqa: E402
from packages.sdlc_phasekit import subject_digest  # noqa: E402
from packages.sdlc_runtime import execute_phase, parse_canonical_artifact  # noqa: E402
from packages.sdlc_runtime.canonical import (  # noqa: E402
    CHECK_HEADERS,
    GATE_SUMMARY_HEADERS,
    find_tables,
    require_single_row,
    require_single_table,
)
from dsn_analyzer import DsnAnalyzer  # noqa: E402
from dsn_common import UpstreamScope, _subject_digest as dsn_subject_digest  # noqa: E402
from dsn_handler_final import DsnHandler  # noqa: E402
from imp_common import CONSIDERATIONS  # noqa: E402
from imp_handler import ImpHandler  # noqa: E402
from imp_result import capture, read_state  # noqa: E402
from pln_common import WORK_HEADERS  # noqa: E402
from pln_runtime import PlnHandler, resolve_inputs  # noqa: E402


FIXED = datetime(2026, 9, 4, 1, 0, tzinfo=timezone.utc)
FIXED_TEXT = "2026-09-04T01:00:00Z"
OWNER = "external-imp-executor"
RETRY_DELAYS = (0, 5, 10, 20, 40)
ARTIFACT_PATTERN = re.compile(
    r"^(CTX|REQ|DSN|PLN|IMP)-[0-9]{14}-[0-9]{2,}$"
)
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


class IntegrationError(RuntimeError):
    """A deterministic acceptance assertion failed."""


class Log:
    def __init__(self, path: Path | None = None):
        self.path = path
        self.lines: list[str] = []

    def add(self, message: str) -> None:
        line = f"[{datetime.now(timezone.utc).isoformat()}] {message}"
        self.lines.append(line)
        print(line, flush=True)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise IntegrationError(message)


def _canonical_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return compute_sha256(raw)


def _git_process(root: Path, *arguments: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        capture_output=True,
        check=False,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
    )


def _git_bytes(root: Path, *arguments: str) -> bytes:
    completed = _git_process(root, *arguments)
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise IntegrationError(f"git {' '.join(arguments)} failed: {detail}")
    return completed.stdout


def _git(root: Path, *arguments: str) -> str:
    return _git_bytes(root, *arguments).decode("utf-8", errors="strict").strip()


def _workspace_snapshot(root: Path) -> dict[str, Any]:
    listed = _git_bytes(
        root,
        "ls-files",
        "-z",
        "--cached",
        "--others",
        "--exclude-standard",
    )
    paths = sorted(
        item.decode("utf-8", errors="surrogateescape")
        for item in listed.split(b"\0")
        if item
    )
    digest = hashlib.sha256()
    records: list[dict[str, Any]] = []
    for relative in paths:
        target = root / relative
        info = target.lstat()
        mode = stat.S_IMODE(info.st_mode)
        if stat.S_ISLNK(info.st_mode):
            kind = "symlink"
            raw = os.readlink(target).encode("utf-8", errors="surrogateescape")
        elif stat.S_ISREG(info.st_mode):
            kind = "file"
            raw = target.read_bytes()
        else:
            raise IntegrationError(f"unsupported tracked path type: {relative}")
        encoded = relative.encode("utf-8", errors="surrogateescape")
        digest.update(encoded + b"\0")
        digest.update(kind.encode("ascii") + b"\0")
        digest.update(f"{mode:o}".encode("ascii") + b"\0")
        digest.update(raw + b"\0")
        records.append(
            {
                "path": relative,
                "kind": kind,
                "mode": mode,
                "sha256": compute_sha256(raw),
            }
        )
    return {"sha256": "sha256:" + digest.hexdigest(), "files": records}


def _git_state(root: Path) -> dict[str, Any]:
    return {
        "head": _git(root, "rev-parse", "HEAD"),
        "status_hex": _git_bytes(
            root,
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
        ).hex(),
        "refs_hex": _git_bytes(
            root,
            "for-each-ref",
            "--format=%(refname)%00%(objectname)",
        ).hex(),
        "workspace": _workspace_snapshot(root),
    }


def _select_resource_root(root: Path) -> str:
    """Choose the smallest safe tracked directory that owns a README.md."""
    paths = [
        item.decode("utf-8", errors="surrogateescape")
        for item in _git_bytes(root, "ls-files", "-z").split(b"\0")
        if item
    ]
    candidates = sorted(
        {
            str(Path(path).parent.as_posix())
            for path in paths
            if Path(path).name == "README.md"
        },
        key=lambda directory: (
            sum(
                True
                if directory == "."
                else path.startswith(directory.rstrip("/") + "/")
                for path in paths
            ),
            directory.count("/"),
            directory,
        ),
    )
    failures: list[str] = []
    for relative in candidates:
        target = root if relative == "." else root / relative
        readme = target / "README.md"
        if not readme.is_file() or readme.is_symlink():
            continue
        try:
            capture(target, "repo")
        except Exception as exc:
            failures.append(f"{relative}: {exc}")
            continue
        return relative
    raise IntegrationError(
        "no safe narrow tracked Resource containing README.md: " + "; ".join(failures)
    )


def _authority_reference(root: Path, name: str, text: str) -> str:
    directory = root / ".sdlc/authority"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / name
    target.write_text(text, encoding="utf-8")
    return target.relative_to(root).as_posix() + "@" + compute_sha256(
        target.read_bytes()
    )


def _fact(value: str, basis: str, *references: str) -> dict[str, Any]:
    return {
        "value": value,
        "basis": basis,
        "basis_references": list(references),
    }


def _none_section() -> dict[str, Any]:
    return {"none": {"basis": "confirmed", "basis_references": ["EVD-001"]}}


def _context_candidate(
    project_label: str,
    expected_sha: str,
    workspace_digest: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    boundary = f"Disposable checkout of {project_label} at {expected_sha}"
    locator = f"vcs:{project_label}@{expected_sha}"
    context = {
        "summary": (
            f"Exact integration context for {project_label} at {expected_sha}."
        ),
        "project_identity": {
            "project_name": _fact(project_label, "confirmed", "EVD-001"),
            "purpose": _fact(
                "Verify the complete deterministic IMP lifecycle",
                "confirmed",
                "EVD-001",
            ),
            "boundary": _fact(boundary, "confirmed", "EVD-001"),
            "primary_resource_reference": _fact(
                "RSC-001", "observed", "EVD-002"
            ),
            "authoritative_references": _fact(
                "EVD-001", "confirmed", "EVD-001"
            ),
        },
        "resources": [
            {
                "id": "RSC-001",
                "type": "repository",
                "name": project_label,
                "role": "primary",
                "locator": locator,
                "baseline_reference": locator,
                "basis": "observed",
                "basis_references": ["EVD-002"],
            }
        ],
        "technologies": _none_section(),
        "engineering_entries": _none_section(),
        "components": _none_section(),
        "rules": _none_section(),
        "environments": _none_section(),
        "constraints": _none_section(),
        "exceptions": [],
    }
    evidence = [
        {
            "id": "EVD-001",
            "type": "confirmation",
            "supports_references": ["CTX-G-002", "CTX-G-004"],
            "source_or_producer": "external-integration-authority",
            "reference": "authority:external-integration",
            "integrity_or_digest": workspace_digest,
            "produced_at": FIXED.isoformat(),
            "sensitivity_or_access": "project-authorized",
        },
        {
            "id": "EVD-002",
            "type": "observation",
            "supports_references": ["CTX-G-003"],
            "source_or_producer": "git",
            "reference": locator,
            "integrity_or_digest": workspace_digest,
            "produced_at": FIXED.isoformat(),
            "sensitivity_or_access": "public",
        },
    ]
    return context, evidence, boundary


def _ctx_invocation(
    root: Path,
    operation: str,
    context: Mapping[str, Any],
    evidence: Sequence[Mapping[str, Any]],
    *,
    reference: str | None = None,
    boundary: str | None = None,
    refresh: Mapping[str, Any] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    inputs: dict[str, Any] = {
        "context": context,
        "evidence": list(evidence),
        "supporting_members": [],
    }
    if refresh is not None:
        inputs["refresh"] = refresh
    confirmations: list[dict[str, Any]] = []
    if operation == "create":
        confirmations = [
            {"type": "write", "approved": True},
            {
                "type": "project_boundary",
                "value": boundary,
                "authority_reference": "EVD-001",
            },
        ]
    return {
        "contract": "sdlc-ai-spec/runtime-invocation/v1",
        "operation": operation,
        "project_root": str(root),
        "artifact_reference": reference,
        "inputs": inputs,
        "confirmations": confirmations,
        "options": {"dry_run": dry_run},
    }


def _create_context(
    root: Path,
    project_label: str,
    expected_sha: str,
    workspace_digest: str,
) -> tuple[str, dict[str, Any]]:
    context, evidence, boundary = _context_candidate(
        project_label, expected_sha, workspace_digest
    )
    source_text = (
        f"project: {project_label}\ncommit: {expected_sha}\n"
        f"workspace: {workspace_digest}\ndecision: context-authorized\n"
    )
    source_reference = _authority_reference(root, "ctx-source.txt", source_text)
    evidence[0]["reference"] = source_reference
    evidence[0]["integrity_or_digest"] = source_reference.rsplit("@", 1)[1]

    created = ctx_runtime.invoke(
        _ctx_invocation(
            root,
            "create",
            context,
            evidence,
            boundary=boundary,
        ),
        clock=lambda: FIXED,
    )
    _assert(
        created.get("artifact") is not None
        and created["artifact"]["revision_state"] == "open",
        "real CTX create did not retain the expected open Revision: "
        + json.dumps(created, ensure_ascii=False, sort_keys=True),
    )
    reference = f"{created['artifact']['id']}@{created['artifact']['revision']}"
    refresh = {
        "base_revision": None,
        "observed_at": FIXED.isoformat(),
        "observation_baseline": f"vcs:{project_label}@{expected_sha}",
        "refresh_reason": "complete exact external integration confirmation",
        "effective_change_references": "None",
        "evidence_references": ["EVD-001", "EVD-002"],
    }
    preview = ctx_runtime.invoke(
        _ctx_invocation(
            root,
            "revise",
            context,
            evidence,
            reference=reference,
            refresh=refresh,
            dry_run=True,
        ),
        clock=lambda: FIXED,
    )
    binding_warning = next(
        (
            item
            for item in preview.get("warnings", [])
            if item.get("code") == "FINAL_CONFIRMATION_BINDINGS"
        ),
        None,
    )
    _assert(binding_warning is not None, "CTX preview omitted confirmation bindings")
    bindings = dict(binding_warning["details"])
    authority_text = "\n".join(
        (
            f"artifact: {reference}",
            f"control: {bindings['control_input_digest']}",
            f"contracts: {bindings['evaluation_contract_set']}",
            f"checks: {bindings['check_set_result_digest']}",
            "decision: approved",
        )
    ) + "\n"
    final_reference = _authority_reference(
        root, "ctx-final-confirmation.txt", authority_text
    )
    final_invocation = _ctx_invocation(
        root,
        "revise",
        context,
        evidence,
        reference=reference,
        refresh=refresh,
    )
    final_invocation["confirmations"] = [
        {"type": "write", "approved": True},
        {
            "type": "final_confirmation",
            "result": "approved",
            "mode": "human",
            "confirmer": "external-integration-authority",
            "role": "Project Maintainer",
            "authority_reference": final_reference,
            "accepted_exception_references": [],
            "confirmed_at": FIXED.isoformat(),
            **bindings,
        },
    ]
    result = ctx_runtime.invoke(final_invocation, clock=lambda: FIXED)
    _assert(
        result.get("ok")
        and result["artifact"]["revision_state"] == "frozen"
        and result["artifact"]["artifact_status"] == "ready",
        "real CTX did not freeze ready: "
        + json.dumps(result, ensure_ascii=False, sort_keys=True),
    )
    return reference, context


def _requirement_candidate(
    project_label: str,
    expected_sha: str,
    resource_root: str,
) -> dict[str, Any]:
    physical_target = (
        "README.md"
        if resource_root == "."
        else f"{resource_root}/README.md"
    )
    return {
        "title": f"Validate deterministic IMP on {project_label}",
        "summary": (
            f"Apply and verify one reversible marker in {physical_target} at {expected_sha}."
        ),
        "sources": [
            {
                "type": "text",
                "content": f"{project_label}@{expected_sha}",
                "evidence_reference": "N/A",
            }
        ],
        "goals": [
            {
                "problem": f"{physical_target} has no IMP integration marker",
                "outcome": "The exact disposable checkout contains the scoped marker",
                "success_condition": "README.md contains the project-specific marker",
            }
        ],
        "in_scope": ["resource:repo", "path:repo/README.md"],
        "out_of_scope": ["dependencies", "release", "remote Git state"],
        "affected_parties": [
            {
                "party": "IMP integration verifier",
                "impact": f"Receives immutable evidence for {project_label}",
            }
        ],
        "requirements": [
            {
                "type": "behavior",
                "source_references": ["SRC-001", "GOAL-001"],
                "statement": (
                    f"The disposable {project_label} checkout shall materialize one "
                    f"project-specific integration marker in {physical_target}."
                ),
            }
        ],
        "acceptance_criteria": [
            {
                "requirement_references": ["R-001"],
                "condition": "The exact fixed commit is checked out and WI-001 is claimed",
                "expected_result": (
                    f"README.md contains the deterministic {project_label} marker and "
                    "the Result digest is reproducible"
                ),
            }
        ],
        "dependencies": [],
        "profile": "full",
        "profile_basis": "A product edit requires design, planning and verification",
        "lifecycle_applicability": [
            {
                "phase": phase,
                "disposition": disposition,
                "host": "N/A",
                "basis": basis,
            }
            for phase, disposition, basis in (
                ("DSN", "required", "The exact resource boundary must be designed"),
                ("PLN", "required", "The implementation needs an exact Work Item"),
                ("IMP", "required", "README.md receives a scoped product edit"),
                ("VFY", "required", "VFY is the mandatory downstream control point"),
                ("RLS", "n/a", "This disposable acceptance probe does not release"),
            )
        ],
        "open_items": [],
        "evidence": [],
        "supporting_members": [],
        "exceptions": [],
    }


def _create_requirement(
    root: Path,
    context_reference: str,
    project_label: str,
    expected_sha: str,
    resource_root: str,
) -> tuple[str, dict[str, Any]]:
    requirement = _requirement_candidate(
        project_label, expected_sha, resource_root
    )
    authority_reference = _authority_reference(
        root,
        "req-approval.md",
        f"project: {project_label}\ncommit: {expected_sha}\ndecision: approved\n",
    )
    confirmation = {
        "mode": "human",
        "confirmer": "external-product-owner",
        "role": "Product Owner",
        "authority_reference": authority_reference,
        "confirmed_at": FIXED_TEXT,
        "subject_digest": req_runtime.base._subject_digest(
            requirement, context_reference, ()
        ),
    }
    invocation = {
        "contract": "sdlc-ai-spec/runtime-invocation/v1",
        "operation": "create",
        "project_root": str(root),
        "artifact_reference": None,
        "inputs": {
            "context_reference": context_reference,
            "requirement": requirement,
            "control_inputs": [],
            "final_confirmation": confirmation,
        },
        "confirmations": [{"type": "artifact_store_write", "approved": True}],
        "options": {"dry_run": False},
    }
    result = req_runtime.execute_phase(
        req_runtime.RequirementHandler(root, clock=lambda: FIXED), invocation
    )
    _assert(
        result.get("ok")
        and result["artifact"]["revision_state"] == "frozen"
        and result["artifact"]["artifact_status"] == "ready",
        "real REQ did not freeze ready: "
        + json.dumps(result, ensure_ascii=False, sort_keys=True),
    )
    return result["artifact"]["reference"], requirement


def _design_candidate(
    root: Path,
    requirement_reference: str,
    project_label: str,
    expected_sha: str,
    readme: bytes,
    resource_root: str,
) -> dict[str, Any]:
    design = deepcopy(pln_fixture.dsn_fixture._design(root, requirement_reference))
    baseline = f"vcs:{project_label}@{expected_sha}"
    design.update(
        title=f"{project_label} README implementation design",
        summary=(
            f"Bind the reversible {project_label} README marker to {resource_root}."
        ),
        boundary="resource:repo and path:repo/README.md",
        change_type="incremental",
        baseline_references=[baseline],
        target_state_summary=(
            f"README.md records the deterministic integration marker for {project_label}"
        ),
        impact_summary=(
            "Only the selected Resource's README.md changes inside the disposable checkout"
        ),
        simplicity_rationale="One preconditioned text replacement is sufficient",
    )
    change = design["changes"][0]
    change.update(
        object_or_boundary="resource:repo",
        change="modify",
        baseline_references=[baseline],
        baseline_state=f"README digest {compute_sha256(readme)}",
        target_state=f"README contains the {project_label} IMP marker",
    )
    design["evidence"] = [
        {
            "id": "EVD-001",
            "type": "repository",
            "supports_references": [
                requirement_reference + "#R-001",
                "DOM-210",
                "DOM-220",
            ],
            "source": project_label,
            "reference": baseline,
            "digest": compute_sha256(readme),
            "produced_at": FIXED_TEXT,
            "sensitivity": "public",
        }
    ]
    design["supporting_members"] = [
        {
            "member_id": "SUP-001",
            "canonical_name": "baseline/README.md",
            "media_type": "text/markdown",
            "encoding": "utf-8",
            "content": readme.decode("utf-8"),
        }
    ]
    return design


def _create_design(
    root: Path,
    context_reference: str,
    requirement_reference: str,
    project_label: str,
    expected_sha: str,
    readme: bytes,
    resource_root: str,
) -> tuple[str, dict[str, Any]]:
    design = _design_candidate(
        root,
        requirement_reference,
        project_label,
        expected_sha,
        readme,
        resource_root,
    )
    upstream = UpstreamScope(
        context_reference=context_reference,
        scope_references=(requirement_reference,),
        control_references=(),
        requirement_items=(requirement_reference + "#R-001",),
        acceptance_items=(requirement_reference + "#AC-001",),
    )
    normalized = DsnAnalyzer().analyze(design, upstream).normalized
    authority_reference = _authority_reference(
        root,
        "dsn-approval.md",
        f"project: {project_label}\ncommit: {expected_sha}\ndecision: approved\n",
    )
    confirmation = {
        "mode": "human",
        "confirmer": "external-design-authority",
        "role": "Design Authority",
        "authority_reference": authority_reference,
        "confirmed_at": FIXED_TEXT,
        "subject_digest": dsn_subject_digest(
            normalized,
            context_reference,
            (requirement_reference,),
            (),
        ),
    }
    invocation = {
        "contract": "sdlc-ai-spec/runtime-invocation/v1",
        "operation": "create",
        "project_root": str(root),
        "artifact_reference": None,
        "inputs": {
            "scope_inputs": [requirement_reference],
            "control_inputs": [],
            "design": design,
            "final_confirmation": confirmation,
        },
        "confirmations": [],
        "options": {"dry_run": False, "write_policy": "auto"},
    }
    result = execute_phase(DsnHandler(root, clock=lambda: FIXED), invocation)
    _assert(
        result.get("ok")
        and result["artifact"]["revision_state"] == "frozen"
        and result["artifact"]["artifact_status"] == "ready",
        "real DSN did not freeze ready: "
        + json.dumps(result, ensure_ascii=False, sort_keys=True),
    )
    return result["artifact"]["reference"], design


def _create_plan(
    root: Path,
    design_reference: str,
    project_label: str,
) -> tuple[str, dict[str, Any]]:
    store = ArtifactStore.open_read_only(root)
    phase_inputs = resolve_inputs(
        store, {"scope_inputs": [design_reference], "control_inputs": []}
    )
    plan = pln_fixture._plan_candidate(root, phase_inputs)
    _assert(len(plan["work_items"]) == 2, "PLN must contain one IMP and one VFY item")
    imp_item = plan["work_items"][0]
    imp_item.update(
        outcome=f"Materialize the reversible README marker for {project_label}",
        execution_scope=["resource:repo", "path:repo/README.md"],
        completion_criteria=(
            f"README.md contains the {project_label} marker and an immutable Result"
        ),
        expected_evidence=(
            f"Exact {project_label} Baseline, changed-path evidence and Result digest"
        ),
    )
    vfy_item = plan["work_items"][1]
    vfy_item.update(
        outcome=f"Verify the completed {project_label} README Result",
        execution_scope=["resource:repo", "path:repo/README.md"],
        completion_criteria="The current completed IMP is the exact VFY input",
        expected_evidence="Frozen IMP Result and completed Current Claim",
    )
    plan["title"] = f"{project_label} external IMP delivery plan"
    plan["summary"] = (
        f"Plan one deterministic README implementation and VFY handoff for {project_label}."
    )
    authority_reference = _authority_reference(
        root,
        "pln-approval.md",
        f"project: {project_label}\nwork_item: WI-001\ndecision: approved\n",
    )
    confirmation = {
        "mode": "human",
        "confirmer": "external-plan-authority",
        "role": "Plan Authority",
        "authority_reference": authority_reference,
        "confirmed_at": FIXED_TEXT,
        "subject_digest": subject_digest(
            plan,
            {
                "context": phase_inputs.context_reference,
                "scope": phase_inputs.scope_references,
                "control": phase_inputs.control_references,
            },
        ),
    }
    invocation = {
        "contract": "sdlc-ai-spec/runtime-invocation/v1",
        "operation": "create",
        "project_root": str(root),
        "artifact_reference": None,
        "inputs": {
            "scope_inputs": [design_reference],
            "control_inputs": [],
            "plan": plan,
            "final_confirmation": confirmation,
        },
        "confirmations": [],
        "options": {"dry_run": False, "write_policy": "auto"},
    }
    result = execute_phase(PlnHandler(root, clock=lambda: FIXED), invocation)
    _assert(
        result.get("ok")
        and result["artifact"]["revision_state"] == "frozen"
        and result["artifact"]["artifact_status"] == "ready",
        "real PLN did not freeze ready: "
        + json.dumps(result, ensure_ascii=False, sort_keys=True),
    )
    return result["artifact"]["reference"], plan


def _implementation_candidate(
    root: Path,
    design_reference: str,
    project_label: str,
    resource_root: str,
) -> tuple[dict[str, Any], str]:
    resource_path = root if resource_root == "." else root / resource_root
    path = resource_path / "README.md"
    before = path.read_text(encoding="utf-8")
    marker = f"<!-- sdlc-imp-integration:{project_label} -->"
    after = before.rstrip("\n") + "\n\n" + marker + "\n"
    method = {
        "title": f"{project_label} README implementation",
        "summary": f"Append the exact reversible integration marker for {project_label}",
        "considerations": [
            {
                "name": name,
                "disposition": (
                    "required" if name == "Effects & Consistency" else "n/a"
                ),
                "basis": (
                    "A preconditioned local README write has one observable effect"
                    if name == "Effects & Consistency"
                    else "This single marker edit introduces no rule, state, mapping, algorithm or failure contract in this category"
                ),
                "steps": ["STEP-001"] if name == "Effects & Consistency" else [],
                "exception": None,
            }
            for name in CONSIDERATIONS
        ],
        "steps": [
            {
                "id": "STEP-001",
                "order": 1,
                "purpose": "Publish the exact README integration marker",
                "target": ["resource:repo", "path:repo/README.md"],
                "basis_references": [design_reference + "#CHG-001"],
                "considerations": ["Effects & Consistency"],
                "logic": [
                    "Read the exact README Baseline",
                    "Replace it once only when its digest and full text match",
                    "Read back the marker and immutable Resource Result",
                ],
                "expected_result": f"README.md contains {marker}",
                "transaction_boundary": "One conditional local file write",
                "failure_boundary": "Stop before mutation when the Baseline mismatches",
                "blocks": [
                    {
                        "id": "EFF-001",
                        "consideration": "Effects & Consistency",
                        "resource_or_effect": "resource:repo path:repo/README.md",
                        "order_and_condition": "Match the exact Baseline, write once, then read back",
                        "consistency_or_atomicity": "One file operation under the Current Claim",
                        "idempotency": "The exact operation identity is retained in the Attempt",
                        "failure_handling": "Preserve the Baseline and stop on any mismatch",
                    }
                ],
            }
        ],
        "resources": [{"id": "repo", "root": resource_root}],
        "operations": [
            {
                "resource": "repo",
                "path": "README.md",
                "step": "STEP-001",
                "op": "replace_text",
                "before": before,
                "after": after,
                "expected_sha256": compute_sha256(path.read_bytes()),
            }
        ],
        "checks": [
            {
                "id": "CHK-001",
                "name": "README contains the exact integration marker",
                "kind": "contains",
                "resource": "repo",
                "path": "README.md",
                "expected": marker,
            }
        ],
        "exceptions": [],
        "open_items": [],
    }
    return method, marker


def _imp_invocation(
    root: Path,
    operation: str,
    *,
    binding: str | None = None,
    reference: str | None = None,
    implementation: Mapping[str, Any] | None = None,
    final_confirmation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    inputs: dict[str, Any] = {"owner": OWNER}
    if binding is not None:
        inputs["binding"] = binding
    if implementation is not None:
        inputs["implementation"] = implementation
    if final_confirmation is not None:
        inputs["final_confirmation"] = final_confirmation
    return {
        "contract": "sdlc-ai-spec/runtime-invocation/v1",
        "operation": operation,
        "project_root": str(root),
        "artifact_reference": reference,
        "inputs": inputs,
        "confirmations": [],
        "options": {"dry_run": False, "write_policy": "auto"},
    }


def _execution_warning(result: Mapping[str, Any]) -> Mapping[str, Any]:
    warning = next(
        (
            item
            for item in result.get("warnings", [])
            if item.get("code") == "IMP_EXECUTION_STATE"
        ),
        None,
    )
    _assert(warning is not None, "IMP result omitted IMP_EXECUTION_STATE")
    return warning


def _complete_imp(
    root: Path,
    binding: str,
    design_reference: str,
    project_label: str,
    resource_root: str,
) -> tuple[dict[str, Any], str]:
    method, marker = _implementation_candidate(
        root, design_reference, project_label, resource_root
    )
    handler = ImpHandler(root, clock=lambda: FIXED)
    created = execute_phase(
        handler,
        _imp_invocation(
            root,
            "create",
            binding=binding,
            implementation=method,
        ),
    )
    _assert(
        created.get("artifact") is not None
        and created["artifact"]["revision_state"] == "open"
        and created["status"] == "action_required",
        "IMP create did not execute and retain an open Revision: "
        + json.dumps(created, ensure_ascii=False, sort_keys=True),
    )
    info = _execution_warning(created)
    reference = created["artifact"]["reference"]
    authority_text = "\n".join(
        (
            f"artifact: {reference}",
            f"subject: {info['subject_digest']}",
            f"control: {info['final_confirmation_bindings']['control_input_digest']}",
            f"contracts: {info['final_confirmation_bindings']['evaluation_contract_set']}",
            f"checks: {info['final_confirmation_bindings']['check_set_result_digest']}",
            "decision: approved",
        )
    ) + "\n"
    authority_reference = _authority_reference(
        root, "imp-approval.md", authority_text
    )
    final_confirmation = {
        "mode": "human",
        "confirmer": "external-implementation-authority",
        "role": "Implementation Authority",
        "authority_reference": authority_reference,
        "confirmed_at": FIXED_TEXT,
        "subject_digest": info["subject_digest"],
        **info["final_confirmation_bindings"],
    }
    completed = execute_phase(
        handler,
        _imp_invocation(
            root,
            "revise",
            reference=reference,
            final_confirmation=final_confirmation,
        ),
    )
    _assert(
        completed.get("ok")
        and completed["status"] == "completed"
        and completed["artifact"]["revision_state"] == "frozen"
        and completed["artifact"]["artifact_status"] == "ready",
        "IMP did not freeze and complete its Current Claim: "
        + json.dumps(completed, ensure_ascii=False, sort_keys=True),
    )
    return completed, marker


def _file_identity(path: Path) -> dict[str, Any]:
    info = path.stat()
    raw = path.read_bytes()
    return {
        "sha256": compute_sha256(raw),
        "size": len(raw),
        "mode": stat.S_IMODE(info.st_mode),
        "mtime_ns": info.st_mtime_ns,
    }


def _artifact_shape(stored) -> dict[str, Any]:
    parsed = parse_canonical_artifact(stored.payload.primary_blob)
    headings = [
        {
            "level": len(level),
            "text": "<artifact-title>" if len(level) == 1 else text,
        }
        for level, text in HEADING_PATTERN.findall(parsed.body)
    ]
    tables = [list(table.headers) for table in parsed.tables]
    members = [
        {
            "member_id": member.member_id,
            "canonical_name": member.canonical_name,
            "media_type": member.media_type,
        }
        for member in stored.payload.members
    ]
    manifest = json.loads(stored.payload.manifest.raw_bytes)
    return {
        "front_matter_keys": list(parsed.front_matter.keys()),
        "headings": headings,
        "tables": tables,
        "members": members,
        "manifest_keys": sorted(manifest),
        "manifest_members": [
            {
                "member_id": item.member_id,
                "canonical_name": item.canonical_name,
                "media_type": item.media_type,
            }
            for item in stored.payload.manifest.local_members
        ],
    }


def _artifact_gate(stored) -> dict[str, Any]:
    parsed = parse_canonical_artifact(stored.payload.primary_blob)
    check_tables = find_tables(parsed, CHECK_HEADERS)
    _assert(bool(check_tables), "canonical Artifact has no Check table")
    summary = require_single_row(
        require_single_table(parsed, GATE_SUMMARY_HEADERS, "Gate Summary"),
        "Gate Summary",
    )
    return {
        "check_tables": [
            [
                {"id": row["Check ID"], "result": row["结果 Result"]}
                for row in table.rows
            ]
            for table in check_tables
        ],
        "summary_result": summary["Gate Result"],
        "summary_headers": list(GATE_SUMMARY_HEADERS),
    }


def _reference_kind(reference: str) -> str:
    match = re.match(r"^(CTX|REQ|DSN|PLN|IMP|VFY|RLS)-", reference)
    return match.group(1) if match else "external"


def _lifecycle_shape(projection) -> dict[str, Any]:
    return {
        "overall_state": projection.overall_state,
        "frontier": [_reference_kind(item) for item in projection.frontier],
        "vfy_inputs": [_reference_kind(item) for item in projection.vfy_inputs],
        "next_actions": [
            {"code": item.code, "phase": item.phase}
            for item in projection.next_actions
        ],
        "edges": sorted(
            {
                (
                    _reference_kind(edge.source_reference),
                    _reference_kind(edge.target_reference),
                    edge.relation,
                )
                for edge in projection.edges
            }
        ),
    }


def _phase_records(root: Path, references: Mapping[str, str]) -> dict[str, Any]:
    store = ArtifactStore.open_read_only(root)
    records: dict[str, Any] = {}
    for phase, reference in references.items():
        artifact_id, revision_text = reference.split("@", 1)
        revision = int(revision_text)
        stored = store.read_revision(artifact_id, revision)
        _assert(ARTIFACT_PATTERN.fullmatch(artifact_id) is not None, f"invalid {phase} ID")
        records[phase] = {
            "reference": reference,
            "id_pattern": f"{phase}-14digits-NN",
            "revision": stored.control.revision,
            "revision_state": stored.control.state,
            "artifact_status": stored.payload.artifact_status,
            "base_revision": stored.control.base_revision,
            "materialized": stored.control.materialized,
            "primary_sha256": stored.payload.primary_sha256,
            "shape": _artifact_shape(stored),
            "gate": _artifact_gate(stored),
        }
    return records


def _aggregate_member_digest(stored, prefix: str) -> str:
    rows = [
        [item.member_id, item.canonical_name, item.media_type, item.sha256]
        for item in stored.payload.members
        if item.member_id.startswith(prefix)
    ]
    return _canonical_digest(rows)


def run_integration(
    root: Path,
    project_label: str,
    expected_sha: str,
    *,
    logger: Log | None = None,
) -> dict[str, Any]:
    """Run one complete probe in an existing disposable exact checkout."""
    root = root.expanduser().resolve()
    log = logger or Log()
    _assert((root / ".git").exists(), "external project must be a Git checkout")
    _assert(re.fullmatch(r"[0-9a-f]{40}", expected_sha) is not None, "invalid fixed SHA")
    initial = _git_state(root)
    _assert(initial["head"] == expected_sha, "checkout HEAD differs from fixed SHA")
    runtime_dir = root / ".sdlc"
    _assert(not runtime_dir.exists(), "external checkout already contains .sdlc")
    resource_root = _select_resource_root(root)
    resource_path = root if resource_root == "." else root / resource_root
    readme_path = resource_path / "README.md"
    _assert(readme_path.is_file() and not readme_path.is_symlink(), "README.md is required")
    original_readme = readme_path.read_bytes()
    original_mode = stat.S_IMODE(readme_path.stat().st_mode)
    _assert(original_readme, "README.md must be non-empty")
    output: dict[str, Any] | None = None
    try:
        log.add(f"{project_label}: create real CTX")
        context_reference, context_candidate = _create_context(
            root,
            project_label,
            expected_sha,
            initial["workspace"]["sha256"],
        )
        log.add(f"{project_label}: create real REQ")
        requirement_reference, requirement_candidate = _create_requirement(
            root,
            context_reference,
            project_label,
            expected_sha,
            resource_root,
        )
        log.add(f"{project_label}: create real DSN")
        design_reference, design_candidate = _create_design(
            root,
            context_reference,
            requirement_reference,
            project_label,
            expected_sha,
            original_readme,
            resource_root,
        )
        log.add(f"{project_label}: create real PLN and select WI-001")
        plan_reference, plan_candidate = _create_plan(
            root, design_reference, project_label
        )
        binding = plan_reference + "#WI-001"
        plan_store = ArtifactStore.open_read_only(root)
        stored_plan = plan_store.read_revision(
            plan_reference.split("@", 1)[0], 1
        )
        parsed_plan = parse_canonical_artifact(stored_plan.payload.primary_blob)
        work_rows = require_single_table(
            parsed_plan, WORK_HEADERS, "PLN Work Items"
        ).rows
        _assert(
            [row["ID"] for row in work_rows] == ["WI-001", "WI-002"]
            and work_rows[0]["目标 Phase Target Phase"] == "IMP"
            and work_rows[1]["目标 Phase Target Phase"] == "VFY",
            "PLN Work Item identities or phase targets are not stable",
        )

        log.add(f"{project_label}: acquire Claim, execute README edit and complete IMP")
        imp_result, marker = _complete_imp(
            root,
            binding,
            design_reference,
            project_label,
            resource_root,
        )
        imp_reference = imp_result["artifact"]["reference"]
        _assert(marker in readme_path.read_text(encoding="utf-8"), "README marker missing")
        _assert(_git(root, "rev-parse", "HEAD") == initial["head"], "IMP changed HEAD")
        _assert(
            _git_state(root)["refs_hex"] == initial["refs_hex"],
            "IMP mutated Git refs",
        )

        store = ArtifactStore.open_read_only(root)
        stored_imp = store.read_revision(imp_result["artifact"]["id"], 1)
        state = read_state(stored_imp)
        result_row = state["resources"][0]
        result_member = next(
            item
            for item in stored_imp.payload.members
            if item.member_id == result_row["result_member"]
        )
        result_snapshot = json.loads(result_member.raw_bytes)
        readme_entry = next(
            item for item in result_snapshot["entries"] if item["path"] == "README.md"
        )
        actual_readme_digest = hashlib.sha256(readme_path.read_bytes()).hexdigest()
        result_digest_reproducible = (
            result_member.sha256 == compute_sha256(result_member.raw_bytes)
            and readme_entry["sha256"] == actual_readme_digest
        )
        _assert(result_digest_reproducible, "IMP Result digest is not reproducible")
        claim = ClaimProvider.open_read_only(root).resolve(binding)
        _assert(claim is not None and claim.state == "completed", "Current Claim is not completed")
        plan_context = parsed_plan.front_matter["context"]
        _assert(
            state["binding"]["context_reference"] == plan_context == context_reference,
            "IMP Context differs from the real PLN Context",
        )

        database = root / ".sdlc/store.sqlite3"
        before_check_database = _file_identity(database)
        before_check_readme = _file_identity(readme_path)
        before_check_git = _git_state(root)
        log.add(f"{project_label}: read-only IMP check and lifecycle projection")
        checked = execute_phase(
            ImpHandler(root, clock=lambda: FIXED),
            _imp_invocation(root, "check", reference=imp_reference),
        )
        after_check_database = _file_identity(database)
        after_check_readme = _file_identity(readme_path)
        after_check_git = _git_state(root)
        check_read_only = (
            before_check_database == after_check_database
            and before_check_readme == after_check_readme
            and before_check_git == after_check_git
        )
        _assert(
            checked.get("ok")
            and checked["status"] == "completed"
            and _execution_warning(checked)["vfy_ready"] is True,
            "IMP readback check is not completed/VFY-ready",
        )
        _assert(check_read_only, "IMP check changed Store, product, HEAD, refs or status")

        projection = LifecycleQueryService(root, plugin_root=ROOT).inspect_requirement(
            requirement_reference
        )
        _assert(
            projection.vfy_inputs == (imp_reference,)
            and any(
                item.code == "START_VFY" and item.phase == "VFY"
                for item in projection.next_actions
            )
            and projection.overall_state == "ready_for_next_phase",
            "lifecycle did not project the completed IMP as VFY ready",
        )
        references = {
            "CTX": context_reference,
            "REQ": requirement_reference,
            "DSN": design_reference,
            "PLN": plan_reference,
            "IMP": imp_reference,
        }
        phases = _phase_records(root, references)
        _assert(
            all(
                record["revision"] == 1
                and record["revision_state"] == "frozen"
                and record["artifact_status"] == "ready"
                and record["base_revision"] is None
                and record["materialized"] is True
                for record in phases.values()
            ),
            "formal artifact Revision semantics are inconsistent",
        )
        semantic_digests = {
            "requirement": _canonical_digest(requirement_candidate),
            "design": _canonical_digest(design_candidate),
            "work_item": _canonical_digest(plan_candidate["work_items"][0]),
            "resource": compute_sha256(original_readme),
            "evidence": _aggregate_member_digest(stored_imp, "EVD-"),
            "result": result_member.sha256,
        }
        output = {
            "contract": "sdlc-ai-spec/external-imp-project/v1",
            "ok": True,
            "project": project_label,
            "project_commit": expected_sha,
            "references": references,
            "binding": binding,
            "owner": OWNER,
            "resource_root": resource_root,
            "target_path": (
                "README.md"
                if resource_root == "."
                else f"{resource_root}/README.md"
            ),
            "claim": {
                "state": claim.state,
                "attempt": claim.attempt,
                "artifact_reference": f"{claim.artifact_id}@{claim.revision}",
            },
            "result": {
                "member": result_member.member_id,
                "reference": result_row["result_reference"],
                "sha256": result_member.sha256,
                "readme_sha256": "sha256:" + readme_entry["sha256"],
                "digest_reproducible": result_digest_reproducible,
            },
            "context_matches_plan": True,
            "check_read_only": check_read_only,
            "vfy_ready": True,
            "phases": phases,
            "lifecycle": _lifecycle_shape(projection),
            "semantic_digests": semantic_digests,
            "during_execution": {
                "head_unchanged": _git(root, "rev-parse", "HEAD") == initial["head"],
                "refs_unchanged": _git_state(root)["refs_hex"] == initial["refs_hex"],
                "readme_modified": readme_path.read_bytes() != original_readme,
            },
            "git_integrity": {
                "initial_head": initial["head"],
                "initial_status_sha256": compute_sha256(
                    bytes.fromhex(initial["status_hex"])
                ),
                "initial_refs_sha256": compute_sha256(
                    bytes.fromhex(initial["refs_hex"])
                ),
                "initial_tracked_untracked_sha256": initial["workspace"]["sha256"],
                "commit_push_or_ref_mutation_executed": False,
            },
        }
        return output
    finally:
        if readme_path.exists() and not readme_path.is_symlink():
            readme_path.write_bytes(original_readme)
            readme_path.chmod(original_mode)
        shutil.rmtree(runtime_dir, ignore_errors=True)
        final = _git_state(root)
        if final != initial:
            raise IntegrationError(
                f"{project_label}: cleanup did not restore exact HEAD/status/refs/workspace"
            )
        if output is not None:
            output["cleanup"] = {
                "runtime_removed": not runtime_dir.exists(),
                "head_equal": final["head"] == initial["head"],
                "status_equal": final["status_hex"] == initial["status_hex"],
                "refs_equal": final["refs_hex"] == initial["refs_hex"],
                "tracked_untracked_digest_equal": (
                    final["workspace"]["sha256"]
                    == initial["workspace"]["sha256"]
                ),
                "final_head": final["head"],
                "final_status_sha256": compute_sha256(
                    bytes.fromhex(final["status_hex"])
                ),
                "final_tracked_untracked_sha256": final["workspace"]["sha256"],
            }
        log.add(f"{project_label}: cleanup restored exact initial Git state")


def compare_projects(projects: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    _assert(len(projects) == 2, "cross-project acceptance requires exactly two projects")
    left, right = projects
    phases = ("CTX", "REQ", "DSN", "PLN", "IMP")
    structure_equal = all(
        left["phases"][phase]["shape"] == right["phases"][phase]["shape"]
        for phase in phases
    )
    id_patterns_equal = [
        left["phases"][phase]["id_pattern"] for phase in phases
    ] == [right["phases"][phase]["id_pattern"] for phase in phases]
    revision_semantics_equal = all(
        {
            key: left["phases"][phase][key]
            for key in (
                "revision",
                "revision_state",
                "artifact_status",
                "base_revision",
                "materialized",
            )
        }
        == {
            key: right["phases"][phase][key]
            for key in (
                "revision",
                "revision_state",
                "artifact_status",
                "base_revision",
                "materialized",
            )
        }
        for phase in phases
    )
    manifest_equal = all(
        left["phases"][phase]["shape"]["manifest_keys"]
        == right["phases"][phase]["shape"]["manifest_keys"]
        and left["phases"][phase]["shape"]["manifest_members"]
        == right["phases"][phase]["shape"]["manifest_members"]
        for phase in phases
    )
    gate_equal = all(
        left["phases"][phase]["gate"] == right["phases"][phase]["gate"]
        for phase in phases
    )
    lifecycle_equal = left["lifecycle"] == right["lifecycle"]
    digest_differences = {
        name: left["semantic_digests"][name] != right["semantic_digests"][name]
        for name in (
            "requirement",
            "design",
            "work_item",
            "resource",
            "evidence",
            "result",
        )
    }
    assertions = {
        "artifact_structure_signature_equal": structure_equal,
        "artifact_id_patterns_equal": id_patterns_equal,
        "revision_semantics_equal": revision_semantics_equal,
        "manifest_structure_equal": manifest_equal,
        "gate_structure_equal": gate_equal,
        "lifecycle_relationship_equal": lifecycle_equal,
        "semantic_content_digests_different": digest_differences,
    }
    _assert(structure_equal, "cross-project Artifact structure signatures differ")
    _assert(id_patterns_equal, "cross-project Artifact ID patterns differ")
    _assert(revision_semantics_equal, "cross-project Revision semantics differ")
    _assert(manifest_equal, "cross-project Manifest structures differ")
    _assert(gate_equal, "cross-project Gate structures differ")
    _assert(lifecycle_equal, "cross-project lifecycle relationships differ")
    _assert(all(digest_differences.values()), "cross-project semantic content is not distinct")
    return {"ok": True, **assertions}


def _clone_with_retry(
    destination: Path,
    repository: str,
    expected_sha: str,
    log: Log,
) -> list[dict[str, Any]]:
    url = f"https://github.com/{repository}.git"
    attempts: list[dict[str, Any]] = []
    for number, delay in enumerate(RETRY_DELAYS, start=1):
        if delay:
            log.add(f"{repository}: retry {number}/5 after {delay}s")
            time.sleep(delay)
        shutil.rmtree(destination, ignore_errors=True)
        completed = subprocess.run(
            ["git", "clone", "--no-checkout", url, str(destination)],
            capture_output=True,
            text=True,
            check=False,
        )
        attempt = {
            "attempt": number,
            "delay_seconds": delay,
            "clone_exit_code": completed.returncode,
            "clone_stdout": completed.stdout,
            "clone_stderr": completed.stderr,
        }
        if completed.returncode == 0:
            checkout = _git_process(destination, "checkout", "--detach", expected_sha)
            attempt.update(
                checkout_exit_code=checkout.returncode,
                checkout_stdout=checkout.stdout.decode("utf-8", errors="replace"),
                checkout_stderr=checkout.stderr.decode("utf-8", errors="replace"),
            )
            if checkout.returncode == 0 and _git(
                destination, "rev-parse", "HEAD"
            ) == expected_sha:
                attempts.append(attempt)
                log.add(f"{repository}: exact fixed SHA checked out on attempt {number}")
                return attempts
        attempts.append(attempt)
        log.add(
            f"{repository}: attempt {number}/5 failed: "
            + str(attempt.get("checkout_stderr") or completed.stderr).strip()
        )
    raise IntegrationError(
        f"{repository}: five bounded clone/checkout attempts failed: "
        + json.dumps(attempts, ensure_ascii=False, sort_keys=True)
    )


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--springgear-sha", required=True)
    parser.add_argument("--gin-vue-admin-sha", required=True)
    parser.add_argument("--json-out", required=True)
    parser.add_argument("--log-out")
    args = parser.parse_args()
    json_out = Path(args.json_out).expanduser().resolve()
    log_out = (
        Path(args.log_out).expanduser().resolve()
        if args.log_out
        else json_out.with_suffix(".log")
    )
    if log_out.exists():
        log_out.unlink()
    log = Log(log_out)
    specifications = (
        ("ousui/springgear", args.springgear_sha),
        ("flipped-aurora/gin-vue-admin", args.gin_vue_admin_sha),
    )
    evidence: dict[str, Any] = {
        "contract": "sdlc-ai-spec/external-imp-integration/v1",
        "ok": False,
        "projects": [],
        "clone_attempts": {},
        "cross_project": None,
        "error": None,
    }
    try:
        with tempfile.TemporaryDirectory(
            prefix="imp-v2-real-projects-", dir="/private/tmp"
        ) as temporary:
            parent = Path(temporary)
            for index, (repository, sha) in enumerate(specifications, start=1):
                checkout = parent / f"project-{index}"
                attempts = _clone_with_retry(checkout, repository, sha, log)
                evidence["clone_attempts"][repository] = attempts
                evidence["projects"].append(
                    run_integration(
                        checkout,
                        repository,
                        sha,
                        logger=log,
                    )
                )
            evidence["cross_project"] = compare_projects(evidence["projects"])
            evidence["ok"] = True
        _write_json(json_out, evidence)
        log.add(f"PASS: evidence written to {json_out}")
        return 0
    except Exception as exc:
        evidence["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        _write_json(json_out, evidence)
        log.add(f"FAIL: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

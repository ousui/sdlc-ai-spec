#!/usr/bin/env python3
"""Formal fixed-oracle evaluation runner for sdlc-000-ctx.

The runner does not alter the approved Design or EVAL-PLAN. It executes the
portable Runtime cases in isolated temporary projects and reports client-only
cases as deferred to their dedicated adapt stage.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any, Iterator


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.sdlc_artifact_store import ArtifactStore, compute_sha256  # noqa: E402
from packages.sdlc_artifact_store.catalog import ArtifactCatalog  # noqa: E402
from tests.skills.test_sdlc_000_ctx import (  # noqa: E402
    CtxRuntimeTests,
    FIXED_TIME,
    fact,
    runtime,
)


RESULTS: list[dict[str, Any]] = []
EXTERNAL_TRACE: dict[str, Any] = {}


def record(case_id: str, status: str, actual: str, evidence: Any = None) -> None:
    RESULTS.append(
        {
            "case": case_id,
            "status": status,
            "actual": actual,
            "evidence": evidence,
        }
    )


def check(case_id: str, condition: bool, actual: str, evidence: Any = None) -> None:
    record(case_id, "PASS" if condition else "FAIL", actual, evidence)


@contextmanager
def fixture() -> Iterator[CtxRuntimeTests]:
    helper = CtxRuntimeTests(
        methodName="test_boundary_key_normalizes_nfc_line_endings_and_outer_whitespace"
    )
    helper.setUp()
    try:
        yield helper
    finally:
        helper.tearDown()


def snapshot(root: Path) -> dict[str, dict[str, Any]]:
    return {
        str(path.relative_to(root)): {
            "size": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def refresh(base_revision: int | None, effective: Any = "None") -> dict[str, Any]:
    return {
        "base_revision": base_revision,
        "observed_at": "2026-08-30T10:11:12+00:00",
        "observation_baseline": "vcs:example@0123456789abcdef",
        "refresh_reason": "formal fixed eval",
        "effective_change_references": effective,
        "evidence_references": ["EVD-001", "EVD-002"],
    }


def active_exception() -> dict[str, str]:
    return {
        "id": "EX-001",
        "state": "active",
        "origin_exception_reference": "N/A",
        "scope_or_skipped_obligation": "Documented compatibility risk",
        "reason": "Fixed formal eval exception",
        "known_risk": "Legacy client may reject the new format",
        "compensating_control": "Retain the compatibility validator",
        "approver_role_time": "Project Maintainer at 2026-08-30T10:11:12+00:00",
        "revisit_condition": "When the legacy client is retired",
        "downstream_obligation": "Carry EX-001",
        "resolution_or_superseding_references": "N/A",
    }


def delegated_authority_text(
    *,
    reference: str,
    bindings: dict[str, str],
    delegation_basis: str,
    reviewer: str,
    reviewed_executor: str,
    variant: str = "valid",
) -> str:
    decided_at = "decided_at: 2026-08-30T10:11:12+00:00"
    independence = runtime.DELEGATED_INDEPENDENCE
    if variant == "missing_decided_at":
        decided_at = ""
    elif variant == "imprecise_fixed_set":
        independence += ", inherited_authorization"
    elif variant != "valid":
        raise ValueError(f"Unknown delegated authority variant: {variant}")
    return "\n".join(
        [
            "---",
            "contract: sdlc-ai-spec/final-confirmation-authority/v1",
            f"artifact: {reference}",
            "decision: approved",
            decided_at,
            "---",
            "",
            "| " + " | ".join(runtime.DELEGATED_AUTHORITY_HEADER) + " |",
            "| " + " | ".join("---" for _ in runtime.DELEGATED_AUTHORITY_HEADER) + " |",
            "| "
            + " | ".join(
                [
                    delegation_basis,
                    reviewer,
                    "Delegated Independent Reviewer",
                    reviewed_executor,
                    independence,
                    bindings["control_input_digest"],
                    bindings["evaluation_contract_set"],
                    bindings["check_set_result_digest"],
                    runtime.DELEGATED_EXCLUDED_AUTHORITY,
                ]
            )
            + " |",
        ]
    ) + "\n"


def create_with_confirmation(
    helper: CtxRuntimeTests,
    *,
    mode: str = "human",
    exceptions: list[dict[str, str]] | None = None,
    delegated_variant: str = "valid",
) -> tuple[dict[str, Any], dict[str, Any]]:
    invocation = helper.invocation()
    invocation["inputs"]["context"]["exceptions"] = exceptions or []
    predicted_id = "CTX-20260830101112-01"
    preview = runtime.build_payload(
        invocation,
        artifact_id=predicted_id,
        revision=1,
        base_revision=None,
        now=FIXED_TIME,
    )
    bindings = next(
        item["details"]
        for item in preview.warnings
        if item["code"] == "FINAL_CONFIRMATION_BINDINGS"
    )
    reference = f"{predicted_id}@1"
    confirmer = "project-owner" if mode == "human" else "reviewer-ctx-01"
    reviewed = None if mode == "human" else "builder-ctx-01"
    authority_dir = helper.project_root / "authority"
    authority_dir.mkdir(exist_ok=True)
    if mode == "delegated":
        delegation_basis_text = "delegation: reviewer-ctx-01 may confirm CTX contract compliance\n"
        delegation_basis_path = authority_dir / "delegation.txt"
        delegation_basis_path.write_text(delegation_basis_text, encoding="utf-8")
        delegation_basis = (
            "authority/delegation.txt@sha256:"
            + hashlib.sha256(delegation_basis_text.encode("utf-8")).hexdigest()
        )
        if delegated_variant == "invalid_delegation_basis":
            delegation_basis = "../delegation.txt@sha256:" + "0" * 64
            document_variant = "valid"
        else:
            document_variant = delegated_variant
        authority_text = delegated_authority_text(
            reference=reference,
            bindings=bindings,
            delegation_basis=delegation_basis,
            reviewer=confirmer,
            reviewed_executor=reviewed or "",
            variant=document_variant,
        )
    else:
        authority_text = "\n".join(
            [
                f"artifact: {reference}",
                f"control: {bindings['control_input_digest']}",
                f"contracts: {bindings['evaluation_contract_set']}",
                f"checks: {bindings['check_set_result_digest']}",
                "decision: approved",
            ]
        ) + "\n"
    authority_path = authority_dir / f"{mode}-{delegated_variant}-confirmation.md"
    authority_path.write_text(authority_text, encoding="utf-8")
    authority_reference = (
        f"{authority_path.relative_to(helper.project_root).as_posix()}@sha256:"
        + hashlib.sha256(authority_text.encode("utf-8")).hexdigest()
    )
    confirmation: dict[str, Any] = {
        "type": "final_confirmation",
        "result": "approved",
        "mode": mode,
        "confirmer": confirmer,
        "role": (
            "Project Maintainer"
            if mode == "human"
            else "Delegated Independent Reviewer"
        ),
        "authority_reference": authority_reference,
        "accepted_exception_references": [
            item["id"]
            for item in (exceptions or [])
            if item["state"] in {"active", "carried"}
        ],
        "confirmed_at": "2026-08-30T10:11:12+00:00",
        **bindings,
    }
    if reviewed:
        confirmation["reviewed_executor"] = reviewed
    invocation["confirmations"].append(confirmation)
    return invocation, helper.invoke(invocation)


def external_conflict_invocation(
    helper: CtxRuntimeTests,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run one explicitly authorized producer without delegating to its dependency."""

    external_dir = helper.project_root / "external"
    external_dir.mkdir()
    dependency = external_dir / "dependency.py"
    dependency.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "Path(sys.argv[1]).write_text('unexpected dependency invocation\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )
    producer = external_dir / "producer.py"
    producer.write_text(
        "import json, subprocess, sys\n"
        "request = json.load(sys.stdin)\n"
        "producer = request['producer']\n"
        "dependency = request['dependency']\n"
        "authorized = set(request['authorized_capabilities'])\n"
        "if producer not in authorized:\n"
        "    raise SystemExit(3)\n"
        "call_log = [producer]\n"
        "dependency_invoked = False\n"
        "if dependency in authorized:\n"
        "    subprocess.run([sys.executable, request['dependency_script'], request['dependency_canary']], check=True)\n"
        "    call_log.append(dependency)\n"
        "    dependency_invoked = True\n"
        "json.dump({'producer': producer, 'dependency_requested': dependency, 'dependency_invoked': dependency_invoked, 'call_log': call_log, 'proposal': {'resource_type': 'workspace'}}, sys.stdout, sort_keys=True)\n",
        encoding="utf-8",
    )
    canary = external_dir / "dependency-canary.txt"
    producer_capability = "fixture:external-context-producer"
    dependency_capability = "fixture:external-normalizer"
    authorization = [producer_capability]
    request = {
        "producer": producer_capability,
        "dependency": dependency_capability,
        "authorized_capabilities": authorization,
        "dependency_script": str(dependency),
        "dependency_canary": str(canary),
    }
    process = subprocess.run(
        [sys.executable, str(producer)],
        input=json.dumps(request),
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    output = json.loads(process.stdout)
    output_bytes = (json.dumps(output, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    output_path = external_dir / "context-output.json"
    output_path.write_bytes(output_bytes)
    digest = hashlib.sha256(output_bytes).hexdigest()

    context = helper.context()
    context["resources"][0].update(
        {
            "type": output["proposal"]["resource_type"],
            "basis": "referenced",
            "basis_references": ["EVD-003"],
        }
    )
    invocation = helper.invocation(context=context)
    invocation["inputs"]["evidence"].append(
        {
            "id": "EVD-003",
            "type": "external_output",
            "supports_references": ["CTX-G-003"],
            "source_or_producer": producer_capability,
            "reference": f"external/context-output.json@sha256:{digest}",
            "integrity_or_digest": f"sha256:{digest}",
            "produced_at": "2026-08-30T10:11:12+00:00",
            "sensitivity_or_access": "project-authorized",
        }
    )
    invocation["inputs"]["supporting_members"].append(
        {
            "member_id": "SUP-001",
            "canonical_name": "external/context-output.json",
            "media_type": "application/json",
            "purpose": "Authorized external candidate output; not CTX authority",
            "content": output_bytes.decode("utf-8"),
        }
    )
    result = helper.invoke(invocation)
    EXTERNAL_TRACE.clear()
    EXTERNAL_TRACE.update(
        {
            "producer_returncode": process.returncode,
            "authorization": authorization,
            "producer": producer_capability,
            "dependency": dependency_capability,
            "call_log": output["call_log"],
            "dependency_requested": output["dependency_requested"],
            "dependency_invoked": output["dependency_invoked"],
            "canary_exists": canary.exists(),
            "peer_input_keys": sorted(invocation["inputs"]),
            "external_digest": digest,
            "result_code": result["errors"][0]["code"] if result.get("errors") else None,
            "store_exists": (helper.project_root / ".sdlc").exists(),
        }
    )
    return invocation, result


def copy_runtime(destination: Path, *, include_packages: bool = True) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "skills", destination / "skills")
    if include_packages:
        shutil.copytree(ROOT / "packages", destination / "packages")
    shutil.copytree(ROOT / "scripts", destination / "scripts")
    for manifest in (".cursor-plugin", ".claude-plugin", ".codex-plugin"):
        source = ROOT / manifest
        if source.exists():
            shutil.copytree(source, destination / manifest)
    return destination / "skills/sdlc-000-ctx/scripts/runtime.py"


def cli(runtime_path: Path, invocation: dict[str, Any], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(runtime_path)],
        input=json.dumps(invocation),
        text=True,
        cwd=cwd,
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )


def parse_json(stdout: str) -> dict[str, Any] | None:
    try:
        value = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def eval_trigger_and_input() -> None:
    skill_text = (ROOT / "skills/sdlc-000-ctx/SKILL.md").read_text(encoding="utf-8")
    metadata = (ROOT / "skills/sdlc-000-ctx/agents/openai.yaml").read_text(encoding="utf-8")
    check(
        "EV-T01",
        "disable-model-invocation: true" in skill_text
        and "allow_implicit_invocation: false" in metadata,
        "portable trigger metadata forbids implicit invocation; real client behavior is deferred",
    )
    with fixture() as helper:
        create = helper.invoke(helper.invocation())
        check("EV-T02", create["operation"] == "create", f"operation={create['operation']}")
        reference = f"{create['artifact']['id']}@1"
        revise_invocation = helper.invocation("revise", reference=reference)
        revise_invocation["inputs"]["refresh"] = refresh(None)
        revise_invocation["confirmations"] = [{"type": "write", "approved": True}]
        revised = helper.invoke(revise_invocation)
        check("EV-T03", revised["operation"] == "revise", f"operation={revised['operation']}")
        checked = helper.invoke(helper.invocation("check", reference=reference))
        check("EV-T04", checked["operation"] == "check", f"operation={checked['operation']}")
    with fixture() as helper:
        invocation = helper.invocation()
        invocation["project_root"] = str(helper.project_root / "missing-target")
        before = snapshot(helper.project_root)
        result = helper.invoke(invocation)
        check(
            "EV-I01",
            result["errors"][0]["code"] == "TARGET_AMBIGUOUS"
            and before == snapshot(helper.project_root),
            f"code={result['errors'][0]['code']}; zero_store_access={before == snapshot(helper.project_root)}",
        )
        missing = helper.invoke(helper.invocation("revise", reference=None))
        check("EV-I02", missing["errors"][0]["code"] == "ARTIFACT_REFERENCE_REQUIRED", missing["errors"][0]["code"])
        latest = helper.invoke(helper.invocation("revise", reference="latest"))
        check("EV-I03", latest["errors"][0]["code"] == "ARTIFACT_REFERENCE_INVALID", latest["errors"][0]["code"])
    with fixture() as helper:
        invocation = helper.invocation()
        invocation["confirmations"] = [{"type": "write", "approved": True}]
        before = snapshot(helper.project_root)
        result = helper.invoke(invocation)
        check(
            "EV-I04",
            result["errors"][0]["code"] == "PROJECT_BOUNDARY_CONFIRMATION_REQUIRED"
            and before == snapshot(helper.project_root),
            f"code={result['errors'][0]['code']}; zero_write={before == snapshot(helper.project_root)}",
        )


def eval_create() -> None:
    with fixture() as helper:
        _, result = create_with_confirmation(helper)
        check(
            "EV-C01",
            result["ok"]
            and result["artifact"]["revision_state"] == "frozen"
            and result["artifact"]["artifact_status"] == "ready"
            and result["artifact"]["reference"] is not None,
            f"status={result['status']}; artifact={result['artifact']}; gate={result['gate']['result']}",
        )
    with fixture() as helper:
        context = helper.context()
        context["summary"] = ""
        context["project_identity"].pop("purpose")
        context["resources"] = []
        result = helper.invoke(helper.invocation(context=context))
        check(
            "EV-C02",
            result["status"] == "action_required"
            and result["artifact"]["revision_state"] == "open"
            and result["artifact"]["artifact_status"] == "waiting_input"
            and result["artifact"]["reference"] is None
            and bool(result["open_items"]),
            f"status={result['status']}; open_items={len(result['open_items'])}",
        )
    with fixture() as helper:
        first = helper.invoke(helper.invocation())
        reader = ArtifactStore.open_read_only(helper.project_root)
        before_artifacts = len(ArtifactCatalog(reader).list_artifacts("CTX"))
        second = helper.invoke(helper.invocation())
        after_artifacts = len(ArtifactCatalog(ArtifactStore.open_read_only(helper.project_root)).list_artifacts("CTX"))
        check(
            "EV-C03",
            second["errors"][0]["code"] == "CTX_LINEAGE_EXISTS"
            and second["artifact"]["id"] == first["artifact"]["id"]
            and before_artifacts == after_artifacts == 1,
            f"code={second['errors'][0]['code']}; artifacts={after_artifacts}",
        )
    with fixture() as helper:
        barrier = threading.Barrier(2)

        def concurrent_create() -> dict[str, Any]:
            barrier.wait()
            return helper.invoke(deepcopy(helper.invocation()))

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: concurrent_create(), range(2)))
        ids = {(result.get("artifact") or {}).get("id") for result in results}
        artifacts = ArtifactCatalog(ArtifactStore.open_read_only(helper.project_root)).list_artifacts("CTX")
        normalized_results = sorted(
            (
                result["status"],
                [
                    (item["code"], item["message"])
                    for item in result["errors"]
                ],
            )
            for result in results
        )
        check(
            "EV-C04",
            len(ids) == 1
            and None not in ids
            and len(artifacts) == 1
            and sorted(result["status"] for result in results) == ["action_required", "blocked"],
            f"results={normalized_results}; ids={sorted(str(item) for item in ids)}; artifacts={len(artifacts)}",
        )
    with fixture() as helper:
        before = snapshot(helper.project_root)
        result = helper.invoke(helper.invocation(dry_run=True))
        after = snapshot(helper.project_root)
        check(
            "EV-C05",
            result["ok"] and result["artifact"] is None and before == after,
            f"status={result['status']}; zero_write={before == after}",
        )


def eval_revise_and_check() -> None:
    with fixture() as helper:
        created = helper.invoke(helper.invocation())
        artifact_id = created["artifact"]["id"]
        reference = f"{artifact_id}@1"
        before = ArtifactStore.open_read_only(helper.project_root).read_revision(artifact_id, 1)
        invocation = helper.invocation("revise", reference=reference)
        invocation["inputs"]["refresh"] = refresh(None)
        invocation["confirmations"] = [{"type": "write", "approved": True}]
        result = helper.invoke(invocation)
        after = ArtifactStore.open_read_only(helper.project_root).read_revision(artifact_id, 1)
        revisions = ArtifactCatalog(ArtifactStore.open_read_only(helper.project_root)).list_revisions(artifact_id)
        check(
            "EV-R01",
            result["artifact"]["revision"] == 1
            and len(revisions) == 1
            and after.control.generation == before.control.generation + 1,
            f"revision_count={len(revisions)}; generation={before.control.generation}->{after.control.generation}",
        )
    with fixture() as helper:
        reference, _ = helper.create_and_freeze()
        artifact_id = reference.split("@", 1)[0]
        before = ArtifactStore.open_read_only(helper.project_root).read_revision(artifact_id, 1).payload.primary_blob
        context = helper.context()
        context["project_identity"]["purpose"] = fact("Changed purpose", "confirmed", "EVD-001")
        invocation = helper.invocation("revise", context=context, reference=reference)
        invocation["inputs"]["refresh"] = refresh(1, [f"{reference}#EVD-001"])
        invocation["confirmations"] = [{"type": "write", "approved": True}]
        result = helper.invoke(invocation)
        after = ArtifactStore.open_read_only(helper.project_root).read_revision(artifact_id, 1).payload.primary_blob
        revisions = ArtifactCatalog(ArtifactStore.open_read_only(helper.project_root)).list_revisions(artifact_id)
        check(
            "EV-R02",
            result["artifact"]["revision"] == 2
            and revisions[-1].base_revision == 1
            and before == after,
            f"revision={result['artifact']['revision']}; base={revisions[-1].base_revision}; frozen_unchanged={before == after}",
        )
    with fixture() as helper:
        reference, _ = helper.create_and_freeze()
        invocation = helper.invocation("revise", reference=reference)
        invocation["inputs"]["refresh"] = refresh(1)
        invocation["confirmations"] = [{"type": "write", "approved": True}]
        result = helper.invoke(invocation)
        artifact_id = reference.split("@", 1)[0]
        revisions = ArtifactCatalog(ArtifactStore.open_read_only(helper.project_root)).list_revisions(artifact_id)
        check(
            "EV-R03",
            result["status"] == "completed"
            and result["artifact"]["reference"] == reference
            and len(revisions) == 1
            and result["warnings"][0]["code"] == "NO_EFFECTIVE_CHANGE",
            f"status={result['status']}; revision_count={len(revisions)}",
        )
    with fixture() as helper:
        writer = ArtifactStore.open_read_write(helper.project_root, clock=lambda: FIXED_TIME)
        writer.initialize()
        allocation = writer.allocate_artifact("CTX", now=FIXED_TIME)
        writer.allocate_revision(allocation.artifact_id, now=FIXED_TIME)
        invocation = helper.invocation("revise", reference=f"{allocation.artifact_id}@1")
        invocation["confirmations"] = [{"type": "write", "approved": True}]
        result = helper.invoke(invocation)
        check("EV-R04", result["errors"][0]["code"] == "CONTROL_RESERVATION", result["errors"][0]["code"])
    with fixture() as helper:
        created = helper.invoke(helper.invocation())
        artifact_id = created["artifact"]["id"]
        ArtifactStore.open_read_write(helper.project_root).abandon_revision(artifact_id, 1, reason="formal eval")
        invocation = helper.invocation("revise", reference=f"{artifact_id}@1")
        invocation["confirmations"] = [{"type": "write", "approved": True}]
        result = helper.invoke(invocation)
        check("EV-R05", result["errors"][0]["code"] == "INVALID_STATE", result["errors"][0]["code"])

    with fixture() as helper:
        reference, _ = helper.create_and_freeze()
        before = snapshot(helper.project_root)
        result = helper.invoke(helper.invocation("check", reference=reference))
        after = snapshot(helper.project_root)
        check(
            "EV-K01",
            result["ok"] and result["artifact"]["reference"] == reference and before == after,
            f"gate={result['gate']['result']}; byte_identical={before == after}",
        )
    with fixture() as helper:
        created = helper.invoke(helper.invocation())
        reference = f"{created['artifact']['id']}@1"
        before = snapshot(helper.project_root)
        result = helper.invoke(helper.invocation("check", reference=reference))
        check(
            "EV-K02",
            result["ok"]
            and result["artifact"]["reference"] is None
            and result["warnings"][0]["code"] == "NON_AUTHORITY_STATE"
            and before == snapshot(helper.project_root),
            f"state={result['artifact']['revision_state']}; byte_identical={before == snapshot(helper.project_root)}",
        )
    with fixture() as helper:
        created = helper.invoke(helper.invocation())
        artifact_id = created["artifact"]["id"]
        ArtifactStore.open_read_write(helper.project_root).abandon_revision(artifact_id, 1, reason="formal eval")
        before = snapshot(helper.project_root)
        result = helper.invoke(helper.invocation("check", reference=f"{artifact_id}@1"))
        check(
            "EV-K03",
            result["ok"]
            and result["artifact"]["revision_state"] == "abandoned"
            and result["artifact"]["reference"] is None
            and before == snapshot(helper.project_root),
            f"state={result['artifact']['revision_state']}; authority={result['artifact']['reference']}",
        )
    with fixture() as helper:
        writer = ArtifactStore.open_read_write(helper.project_root, clock=lambda: FIXED_TIME)
        writer.initialize()
        allocation = writer.allocate_artifact("CTX", now=FIXED_TIME)
        writer.allocate_revision(allocation.artifact_id, now=FIXED_TIME)
        before = snapshot(helper.project_root)
        result = helper.invoke(helper.invocation("check", reference=f"{allocation.artifact_id}@1"))
        check(
            "EV-K04",
            result["errors"][0]["code"] == "CONTROL_RESERVATION" and before == snapshot(helper.project_root),
            f"code={result['errors'][0]['code']}; byte_identical={before == snapshot(helper.project_root)}",
        )
    with fixture() as helper:
        before = snapshot(helper.project_root)
        result = helper.invoke(helper.invocation("check", reference="CTX-20260830101112-01@1"))
        check(
            "EV-K05",
            result["errors"][0]["code"] == "STORE_NOT_FOUND"
            and before == snapshot(helper.project_root)
            and not (helper.project_root / ".sdlc").exists(),
            f"code={result['errors'][0]['code']}; zero_write={before == snapshot(helper.project_root)}",
        )
    with fixture() as helper:
        created = helper.invoke(helper.invocation())
        artifact_id = created["artifact"]["id"]
        writer = ArtifactStore.open_read_write(helper.project_root)
        stored = writer.read_revision(artifact_id, 1)
        tampered_primary = stored.payload.primary_blob.replace(
            b"| observed | EVD-002 |", b"| inferred | EVD-002 |", 1
        )
        writer.write_open_revision(
            replace(
                stored.payload,
                primary_blob=tampered_primary,
                primary_sha256=compute_sha256(tampered_primary),
            ),
            expected_generation=stored.control.generation,
        )
        result = helper.invoke(helper.invocation("check", reference=f"{artifact_id}@1"))
        check(
            "EV-K06",
            not result["ok"]
            and result["errors"][0]["code"] == "CTX_DOMAIN_INVALID"
            and "CTX-G-002" in result["gate"]["failed_checks"],
            f"code={result['errors'][0]['code']}; failed_checks={result['gate']['failed_checks']}",
        )


def eval_review_regressions() -> None:
    with fixture() as helper:
        context = helper.context()
        context["resources"] = {
            "none": {"basis": "confirmed", "basis_references": ["EVD-001"]}
        }
        result = helper.invoke(helper.invocation(context=context))
        check(
            "EV-REV001",
            not result["ok"]
            and result["errors"][0]["code"] == "CTX_CONTENT_INVALID"
            and not (helper.project_root / ".sdlc").exists(),
            f"code={result['errors'][0]['code']}; store_created={(helper.project_root / '.sdlc').exists()}",
        )

    with fixture() as helper:
        reference_one, _ = helper.create_and_freeze()
        artifact_id = reference_one.split("@", 1)[0]
        context_two = helper.context()
        context_two["project_identity"]["purpose"] = fact(
            "Formal Eval revision two", "confirmed", "EVD-001"
        )
        revise_two = helper.invocation(
            "revise", context=context_two, reference=reference_one
        )
        revise_two["inputs"]["refresh"] = refresh(
            1, [f"{reference_one}#EVD-001"]
        )
        revise_two["confirmations"] = [{"type": "write", "approved": True}]
        open_two = helper.invoke(revise_two)
        reference_two = f"{artifact_id}@2"
        frozen_two = helper.finalize_open(
            reference_two, context_two, revise_two["inputs"]["refresh"]
        )

        context_three = helper.context()
        context_three["project_identity"]["purpose"] = fact(
            "Formal Eval revision three from revision one", "confirmed", "EVD-001"
        )
        revise_three = helper.invocation(
            "revise", context=context_three, reference=reference_one
        )
        revise_three["inputs"]["refresh"] = refresh(
            1, [f"{reference_one}#EVD-001"]
        )
        revise_three["confirmations"] = [{"type": "write", "approved": True}]
        open_three = helper.invoke(revise_three)
        reader = ArtifactStore.open_read_only(helper.project_root)
        controls = ArtifactCatalog(reader).list_revisions(artifact_id)
        stored_three = reader.read_revision(artifact_id, 3)
        check(
            "EV-REV002-MAX",
            open_two["artifact"]["revision"] == 2
            and frozen_two["ok"]
            and open_three["artifact"]["revision"] == 3
            and stored_three.control.base_revision == 1
            and b"revision: 3\n" in stored_three.payload.primary_blob
            and [item.revision for item in controls] == [1, 2, 3],
            f"revisions={[item.revision for item in controls]}; base={stored_three.control.base_revision}; materialized={stored_three.control.materialized}",
        )

    with fixture() as helper:
        reference, _ = helper.create_and_freeze()
        artifact_id = reference.split("@", 1)[0]
        changed = helper.context()
        changed["project_identity"]["purpose"] = fact(
            "Formal Eval post-allocation failure", "confirmed", "EVD-001"
        )
        invocation = helper.invocation("revise", context=changed, reference=reference)
        invocation["inputs"]["refresh"] = refresh(
            1, [f"{reference}#EVD-001"]
        )
        invocation["confirmations"] = [{"type": "write", "approved": True}]
        original = runtime.build_payload
        calls = 0

        def fail_after_allocation(*args: Any, **kwargs: Any) -> Any:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("formal fixture post-allocation failure")
            return original(*args, **kwargs)

        runtime.build_payload = fail_after_allocation
        try:
            failed = helper.invoke(invocation)
        finally:
            runtime.build_payload = original
        controls = ArtifactCatalog(
            ArtifactStore.open_read_only(helper.project_root)
        ).list_revisions(artifact_id)
        check(
            "EV-REV002-CLEANUP",
            not failed["ok"]
            and controls[-1].state == "abandoned"
            and not controls[-1].materialized
            and not any(item.state == "open" for item in controls),
            f"result={failed['status']}; controls={[(item.revision, item.state, item.materialized) for item in controls]}",
        )

    with fixture() as helper:
        invocation = helper.invocation()
        invocation["inputs"]["supporting_members"] = [
            {
                "member_id": "SUP-001",
                "canonical_name": "evidence/context.txt",
                "media_type": "text/plain",
                "purpose": "Formal peer-input evidence",
                "content": "formal fixture\n",
            }
        ]
        created = helper.invoke(invocation)
        stored = ArtifactStore.open_read_only(helper.project_root).read_revision(
            created["artifact"]["id"], 1
        )
        check(
            "EV-REV006-PEER",
            sorted(invocation["inputs"])
            == ["context", "evidence", "supporting_members"]
            and [item.member_id for item in stored.payload.members] == ["SUP-001"]
            and b"EVD-001" in stored.payload.primary_blob,
            f"input_keys={sorted(invocation['inputs'])}; members={[item.member_id for item in stored.payload.members]}",
        )
    with fixture() as helper:
        nested = helper.invocation()
        nested["inputs"]["context"]["evidence"] = deepcopy(
            nested["inputs"]["evidence"]
        )
        nested["inputs"]["context"]["supporting_members"] = []
        result = helper.invoke(nested)
        check(
            "EV-REV006-NESTED",
            not result["ok"]
            and result["errors"][0]["code"] == "CTX_CONTENT_INVALID"
            and not (helper.project_root / ".sdlc").exists(),
            f"code={result['errors'][0]['code']}; store_created={(helper.project_root / '.sdlc').exists()}",
        )


def eval_domain() -> None:
    with fixture() as helper:
        _, result = create_with_confirmation(helper, exceptions=[active_exception()])
        check(
            "EV-D01",
            result["ok"]
            and result["gate"]["result"] == "pass_with_exception"
            and result["artifact"]["artifact_status"] == "ready_with_exception",
            f"gate={result['gate']['result']}; status={result['artifact']['artifact_status']}",
        )
    with fixture() as helper:
        _, result = create_with_confirmation(helper, mode="delegated")
        check(
            "EV-D02",
            result["ok"]
            and result["gate"]["result"] == "pass"
            and result["artifact"]["artifact_status"] == "ready",
            f"gate={result['gate']['result']}; status={result['artifact']['artifact_status']}",
        )
    for case_id, variant in (
        ("EV-D02-N01", "missing_decided_at"),
        ("EV-D02-N02", "imprecise_fixed_set"),
        ("EV-D02-N03", "invalid_delegation_basis"),
    ):
        with fixture() as helper:
            _, result = create_with_confirmation(
                helper, mode="delegated", delegated_variant=variant
            )
            check(
                case_id,
                not result["ok"]
                and result["status"] == "action_required"
                and result["artifact"]["revision_state"] == "open"
                and result["artifact"]["reference"] is None,
                f"variant={variant}; status={result['status']}; state={result['artifact']['revision_state']}",
            )
    with fixture() as helper:
        invocation, result = external_conflict_invocation(helper)
        check(
            "EV-D03",
            not result["ok"]
            and result["status"] == "failed"
            and result["errors"][0]["code"] == "CTX_CONTENT_INVALID"
            and sorted(invocation["inputs"])
            == ["context", "evidence", "supporting_members"]
            and not EXTERNAL_TRACE["store_exists"],
            f"status={result['status']}; code={result['errors'][0]['code']}; external_digest={EXTERNAL_TRACE['external_digest']}; zero_store={not EXTERNAL_TRACE['store_exists']}",
            deepcopy(EXTERNAL_TRACE),
        )
    expected = {
        "docs/v1.1/core-spec.md@sha256:1eefa7a138f2d221140137a5fac0f5429b7f847273fe9d70e891ace6c3b7a89b",
        "docs/v1.1/artifact-store-spec.md@sha256:b340ca2a38dfe0f7409acaa8f9ac559e8872bed44725037889528e3d167d4764",
        "docs/v1.1/000-ctx-spec.md@sha256:1d98e7cce686664cbf9897cbac852c425644ba3ea81a0d9c1db5e27b0e530470",
    }
    check("EV-D04", set(runtime.SPEC_REFERENCES) == expected, f"references={len(runtime.SPEC_REFERENCES)}")


def eval_runtime_and_source() -> None:
    lock = json.loads((ROOT / "skills/sdlc-000-ctx/references/source-lock.json").read_text(encoding="utf-8"))
    runtime._verify_bundled_source_lock()
    check(
        "EV-S01",
        len(lock["contracts"]) == 8
        and [item["contract_id"] for item in lock["contracts"]]
        == sorted(item["contract_id"] for item in lock["contracts"]),
        f"contract_count={len(lock['contracts'])}; exact_runtime_verification=pass",
    )
    with tempfile.TemporaryDirectory() as temporary:
        base = Path(temporary)
        plugin = base / "drift-plugin"
        runtime_path = copy_runtime(plugin)
        contract = plugin / "skills/_shared/contracts/skill-execution.md"
        contract.write_text(contract.read_text(encoding="utf-8") + "\nfixture drift\n", encoding="utf-8")
        project = base / "project"
        project.mkdir()
        invocation = {
            "contract": "sdlc-ai-spec/runtime-invocation/v1",
            "operation": "check",
            "project_root": str(project),
            "artifact_reference": "CTX-20260830101112-01@1",
            "inputs": {},
            "confirmations": [],
            "options": {"dry_run": False},
        }
        result = parse_json(cli(runtime_path, invocation, cwd=base).stdout)
        check(
            "EV-S02",
            result is not None and result["errors"][0]["code"] == "SOURCE_LOCK_INVALID",
            f"result_code={result['errors'][0]['code'] if result else 'NO_STRUCTURED_RESULT'}",
        )
    with tempfile.TemporaryDirectory() as temporary:
        base = Path(temporary)
        plugin = base / "no-docs-plugin"
        runtime_path = copy_runtime(plugin)
        project = base / "project"
        project.mkdir()
        with fixture() as helper:
            invocation = helper.invocation()
            invocation["project_root"] = str(project)
            created = parse_json(cli(runtime_path, invocation, cwd=base).stdout)
            assert created is not None
            reference = f"{created['artifact']['id']}@1"
            revise = helper.invocation("revise", reference=reference, dry_run=True)
            revise["project_root"] = str(project)
            revise["inputs"]["refresh"] = refresh(None)
            preview = parse_json(cli(runtime_path, revise, cwd=base).stdout)
            assert preview is not None
            bindings = next(item["details"] for item in preview["warnings"] if item["code"] == "FINAL_CONFIRMATION_BINDINGS")
            authority_dir = project / "authority"
            authority_dir.mkdir()
            authority_text = "\n".join(
                [
                    f"artifact: {reference}",
                    f"control: {bindings['control_input_digest']}",
                    f"contracts: {bindings['evaluation_contract_set']}",
                    f"checks: {bindings['check_set_result_digest']}",
                    "decision: approved",
                ]
            ) + "\n"
            authority_path = authority_dir / "confirmation.txt"
            authority_path.write_text(authority_text, encoding="utf-8")
            authority_reference = "authority/confirmation.txt@sha256:" + hashlib.sha256(authority_text.encode("utf-8")).hexdigest()
            revise["options"]["dry_run"] = False
            revise["confirmations"] = [
                {"type": "write", "approved": True},
                {
                    "type": "final_confirmation",
                    "result": "approved",
                    "mode": "human",
                    "confirmer": "project-owner",
                    "role": "Project Maintainer",
                    "authority_reference": authority_reference,
                    "accepted_exception_references": [],
                    "confirmed_at": "2026-08-30T10:11:12+00:00",
                    **bindings,
                },
            ]
            revised = parse_json(cli(runtime_path, revise, cwd=base).stdout)
            checked = parse_json(
                cli(
                    runtime_path,
                    {
                        "contract": "sdlc-ai-spec/runtime-invocation/v1",
                        "operation": "check",
                        "project_root": str(project),
                        "artifact_reference": reference,
                        "inputs": {},
                        "confirmations": [],
                        "options": {"dry_run": False},
                    },
                    cwd=base,
                ).stdout
            )
        check(
            "EV-S03",
            not (plugin / "docs").exists()
            and created["status"] == "action_required"
            and revised is not None
            and revised["ok"]
            and checked is not None
            and checked["ok"],
            f"docs_present={(plugin / 'docs').exists()}; create={created['status']}; revise={revised['status'] if revised else None}; check={checked['status'] if checked else None}",
        )
        missing_project = base / "missing-store"
        missing_project.mkdir()
        different_cwd = base / "different-cwd"
        different_cwd.mkdir()
        invocation = {
            "contract": "sdlc-ai-spec/runtime-invocation/v1",
            "operation": "check",
            "project_root": str(missing_project),
            "artifact_reference": "CTX-20260830101112-01@1",
            "inputs": {},
            "confirmations": [],
            "options": {"dry_run": False},
        }
        result = parse_json(cli(runtime_path, invocation, cwd=different_cwd).stdout)
        check(
            "EV-S04",
            result is not None and result["errors"][0]["code"] == "STORE_NOT_FOUND",
            f"cwd={different_cwd.name}; result_code={result['errors'][0]['code'] if result else 'NO_STRUCTURED_RESULT'}",
        )
    with tempfile.TemporaryDirectory() as temporary:
        base = Path(temporary)
        plugin = base / "missing-foundation-plugin"
        runtime_path = copy_runtime(plugin, include_packages=False)
        project = base / "project"
        project.mkdir()
        invocation = {
            "contract": "sdlc-ai-spec/runtime-invocation/v1",
            "operation": "check",
            "project_root": str(project),
            "artifact_reference": "CTX-20260830101112-01@1",
            "inputs": {},
            "confirmations": [],
            "options": {"dry_run": False},
        }
        process = cli(runtime_path, invocation, cwd=base)
        result = parse_json(process.stdout)
        structured_foundation_error = (
            result is not None
            and not result.get("ok", True)
            and result.get("errors")
            and result["errors"][0]["code"]
            in {"FOUNDATION_RUNTIME_UNAVAILABLE", "SOURCE_LOCK_INVALID"}
            and "Traceback" not in process.stderr
        )
        check(
            "EV-S05",
            structured_foundation_error,
            f"returncode={process.returncode}; structured={result is not None}; traceback={'Traceback' in process.stderr}",
        )
    runtime_files = [
        path
        for root in (ROOT / "skills/sdlc-000-ctx", ROOT / "packages", ROOT / "scripts")
        for path in root.rglob("*")
        if path.is_file() and path.suffix in {".py", ".md", ".json", ".yaml"}
    ]
    target_runtime_text = (ROOT / "skills/sdlc-000-ctx/scripts/runtime.py").read_text(encoding="utf-8")
    docs_reads = [
        str(path.relative_to(ROOT))
        for path in runtime_files
        if "docs/v1." in path.read_text(encoding="utf-8", errors="ignore")
        and path.suffix == ".py"
    ]
    check(
        "EV-S06",
        not docs_reads
        and "sqlite3" not in target_runtime_text
        and ".execute(" not in target_runtime_text,
        f"python_docs_path_hits={docs_reads}; direct_sql={'.execute(' in target_runtime_text}",
    )


def eval_comparison_exclusive_and_clients() -> None:
    for case_id in ("EV-W01-C01", "EV-W02-C02", "EV-W03-R01", "EV-W04-K05"):
        record(
            case_id,
            "NOT_RUN",
            "without-skill ordinary-Agent execution was not available inside this exclusive work-package session; no result was fabricated",
        )
    target_files = [path for path in (ROOT / "skills/sdlc-000-ctx").rglob("*") if path.is_file()]
    target_text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in target_files)
    check(
        "EV-X01",
        "subprocess" not in target_text
        and "skills/sdlc-100" not in target_text
        and "skills/sdlc-200" not in target_text,
        "no sibling Skill invocation path in the bundled target Skill",
    )
    check(
        "EV-X02",
        EXTERNAL_TRACE.get("producer_returncode") == 0
        and EXTERNAL_TRACE.get("authorization") == [EXTERNAL_TRACE.get("producer")]
        and EXTERNAL_TRACE.get("dependency_requested")
        == EXTERNAL_TRACE.get("dependency")
        and not EXTERNAL_TRACE.get("dependency_invoked")
        and EXTERNAL_TRACE.get("call_log") == [EXTERNAL_TRACE.get("producer")]
        and not EXTERNAL_TRACE.get("canary_exists")
        and EXTERNAL_TRACE.get("peer_input_keys")
        == ["context", "evidence", "supporting_members"]
        and EXTERNAL_TRACE.get("result_code") == "CTX_CONTENT_INVALID",
        "authorized producer executed once; requested dependency received no delegated authorization and wrote no canary; output stayed in peer Evidence/Supporting Member and its conflicting proposal was rejected",
        deepcopy(EXTERNAL_TRACE),
    )
    for case_id, client in (
        ("EV-P01", "Cursor"),
        ("EV-P02", "Claude Code"),
        ("EV-P03", "Codex"),
    ):
        record(
            case_id,
            "DEFERRED",
            f"{client} Discovery/Invocation/Behavior not executed in evaluate; dedicated client evidence belongs to adapt-codex or an explicitly authorized future client stage",
        )


def main() -> int:
    eval_trigger_and_input()
    eval_create()
    eval_revise_and_check()
    eval_review_regressions()
    eval_domain()
    eval_runtime_and_source()
    eval_comparison_exclusive_and_clients()
    counts = {
        status: sum(item["status"] == status for item in RESULTS)
        for status in ("PASS", "FAIL", "NOT_RUN", "DEFERRED")
    }
    output = {
        "contract": "sdlc-ai-spec/sdlc-000-ctx-eval-results/v1",
        "fixed_time": FIXED_TIME.isoformat(),
        "case_count": len(RESULTS),
        "counts": counts,
        "cases": RESULTS,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if counts["FAIL"] == 0 and counts["NOT_RUN"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

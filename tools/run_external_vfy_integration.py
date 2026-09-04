#!/usr/bin/env python3
"""Run real CTX→REQ→DSN→PLN→IMP→VFY probes at two fixed Git SHAs."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import traceback
from typing import Any, Callable, Mapping


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
VFY_SCRIPTS = ROOT / "skills/sdlc-500-vfy/scripts"
STATUS_RUNTIME_PATH = ROOT / "skills/sdlc-status/scripts/runtime.py"
for entry in (ROOT, ROOT / "packages", TOOLS, VFY_SCRIPTS):
    value = str(entry)
    if value not in sys.path:
        sys.path.insert(0, value)

import run_external_imp_integration as upstream  # noqa: E402
from packages.sdlc_artifact_store import ArtifactStore, compute_sha256  # noqa: E402
from packages.sdlc_lifecycle import LifecycleQueryService  # noqa: E402
from packages.sdlc_runtime import parse_canonical_artifact  # noqa: E402
from packages.sdlc_runtime.authority import (  # noqa: E402
    DELEGATED_AUTHORITY_HEADERS,
    DELEGATED_EXCLUDED_AUTHORITY,
    DELEGATED_INDEPENDENCE,
)
from vfy_handler import VfyHandler  # noqa: E402


FIXED_PROJECTS = (
    {
        "name": "springgear",
        "repository": "ousui/springgear",
        "sha": "e855096ff19dcdb303dc4250ba19c30acd743ac7",
    },
    {
        "name": "gin-vue-admin",
        "repository": "flipped-aurora/gin-vue-admin",
        "sha": "a6882210a80bb27e3aa5dff0b4c21aa4afe8988a",
    },
)
VFY_EXECUTOR = "external-vfy-executor"
VFY_REVIEWER = "external-vfy-independent-reviewer"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


status_runtime = _load_module("external_vfy_status_runtime", STATUS_RUNTIME_PATH)


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def canonical_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


class Log:
    def __init__(self, path: Path):
        self.path = path
        self.lines: list[str] = []

    def add(self, message: str) -> None:
        line = f"[{utc_now()}] {message}"
        self.lines.append(line)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        print(line, flush=True)

    def receipt(self) -> dict[str, Any]:
        raw = self.path.read_bytes() if self.path.is_file() else b""
        return {
            "path": self.path.name,
            "sha256": "sha256:" + hashlib.sha256(raw).hexdigest(),
            "line_count": len(self.lines),
        }


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _command(
    arguments: list[str],
    *,
    cwd: Path,
    timeout: int = 900,
) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    started_at = utc_now()
    started = time.monotonic()
    completed = subprocess.run(
        arguments,
        cwd=cwd,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0"},
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        timeout=timeout,
    )
    finished_at = utc_now()
    receipt = {
        "command": arguments,
        "cwd": ".",
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_ms": int((time.monotonic() - started) * 1000),
        "exit_code": completed.returncode,
        "stdout_sha256": canonical_digest(completed.stdout),
        "stderr_sha256": canonical_digest(completed.stderr),
    }
    return completed, receipt


def clone_exact_once(
    destination: Path,
    repository: str,
    expected_sha: str,
    log: Log,
) -> list[dict[str, Any]]:
    """Perform exactly one clone attempt; retry policy belongs to the controller."""

    url = f"https://github.com/{repository}.git"
    log.add(f"{repository}: clone attempt 1/1")
    clone, clone_receipt = _command(
        ["git", "clone", "--no-checkout", url, destination.name],
        cwd=destination.parent,
    )
    clone_receipt.update(kind="clone", repository=repository, attempt=1)
    if clone.returncode != 0:
        detail = clone.stderr.strip()[-4000:]
        raise upstream.IntegrationError(
            f"{repository}: one clone attempt failed: {detail}"
        )
    checkout, checkout_receipt = _command(
        ["git", "-C", destination.name, "checkout", "--detach", expected_sha],
        cwd=destination.parent,
    )
    checkout_receipt.update(kind="checkout", repository=repository, attempt=1)
    if checkout.returncode != 0:
        detail = checkout.stderr.strip()[-4000:]
        raise upstream.IntegrationError(
            f"{repository}: exact fixed SHA checkout failed: {detail}"
        )
    actual = upstream._git(destination, "rev-parse", "HEAD")
    if actual != expected_sha:
        raise upstream.IntegrationError(
            f"{repository}: expected {expected_sha}, got {actual}"
        )
    log.add(f"{repository}: exact fixed SHA checked out")
    return [clone_receipt, checkout_receipt]


def repository_snapshot(root: Path) -> dict[str, Any]:
    state = upstream._git_state(root)
    mode_rows = [
        [item["path"], item["kind"], item["mode"]]
        for item in state["workspace"]["files"]
    ]
    status = bytes.fromhex(state["status_hex"])
    refs = bytes.fromhex(state["refs_hex"])
    return {
        "head": state["head"],
        "status_hex": state["status_hex"],
        "status_sha256": "sha256:" + hashlib.sha256(status).hexdigest(),
        "refs_sha256": "sha256:" + hashlib.sha256(refs).hexdigest(),
        "tracked_untracked_sha256": state["workspace"]["sha256"],
        "file_mode_sha256": canonical_digest(mode_rows),
        "file_count": len(mode_rows),
        "sdlc_exists": (root / ".sdlc").exists(),
    }


def _phase_call(
    phase: str,
    callable_name: str,
    operation: Callable[[], Any],
    receipts: list[dict[str, Any]],
    log: Log,
) -> Any:
    started_at = utc_now()
    started = time.monotonic()
    log.add(f"{phase}: execute {callable_name}")
    try:
        result = operation()
    except Exception:
        receipts.append(
            {
                "phase": phase,
                "execution": "in_process_runtime_handler",
                "callable": callable_name,
                "started_at": started_at,
                "finished_at": utc_now(),
                "duration_ms": int((time.monotonic() - started) * 1000),
                "exit_code": 1,
                "output_digest": None,
            }
        )
        raise
    receipts.append(
        {
            "phase": phase,
            "execution": "in_process_runtime_handler",
            "callable": callable_name,
            "started_at": started_at,
            "finished_at": utc_now(),
            "duration_ms": int((time.monotonic() - started) * 1000),
            "exit_code": 0,
            "output_digest": canonical_digest(result),
        }
    )
    return result


def _vfy_strategy(requirement_reference: str, target_path: str) -> str:
    acceptance = requirement_reference + "#AC-001"
    return (
        "## 设计结果 Design Result\n\n"
        "### VFY 目标 VFY Objectives\n\n"
        "| ID | Kind | Requirement, AC, Goal or Intended-use References | Design or Decision References | Domain VFY Point References | 可观察结果 Observable Result | 风险或重要性 Risk or Importance | Method References | Pass Criteria References | Evidence Contract References |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
        f"| VFO-001 | both | {acceptance} | CHG-001 | VFP-210-001, VFP-220-001 | {target_path} contains the exact completed IMP marker | required | VFM-001, VFM-002 | VPC-001 | VEC-001 |\n\n"
        "### 方法选择 VFY Methods\n\n"
        "| ID | 类型 Type | Disposition | 方法明细 Method Detail | 适用范围 Scope | 方法 Method | 选择依据 Selection Basis | 承载位置 Host | Exception Reference |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
        f"| VFM-001 | inspection | required | Inspect {target_path} | VFO-001 | file_exists | direct repository fact | VFY | None |\n"
        f"| VFM-002 | analysis | required | Analyze {target_path} digest | VFO-001 | sha256_equals | immutable result comparison | VFY | None |\n\n"
        "### 环境与数据 Environment and Data\n\n"
        "| VFY Objective | 环境 Environment | Dependencies | 数据 Data | 隔离与重置 Isolation and Reset | Sensitivity Reference |\n"
        "|---|---|---|---|---|---|\n"
        "| VFO-001 | disposable exact-SHA checkout | none installed | tracked README | restore bytes and mode; remove .sdlc | public |\n\n"
        "### 覆盖策略 Coverage Strategy\n\n"
        "| 范围或风险 Scope or Risk | 正常 Normal | 异常 Exception | 边界 Boundary | 兼容或质量属性 Compatibility or Quality Attribute | 排除项及原因 Exclusion and Reason |\n"
        "|---|---|---|---|---|---|\n"
        "| completed IMP Result | exists and digest matches | mismatch fails closed | exact Result Subject | deterministic | dependency installation and release excluded |\n\n"
        "### 通过条件 Pass Criteria\n\n"
        "| ID | VFY Objective | 输入或条件 Input or Condition | 预期结果 Expected Result | 容差 Tolerance | 失败条件 Failure Condition |\n"
        "|---|---|---|---|---|---|\n"
        f"| VPC-001 | VFO-001 | current completed IMP Result | {target_path} exists and its SHA-256 matches | exact | missing path or digest mismatch |\n\n"
        "### Evidence Contract\n\n"
        "| ID | VFY Objective | Evidence Type | 生成方或来源 Producer or Source | 必要内容 Required Content | 敏感性与处理 Sensitivity and Handling | 保留要求 Retention Requirement | 保存或引用位置 Storage or Reference |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| VEC-001 | VFO-001 | observation | VFY automated executor | exact Subject, path and digest | public | retained in frozen VFY | VFY Evidence Set |\n\n"
        "### 限制与例外 Limitations and Exceptions\n\n"
        "| VFY Objective | 限制 Limitation | 未覆盖风险 Uncovered Risk | 缓解 Mitigation | Exception Reference |\n"
        "|---|---|---|---|---|\n"
        "| VFO-001 | no human UX claim | subjective usability is not asserted | deterministic inspection and analysis only | None |"
    )


@contextmanager
def _external_design_with_vfy_strategy():
    original = upstream._design_candidate

    def replacement(
        root: Path,
        requirement_reference: str,
        project_label: str,
        expected_sha: str,
        readme: bytes,
        resource_root: str,
    ) -> dict[str, Any]:
        design = original(
            root,
            requirement_reference,
            project_label,
            expected_sha,
            readme,
            resource_root,
        )
        target_path = (
            "README.md" if resource_root == "." else f"{resource_root}/README.md"
        )
        design["domains"]["DOM-510"]["design_result_markdown"] = _vfy_strategy(
            requirement_reference, target_path
        )
        return design

    upstream._design_candidate = replacement
    try:
        yield
    finally:
        upstream._design_candidate = original


def _delegated_confirmation(
    root: Path,
    handler: VfyHandler,
    state: Mapping[str, Any],
) -> dict[str, Any]:
    bindings = handler.confirmation_requirements(state)
    authority_dir = root / ".sdlc/authority"
    authority_dir.mkdir(parents=True, exist_ok=True)
    basis = authority_dir / "vfy-delegation-basis.txt"
    basis.write_text(
        "The independent test reviewer may confirm deterministic VFY contract compliance; human experience judgment is excluded.\n",
        encoding="utf-8",
    )
    basis_reference = (
        basis.relative_to(root).as_posix() + "@" + compute_sha256(basis.read_bytes())
    )
    values = (
        basis_reference,
        VFY_REVIEWER,
        "Delegated Independent Reviewer",
        VFY_EXECUTOR,
        DELEGATED_INDEPENDENCE,
        bindings["control_input_digest"],
        bindings["evaluation_contract_set"],
        bindings["check_set_result_digest"],
        DELEGATED_EXCLUDED_AUTHORITY,
    )
    raw = (
        "\n".join(
            (
                "---",
                "contract: sdlc-ai-spec/final-confirmation-authority/v1",
                f"artifact: {state['artifact']['reference']}",
                "decision: approved",
                f"decided_at: {upstream.FIXED_TEXT}",
                "---",
                "",
                "| " + " | ".join(DELEGATED_AUTHORITY_HEADERS) + " |",
                "|" + "|".join("---" for _ in DELEGATED_AUTHORITY_HEADERS) + "|",
                "| " + " | ".join(values) + " |",
            )
        )
        + "\n"
    ).encode("utf-8")
    authority = authority_dir / "vfy-delegated-confirmation.md"
    authority.write_bytes(raw)
    return {
        "mode": "delegated",
        "confirmer": VFY_REVIEWER,
        "role": "Delegated Independent Reviewer",
        "reviewed_executor": VFY_EXECUTOR,
        "authority_reference": authority.relative_to(root).as_posix()
        + "@"
        + compute_sha256(raw),
        "accepted_exception_references": [],
        "confirmed_at": upstream.FIXED_TEXT,
        **bindings,
    }


def _candidate_from_lifecycle(
    *,
    root: Path,
    project_label: str,
    context_reference: str,
    design_reference: str,
    plan_reference: str,
    plan_candidate: Mapping[str, Any],
    projection,
    target_path: str,
) -> dict[str, Any]:
    claims = [item for item in projection.current_claims if item.completed and item.vfy_ready]
    if len(claims) != 1 or not claims[0].results:
        raise upstream.IntegrationError(
            "VFY requires one exact Current completed IMP Claim with Results"
        )
    claim = claims[0]
    subjects = [
        {
            "reference": result["result_reference"],
            "resource_id": result["resource"],
            "imp_revision_reference": claim.artifact_reference,
            "binding_lineage": claim.binding_lineage,
            "attempt": str(claim.attempt),
            "claim_state": claim.claim_state,
            "imp_revision_state": claim.revision_state,
            "baseline_reference": result["baseline_reference"],
            "result_digest": result["result_digest"],
            "cumulative_changed_scope": list(result["changed_scope"]),
            "dependency_result_references": list(claim.dependency_results),
            "current_valid": True,
            "dependency_chain_valid": True,
        }
        for result in claim.results
    ]
    subject_refs = [item["reference"] for item in subjects]
    result_resources = [item["resource_id"] for item in subjects]
    vfy_item = next(
        item for item in plan_candidate["work_items"] if item["target_phase"] == "VFY"
    )
    rls = next(
        item
        for item in plan_candidate["aggregated_applicability"]
        if item["phase"] == "RLS"
    )
    if rls["disposition"] != "n/a":
        raise upstream.IntegrationError("external VFY requires authoritative RLS n/a")
    target = design_reference + "#VFO-001"
    vfp_210 = design_reference + "#VFP-210-001"
    vfp_220 = design_reference + "#VFP-220-001"
    binding = claim.binding_reference
    expected = "sha256:" + hashlib.sha256((root / target_path).read_bytes()).hexdigest()
    return {
        "contract": "sdlc-ai-spec/vfy-candidate/v1",
        "context_reference": context_reference,
        "profile": "full",
        "title": f"{project_label} exact IMP Result verification",
        "scope": {
            "reference": plan_reference,
            "disposition": "required",
            "delivery_scope": sorted(claim.execution_scope),
            "input_references": [context_reference],
            "imp_work_items": [
                {
                    "reference": binding,
                    "target_phase": "IMP",
                    "binding_reference": binding,
                    "resource_ids": result_resources,
                    "depends_on": [],
                }
            ],
        },
        "subjects": subjects,
        "targets": [
            {
                "reference": target,
                "purpose": "both",
                "summary": f"{target_path} contains the exact completed IMP marker",
                "source_kind": "vfo",
                "obligation_references": [vfp_210, vfp_220],
            }
        ],
        "methods": [
            {
                "id": "VFM-001",
                "title": "Inspect exact completed Result path",
                "purpose": "verification",
                "target_references": [target],
                "subject_references": subject_refs,
                "obligation_references": [vfp_210, binding,
                    design_reference + "#VFM-001", design_reference + "#VPC-001",
                    design_reference + "#VEC-001", plan_reference + "#" + vfy_item["id"]],
                "method_type": "inspection",
                "disposition": "required",
                "execution_mode": "automated",
                "executor_identity": VFY_EXECUTOR,
                "procedure": {"kind": "file_exists", "path": target_path},
                "pass_criteria": f"{target_path} exists in the exact IMP product state",
                "evidence_requirement": "Immutable path observation",
            },
            {
                "id": "VFM-002",
                "title": "Analyze exact completed Result digest",
                "purpose": "validation",
                "target_references": [target],
                "subject_references": subject_refs,
                "obligation_references": [vfp_220, binding,
                    design_reference + "#VFM-002", design_reference + "#VPC-001",
                    design_reference + "#VEC-001", plan_reference + "#" + vfy_item["id"]],
                "method_type": "analysis",
                "disposition": "required",
                "execution_mode": "automated",
                "executor_identity": VFY_EXECUTOR,
                "procedure": {
                    "kind": "sha256_equals",
                    "path": target_path,
                    "expected": expected,
                },
                "pass_criteria": "The exact current product digest matches",
                "evidence_requirement": "Immutable SHA-256 observation",
            },
        ],
        "required_obligation_references": sorted([
            vfp_210, vfp_220, binding, design_reference + "#VFM-001",
            design_reference + "#VFM-002", design_reference + "#VPC-001",
            design_reference + "#VEC-001", plan_reference + "#" + vfy_item["id"],
        ]),
        "control_inputs": [],
        "returns": [],
        "rls_applicability": "n/a",
        "release_target_obligations": [],
    }


def _vfy_phase_record(root: Path, reference: str) -> dict[str, Any]:
    artifact_id, revision_text = reference.split("@", 1)
    if not artifact_id.startswith("VFY-") or not revision_text.isdigit():
        raise upstream.IntegrationError(f"invalid VFY reference: {reference}")
    stored = ArtifactStore.open_read_only(root).read_revision(
        artifact_id, int(revision_text)
    )
    return {
        "reference": reference,
        "id_pattern": "VFY-14digits-NN",
        "revision": stored.control.revision,
        "revision_state": stored.control.state,
        "artifact_status": stored.payload.artifact_status,
        "base_revision": stored.control.base_revision,
        "materialized": stored.control.materialized,
        "primary_sha256": stored.payload.primary_sha256,
        "shape": upstream._artifact_shape(stored),
        "gate": upstream._artifact_gate(stored),
    }


def run_project(
    root: Path,
    *,
    name: str,
    repository: str,
    expected_sha: str,
    log: Log,
    command_receipts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run one complete probe in an existing disposable exact checkout."""

    root = root.resolve()
    if not (root / ".git").exists():
        raise upstream.IntegrationError("external project must be a Git checkout")
    initial_state = upstream._git_state(root)
    initial = repository_snapshot(root)
    if initial["head"] != expected_sha:
        raise upstream.IntegrationError(
            f"{repository}: HEAD mismatch: expected {expected_sha}, got {initial['head']}"
        )
    if initial["status_hex"] or initial["sdlc_exists"]:
        raise upstream.IntegrationError(
            f"{repository}: external checkout must start clean without .sdlc"
        )
    resource_root = upstream._select_resource_root(root)
    resource_path = root if resource_root == "." else root / resource_root
    readme = resource_path / "README.md"
    if not readme.is_file() or readme.is_symlink():
        raise upstream.IntegrationError("external probe requires one regular README.md")
    original_readme = readme.read_bytes()
    original_mode = stat.S_IMODE(readme.stat().st_mode)
    runtime_dir = root / ".sdlc"
    receipts: list[dict[str, Any]] = []
    output: dict[str, Any] | None = None
    try:
        context_reference, context_candidate = _phase_call(
            "CTX",
            "external_imp._create_context",
            lambda: upstream._create_context(
                root,
                repository,
                expected_sha,
                initial_state["workspace"]["sha256"],
            ),
            receipts,
            log,
        )
        requirement_reference, requirement_candidate = _phase_call(
            "REQ",
            "external_imp._create_requirement",
            lambda: upstream._create_requirement(
                root,
                context_reference,
                repository,
                expected_sha,
                resource_root,
            ),
            receipts,
            log,
        )
        target_path = (
            "README.md" if resource_root == "." else f"{resource_root}/README.md"
        )
        with _external_design_with_vfy_strategy():
            design_reference, design_candidate = _phase_call(
                "DSN",
                "external_imp._create_design",
                lambda: upstream._create_design(
                    root,
                    context_reference,
                    requirement_reference,
                    repository,
                    expected_sha,
                    original_readme,
                    resource_root,
                ),
                receipts,
                log,
            )
        plan_reference, plan_candidate = _phase_call(
            "PLN",
            "external_imp._create_plan",
            lambda: upstream._create_plan(root, design_reference, repository),
            receipts,
            log,
        )
        binding = plan_reference + "#WI-001"
        imp_result, marker = _phase_call(
            "IMP",
            "external_imp._complete_imp",
            lambda: upstream._complete_imp(
                root, binding, design_reference, repository, resource_root
            ),
            receipts,
            log,
        )
        imp_reference = imp_result["artifact"]["reference"]
        if marker not in readme.read_text(encoding="utf-8"):
            raise upstream.IntegrationError("completed IMP marker is missing")

        before_vfy = LifecycleQueryService(root, plugin_root=ROOT).inspect_requirement(
            requirement_reference
        )
        if before_vfy.overall_state != "ready_for_next_phase":
            raise upstream.IntegrationError("completed IMP is not VFY-ready")
        candidate = _candidate_from_lifecycle(
            root=root,
            project_label=repository,
            context_reference=context_reference,
            design_reference=design_reference,
            plan_reference=plan_reference,
            plan_candidate=plan_candidate,
            projection=before_vfy,
            target_path=target_path,
        )
        store = ArtifactStore.open_read_only(root)
        design_artifact_id, design_revision = design_reference.split("@", 1)
        stored_design = store.read_revision(design_artifact_id, int(design_revision))
        dom_510 = next(
            member for member in stored_design.payload.members if member.member_id == "DOM-510"
        )
        design_target_text = dom_510.raw_bytes.decode("utf-8")
        if not all(
            token in design_target_text
            for token in ("VFO-001", "VFP-210-001", "VFP-220-001")
        ):
            raise upstream.IntegrationError("DSN does not retain the exact VFY Target authority")

        def execute_vfy() -> dict[str, Any]:
            handler = VfyHandler(root)
            opened = handler.create(
                candidate,
                persist=True,
                run_automated=True,
                allow_commands=False,
                finalize=False,
            )
            confirmation = _delegated_confirmation(root, handler, opened["state"])
            finalized = handler.run(
                reference=None,
                state=opened["state"],
                store_generation=opened["store_generation"],
                persist=True,
                method_ids=[],
                allow_commands=False,
                automated_only=False,
                manual_observations=None,
                failure_returns=None,
                early_stop_basis=None,
                finalize=True,
                confirmation=confirmation,
            )
            return {
                "opened_reference": opened["state"]["artifact"]["reference"],
                "confirmation": confirmation,
                "state": finalized["state"],
            }

        vfy_execution = _phase_call(
            "VFY",
            "VfyHandler.create+run",
            execute_vfy,
            receipts,
            log,
        )
        vfy_state = vfy_execution["state"]
        vfy_reference = vfy_state["artifact"]["reference"]
        if (
            vfy_state["artifact"]["revision_state"] != "frozen"
            or vfy_state["artifact"]["artifact_status"] != "ready"
            or vfy_state["product_result"] != "pass"
            or vfy_state["artifact_gate"] != "pass"
            or vfy_state["rls_ready"]
        ):
            raise upstream.IntegrationError("VFY did not freeze pass with authoritative RLS n/a")
        if [item["method_type"] for item in vfy_state["methods"]] != [
            "inspection",
            "analysis",
        ] or any(item["result"] != "pass" for item in vfy_state["method_results"]):
            raise upstream.IntegrationError("VFY did not execute both independent Method Types")

        database = root / ".sdlc/store.sqlite3"
        check_before = {
            "database": upstream._file_identity(database),
            "product": upstream._file_identity(readme),
            "git": upstream._git_state(root),
        }
        checked = VfyHandler(root).check(reference=vfy_reference)
        lifecycle = LifecycleQueryService(root, plugin_root=ROOT).inspect_requirement(
            requirement_reference
        )
        status = status_runtime.run_status(
            ["inspect", "-r", requirement_reference], cwd=root
        )
        check_after = {
            "database": upstream._file_identity(database),
            "product": upstream._file_identity(readme),
            "git": upstream._git_state(root),
        }
        check_read_only = check_before == check_after
        if not check_read_only or checked["state"] != vfy_state:
            raise upstream.IntegrationError("VFY check/status readback changed stored or product bytes")
        if (
            lifecycle.vfy_projection is None
            or lifecycle.vfy_projection["artifact_reference"] != vfy_reference
            or lifecycle.vfy_projection["product_result"] != "pass"
            or lifecycle.vfy_projection["artifact_gate"] != "pass"
            or lifecycle.vfy_projection["next_action"] != "LIFECYCLE_COMPLETE"
            or lifecycle.overall_state != "complete"
        ):
            raise upstream.IntegrationError("Lifecycle did not read back the exact frozen VFY")
        if (
            not status.get("ok")
            or status.get("projection", {}).get("vfy_projection", {}).get(
                "artifact_reference"
            )
            != vfy_reference
        ):
            raise upstream.IntegrationError("sdlc-status did not project the exact frozen VFY")

        references = {
            "CTX": context_reference,
            "REQ": requirement_reference,
            "DSN": design_reference,
            "PLN": plan_reference,
            "IMP": imp_reference,
            "VFY": vfy_reference,
        }
        phases = upstream._phase_records(
            root, {phase: reference for phase, reference in references.items() if phase != "VFY"}
        )
        phases["VFY"] = _vfy_phase_record(root, vfy_reference)
        claim = before_vfy.current_claims[0]
        result = claim.results[0]
        conclusions = {item["id"]: item for item in vfy_state["fixed_conclusions"]}
        during = repository_snapshot(root)
        if during["head"] != initial["head"] or during["refs_sha256"] != initial["refs_sha256"]:
            raise upstream.IntegrationError("phase execution changed HEAD or Git refs")
        output = {
            "name": name,
            "repository": repository,
            "expected_sha": expected_sha,
            "actual_sha": during["head"],
            "status": "PASS",
            "phase_execution_receipts": receipts,
            "references": references,
            "phases": phases,
            "imp_claim": {
                "binding_reference": claim.binding_reference,
                "binding_lineage": claim.binding_lineage,
                "attempt": claim.attempt,
                "state": claim.claim_state,
                "artifact_reference": claim.artifact_reference,
            },
            "imp_result": dict(result),
            "vfy_subject_set": vfy_state["subjects"],
            "design_target_authority": {
                "member": "DOM-510",
                "sha256": dom_510.sha256,
                "target": design_reference + "#VFO-001",
                "obligations": [
                    design_reference + "#VFP-210-001",
                    design_reference + "#VFP-220-001",
                ],
            },
            "method_types": [item["method_type"] for item in vfy_state["methods"]],
            "method_results": vfy_state["method_results"],
            "evidence": vfy_state["evidence"],
            "con_ver": conclusions["CON-VER"],
            "con_val": conclusions["CON-VAL"],
            "product_result": vfy_state["product_result"],
            "artifact_gate": vfy_state["artifact_gate"],
            "rls_applicability": vfy_state["rls_applicability"],
            "rls_ready": vfy_state["rls_ready"],
            "final_confirmation": {
                "mode": vfy_state["final_confirmation"]["mode"],
                "reviewer": vfy_state["final_confirmation"]["confirmer"],
                "authority_reference": vfy_state["final_confirmation"][
                    "authority_reference"
                ],
                "manual_or_hybrid_evidence": False,
            },
            "lifecycle": lifecycle.to_dict(),
            "status_projection": status["projection"]["vfy_projection"],
            "check_read_only": check_read_only,
            "repository_before": initial,
            "repository_during": during,
            "remote_writes": 0,
            "dependency_installations": 0,
            "commit_push_tag_or_ref_mutations": 0,
            "command_receipts": list(command_receipts or []),
            "upstream_candidate_digests": {
                "CTX": canonical_digest(context_candidate),
                "REQ": canonical_digest(requirement_candidate),
                "DSN": canonical_digest(design_candidate),
                "PLN": canonical_digest(plan_candidate),
            },
        }
        return output
    finally:
        if readme.exists() and not readme.is_symlink():
            readme.write_bytes(original_readme)
            readme.chmod(original_mode)
        shutil.rmtree(runtime_dir, ignore_errors=True)
        final_state = upstream._git_state(root)
        final = repository_snapshot(root)
        if final_state != initial_state:
            raise upstream.IntegrationError(
                f"{repository}: cleanup did not restore exact Git/workspace state"
            )
        if output is not None:
            output["repository_after"] = final
            output["cleanup_assertions"] = {
                "head_unchanged": final["head"] == initial["head"],
                "refs_unchanged": final["refs_sha256"] == initial["refs_sha256"],
                "status_bytes_identical": final["status_hex"] == initial["status_hex"],
                "tracked_untracked_digest_identical": final[
                    "tracked_untracked_sha256"
                ]
                == initial["tracked_untracked_sha256"],
                "file_mode_identical": final["file_mode_sha256"]
                == initial["file_mode_sha256"],
                "sdlc_removed": not final["sdlc_exists"],
                "temporary_authority_removed": not (root / ".sdlc/authority").exists(),
                "temporary_evidence_removed": not runtime_dir.exists(),
            }
        log.add(f"{repository}: cleanup restored exact initial state")


def compare_projects(projects: list[Mapping[str, Any]]) -> dict[str, Any]:
    if len(projects) != 2:
        raise upstream.IntegrationError("external acceptance requires exactly two projects")
    expected_phases = ["CTX", "REQ", "DSN", "PLN", "IMP", "VFY"]
    for project in projects:
        actual = [item["phase"] for item in project["phase_execution_receipts"]]
        if actual != expected_phases:
            raise upstream.IntegrationError(f"incomplete external phase chain: {actual}")
        if project["method_types"] != ["inspection", "analysis"]:
            raise upstream.IntegrationError("external Method Type set is inconsistent")
        if not all(project["cleanup_assertions"].values()):
            raise upstream.IntegrationError("external cleanup assertion failed")
    return {
        "status": "PASS",
        "phase_chain_equal": True,
        "method_types_equal": True,
        "semantic_subjects_distinct": (
            projects[0]["vfy_subject_set"] != projects[1]["vfy_subject_set"]
        ),
    }


def run_live(
    json_out: Path,
    log_out: Path,
    *,
    source_sha: str,
    base_sha: str,
) -> dict[str, Any]:
    log = Log(log_out)
    report: dict[str, Any] = {
        "contract": "sdlc-ai-spec/vfy-external-integration-result/v1",
        "generated_at": utc_now(),
        "status": "FAIL",
        "source_sha": source_sha,
        "base_sha": base_sha,
        "integration_mode": "PREMERGE_DIRECT_DESIGN_ANCESTRY",
        "fixed_projects": list(FIXED_PROJECTS),
        "clone_policy": {
            "attempts_per_project_per_runner_invocation": 1,
            "retry_owner": "run_vfy_delivery_validation.py",
        },
        "projects": [],
        "cross_project": None,
        "remote_writes": 0,
        "dependency_installations": 0,
    }
    try:
        with tempfile.TemporaryDirectory(
            prefix="vfy-v2-real-projects-", dir="/private/tmp"
        ) as temporary:
            parent = Path(temporary)
            for index, specification in enumerate(FIXED_PROJECTS, start=1):
                checkout = parent / f"project-{index}"
                commands = clone_exact_once(
                    checkout,
                    specification["repository"],
                    specification["sha"],
                    log,
                )
                report["projects"].append(
                    run_project(
                        checkout,
                        name=specification["name"],
                        repository=specification["repository"],
                        expected_sha=specification["sha"],
                        log=log,
                        command_receipts=commands,
                    )
                )
            report["cross_project"] = compare_projects(report["projects"])
            report["status"] = "PASS"
        log.add("PASS: two exact external projects completed and were removed")
    except Exception as exc:
        report["error"] = {
            "type": exc.__class__.__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        log.add(f"FAIL: {exc.__class__.__name__}: {exc}")
    report["remote_writes"] = sum(
        int(item.get("remote_writes", 0)) for item in report["projects"]
    )
    report["dependency_installations"] = sum(
        int(item.get("dependency_installations", 0)) for item in report["projects"]
    )
    report["log"] = log.receipt()
    _write_json(json_out, report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--json-out", type=Path, required=True)
    parser.add_argument("--log-out", type=Path)
    arguments = parser.parse_args(argv)
    json_out = arguments.json_out.expanduser().resolve()
    log_out = (
        arguments.log_out.expanduser().resolve()
        if arguments.log_out
        else json_out.with_suffix(".log")
    )
    if log_out.exists():
        log_out.unlink()
    report = run_live(
        json_out,
        log_out,
        source_sha=arguments.source_sha,
        base_sha=arguments.base_sha,
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

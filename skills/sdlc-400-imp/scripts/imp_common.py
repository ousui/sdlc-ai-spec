"""IMP value objects and bundled input/output contracts."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path, PurePosixPath
import re
from typing import Mapping

from packages.sdlc_phasekit import contains_secret, refs
from packages.sdlc_runtime import exact_artifact_reference

CONSIDERATIONS = (
    "Calculation Rules",
    "Decision Rules",
    "State Transitions",
    "Algorithm & Invariants",
    "Data Contract & Transformation",
    "Boundary & Failure Handling",
    "Effects & Consistency",
)
READINESS = (
    "Binding uniquely resolves to the declared upstream disposition",
    "One atomic Outcome is preserved",
    "Completion Criteria and Expected Evidence are authoritative",
    "Every Claim Resource has an exact Scope and Baseline source",
    "All seven Implementation Considerations have a complete disposition",
    "Context, Decisions, Dependencies and Exceptions remain traceable",
)
WORK_HEADERS = (
    "ID", "目标 Phase Target Phase", "结果 Outcome", "执行范围 Execution Scope",
    "来源引用 Source References", "约束引用 Constraint References",
    "依赖 Depends On", "完成条件 Completion Criteria",
    "预期证据 Expected Evidence", "责任角色 Responsible Role",
)
CHANGE_HEADERS = (
    "Change ID", "Object or Boundary", "Change", "Baseline References",
    "Baseline State", "Target State", "Affected Domains",
)
APPLICABILITY_HEADERS = ("Phase", "Disposition", "Host", "判断依据 Basis")
BINDING_HEADERS = (
    "IMP Binding Reference", "Binding Lineage Key", "Attempt", "Owner", "Rework References",
)
RESULT_HEADERS = (
    "ID", "Resource", "Baseline Reference", "Change Reference", "Result Reference",
    "Changed Scope", "Approach Step References",
)
MATRIX_HEADERS = (
    "实施考量项 Implementation Consideration", "Disposition", "触发依据或 N/A 原因",
    "Approach Step 引用", "Exception 引用",
)
LOCAL_CHECK_HEADERS = ("ID", "检查或方法 Check or Method", "范围 Scope", "结果 Result", "依据 Basis")
RESOURCE_ID = re.compile(r"^[A-Za-z0-9._+-]+$")
EXACT_BINDING = re.compile(
    r"^(?:(?:PLN-[0-9]{14}-[0-9]{2,}@[1-9][0-9]*#WI-[0-9]{3})"
    r"|(?:(?:REQ|DSN)-[0-9]{14}-[0-9]{2,}@[1-9][0-9]*))$"
)
STATE_MEMBER = "IMP-STATE"


class ImpError(ValueError):
    def __init__(self, code, message, *, status="blocked", action=None, details=None):
        super().__init__(message)
        self.code, self.status = code, status
        self.action = action or code
        self.details = details or {}


def require(condition, code, message, **kwargs):
    if not condition:
        raise ImpError(code, message, **kwargs)


def exact_base(reference, phase=None):
    require(isinstance(reference, str), "IMP_BINDING_MISMATCH", "Reference must be text")
    try:
        artifact_id, revision = exact_artifact_reference(reference)
    except ValueError as exc:
        raise ImpError("IMP_BINDING_MISMATCH", "Reference requires an exact numeric Revision") from exc
    require(reference == f"{artifact_id}@{revision}", "IMP_BINDING_MISMATCH",
            "A complete exact Artifact Revision is required")
    if phase:
        require(artifact_id.startswith(phase + "-"), "IMP_BINDING_MISMATCH", f"Expected {phase} Reference")
    return artifact_id, revision


def base_ref(reference):
    return reference.split("#", 1)[0].split("/", 1)[0]


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def safe_path(value, *, allow_root=False):
    require(isinstance(value, str) and value, "IMP_SCOPE_VIOLATION", "Resource path is required")
    path = PurePosixPath(value)
    require(not path.is_absolute() and ".." not in path.parts and "\\" not in value,
            "IMP_SCOPE_VIOLATION", "Resource path must remain within Project Root")
    require(not any(part in {".git", ".sdlc"} for part in path.parts),
            "IMP_SCOPE_VIOLATION", "Git and runtime control paths are not product resources")
    require(allow_root or str(path) != ".", "IMP_SCOPE_VIOLATION", "Product file path is empty")
    return path.as_posix()


def resolve_owner(explicit=None, *, environment=None, candidates=()):
    """Only an explicit token or the registered stable environment entry is used."""
    environment = os.environ if environment is None else environment
    if explicit is not None:
        require(isinstance(explicit, str) and explicit.strip(), "IMP_OWNER_MISMATCH",
                "Explicit Owner must be a non-empty stable token", status="action_required")
        values = [explicit.strip()]
    else:
        raw = environment.get("SDLC_EXECUTOR_TOKEN")
        values = list(dict.fromkeys(str(item).strip() for item in (*candidates, raw) if item))
        require(len(values) == 1, "IMP_OWNER_MISMATCH",
                "Provide one stable Owner with --owner or SDLC_EXECUTOR_TOKEN",
                status="action_required", details={"candidate_count": len(values)})
    owner = values[0]
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/@%+#-]{0,199}", owner) is not None,
            "IMP_OWNER_MISMATCH", "Owner must be one stable token", status="action_required")
    return owner


def validate_scope(value):
    scope = refs(value, "execution_scope", required=True)
    resources = tuple(item[9:] for item in scope if item.startswith("resource:"))
    require(resources and all(RESOURCE_ID.fullmatch(item) for item in resources),
            "IMP_READINESS_FAILED", "Execution Scope requires canonical resource:<id> tokens",
            action="RETURN_TO_PLAN")
    for item in scope:
        if item.startswith("path:"):
            resource, separator, path = item[5:].partition("/")
            require(separator and resource in resources, "IMP_READINESS_FAILED",
                    "Path scope must name a declared Resource", action="RETURN_TO_PLAN")
            safe_path(path.rstrip("/"))
    return scope


def path_allowed(resource, path, scope):
    if f"resource:{resource}" not in scope:
        return False
    prefix = f"path:{resource}/"
    paths = [item[len(prefix):].rstrip("/") for item in scope if item.startswith(prefix)]
    return not paths or any(path == item or path.startswith(item + "/") for item in paths)


def reject_secrets(value):
    require(not contains_secret(value), "IMP_READINESS_FAILED",
            "Potential Secret cannot be persisted in IMP Artifact or Evidence")


@dataclass(frozen=True)
class Binding:
    reference: str
    lineage: str
    upstream_reference: str
    context_reference: str
    plan_reference: str | None
    wi_id: str | None
    lineage_references: tuple[str, ...]
    execution_scope: tuple[str, ...]
    dependencies: tuple[str, ...]
    outcome: str
    completion_criteria: str
    expected_evidence: str
    basis_references: tuple[str, ...]
    design_decisions: tuple[str, ...]
    lifecycle_applicability: tuple[dict, ...]
    exceptions: tuple[dict, ...] = ()

    def to_dict(self):
        return json.loads(canonical(asdict(self)))

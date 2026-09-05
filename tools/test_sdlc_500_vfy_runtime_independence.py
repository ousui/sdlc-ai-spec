#!/usr/bin/env python3
"""Exercise the complete VFY surface from the installed Plugin boundary only."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
META_COMMANDS = ("help", "version", "commands", "examples")
ALLOWED_SKILLS = ("_shared", "sdlc-500-vfy", "sdlc-status")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.skill_vfy.support import persistent_authority_candidate  # noqa: E402


def tree_digest(root: Path) -> str:
    rows: list[tuple[str, str]] = []
    if not root.exists():
        return hashlib.sha256(b"absent").hexdigest()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        rows.append((relative, hashlib.sha256(path.read_bytes()).hexdigest()))
    return hashlib.sha256(
        json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def product_tree_digest(root: Path) -> str:
    rows: list[tuple[str, str]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root)
        if relative.parts[0] in {".git", ".sdlc"}:
            continue
        rows.append(
            (
                relative.as_posix(),
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        )
    return hashlib.sha256(
        json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def candidate() -> dict[str, Any]:
    ctx = "CTX-20260904100000-01@1"
    pln = "PLN-20260904101000-01@1"
    wi = pln + "#WI-001"
    imp = "IMP-20260904102000-01@1"
    subject = imp + "/RES-001"
    vfo_ver = "DSN-20260904100500-01@1#VFO-001"
    vfo_val = "DSN-20260904100500-01@1#VFO-002"
    vfp_ver = "DSN-20260904100500-01@1#VFP-001"
    vfp_val = "DSN-20260904100500-01@1#VFP-002"
    return {
        "contract": "sdlc-ai-spec/vfy-candidate/v1",
        "context_reference": ctx,
        "profile": "full",
        "title": "Installed-boundary verification",
        "scope": {
            "reference": pln,
            "disposition": "required",
            "delivery_scope": ["resource:app"],
            "input_references": [ctx],
            "imp_work_items": [
                {
                    "reference": wi,
                    "target_phase": "IMP",
                    "binding_reference": wi,
                    "resource_ids": ["app"],
                    "depends_on": [],
                }
            ],
        },
        "subjects": [
            {
                "reference": subject,
                "resource_id": "app",
                "imp_revision_reference": imp,
                "binding_lineage": wi,
                "attempt": "attempt-installed",
                "claim_state": "completed",
                "imp_revision_state": "frozen",
                "baseline_reference": "vcs:git:" + "0" * 40,
                "result_digest": "sha256:" + "1" * 64,
                "cumulative_changed_scope": ["path:app/README.md"],
                "dependency_result_references": [],
                "current_valid": True,
                "dependency_chain_valid": True,
            }
        ],
        "targets": [
            {
                "reference": vfo_ver,
                "purpose": "verification",
                "summary": "The exact product entry exists",
                "source_kind": "vfo",
                "obligation_references": [vfp_ver],
            },
            {
                "reference": vfo_val,
                "purpose": "validation",
                "summary": "The exact product entry is usable",
                "source_kind": "vfo",
                "obligation_references": [vfp_val],
            },
        ],
        "methods": [
            {
                "id": "VFM-001",
                "title": "Inspect entry",
                "purpose": "verification",
                "target_references": [vfo_ver],
                "subject_references": [subject],
                "obligation_references": [vfp_ver, wi],
                "method_type": "inspection",
                "disposition": "required",
                "execution_mode": "automated",
                "executor_identity": "installed-runtime",
                "procedure": {"kind": "file_exists", "path": "README.md"},
                "pass_criteria": "README.md exists",
                "evidence_requirement": "Immutable path observation",
            },
            {
                "id": "VFM-002",
                "title": "Demonstrate entry",
                "purpose": "validation",
                "target_references": [vfo_val],
                "subject_references": [subject],
                "obligation_references": [vfp_val, wi],
                "method_type": "demonstration",
                "disposition": "required",
                "execution_mode": "automated",
                "executor_identity": "installed-runtime",
                "procedure": {"kind": "file_exists", "path": "README.md"},
                "pass_criteria": "README.md is observable",
                "evidence_requirement": "Immutable intended-use observation",
            },
        ],
        "required_obligation_references": [vfp_ver, vfp_val, wi],
        "control_inputs": [],
        "returns": [],
        "rls_applicability": "required",
        "release_target_obligations": [],
    }


def run_command(command: list[str], *, cwd: Path, stdin: str | None = None) -> dict[str, Any]:
    environment = dict(os.environ)
    environment.update(
        {
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            "NO_COLOR": "1",
        }
    )
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        input=stdin,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=180,
    )
    return {
        "command": command,
        "cwd": str(cwd),
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def receipt(name: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "command": result["command"],
        "cwd": result["cwd"],
        "exit_code": result["exit_code"],
        "stdout_sha256": hashlib.sha256(result["stdout"].encode("utf-8")).hexdigest(),
        "stderr_sha256": hashlib.sha256(result["stderr"].encode("utf-8")).hexdigest(),
    }


def require_success(name: str, result: dict[str, Any]) -> None:
    if result["exit_code"] != 0:
        raise AssertionError(f"{name} failed: {result}")


def runtime_state(
    name: str,
    result: dict[str, Any],
    *,
    expected_effects: list[str] | None = None,
) -> dict[str, Any]:
    require_success(name, result)
    try:
        payload = json.loads(result["stdout"])
        state = payload["result"]["state"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise AssertionError(f"{name} returned invalid Runtime JSON: {result}") from exc
    expected = [] if expected_effects is None else expected_effects
    if payload.get("effects") != expected:
        raise AssertionError(
            f"{name} reported unexpected effects: {payload.get('effects')}"
        )
    return state


def authority_arguments(value: dict[str, Any]) -> list[str]:
    arguments: list[str] = []
    references = [
        value["scope"]["reference"],
        *(item["reference"] for item in value["subjects"]),
        *(item["origin_reference"] for item in value.get("exceptions", [])),
        *value.get("control_inputs", []),
    ]
    for reference in references:
        arguments.extend(["--input", str(reference)])
    return arguments


CONFIRMATION_SCRIPT = r'''
import json
from pathlib import Path
import sys

installed = Path(sys.argv[1])
root = Path(sys.argv[2])
label = sys.argv[3]
mode = sys.argv[4]
sys.path[:0] = [str(installed), str(installed / "skills/sdlc-500-vfy/scripts")]

from packages.sdlc_artifact_store import compute_sha256
from packages.sdlc_runtime.authority import (
    DELEGATED_AUTHORITY_HEADERS,
    DELEGATED_EXCLUDED_AUTHORITY,
    DELEGATED_INDEPENDENCE,
)
from vfy_handler import VfyHandler

state = json.load(sys.stdin)
bindings = VfyHandler(root).confirmation_requirements(state)
authority_dir = root / ".sdlc/authority"
authority_dir.mkdir(parents=True, exist_ok=True)
if mode == "human":
    raw = b"decision: approved\nauthority: product owner\n"
    authority = authority_dir / f"vfy-installed-{label}-human.txt"
    authority.write_bytes(raw)
    accepted = [
        f"{state['artifact']['reference']}#{item['id']}"
        for item in state.get("exceptions", [])
        if item.get("state") in {"active", "carried"}
    ]
    print(json.dumps({
        "mode": "human",
        "confirmer": "installed-product-owner",
        "role": "Product Owner",
        "authority_reference": authority.relative_to(root).as_posix() + "@" + compute_sha256(raw),
        "accepted_exception_references": accepted,
        "confirmed_at": "2026-09-04T10:30:00Z",
        **bindings,
    }, sort_keys=True))
    raise SystemExit(0)
if mode != "delegated":
    raise SystemExit("unsupported confirmation mode")
basis = authority_dir / f"vfy-installed-{label}-delegation.txt"
basis.write_text("Independent deterministic VFY contract review authority.\n", encoding="utf-8")
basis_reference = basis.relative_to(root).as_posix() + "@" + compute_sha256(basis.read_bytes())
reviewer = "installed-independent-reviewer"
executors = {
    item["executor_identity"]
    for item in state["methods"]
    if item["disposition"] in {"required", "embedded"}
}
if len(executors) != 1:
    raise SystemExit("installed fixture requires one exact Executor identity")
executor = next(iter(executors))
values = (
    basis_reference,
    reviewer,
    "Delegated Independent Reviewer",
    executor,
    DELEGATED_INDEPENDENCE,
    bindings["control_input_digest"],
    bindings["evaluation_contract_set"],
    bindings["check_set_result_digest"],
    DELEGATED_EXCLUDED_AUTHORITY,
)
raw = ("\n".join((
    "---",
    "contract: sdlc-ai-spec/final-confirmation-authority/v1",
    f"artifact: {state['artifact']['reference']}",
    "decision: approved",
    "decided_at: 2026-09-04T10:30:00Z",
    "---",
    "",
    "| " + " | ".join(DELEGATED_AUTHORITY_HEADERS) + " |",
    "|" + "|".join("---" for _ in DELEGATED_AUTHORITY_HEADERS) + "|",
    "| " + " | ".join(values) + " |",
)) + "\n").encode("utf-8")
authority = authority_dir / f"vfy-installed-{label}-confirmation.md"
authority.write_bytes(raw)
print(json.dumps({
    "mode": "delegated",
    "confirmer": reviewer,
    "role": "Delegated Independent Reviewer",
    "reviewed_executor": executor,
    "authority_reference": authority.relative_to(root).as_posix() + "@" + compute_sha256(raw),
    "accepted_exception_references": [],
    "confirmed_at": "2026-09-04T10:30:00Z",
    **bindings,
}, sort_keys=True))
'''


PROJECTION_SCRIPT = r'''
import json
from pathlib import Path
import sys

installed = Path(sys.argv[1])
sys.path[:0] = [
    str(installed),
    str(installed / "skills/sdlc-status/scripts"),
]
from packages.sdlc_lifecycle.query_vfy import project_vfy_state
from vfy_projection import project_vfy_status

state = json.load(sys.stdin)
print(json.dumps({
    "lifecycle": project_vfy_state(state).to_dict(),
    "status": project_vfy_status(state),
}, sort_keys=True))
'''


def build_confirmation(
    installed: Path,
    project: Path,
    state: dict[str, Any],
    label: str,
    *,
    mode: str = "delegated",
) -> tuple[dict[str, Any], dict[str, Any]]:
    result = run_command(
        [
            sys.executable,
            "-c",
            CONFIRMATION_SCRIPT,
            str(installed),
            str(project),
            label,
            mode,
        ],
        cwd=project,
        stdin=json.dumps(state),
    )
    require_success(f"{label}_confirmation", result)
    try:
        return json.loads(result["stdout"]), result
    except json.JSONDecodeError as exc:
        raise AssertionError(f"invalid {label} confirmation JSON: {result}") from exc


def _copy_installed_boundary(installed: Path) -> None:
    shutil.copytree(
        ROOT / "packages",
        installed / "packages",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    shutil.copytree(
        ROOT / "scripts",
        installed / "scripts",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    for skill in ALLOWED_SKILLS:
        shutil.copytree(
            ROOT / "skills" / skill,
            installed / "skills" / skill,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )


def validate() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="vfy-installed-") as directory:
        temp = Path(directory)
        installed = temp / "plugin"
        project = temp / "project"
        installed.mkdir()
        project.mkdir()
        _copy_installed_boundary(installed)
        forbidden = [
            installed / "docs",
            installed / "tests",
            installed / "AGENTS.md",
            installed / "CLAUDE.md",
            installed / "HANDOFF.md",
        ]
        if any(path.exists() for path in forbidden):
            raise AssertionError("installed boundary contains a forbidden development source")
        if tuple(sorted(path.name for path in (installed / "skills").iterdir())) != tuple(
            sorted(ALLOWED_SKILLS)
        ):
            raise AssertionError("installed boundary contains an unexpected business Skill")
        (project / "README.md").write_text("installed runtime fixture\n", encoding="utf-8")
        authoritative_candidate = persistent_authority_candidate(project)
        runtime = installed / "skills/sdlc-500-vfy/scripts/runtime.py"
        if not runtime.is_file():
            raise AssertionError("installed VFY Runtime is missing")

        installed_before = tree_digest(installed)
        project_initial = product_tree_digest(project)
        commands: list[dict[str, Any]] = []

        for command in META_COMMANDS:
            result = run_command([sys.executable, str(runtime), command], cwd=project)
            require_success(command, result)
            commands.append(receipt(command, result))

        create = run_command(
            [
                sys.executable,
                str(runtime),
                "create",
                "--project-root",
                str(project),
                "--output",
                "json",
                *authority_arguments(authoritative_candidate),
            ],
            cwd=project,
            stdin=json.dumps(
                {
                    "candidate": authoritative_candidate,
                    "persist": True,
                    "run_automated": False,
                }
            ),
        )
        pass_open = runtime_state(
            "create", create, expected_effects=["artifact_store_write"]
        )
        commands.append(receipt("create", create))
        pass_reference = pass_open["artifact"]["reference"]

        run = run_command(
            [
                sys.executable,
                str(runtime),
                "run",
                "--project-root",
                str(project),
                "--reference",
                pass_reference,
                "--output",
                "json",
            ],
            cwd=project,
            stdin=json.dumps({"persist": True}),
        )
        pass_executed = runtime_state(
            "run", run, expected_effects=["artifact_store_write"]
        )
        commands.append(receipt("run", run))
        if pass_executed["product_result"] != "pass":
            raise AssertionError("installed run did not produce product pass")
        if product_tree_digest(project) != project_initial:
            raise AssertionError("persistent create/run changed product bytes")

        confirmation, confirmation_run = build_confirmation(
            installed, project, pass_executed, "pass"
        )
        commands.append(receipt("delegated_confirmation_pass", confirmation_run))
        before_finalize = product_tree_digest(project)
        finalize = run_command(
            [
                sys.executable,
                str(runtime),
                "run",
                "--project-root",
                str(project),
                "--reference",
                pass_reference,
                "--output",
                "json",
            ],
            cwd=project,
            stdin=json.dumps(
                {
                    "persist": True,
                    "method_ids": [],
                    "finalize": True,
                    "confirmation": confirmation,
                }
            ),
        )
        pass_frozen = runtime_state(
            "finalize", finalize, expected_effects=["artifact_store_write"]
        )
        commands.append(receipt("finalize", finalize))
        if pass_frozen["artifact"]["revision_state"] != "frozen":
            raise AssertionError("installed VFY did not freeze the confirmed Revision")
        if (
            pass_frozen["artifact_gate"] != "pass"
            or pass_frozen["next_action"] != "LIFECYCLE_COMPLETE"
        ):
            raise AssertionError("installed pass projection did not preserve RLS n/a")
        if product_tree_digest(project) != before_finalize:
            raise AssertionError("persistent finalization changed product bytes")

        check_before = tree_digest(project)
        check = run_command(
            [
                sys.executable,
                str(runtime),
                "check",
                "--project-root",
                str(project),
                "--reference",
                pass_reference,
                "--output",
                "json",
            ],
            cwd=project,
            stdin=json.dumps({}),
        )
        checked = runtime_state("check", check)
        commands.append(receipt("check", check))
        if checked != pass_frozen or tree_digest(project) != check_before:
            raise AssertionError("installed check was not absolutely read-only")

        replacement = json.loads(json.dumps(authoritative_candidate))
        replacement["title"] = "Installed-boundary revised verification"
        replacement["methods"][0]["pass_criteria"] = (
            "README.md exists in the revised installed contract"
        )
        revise = run_command(
            [
                sys.executable,
                str(runtime),
                "revise",
                "--project-root",
                str(project),
                "--reference",
                pass_reference,
                "--output",
                "json",
                *authority_arguments(replacement),
            ],
            cwd=project,
            stdin=json.dumps(
                {"candidate": replacement, "persist": True}
            ),
        )
        revised = runtime_state(
            "revise", revise, expected_effects=["artifact_store_write"]
        )
        commands.append(receipt("revise", revise))
        if revised["artifact"]["revision"] != pass_frozen["artifact"]["revision"] + 1:
            raise AssertionError("installed revise did not allocate the next Revision")
        if product_tree_digest(project) != project_initial:
            raise AssertionError("persistent revise changed product bytes")

        return_project = temp / "return-project"
        return_project.mkdir()
        (return_project / "README.md").write_text(
            "installed runtime return fixture\n", encoding="utf-8"
        )
        return_authoritative_candidate = persistent_authority_candidate(return_project)
        return_project_initial = product_tree_digest(return_project)
        failing = json.loads(json.dumps(return_authoritative_candidate))
        failing["title"] = "Installed-boundary Return verification"
        failing["methods"][0]["procedure"]["path"] = "MISSING.md"
        fail_create = run_command(
            [
                sys.executable,
                str(runtime),
                "create",
                "--project-root",
                str(return_project),
                "--output",
                "json",
                *authority_arguments(failing),
            ],
            cwd=return_project,
            stdin=json.dumps(
                {"candidate": failing, "persist": True, "run_automated": False}
            ),
        )
        fail_open = runtime_state(
            "return_create", fail_create, expected_effects=["artifact_store_write"]
        )
        commands.append(receipt("return_create", fail_create))
        fail_reference = fail_open["artifact"]["reference"]
        wi = failing["scope"]["imp_work_items"][0]["binding_reference"]
        lineage = failing["subjects"][0]["binding_lineage"]
        return_run = run_command(
            [
                sys.executable,
                str(runtime),
                "run",
                "--project-root",
                str(return_project),
                "--reference",
                fail_reference,
                "--output",
                "json",
            ],
            cwd=return_project,
            stdin=json.dumps(
                {
                    "persist": True,
                    "failure_returns": {
                        "VFM-001": {
                            "return_phase": "IMP",
                            "imp_binding_reference": wi,
                            "imp_binding_lineage": lineage,
                            "observed_gap": "The required installed product file is absent",
                            "required_outcome": "Restore the exact declared product file",
                            "status": "open",
                        }
                    },
                }
            ),
        )
        return_open = runtime_state(
            "return", return_run, expected_effects=["artifact_store_write"]
        )
        commands.append(receipt("return", return_run))
        if return_open["product_result"] != "fail" or len(return_open["returns"]) != 1:
            raise AssertionError("installed failure did not produce one exact Return")

        return_confirmation, return_confirmation_run = build_confirmation(
            installed, return_project, return_open, "return"
        )
        commands.append(receipt("delegated_confirmation_return", return_confirmation_run))
        return_finalize = run_command(
            [
                sys.executable,
                str(runtime),
                "run",
                "--project-root",
                str(return_project),
                "--reference",
                fail_reference,
                "--output",
                "json",
            ],
            cwd=return_project,
            stdin=json.dumps(
                {
                    "persist": True,
                    "method_ids": [],
                    "finalize": True,
                    "confirmation": return_confirmation,
                }
            ),
        )
        return_frozen = runtime_state(
            "return_finalize",
            return_finalize,
            expected_effects=["artifact_store_write"],
        )
        commands.append(receipt("return_finalize", return_finalize))

        projection_run = run_command(
            [sys.executable, "-c", PROJECTION_SCRIPT, str(installed)],
            cwd=return_project,
            stdin=json.dumps(return_frozen),
        )
        require_success("lifecycle_projection", projection_run)
        commands.append(receipt("lifecycle_projection", projection_run))
        projection = json.loads(projection_run["stdout"])
        lifecycle = projection["lifecycle"]
        status = projection["status"]
        if lifecycle["next_phase"] != "IMP" or lifecycle["next_action"] != "RETURN_UPSTREAM":
            raise AssertionError(f"installed lifecycle Return projection is wrong: {projection}")
        if status["product_result"] != "fail" or status["artifact_gate"] != "pass":
            raise AssertionError(f"installed status conflated product and Artifact Gate: {projection}")

        exception_project = temp / "exception-project"
        exception_project.mkdir()
        (exception_project / "README.md").write_text(
            "installed runtime exception fixture\n", encoding="utf-8"
        )
        exception_initial = product_tree_digest(exception_project)
        exception_candidate = candidate()
        exception_reference = "DSN-20260904100500-01@1#EX-001"
        exception_candidate["methods"][0].update(
            disposition="waived",
            exception_reference=exception_reference,
        )
        exception_candidate["exceptions"] = [
            {
                "id": "EX-001",
                "state": "active",
                "origin_reference": exception_reference,
                "scope": ["VFM-001"],
                "reason": "explicit installed-boundary waiver",
                "known_risk": "verification Method is not executed",
                "compensating_control": "RLS retains the exact obligation",
                "approval": "Product Owner at 2026-09-04T10:30:00Z",
                "revisit_condition": "next release",
                "downstream_obligation": "RLS executes the waived verification",
                "resolution_references": [],
                "authority_verified": True,
                "accepts_product_failure": False,
            }
        ]
        exception_create = run_command(
            [
                sys.executable,
                str(runtime),
                "create",
                "--project-root",
                str(exception_project),
                "--output",
                "json",
            ],
            cwd=exception_project,
            stdin=json.dumps(
                {
                    "candidate": exception_candidate,
                    "persist": False,
                    "run_automated": True,
                }
            ),
        )
        exception_open = runtime_state("exception_create", exception_create)
        commands.append(receipt("exception_create", exception_create))
        exception_confirmation, exception_confirmation_run = build_confirmation(
            installed,
            exception_project,
            exception_open,
            "exception",
            mode="human",
        )
        commands.append(receipt("human_confirmation_exception", exception_confirmation_run))
        exception_finalize = run_command(
            [
                sys.executable,
                str(runtime),
                "auto",
                "--project-root",
                str(exception_project),
                "--output",
                "json",
            ],
            cwd=exception_project,
            stdin=json.dumps(
                {
                    "state": exception_open,
                    "persist": False,
                    "method_ids": [],
                    "finalize": True,
                    "confirmation": exception_confirmation,
                }
            ),
        )
        exception_frozen = runtime_state("exception_finalize", exception_finalize)
        commands.append(receipt("exception_finalize", exception_finalize))
        if (
            exception_frozen["artifact_gate"] != "pass_with_exception"
            or exception_frozen["artifact"]["artifact_status"]
            != "ready_with_exception"
            or not exception_frozen["final_confirmation"][
                "accepted_exception_references"
            ]
        ):
            raise AssertionError("installed Exception closure is incomplete")
        if product_tree_digest(exception_project) != exception_initial:
            raise AssertionError("installed Exception flow changed product bytes")

        installed_after = tree_digest(installed)
        if installed_before != installed_after:
            raise AssertionError("installed Plugin bytes changed during Runtime Independence test")
        if product_tree_digest(project) != project_initial:
            raise AssertionError("installed operations changed pass-project product bytes")
        if product_tree_digest(return_project) != return_project_initial:
            raise AssertionError("installed operations changed return-project product bytes")
        return {
            "contract": "sdlc-ai-spec/vfy-runtime-independence-result/v1",
            "status": "PASS",
            "installed_boundary": {
                "packages": True,
                "scripts": True,
                "skills": list(ALLOWED_SKILLS),
                "docs_present": False,
                "tests_present": False,
                "agents_present": False,
                "claude_present": False,
                "handoff_present": False,
            },
            "commands": commands,
            "meta_commands": list(META_COMMANDS),
            "operations": [
                "create",
                "run",
                "revise",
                "check",
                "Return",
                "Exception",
                "Lifecycle projection",
            ],
            "pass_projection": {
                "product_result": pass_frozen["product_result"],
                "artifact_gate": pass_frozen["artifact_gate"],
                "rls_ready": pass_frozen["rls_ready"],
            },
            "return_projection": lifecycle,
            "status_projection": status,
            "exception_projection": {
                "artifact_status": exception_frozen["artifact"]["artifact_status"],
                "artifact_gate": exception_frozen["artifact_gate"],
                "product_result": exception_frozen["product_result"],
            },
            "check_read_only": True,
            "installed_digest": installed_after,
            "project_initial_digest": project_initial,
            "project_final_digest": product_tree_digest(project),
            "return_project_initial_digest": return_project_initial,
            "return_project_final_digest": product_tree_digest(return_project),
        }


def main() -> int:
    try:
        report = validate()
        code = 0
    except Exception as exc:
        report = {
            "contract": "sdlc-ai-spec/vfy-runtime-independence-result/v1",
            "status": "FAIL",
            "error": {"type": exc.__class__.__name__, "message": str(exc)},
        }
        code = 2
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

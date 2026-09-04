"""Claim-scoped, preconditioned product operations and real local check evidence."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from packages.sdlc_artifact_store import compute_sha256
from packages.sdlc_execution import run_command
from packages.sdlc_resource import apply_operations
from packages.sdlc_runtime import parse_canonical_artifact
from packages.sdlc_runtime.authority import is_rfc3339
from packages.sdlc_runtime.canonical import (
    GATE_SUMMARY_HEADERS, require_single_row, require_single_table,
)

from imp_common import READINESS, canonical, path_allowed, reject_secrets, require, safe_path
from imp_result import capture, member, read_member

PRE_EXECUTION_CONTRACT = "sdlc-ai-spec/imp-pre-execution-readback/v1"
PROJECT_CHECK_CONTRACT = "sdlc-ai-spec/imp-isolated-project-check/v1"
PROJECT_SCRIPT_NAMES = frozenset({"build", "check", "lint", "test", "typecheck", "verify"})
GO_PACKAGE_RE = re.compile(r"^[A-Za-z0-9._/+~-]+$")
CARGO_VALUE_RE = re.compile(r"^[A-Za-z0-9._+~-]+$")
CARGO_SWITCHES = frozenset({
    "--workspace", "--all-targets", "--all-features", "--locked",
    "--no-default-features", "--release", "--quiet", "-q", "--lib",
    "--bins", "--tests", "--examples", "--benches",
})
CARGO_VALUE_OPTIONS = frozenset({"--package", "-p", "--features"})


def _sandbox_adapter(tool):
    if tool == "python":
        return "python-audit-hook"
    if sys.platform == "darwin" and Path("/usr/bin/sandbox-exec").is_file():
        return "darwin-sandbox-exec"
    if sys.platform.startswith("linux") and shutil.which("bwrap"):
        return "linux-bwrap"
    return None


def _sandbox_ready(adapter):
    if adapter == "python-audit-hook":
        return True
    if adapter == "darwin-sandbox-exec":
        command = [
            "/usr/bin/sandbox-exec", "-p",
            "(version 1)(allow default)(deny network*)", "/usr/bin/true",
        ]
    elif adapter == "linux-bwrap":
        command = [
            shutil.which("bwrap"), "--die-with-parent", "--unshare-net",
            "--ro-bind", "/", "/", "--", "/bin/true",
        ]
    else:
        return False
    try:
        return subprocess.run(
            command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=5, check=False,
        ).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _sandboxed_command(command, temporary_root, tool):
    adapter = _sandbox_adapter(tool)
    require(adapter is not None, "IMP_READINESS_FAILED",
            "Project Check requires a supported local network/write sandbox")
    temporary = str(Path(temporary_root).resolve())
    if adapter == "python-audit-hook":
        runner = Path(__file__).with_name("imp_project_check.py")
        require(command[1:5] == ["-I", "-B", "-S", "-m"],
                "IMP_READINESS_FAILED", "Python project Check adapter is invalid")
        return [
            sys.executable, "-I", "-B", "-S", str(runner), temporary,
            *command[4:],
        ], adapter
    if adapter == "darwin-sandbox-exec":
        require('"' not in temporary and "\\" not in temporary,
                "IMP_READINESS_FAILED", "Temporary sandbox path is not representable")
        profile = "\n".join((
            "(version 1)",
            "(deny default)",
            "(allow process*)",
            "(allow file-read*)",
            "(allow sysctl-read)",
            "(allow mach-lookup)",
            f'(allow file-write* (subpath "{temporary}"))',
        ))
        return ["/usr/bin/sandbox-exec", "-p", profile, *command], adapter
    return [
        shutil.which("bwrap"), "--die-with-parent", "--unshare-net",
        "--ro-bind", "/", "/", "--bind", temporary, temporary,
        "--", *command,
    ], adapter


def _safe_go_arguments(arguments):
    for value in arguments:
        path = Path(value)
        require(
            not value.startswith(("-", "/"))
            and "\\" not in value
            and GO_PACKAGE_RE.fullmatch(value) is not None
            and ".." not in path.parts,
            "IMP_READINESS_FAILED",
            "Go project Checks accept only package selectors after the fixed command",
        )


def _safe_cargo_arguments(arguments):
    index = 0
    while index < len(arguments):
        value = arguments[index]
        if value in CARGO_SWITCHES:
            index += 1
            continue
        if value in CARGO_VALUE_OPTIONS:
            require(index + 1 < len(arguments)
                    and CARGO_VALUE_RE.fullmatch(arguments[index + 1]) is not None,
                    "IMP_READINESS_FAILED",
                    "Cargo project Check option requires one bounded local value")
            index += 2
            continue
        require(not value.startswith("-")
                and CARGO_VALUE_RE.fullmatch(value) is not None,
                "IMP_READINESS_FAILED",
                "Cargo project Checks reject wrapper, config and forwarded arguments")
        index += 1


def _project_command(check, *, require_available=False):
    """Return executable and stable evidence forms for one bounded project Check."""
    declared = check.get("command")
    require(isinstance(declared, list) and 2 <= len(declared) <= 64
            and all(isinstance(item, str) and item and "\0" not in item
                    and "\n" not in item for item in declared),
            "IMP_READINESS_FAILED", "Project Check command must be a bounded argument array")
    tool, arguments = declared[0], declared[1:]
    actual, recorded = None, None
    if tool == "python":
        require(len(arguments) >= 2 and arguments[0] == "-m"
                and arguments[1] in {"compileall", "unittest"},
                "IMP_READINESS_FAILED",
                "Python project Checks are limited to compileall or unittest")
        actual = [sys.executable, "-I", "-B", "-S", *arguments]
        recorded = ["python", "-I", "-B", "-S", *arguments]
    elif tool == "go":
        require(arguments[0] in {"build", "test", "vet"}, "IMP_READINESS_FAILED",
                "Go project Checks are limited to build, test or vet")
        _safe_go_arguments(arguments[1:])
        actual = recorded = list(declared)
    elif tool == "cargo":
        require(arguments[0] in {"check", "clippy", "test"}, "IMP_READINESS_FAILED",
                "Cargo project Checks are limited to check, clippy or test")
        _safe_cargo_arguments(arguments[1:])
        actual = recorded = ["cargo", "--offline", *arguments]
    elif tool in {"npm", "pnpm", "yarn"}:
        direct = len(arguments) == 1 and arguments[0] == "test"
        scripted = (len(arguments) == 2 and arguments[0] == "run"
                    and arguments[1] in PROJECT_SCRIPT_NAMES)
        require(direct or scripted, "IMP_READINESS_FAILED",
                "Package project Checks require a fixed check/build/lint/test/typecheck/verify script")
        actual = recorded = [tool, "--offline", *arguments]
    elif tool == "mvn":
        require(all(not item.startswith("-") for item in arguments)
                and set(arguments).issubset({"compile", "package", "test", "verify"}),
                "IMP_READINESS_FAILED",
                "Maven project Checks require fixed offline lifecycle goals")
        actual = recorded = ["mvn", "-o", *arguments]
    elif tool in {"gradle", "./gradlew"}:
        require(all(not item.startswith("-") and item.rsplit(":", 1)[-1]
                    in {"assemble", "build", "check", "test"} for item in arguments),
                "IMP_READINESS_FAILED",
                "Gradle project Checks require fixed offline build/check/test tasks")
        actual = recorded = [tool, "--offline", *arguments]
    else:
        require(False, "IMP_READINESS_FAILED", "Unsupported project Check tool")
    if require_available and tool != "python" and not tool.startswith("./"):
        require(shutil.which(tool) is not None, "IMP_READINESS_FAILED",
                f"Project Check tool is unavailable: {tool}")
    return actual, recorded


def _materialize_snapshot(target, snapshot):
    target.mkdir(parents=True)
    if snapshot["root_mode"] is not None:
        target.chmod(snapshot["root_mode"])
    for directory in sorted(snapshot["directories"], key=lambda item: item["path"].count("/")):
        path = target / directory["path"]
        path.mkdir(parents=True, exist_ok=True)
        path.chmod(directory["mode"])
    for entry in snapshot["entries"]:
        path = target / entry["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(bytes.fromhex(entry["content_hex"]))
        path.chmod(entry["mode"])


def _offline_environment(temporary_root):
    home = Path(temporary_root) / "home"
    cache = Path(temporary_root) / "cache"
    scratch = Path(temporary_root) / "tmp"
    for path in (home, cache, scratch):
        path.mkdir()
    return {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(home),
        "XDG_CACHE_HOME": str(cache),
        "TMPDIR": str(scratch),
        "PYTHONPYCACHEPREFIX": str(cache / "pycache"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "CI": "1",
        "PIP_NO_INDEX": "1",
        "GOPROXY": "off",
        "GOSUMDB": "off",
        "CARGO_NET_OFFLINE": "true",
        "npm_config_offline": "true",
        "YARN_ENABLE_NETWORK": "0",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "http_proxy": "http://127.0.0.1:9",
        "https_proxy": "http://127.0.0.1:9",
        "HTTP_PROXY": "http://127.0.0.1:9",
        "HTTPS_PROXY": "http://127.0.0.1:9",
        "NO_PROXY": "",
    }


def dirty_paths(project_root):
    root = Path(project_root)
    if not (root / ".git").exists():
        return set()
    result = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        capture_output=True, check=False,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
    )
    require(result.returncode == 0, "IMP_BASELINE_UNRESOLVED", "Cannot read the actual dirty workspace state")
    entries = result.stdout.decode("utf-8", errors="strict").split("\0")
    paths = set()
    index = 0
    while index < len(entries):
        item = entries[index]
        if item:
            paths.add(item[3:])
            if "R" in item[:2] or "C" in item[:2]:
                index += 1
                if index < len(entries):
                    paths.add(entries[index])
        index += 1
    return paths


def operation_digest(operation):
    return compute_sha256(canonical(operation))


def validate_execution_history(method, completed, actions):
    """Bind every retained product effect to one unchanged current operation."""
    require(isinstance(completed, (list, tuple)) and
            all(isinstance(item, str) for item in completed),
            "IMP_RESULT_INCOMPLETE", "Completed operation history is invalid")
    require(isinstance(actions, list) and all(isinstance(item, dict) for item in actions),
            "IMP_RESULT_INCOMPLETE", "Executed action history is invalid")
    action_digests = [operation_digest(item) for item in actions]
    require(action_digests == list(completed) and len(action_digests) == len(set(action_digests)),
            "IMP_RESULT_INCOMPLETE",
            "Executed actions and completed operation identities disagree")
    current = [operation_digest(item) for item in method.get("operations", [])
               if isinstance(item, dict)]
    require(len(current) == len(set(current)), "IMP_READINESS_FAILED",
            "Implementation operations must have unique identities")
    require(current[:len(completed)] == list(completed), "IMP_BINDING_MISMATCH",
            "An active revision must retain executed operations as its exact ordered prefix")


def preflight(project_root, binding, method, roots, snapshots, *, completed=(), owned=()):
    if method.get("external_effects"):
        require(False, "IMP_SCOPE_VIOLATION",
                "IMP does not execute or authorize external effects")
    operations = method.get("operations")
    require(isinstance(operations, list), "IMP_READINESS_FAILED", "Implementation operations must be an array")
    dirty = dirty_paths(project_root)
    steps = {item["id"]: item for item in method["steps"]}
    targets, planned, order = set(), [], 0
    for operation in operations:
        require(isinstance(operation, dict), "IMP_READINESS_FAILED", "Invalid product operation")
        resource, step_id = operation.get("resource"), operation.get("step")
        require(resource in roots and step_id in steps, "IMP_SCOPE_VIOLATION", "Operation Resource or Step is unbound")
        path = safe_path(operation.get("path"))
        require(path_allowed(resource, path, binding.execution_scope), "IMP_SCOPE_VIOLATION",
                "Operation is outside Claim Scope")
        step_targets = steps[step_id]["target"]
        require(any(token == f"resource:{resource}" or token.startswith(f"path:{resource}/") for token in step_targets)
                and path_allowed(resource, path, [f"resource:{resource}", *step_targets]),
                "IMP_SCOPE_VIOLATION", "Operation is outside its Method Step Target")
        require(steps[step_id]["order"] >= order, "IMP_READINESS_FAILED", "Operations must follow continuous Step Order")
        order = steps[step_id]["order"]
        require((resource, path) not in targets, "IMP_READINESS_FAILED", "Use one preconditioned operation per file")
        targets.add((resource, path))
        if operation_digest(operation) in completed:
            continue
        before = next((item for item in snapshots[resource]["entries"] if item["path"] == path), None)
        product_path = (Path(roots[resource]) / path).as_posix()
        require(product_path not in dirty or (resource, path) in owned, "IMP_BASELINE_UNRESOLVED",
                "Target contains user uncommitted changes; preserve them before choosing another operation")
        expected = "absent" if before is None else "sha256:" + before["sha256"]
        require(operation.get("expected_sha256") == expected, "IMP_BASELINE_UNRESOLVED",
                "Operation precondition does not match the actual workspace Baseline")
        kind = operation.get("op")
        if kind == "replace_text":
            require(before is not None, "IMP_BASELINE_UNRESOLVED", "Replacement requires an existing file")
            source = bytes.fromhex(before["content_hex"]).decode("utf-8")
            old, new = operation.get("before"), operation.get("after")
            require(isinstance(old, str) and old and isinstance(new, str) and source.count(old) == 1,
                    "IMP_READINESS_FAILED", "Replacement requires one exact source span")
            product = {"op": "write_text", "path": path, "content": source.replace(old, new, 1)}
        elif kind == "write_text":
            require(isinstance(operation.get("content"), str), "IMP_READINESS_FAILED", "write_text needs text content")
            product = {"op": kind, "path": path, "content": operation["content"]}
        elif kind == "delete":
            require(before is not None, "IMP_BASELINE_UNRESOLVED", "Delete requires an existing exact file")
            product = {"op": kind, "path": path}
        else:
            require(False, "IMP_READINESS_FAILED", "Unsupported product operation")
        reject_secrets(product)
        planned.append((operation, product))
    planned_resources = {operation["resource"] for operation, _ in planned}
    for resource, snapshot in snapshots.items():
        require(snapshot["existed"] or resource in planned_resources,
                "IMP_RESULT_INCOMPLETE",
                "A new Claim Resource requires a planned operation that creates its immutable Result")
    checks = method.get("checks")
    require(isinstance(checks, list) and checks, "IMP_READINESS_FAILED", "Provide applicable local Implementation Checks")
    seen = set()
    for check in checks:
        require(isinstance(check, dict) and check.get("id") not in seen and
                isinstance(check.get("id"), str) and check["id"].startswith("CHK-"),
                "IMP_READINESS_FAILED", "Local Check requires a stable unique CHK ID")
        seen.add(check["id"])
        resource = check.get("resource")
        require(resource in roots, "IMP_SCOPE_VIOLATION",
                "Check Resource is outside Claim Scope")
        kind = check.get("kind")
        if kind == "project_command":
            cwd = safe_path(check.get("cwd", "."), allow_root=True)
            require(not any(item.startswith(f"path:{resource}/")
                            for item in binding.execution_scope),
                    "IMP_SCOPE_VIOLATION",
                    "A project command Check requires the complete claimed Resource")
            target = Path(project_root) / roots[resource] / cwd
            require(target.is_dir() and not target.is_symlink(),
                    "IMP_READINESS_FAILED", "Project Check cwd must be an existing Resource directory")
            timeout = check.get("timeout_seconds", 120)
            require(isinstance(timeout, int) and not isinstance(timeout, bool) and 1 <= timeout <= 300,
                    "IMP_READINESS_FAILED", "Project Check timeout must be 1..300 seconds")
            _project_command(check, require_available=True)
            tool = check["command"][0]
            if tool.startswith("./"):
                executable = target / tool[2:]
                require(executable.is_file() and not executable.is_symlink()
                        and os.access(executable, os.X_OK),
                        "IMP_READINESS_FAILED",
                        "Project-local Check tool is unavailable or not executable")
            require(_sandbox_ready(_sandbox_adapter(tool)), "IMP_READINESS_FAILED",
                    "Project Check requires a supported local network/write sandbox")
        else:
            path = safe_path(check.get("path"))
            require(path_allowed(resource, path, binding.execution_scope),
                    "IMP_SCOPE_VIOLATION", "Check target is outside Claim Scope")
            require(kind in {"contains", "equals", "python_syntax", "json"},
                    "IMP_READINESS_FAILED", "Check must use a declared read-only method")
        require(isinstance(check.get("name"), str) and check["name"].strip(),
                "IMP_READINESS_FAILED", "Check description is required")
        if kind in {"contains", "equals"}:
            require(isinstance(check.get("expected"), str) and check["expected"],
                    "IMP_READINESS_FAILED", "Content Check must have a concrete expected result")
    return planned


def execute(project_root, binding, planned, roots, expected_snapshots, *, guard):
    current = dict(expected_snapshots)
    applied = []
    for operation, product in planned:
        resource = operation["resource"]
        root = Path(project_root) / roots[resource]
        guard()
        require(capture(root, resource) == current[resource], "IMP_BASELINE_UNRESOLVED",
                "Workspace changed after the pre-execution readback")
        apply_operations(root, resource, [product], allowed_scope=binding.execution_scope)
        current[resource] = capture(root, resource)
        applied.append(operation_digest(operation))
    return current, applied


def execute_checks(project_root, method, roots, snapshots):
    records, members = [], []
    runner = Path(__file__).with_name("imp_check.py")
    for check in method["checks"]:
        resource = check["resource"]
        if check["kind"] == "project_command":
            actual, recorded = _project_command(check)
            cwd = safe_path(check.get("cwd", "."), allow_root=True)
            snapshot = snapshots[resource]
            with tempfile.TemporaryDirectory(prefix="sdlc-imp-check-") as temporary:
                isolated = Path(temporary) / "resource"
                _materialize_snapshot(isolated, snapshot)
                sandboxed, sandbox = _sandboxed_command(
                    actual, temporary, check["command"][0],
                )
                execution = run_command(
                    isolated, sandboxed, cwd=cwd,
                    timeout_seconds=check.get("timeout_seconds", 120),
                    environment=_offline_environment(temporary),
                )
            observed = json.loads(execution.raw_bytes)
            evidence_value = {
                "contract": PROJECT_CHECK_CONTRACT,
                "resource": resource,
                "subject_sha256": compute_sha256(canonical(snapshot)),
                "command": list(check["command"]),
                "executed_command": recorded,
                "cwd": cwd,
                "timeout_seconds": check.get("timeout_seconds", 120),
                "isolation": "complete-resource-snapshot",
                "sandbox": sandbox,
                "network": "denied-offline-no-credentials",
                "exit_code": observed["exit_code"],
                "stdout": observed["stdout"],
                "stderr": observed["stderr"],
                "result": execution.result,
            }
            path = cwd
        else:
            path = check["path"]
            target = Path(project_root) / roots[resource] / path
            require(not target.is_symlink() and target.resolve().is_relative_to(Path(project_root).resolve()),
                    "IMP_SCOPE_VIOLATION", "Check path escapes the captured Resource")
            execution = run_command(
                project_root,
                [sys.executable, "-I", "-B", "-S", str(runner), check["kind"], str(target), check.get("expected", "")],
                timeout_seconds=30,
            )
            evidence_value = execution.raw_bytes
        identity = "EVD-" + check["id"]
        members.append(member(identity, evidence_value))
        records.append({
            "id": check["id"], "name": check["name"], "resource": resource,
            "path": path, "result": execution.result, "evidence_member": identity,
        })
    return records, members


def _pre_execution_checklist(stored, state):
    parsed = parse_canonical_artifact(stored.payload.primary_blob)
    summary = require_single_row(
        require_single_table(parsed, GATE_SUMMARY_HEADERS, "Gate Summary"),
        "Gate Summary",
    )
    contract_set = summary["Evaluation Contract Set"].strip()
    require(contract_set and contract_set != "N/A", "IMP_READINESS_FAILED",
            "Pre-execution Evaluation Contract Set must be non-empty")
    baselines = []
    for row in state["resources"]:
        baseline = read_member(stored, row["baseline_member"])
        baselines.append({
            "id": row["id"],
            "resource": row["resource"],
            "baseline_reference": row["baseline_reference"],
            "baseline_member": row["baseline_member"],
            "baseline_sha256": baseline.sha256,
        })
    return contract_set, {
        "implementation_binding": state["binding"],
        "front_matter": {
            "context": parsed.front_matter.get("context"),
            "inputs": parsed.front_matter.get("inputs"),
        },
        "execution_scope": state["claim"]["execution_scope"],
        "input_readiness_check_set": [
            {
                "id": f"IMP-RDY-{index:03d}",
                "check": name,
                "result": "pass",
                "evidence": state["binding"]["reference"],
            }
            for index, name in enumerate(READINESS, 1)
        ],
        "claim_identity": state["claim"],
        "resource_baselines": baselines,
        "implementation_method_contract": state["method"],
    }


def readback_evidence(stored, state, observed_at):
    """Build the fixed Checklist from an already persisted complete Payload."""
    require(is_rfc3339(observed_at), "IMP_READINESS_FAILED",
            "Pre-execution Observed At must use RFC 3339")
    contract_set, checklist = _pre_execution_checklist(stored, state)
    value = {
        "contract": PRE_EXECUTION_CONTRACT,
        "artifact_reference": f"{stored.control.artifact_id}@{stored.control.revision}",
        "observed_at": observed_at,
        "evaluation_contract_set": contract_set,
        "checklist": checklist,
        "checklist_digest": compute_sha256(canonical(checklist)),
        "executor": state["claim"]["owner"],
        "result": "pass",
    }
    evidence = member("EVD-PRE", value)
    record = {
        "contract": PRE_EXECUTION_CONTRACT,
        "evidence_member": evidence.member_id,
        "evidence_sha256": evidence.sha256,
        "observed_at": observed_at,
        "evaluation_contract_set": contract_set,
        "checklist_digest": value["checklist_digest"],
    }
    return evidence, record


def verify_pre_execution_readback(stored, state):
    record = state.get("pre_execution")
    require(isinstance(record, dict) and set(record) == {
        "contract", "evidence_member", "evidence_sha256", "observed_at",
        "evaluation_contract_set", "checklist_digest",
    }, "IMP_READINESS_FAILED", "Pre-execution readback record is incomplete")
    require(record["contract"] == PRE_EXECUTION_CONTRACT
            and record["evidence_member"] == "EVD-PRE"
            and is_rfc3339(record["observed_at"]),
            "IMP_READINESS_FAILED", "Pre-execution readback identity or time is invalid")
    evidence = read_member(stored, "EVD-PRE")
    require(evidence.sha256 == record["evidence_sha256"], "IMP_READINESS_FAILED",
            "Pre-execution Evidence digest changed")
    try:
        value = json.loads(evidence.raw_bytes)
    except (TypeError, json.JSONDecodeError):
        value = None
    require(isinstance(value, dict) and evidence.raw_bytes == canonical(value) and set(value) == {
        "contract", "artifact_reference", "observed_at", "evaluation_contract_set",
        "checklist", "checklist_digest", "executor", "result",
    }, "IMP_READINESS_FAILED", "Pre-execution Evidence shape is invalid")
    contract_set, checklist = _pre_execution_checklist(stored, state)
    expected_digest = compute_sha256(canonical(checklist))
    require(
        value["contract"] == PRE_EXECUTION_CONTRACT
        and value["artifact_reference"] == f"{stored.control.artifact_id}@{stored.control.revision}"
        and value["observed_at"] == record["observed_at"]
        and value["evaluation_contract_set"] == record["evaluation_contract_set"] == contract_set
        and value["checklist"] == checklist
        and value["checklist_digest"] == record["checklist_digest"] == expected_digest
        and value["executor"] == state["claim"]["owner"]
        and value["result"] == "pass",
        "IMP_READINESS_FAILED",
        "Pre-execution Evidence does not match the current fixed Checklist",
    )
    return value

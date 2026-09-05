"""Bounded VFY Method executor with positive command and human-Evidence policy."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
from typing import Any, Mapping

from packages.sdlc_runtime.authority import is_rfc3339

from vfy_common import (
    VfyError,
    canonical_bytes,
    reject_secrets,
    require,
    safe_project_path,
    sha256_value,
)
from vfy_results import build_evidence, record_result

_COMMAND_POLICY = "deterministic-test-v1"
_DENIED_EXECUTABLES = frozenset(
    {
        "sh",
        "bash",
        "zsh",
        "dash",
        "fish",
        "node",
        "perl",
        "ruby",
        "php",
        "powershell",
        "pwsh",
        "curl",
        "wget",
        "scp",
        "ssh",
        "git",
        "pip",
        "pip3",
        "npm",
        "pnpm",
        "yarn",
        "brew",
        "apt",
        "apt-get",
        "dnf",
        "yum",
        "rm",
        "mv",
        "cp",
        "touch",
    }
)
_ALLOWED = frozenset(
    {
        "python",
        "python3",
        "pytest",
        "go",
        "cargo",
        "mvn",
        "mvnw",
        "gradle",
        "gradlew",
    }
)
_SHELL_MARKS = (";", "&&", "||", "`", "$(", ">", "<", "\n", "\r")
_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_./:+,=@%-]+$")


def _resolve_path(project_root: Path, value: str) -> Path:
    relative = safe_project_path(value)
    resolved_root = project_root.resolve()
    target = (resolved_root / relative).resolve()
    require(
        target == resolved_root or resolved_root in target.parents,
        "VFY_METHOD_NOT_READY",
        "Method path escaped the project root",
        details={"path": relative},
    )
    return target


def _json_field(value: Any, dotted_path: str) -> Any:
    current = value
    for part in dotted_path.split("."):
        if isinstance(current, Mapping) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            raise VfyError(
                "VFY_METHOD_EXECUTION_FAILED",
                "JSON field does not exist",
                details={"field": dotted_path},
            )
    return current


def _workspace_digest(root: Path) -> str:
    rows: list[tuple[str, str, int]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in {".git", ".sdlc", "__pycache__"} for part in relative.parts):
            continue
        if path.is_symlink():
            rows.append((relative.as_posix(), "SYMLINK:" + os.readlink(path), 0))
        elif path.is_file():
            rows.append(
                (
                    relative.as_posix(),
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                    path.stat().st_mode & 0o777,
                )
            )
        elif path.is_dir():
            rows.append((relative.as_posix() + "/", "DIR", path.stat().st_mode & 0o777))
    return sha256_value(rows)


def _execute_builtin(
    project_root: Path, procedure: Mapping[str, Any]
) -> tuple[str, dict[str, Any]]:
    kind = procedure["kind"]
    if kind == "file_exists":
        path = _resolve_path(project_root, str(procedure["path"]))
        exists = path.is_file() or path.is_dir()
        return ("pass" if exists else "fail"), {
            "kind": kind,
            "path": str(procedure["path"]),
            "exists": exists,
        }
    if kind == "file_not_exists":
        path = _resolve_path(project_root, str(procedure["path"]))
        exists = path.exists()
        return ("pass" if not exists else "fail"), {
            "kind": kind,
            "path": str(procedure["path"]),
            "exists": exists,
        }
    if kind == "sha256_equals":
        path = _resolve_path(project_root, str(procedure["path"]))
        require(
            path.is_file() and not path.is_symlink(),
            "VFY_METHOD_EXECUTION_FAILED",
            "Digest procedure requires an existing regular file",
            details={"path": str(procedure["path"])},
        )
        actual = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        expected = str(procedure.get("expected", ""))
        return ("pass" if actual == expected else "fail"), {
            "kind": kind,
            "path": str(procedure["path"]),
            "actual": actual,
            "expected": expected,
        }
    if kind == "json_field_equals":
        path = _resolve_path(project_root, str(procedure["path"]))
        require(
            path.is_file() and not path.is_symlink(),
            "VFY_METHOD_EXECUTION_FAILED",
            "JSON procedure requires an existing regular file",
            details={"path": str(procedure["path"])},
        )
        parsed = json.loads(path.read_text(encoding="utf-8"))
        field = str(procedure.get("field", ""))
        actual = _json_field(parsed, field)
        expected = procedure.get("expected")
        return ("pass" if actual == expected else "fail"), {
            "kind": kind,
            "path": str(procedure["path"]),
            "field": field,
            "actual": actual,
            "expected": expected,
        }
    if kind == "evidence_review":
        value = procedure.get("candidate_evidence")
        require(
            isinstance(value, Mapping),
            "VFY_EVIDENCE_INSUFFICIENT",
            "Embedded Evidence review requires immutable source facts",
        )
        expected_subjects = list(procedure.get("subject_references", []))
        actual_subjects = list(value.get("subject_references", []))
        passed = (
            value.get("immutable") is True
            and isinstance(value.get("digest"), str)
            and str(value["digest"]).startswith("sha256:")
            and actual_subjects == expected_subjects
        )
        return ("pass" if passed else "fail"), {
            "kind": kind,
            "source_digest": value.get("digest"),
            "immutable": value.get("immutable"),
            "expected_subjects": expected_subjects,
            "actual_subjects": actual_subjects,
        }
    raise VfyError(
        "VFY_METHOD_NOT_READY",
        "Procedure requires a different execution path",
        details={"kind": kind},
    )


def _validate_command(argv: list[str]) -> None:
    executable = Path(argv[0]).name.lower()
    require(
        executable not in _DENIED_EXECUTABLES and executable in _ALLOWED,
        "VFY_METHOD_NOT_READY",
        "Command executable is outside the positive deterministic allowlist",
        details={"executable": executable},
    )
    require(
        all(
            token
            and not PurePosixPath(token).is_absolute()
            and not any(mark in token for mark in _SHELL_MARKS)
            and _SAFE_TOKEN.fullmatch(token) is not None
            for token in argv[1:]
        ),
        "VFY_METHOD_NOT_READY",
        "Command arguments contain shell syntax, absolute paths or unsafe tokens",
    )
    lowered = [item.lower() for item in argv[1:]]
    require(
        "-c" not in lowered
        and "--eval" not in lowered
        and "-e" not in lowered
        and "install" not in lowered
        and "publish" not in lowered
        and "deploy" not in lowered
        and "release" not in lowered,
        "VFY_METHOD_NOT_READY",
        "Inline arbitrary code, install, publish, deploy and release are forbidden",
    )
    if executable.startswith("python"):
        require(
            len(argv) >= 3 and argv[1:3] == ["-m", "unittest"],
            "VFY_METHOD_NOT_READY",
            "Python command policy only permits `python -m unittest ...`",
        )
    elif executable == "pytest":
        require(
            all(not item.startswith("--basetemp=/") for item in argv[1:]),
            "VFY_METHOD_NOT_READY",
            "pytest paths must remain in the isolated copy",
        )
    elif executable == "go":
        require(len(argv) >= 2 and argv[1] == "test", "VFY_METHOD_NOT_READY", "Only `go test` is allowed")
    elif executable == "cargo":
        require(len(argv) >= 2 and argv[1] == "test", "VFY_METHOD_NOT_READY", "Only `cargo test` is allowed")
    elif executable in {"mvn", "mvnw", "gradle", "gradlew"}:
        require("test" in lowered, "VFY_METHOD_NOT_READY", "Build-tool command must be an explicit test goal")


def _copy_workspace(source: Path, destination: Path) -> None:
    def ignore(_directory: str, names: list[str]):
        return [name for name in names if name in {".git", ".sdlc", "__pycache__", ".venv", "node_modules"}]

    for path in source.rglob("*"):
        if path.is_symlink() and not any(part in {".git", ".sdlc", ".venv", "node_modules", "__pycache__"}
                                       for part in path.relative_to(source).parts):
            _resolve_path(source, path.relative_to(source).as_posix())
    shutil.copytree(source, destination, symlinks=False, ignore=ignore)
    (destination / ".tmp").mkdir(exist_ok=True)
    (destination / ".home").mkdir(exist_ok=True)


def _sandbox_argv(argv: list[str], root: Path, cwd: Path) -> list[str]:
    """Apply OS-enforced network and write boundaries; unavailable means stop."""
    root = root.resolve()
    if sys.platform == "darwin" and Path("/usr/bin/sandbox-exec").is_file():
        profile = (
            '(version 1)(allow default)(deny network*)(deny file-write*)'
            f'(allow file-write* (subpath {json.dumps(str(root))}) (literal "/dev/null"))'
        )
        return ["/usr/bin/sandbox-exec", "-p", profile, *argv]
    bubblewrap = shutil.which("bwrap") if sys.platform.startswith("linux") else None
    require(bubblewrap is not None, "VFY_METHOD_NOT_READY",
            "OS sandbox is unavailable; command execution remains pending",
            status="action_required")
    return [str(bubblewrap), "--die-with-parent", "--unshare-all", "--ro-bind", "/", "/",
            "--bind", str(root), str(root), "--proc", "/proc", "--dev", "/dev",
            "--chdir", str(cwd.resolve()), "--", *argv]


def _bounded_process(
    argv: list[str],
    *,
    cwd: Path,
    root: Path,
    timeout: int,
    max_output: int,
) -> tuple[int, str, str, bool]:
    stdout_path = root / ".stdout"
    stderr_path = root / ".stderr"

    def limits() -> None:
        resource.setrlimit(resource.RLIMIT_FSIZE, (max_output, max_output))
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    environment = {
        "PATH": os.environ.get("PATH", ""),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "NO_COLOR": "1",
        "HOME": str(root / ".home"),
        "TMPDIR": str(root / ".tmp"),
        "XDG_CACHE_HOME": str(root / ".home/cache"),
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_CONFIG_NOSYSTEM": "1",
        "http_proxy": "http://127.0.0.1:9",
        "https_proxy": "http://127.0.0.1:9",
        "HTTP_PROXY": "http://127.0.0.1:9",
        "HTTPS_PROXY": "http://127.0.0.1:9",
        "NO_PROXY": "",
        "PYTEST_ADDOPTS": "-p no:cacheprovider",
        "GOPROXY": "off",
        "GOSUMDB": "off",
        "CARGO_NET_OFFLINE": "true",
    }
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        process = subprocess.Popen(
            _sandbox_argv(argv, root, cwd),
            cwd=cwd,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            shell=False,
            start_new_session=True,
            preexec_fn=limits if os.name == "posix" else None,
        )
        timed_out = False
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            code = process.wait(timeout=10)
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    stdout_raw = stdout_path.read_bytes()[:max_output]
    stderr_raw = stderr_path.read_bytes()[:max_output]
    require(not (code != 0 and (b"sandbox-exec: sandbox_apply:" in stderr_raw
                                or stderr_raw.startswith(b"bwrap:"))),
            "VFY_METHOD_NOT_READY", "OS sandbox could not be activated",
            status="action_required")
    return (
        code,
        stdout_raw.decode("utf-8", errors="replace"),
        stderr_raw.decode("utf-8", errors="replace"),
        timed_out,
    )


def _execute_command(
    project_root: Path,
    procedure: Mapping[str, Any],
    *,
    allow_commands: bool,
) -> tuple[str, dict[str, Any]]:
    require(
        allow_commands,
        "VFY_METHOD_NOT_READY",
        "Command execution requires explicit invocation authorization",
        status="action_required",
    )
    require(
        procedure.get("policy") == _COMMAND_POLICY
        and procedure.get("workspace") == "isolated-copy"
        and procedure.get("network") == "disabled",
        "VFY_METHOD_NOT_READY",
        "Command requires the persisted deterministic isolated-copy policy",
    )
    argv = [str(item) for item in procedure["argv"]]
    _validate_command(argv)
    timeout = int(procedure.get("timeout_seconds", 120))
    max_output = int(procedure.get("max_output_bytes", 262144))
    source_before = _workspace_digest(project_root)
    with tempfile.TemporaryDirectory(prefix="vfy-command-") as directory:
        isolated = Path(directory) / "workspace"
        _copy_workspace(project_root, isolated)
        cwd = isolated
        if procedure.get("cwd"):
            cwd = _resolve_path(isolated, str(procedure["cwd"]))
        require(cwd.is_dir(), "VFY_METHOD_NOT_READY", "Isolated command cwd does not exist")
        isolated_before = _workspace_digest(isolated)
        code, stdout, stderr, timed_out = _bounded_process(
            argv,
            cwd=cwd,
            root=isolated,
            timeout=timeout,
            max_output=max_output,
        )
        isolated_after = _workspace_digest(isolated)
    source_after = _workspace_digest(project_root)
    require(
        source_before == source_after,
        "VFY_METHOD_EXECUTION_FAILED",
        "Command changed the authoritative source workspace",
        details={"source_before": source_before, "source_after": source_after},
    )
    observed = {
        "kind": "command",
        "policy": _COMMAND_POLICY,
        "workspace": "isolated-copy",
        "network": "disabled",
        "containment": "os-sandbox",
        "argv": argv,
        "cwd": str(procedure.get("cwd") or "."),
        "exit_code": code,
        "stdout": stdout,
        "stderr": stderr,
        "timed_out": timed_out,
        "source_before": source_before,
        "source_after": source_after,
        "isolated_before": isolated_before,
        "isolated_after": isolated_after,
        "output_budget_bytes": max_output,
    }
    reject_secrets(observed)
    return ("pass" if code == 0 and not timed_out else "fail"), observed


def _manual_result(
    method: Mapping[str, Any], manual_observation: Mapping[str, Any] | None
) -> tuple[str, dict[str, Any], str, str, Mapping[str, Any]]:
    require(
        isinstance(manual_observation, Mapping),
        "VFY_METHOD_NOT_READY",
        "Manual/hybrid Method is waiting for a real evaluator observation",
        status="action_required",
        details={"method_id": method["id"]},
    )
    decision = str(manual_observation.get("decision", "")).strip()
    evaluator = str(manual_observation.get("evaluator_identity", "")).strip()
    observed_at = str(manual_observation.get("observed_at", "")).strip()
    observed = manual_observation.get("observed")
    scenario = str(manual_observation.get("scenario", "")).strip()
    expected = str(manual_observation.get("expected", "")).strip()
    scope = manual_observation.get("scope")
    source = manual_observation.get("evidence")
    require(
        decision in {"pass", "fail"},
        "VFY_EVIDENCE_INSUFFICIENT",
        "Manual decision must be pass or fail",
        details={"method_id": method["id"]},
    )
    require(
        evaluator == method["executor_identity"],
        "VFY_EVIDENCE_INSUFFICIENT",
        "Manual evaluator differs from the frozen Method executor identity",
        details={"method_id": method["id"]},
    )
    require(
        is_rfc3339(observed_at)
        and bool(scenario)
        and bool(expected)
        and isinstance(scope, (str, list, dict))
        and bool(scope)
        and isinstance(observed, (str, dict, list))
        and bool(observed)
        and isinstance(source, Mapping)
        and set(source) == {"reference", "sha256"}
        and isinstance(source.get("reference"), str)
        and bool(source["reference"])
        and isinstance(source.get("sha256"), str)
        and str(source["sha256"]).startswith("sha256:"),
        "VFY_EVIDENCE_INSUFFICIENT",
        "Manual Evidence requires time, scenario, expected, scope, observed facts and immutable source reference/digest",
        details={"method_id": method["id"]},
    )
    payload = {
        "scenario": scenario,
        "expected": expected,
        "scope": deepcopy_json(scope),
        "observed": deepcopy_json(observed),
    }
    reject_secrets(payload)
    return decision, payload, evaluator, observed_at, source


def deepcopy_json(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True))


def execute_method(
    method: Mapping[str, Any],
    *,
    project_root: Path,
    evidence_sequence: int,
    allow_commands: bool = False,
    manual_observation: Mapping[str, Any] | None = None,
    environment: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    disposition = str(method["disposition"])
    require(
        disposition in {"required", "embedded"},
        "VFY_METHOD_NOT_READY",
        "Only required or embedded Methods execute",
        details={"method_id": method["id"]},
    )
    mode = str(method["execution_mode"])
    source_evidence = None
    if mode in {"manual", "hybrid"}:
        result, observed, executor, observed_at, source_evidence = _manual_result(
            method, manual_observation
        )
    else:
        procedure = method["procedure"]
        if procedure["kind"] == "command":
            result, observed = _execute_command(
                project_root, procedure, allow_commands=allow_commands
            )
        else:
            source_before = _workspace_digest(project_root)
            result, observed = _execute_builtin(project_root, procedure)
            source_after = _workspace_digest(project_root)
            require(
                source_before == source_after,
                "VFY_METHOD_EXECUTION_FAILED",
                "Read-only Method changed the product workspace",
            )
            observed["source_before"] = source_before
            observed["source_after"] = source_after
        executor = str(method["executor_identity"])
        observed_at = None

    evidence = build_evidence(
        evidence_id=f"EVD-{evidence_sequence:03d}",
        method=method,
        result=result,
        observed=observed,
        actual_subject_references=list(method["subject_references"]),
        environment=dict(environment or method.get("environment") or {}),
        executor_identity=executor,
        observed_at=observed_at,
        source_evidence=source_evidence,
    )
    method_result = record_result(
        method,
        result=result,
        actual_result=json.dumps(observed, ensure_ascii=False, sort_keys=True),
        evidence_references=[evidence["reference"]],
    )
    return method_result, evidence

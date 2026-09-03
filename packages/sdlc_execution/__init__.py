from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Mapping, Sequence


class ExecutionError(RuntimeError):
    pass


_SECRET_PATTERNS = (
    re.compile(r"(?i)(?:token|password|passwd|secret|api[_-]?key)\s*[:=]\s*[^\s]{6,}"),
    re.compile(r"\b(?:ghp_|github_pat_|sk-[A-Za-z0-9_-]{8,})[A-Za-z0-9_-]+"),
)


@dataclass(frozen=True)
class ExecutionEvidence:
    reference: str
    raw_bytes: bytes
    result: str
    exit_code: int | None = None


def _evidence(prefix: str, payload: dict, result: str, exit_code: int | None = None) -> ExecutionEvidence:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return ExecutionEvidence(f"{prefix}@sha256:{digest}", raw, result, exit_code)


def _reject_secret(text: str) -> None:
    if any(pattern.search(text) for pattern in _SECRET_PATTERNS):
        raise ExecutionError("command evidence contains a potential secret")


def run_command(
    root: str | Path,
    command: Sequence[str],
    *,
    cwd: str = ".",
    timeout_seconds: int | float = 120,
    environment: Mapping[str, str] | None = None,
) -> ExecutionEvidence:
    base = Path(root).resolve()
    work = (base / cwd).resolve()
    try:
        work.relative_to(base)
    except ValueError as exc:
        raise ExecutionError("command cwd escapes project root") from exc
    if not work.exists() or not work.is_dir():
        raise ExecutionError("command cwd does not exist")
    if not command or not all(isinstance(item, str) and item for item in command):
        raise ExecutionError("command must be a non-empty string sequence")
    try:
        completed = subprocess.run(
            list(command), cwd=work, text=True, capture_output=True,
            timeout=float(timeout_seconds), check=False,
            env=dict(environment) if environment is not None else None,
        )
        stdout, stderr = completed.stdout, completed.stderr
        _reject_secret(stdout + "\n" + stderr)
        result = "pass" if completed.returncode == 0 else "fail"
        return _evidence("command", {
            "command": list(command), "cwd": str(Path(cwd).as_posix()),
            "exit_code": completed.returncode, "stdout": stdout, "stderr": stderr,
            "result": result,
        }, result, completed.returncode)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        _reject_secret(stdout + "\n" + stderr)
        return _evidence("command", {
            "command": list(command), "cwd": str(Path(cwd).as_posix()),
            "exit_code": None, "stdout": stdout, "stderr": stderr,
            "result": "fail", "timeout": True,
        }, "fail", None)


def manual_evidence(*, executor: str, statement: str, observed: str, result: str) -> ExecutionEvidence:
    if not executor.strip() or not statement.strip() or not observed.strip():
        raise ExecutionError("manual evidence fields must be non-empty")
    if result not in {"pass", "fail"}:
        raise ExecutionError("manual evidence result must be pass or fail")
    _reject_secret(statement + "\n" + observed)
    return _evidence("manual", {
        "executor": executor, "statement": statement, "observed": observed, "result": result,
    }, result)

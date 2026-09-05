"""RLS process receipts; redact in memory before any log or JSON persistence."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any, Iterable

REDACTION_POLICY = "sdlc-ai-spec/validation-redaction/v2"
REDACTED = "[REDACTED]"
# Do not match authority, authorization_id, source_sha, or other audit bindings.
_SECRET_KEY = re.compile(
    r"^(?:.*[_-])?(?:password|passwd|secret|token|cookie|credential|api[_-]?key|"
    r"private[_-]?key|access[_-]?key)(?:[_-]value)?$|^(?:proxy[_-]?)?authorization$",
    re.IGNORECASE,
)
_PRIVATE_KEY = re.compile(
    r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----.*?"
    r"(?:-----END (?:[A-Z0-9]+ )*PRIVATE KEY-----|$)", re.DOTALL,
)
_TOKEN = re.compile(
    r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{16,})"
)
_AUTH = re.compile(r"\b(?:Bearer|Basic)\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
# JSON, key=value, query parameters, and command option assignments.
_ASSIGNMENT = re.compile(
    r'''(?ix)(?<![A-Za-z0-9_-])(?P<key>["']?(?:(?:[A-Za-z0-9_-]*[_-])?(?:password|passwd|secret|token|cookie|credential|api[_-]?key|private[_-]?key|access[_-]?key)|(?:proxy[_-]?)?authorization)["']?\s*[:=]\s*)'''
    r'''(?P<value>\[REDACTED\]|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[^\s,;&}\]\r\n]+)'''
)
_URL_CREDENTIALS = re.compile(r"(\b[a-z][a-z0-9+.-]*://)[^\s/@]+:[^\s/@]+@", re.IGNORECASE)
_HEADER = re.compile(r"(?im)^\s*((?:proxy-)?authorization|(?:set-)?cookie)\s*:\s*[^\r\n]+")


def digest(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


# A context is scoped to one captured operation/object. Never persist its values.
_MAX_DEPTH = 128
_MAX_VALUES = 2048
_JSON_START = re.compile(r'[\[{"]')


class _Pairs(list):
    """Keep duplicate JSON keys during discovery; none may hide a credential."""


def _text(raw: bytes | str | None) -> str:
    return raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw or ""


def _add_secret(value, values):
    if isinstance(value, bytes):
        value = _text(value)
    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        value = str(value)
        if value and value != REDACTED:
            values.add(value)
            if len(values) > _MAX_VALUES:
                raise ValueError("redaction context exceeds its safe limit")


def _depth(depth):
    if depth > _MAX_DEPTH:
        raise ValueError("redaction input exceeds its safe nesting limit")


def _discover_argv(argv, values, depth=0):
    _depth(depth)
    following = False
    for raw in argv:
        item = str(raw)
        if following:
            _add_secret(item, values)
            following = False
        key, separator, value = item.lstrip("-").partition("=")
        if _SECRET_KEY.fullmatch(key):
            if separator:
                _add_secret(value, values)
            else:
                following = True
        # A -c program is code, not a captured credential object. Inspect argv
        # payloads only when the entire argument is JSON, never infer variable
        # names in source snippets as password values.
        _discover_syntax(item, values)
        if item.lstrip().startswith(("{", "[")):
            try:
                parsed = json.loads(item, object_pairs_hook=_Pairs)
            except (ValueError, RecursionError):
                parsed = None
            if parsed is not None:
                _discover_value(parsed, values, depth + 1)


def _discover_value(value, values, depth=0, sensitive=False):
    _depth(depth)
    if isinstance(value, (dict, _Pairs)):
        for key, item in (value.items() if isinstance(value, dict) else value):
            if key == "argv" and isinstance(item, (list, tuple)) and not sensitive:
                _discover_argv(item, values, depth + 1)
            else:
                _discover_value(item, values, depth + 1,
                                sensitive or bool(_SECRET_KEY.fullmatch(str(key))))
    elif isinstance(value, (list, tuple)):
        for item in value:
            _discover_value(item, values, depth + 1, sensitive)
    else:
        if sensitive:
            _add_secret(value, values)
        if isinstance(value, (str, bytes, Path)):
            _discover_text(_text(value) if isinstance(value, bytes) else str(value),
                           values, depth + 1)


def _discover_text(text, values, depth=0):
    _depth(depth)
    # Scan complete objects in JSON, JSONL and mixed diagnostic output. Parsing
    # here is discovery only; malformed surrounding prose is not an authority.
    decoder = json.JSONDecoder(object_pairs_hook=_Pairs)
    position = 0
    while position < len(text):
        match = _JSON_START.search(text, position)
        if not match:
            break
        position = match.start()
        try:
            value, end = decoder.raw_decode(text, position)
        except (ValueError, RecursionError):
            position += 1
            continue
        _discover_value(value, values, depth + 1)
        position = end
    for match in _ASSIGNMENT.finditer(text):
        raw = match["value"]
        if raw[:1] in {"{", "["}:
            continue  # Objects were handled above, not the literal '{' as a secret.
        if raw.startswith('"'):
            try:
                raw = json.loads(raw)
            except ValueError:
                raw = raw[1:-1] if raw.endswith('"') else raw[1:]
        elif raw.startswith("'"):
            raw = (raw[1:-1] if raw.endswith("'") else raw[1:]).replace("\\'", "'").replace("\\\\", "\\")
        _add_secret(raw, values)
    _discover_syntax(text, values)


def _discover_syntax(text, values):
    for match in _TOKEN.finditer(text):
        _add_secret(match[0], values)
    for match in _AUTH.finditer(text):
        _add_secret(match[0], values)
        _add_secret(match[0].split(None, 1)[1], values)
    for match in _PRIVATE_KEY.finditer(text):
        _add_secret(match[0], values)
    for match in _URL_CREDENTIALS.finditer(text):
        credentials = match[0][len(match[1]):-1]
        _add_secret(credentials.split(":", 1)[1], values)
    for match in _HEADER.finditer(text):
        _add_secret(match[0].split(":", 1)[1].strip(), values)


def _known_secrets(environment: dict[str, str] | None = None) -> tuple[str, ...]:
    # Explicit labels, even on short values, take precedence over entropy guesses.
    values = set()
    for key, value in (environment or {}).items():
        if _SECRET_KEY.fullmatch(str(key)):
            _add_secret(value, values)
    return tuple(sorted(values, key=lambda item: (-len(item), item)))


class _Redactor:
    """Two-pass operation: finish discovery before touching any output sink."""

    def __init__(self, *sources, secrets=(), argv=()):
        values = set()
        for value in secrets:
            _add_secret(value, values)
        _discover_argv(argv, values)
        for source in sources:
            _discover_value(source, values)
        # Simultaneous longest-first substitution avoids cascading replacements,
        # overlaps and corruption of the [REDACTED] marker on repeated calls.
        alternatives = [re.escape(value) for value in
                        sorted(values | {REDACTED}, key=lambda item: (-len(item), item))]
        self._literal = re.compile("|".join(alternatives))
        self._values = values

    def text(self, text, depth=0):
        _depth(depth)
        duplicates = []
        def pairs(items):
            result = dict(items)
            if len(result) != len(items):
                duplicates.append(True)
            return result
        decoder = json.JSONDecoder(object_pairs_hook=pairs)
        if text.lstrip().startswith(("{", "[", '"')):
            try:
                parsed = decoder.decode(text)
            except (ValueError, RecursionError):
                parsed = None
            if isinstance(parsed, (dict, list, str)):
                safe = self.value(parsed, depth + 1)
                # A discarded duplicate key can contain an earlier credential.
                unchanged = not duplicates and safe == parsed and self._literal.sub(lambda match: REDACTED, text) == text
                return text if unchanged else json.dumps(safe, ensure_ascii=False) + ("\n" if text.endswith("\n") else "")
        # Handle JSONL and JSON embedded in prose without corrupting escaping.
        # Surrounding non-JSON text is still scrubbed below with the same context.
        position, copied, parts = 0, 0, []
        while position < len(text):
            match = _JSON_START.search(text, position)
            if not match:
                break
            position = match.start()
            try:
                duplicates.clear()
                parsed, end = decoder.raw_decode(text, position)
            except (ValueError, RecursionError):
                position += 1
                continue
            safe = self.value(parsed, depth + 1)
            fragment = text[position:end]
            unchanged = not duplicates and safe == parsed and self._literal.sub(lambda match: REDACTED, fragment) == fragment
            parts.extend([text[copied:position], fragment if unchanged else json.dumps(safe, ensure_ascii=False)])
            position = copied = end
        text = "".join(parts) + text[copied:]
        text = self._literal.sub(lambda match: REDACTED, text)
        text = _PRIVATE_KEY.sub(REDACTED, text)
        text = _TOKEN.sub(REDACTED, text)
        text = _AUTH.sub(REDACTED, text)
        text = _URL_CREDENTIALS.sub(lambda match: match[1] + REDACTED + "@", text)
        text = _HEADER.sub(lambda match: match[1] + ": " + REDACTED, text)
        def assignment(match):
            value = match["value"]
            quote = value[0] if value[:1] in {"'", '"'} else ""
            return match["key"] + quote + REDACTED + quote
        return _ASSIGNMENT.sub(assignment, text)

    def argv(self, argv, depth=0):
        _depth(depth)
        output, following = [], False
        for raw in argv:
            item = str(raw)
            if following:
                output.append(REDACTED)
                following = False
                continue
            output.append(self.text(item, depth + 1))
            key = item.lstrip("-")
            following = "=" not in key and bool(_SECRET_KEY.fullmatch(key))
        return output

    def value(self, value, depth=0):
        _depth(depth)
        if isinstance(value, dict):
            return {self.text(str(key), depth + 1): (
                REDACTED if _SECRET_KEY.fullmatch(str(key)) else
                self.argv(item, depth + 1) if key == "argv" and isinstance(item, (list, tuple)) else
                self.value(item, depth + 1)
            ) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self.value(item, depth + 1) for item in value]
        if isinstance(value, (str, bytes, Path)):
            return self.text(_text(value) if isinstance(value, bytes) else str(value), depth + 1)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and str(value) in self._values:
            return REDACTED
        return value


def redact_text(text: str, secrets: Iterable[str] = ()) -> str:
    return _Redactor(text, secrets=secrets).text(text)


def redact_argv(argv: Iterable[Any], secrets: Iterable[str] = ()) -> list[str]:
    argv = list(map(str, argv))
    return _Redactor(argv=argv, secrets=secrets).argv(argv)


def redact_value(value: Any, secrets: Iterable[str] = ()) -> Any:
    return _Redactor(value, secrets=secrets).value(value)


def redact_receipt(value: Any, environment: dict[str, str] | None = None) -> Any:
    return redact_value(value, _known_secrets({**os.environ, **(environment or {})}))


def _stream(raw: bytes | str | None, secrets: Iterable[str]) -> bytes:
    return redact_text(_text(raw), secrets).encode("utf-8")


def git(root, *args):
    environment = {**os.environ, "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0"}
    argv = ["git", "-C", str(root), *args]
    try:
        result = subprocess.run(argv, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60,
                                env=environment)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raw = [_text(getattr(exc, "stdout", None)), _text(getattr(exc, "stderr", None)), str(exc)]
        redactor = _Redactor(raw, argv=argv, secrets=_known_secrets(environment))
        raise RuntimeError("Git read failed: " + redactor.text(raw[-1])) from None
    if result.returncode:
        redactor = _Redactor(result.stdout, result.stderr, argv=argv,
                             secrets=_known_secrets(environment))
        raise RuntimeError("Git read failed: " + redactor.text(_text(result.stderr))) from None
    return result.stdout.decode().strip()


def source_state(root):
    return {"root": git(root, "rev-parse", "--show-toplevel"), "sha": git(root, "rev-parse", "HEAD"),
            "tree": git(root, "rev-parse", "HEAD^{tree}"), "parents": git(root, "show", "-s", "--format=%P", "HEAD").split(),
            "branch": git(root, "branch", "--show-current"),
            "status": git(root, "status", "--porcelain=v1", "--untracked-files=all")}


def _check_stream_bindings(value):
    if isinstance(value, dict):
        if value.get("stream_hashes_bind") == "ARCHIVED_REDACTED_UTF8_BYTES":
            for stream in ("stdout", "stderr"):
                text = value.get(stream)
                if not isinstance(text, str) or digest(text.encode("utf-8")) != value.get(stream + "_sha256"):
                    raise ValueError("nested receipt must be redacted before its stream hashes are frozen")
        for item in value.values():
            _check_stream_bindings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _check_stream_bindings(item)


def _write_safe_json(path, safe):
    # Private sink: caller has already applied one complete context. Do not run
    # another scope that could change archived streams after their hashes exist.
    _check_stream_bindings(safe)
    raw = (json.dumps(safe, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def write_json(path, value):
    """Collect from the whole object before masking any sibling or nested log."""
    _write_safe_json(path, redact_receipt(value))


def run_step(root, name, argv, output, *, timeout=1800, attempt=1, environment=None, track_source=True):
    root = Path(root).resolve()
    output = Path(output).resolve()
    argv = list(map(str, argv))  # Execute the original arguments, exactly once.
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name) or ".." in name:
        raise ValueError("invalid receipt step name")
    if type(attempt) is not int or attempt < 1:
        raise ValueError("invalid receipt attempt")
    if track_source and output.is_relative_to(root):
        raise ValueError("receipt output must be outside the tracked source")
    child_environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "GIT_OPTIONAL_LOCKS": "0",
                         "GIT_TERMINAL_PROMPT": "0", **(environment or {})}
    try:
        before = source_state(root) if track_source else None
    except Exception as exc:
        redactor = _Redactor(str(exc), argv=argv, secrets=_known_secrets(child_environment))
        raise RuntimeError("source-state read failed: " + redactor.text(str(exc))) from None
    started, started_at = time.monotonic(), now()
    stdout, stderr, code = b"", b"", 127
    try:
        completed = subprocess.run(argv, cwd=root, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, env=child_environment)
        code, stdout, stderr = completed.returncode, completed.stdout, completed.stderr
    except subprocess.TimeoutExpired as exc:
        code, stdout, stderr = 124, exc.stdout or b"", _text(exc.stderr) + "\nprocess timeout"
    except OSError as exc:
        stderr = str(exc)
    try:
        after = source_state(root) if track_source else None
    except Exception as exc:
        redactor = _Redactor(stdout, stderr, str(exc), argv=argv,
                             secrets=_known_secrets(child_environment))
        raise RuntimeError("source-state read failed: " + redactor.text(str(exc))) from None
    raw = {"name": name, "argv": argv, "cwd": str(root), "output": str(output),
           "stdout": _text(stdout), "stderr": _text(stderr),
           "source_before": before, "source_after": after}
    # Both complete streams, metadata and argv contribute before the FIRST write.
    redactor = _Redactor(raw, secrets=_known_secrets(child_environment))
    safe = redactor.value(raw)
    if safe["name"] != name or safe["cwd"] != str(root) or safe["output"] != str(output):
        raise ValueError("credential-bearing receipt locators cannot be archived")
    safe_stdout, safe_stderr = safe["stdout"].encode("utf-8"), safe["stderr"].encode("utf-8")
    stdout_path = output / f"{name}-attempt-{attempt}.stdout.log"
    stderr_path = output / f"{name}-attempt-{attempt}.stderr.log"
    result = {"name": name, "attempt": attempt, "argv": safe["argv"], "cwd": safe["cwd"],
              "started_at": started_at, "finished_at": now(), "duration_ms": round((time.monotonic()-started)*1000),
              "exit_code": code, "stdout": safe["stdout"], "stderr": safe["stderr"],
              "stdout_log": str(stdout_path), "stderr_log": str(stderr_path),
              "stdout_sha256": digest(safe_stdout), "stderr_sha256": digest(safe_stderr),
              "redaction_policy": REDACTION_POLICY, "redaction_applied": safe != raw or
                  safe_stdout != (stdout.encode() if isinstance(stdout, str) else stdout) or
                  safe_stderr != (stderr.encode() if isinstance(stderr, str) else stderr),
              "stream_hashes_bind": "ARCHIVED_REDACTED_UTF8_BYTES",
              "source_before": safe["source_before"], "source_after": safe["source_after"],
              "source_unchanged": before == after, "success": code == 0 and before == after}
    output.mkdir(parents=True, exist_ok=True)
    stdout_path.write_bytes(safe_stdout)
    stderr_path.write_bytes(safe_stderr)
    _write_safe_json(output / f"{name}-attempt-{attempt}.receipt.json", result)
    return result

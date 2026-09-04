from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Iterable, Mapping, Sequence


class ResourceError(RuntimeError):
    pass


@dataclass(frozen=True)
class ResourceSnapshot:
    resource_id: str
    reference: str
    entries: tuple[dict[str, str], ...]

    @property
    def paths(self) -> tuple[str, ...]:
        return tuple(item["path"] for item in self.entries)

    @property
    def raw_bytes(self) -> bytes:
        return json.dumps(
            {"resource": self.resource_id, "entries": list(self.entries)},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")


@dataclass(frozen=True)
class ResourceChange:
    resource_id: str
    before: ResourceSnapshot
    after: ResourceSnapshot
    changed_paths: tuple[str, ...]


def _safe_rel(path: str) -> str:
    value = Path(path)
    if value.is_absolute() or ".." in value.parts:
        raise ResourceError(f"path escapes resource root: {path}")
    normalized = value.as_posix()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized or normalized == ".":
        raise ResourceError("resource path is empty")
    if normalized == ".sdlc" or normalized.startswith(".sdlc/") or normalized == ".git" or normalized.startswith(".git/"):
        raise ResourceError(f"runtime/control path is not a product resource: {path}")
    return normalized


def _snapshot_entries(root: Path) -> tuple[dict[str, str], ...]:
    entries: list[dict[str, str]] = []
    if not root.exists():
        return ()
    for path in sorted((item for item in root.rglob("*") if item.is_file()), key=lambda p: p.as_posix()):
        rel = path.relative_to(root).as_posix()
        if rel == ".git" or rel.startswith(".git/") or rel == ".sdlc" or rel.startswith(".sdlc/"):
            continue
        raw = path.read_bytes()
        entries.append({
            "path": rel,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "content_hex": raw.hex(),
        })
    return tuple(entries)


def capture_snapshot(root: str | Path, resource_id: str = "repo") -> ResourceSnapshot:
    base = Path(root).resolve()
    entries = _snapshot_entries(base)
    canonical = json.dumps(
        {"resource": resource_id, "entries": [{"path": i["path"], "sha256": i["sha256"]} for i in entries]},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    return ResourceSnapshot(resource_id, f"snapshot:{resource_id}@sha256:{digest}", entries)


def _allowed(resource_id: str, rel: str, allowed_scope: Sequence[str]) -> bool:
    if f"resource:{resource_id}" not in allowed_scope:
        return False
    path_scopes = [item[len(f"path:{resource_id}/"):].rstrip("/") for item in allowed_scope if item.startswith(f"path:{resource_id}/")]
    if not path_scopes:
        return True
    return any(rel == prefix or rel.startswith(prefix + "/") for prefix in path_scopes)


def restore_snapshot(root: str | Path, snapshot: ResourceSnapshot) -> None:
    base = Path(root).resolve()
    base.mkdir(parents=True, exist_ok=True)
    wanted = {item["path"]: bytes.fromhex(item["content_hex"]) for item in snapshot.entries}
    current = _snapshot_entries(base)
    for item in current:
        rel = item["path"]
        if rel not in wanted:
            (base / rel).unlink(missing_ok=True)
    for rel, raw in wanted.items():
        target = base / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    # prune empty product directories only; never touch .git/.sdlc
    for path in sorted((p for p in base.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        rel = path.relative_to(base).as_posix()
        if rel == ".git" or rel.startswith(".git/") or rel == ".sdlc" or rel.startswith(".sdlc/"):
            continue
        try:
            path.rmdir()
        except OSError:
            pass


def apply_operations(
    root: str | Path,
    resource_id: str,
    operations: Sequence[Mapping[str, object]],
    *,
    allowed_scope: Sequence[str],
) -> ResourceChange:
    base = Path(root).resolve()
    before = capture_snapshot(base, resource_id)
    try:
        for operation in operations:
            op = str(operation.get("op") or "")
            rel = _safe_rel(str(operation.get("path") or ""))
            if not _allowed(resource_id, rel, allowed_scope):
                raise ResourceError(f"path is outside the claimed path scope: {rel}")
            target = (base / rel).resolve()
            try:
                target.relative_to(base)
            except ValueError as exc:
                raise ResourceError(f"path escapes resource root: {rel}") from exc
            if op == "write_text":
                content = operation.get("content")
                if not isinstance(content, str):
                    raise ResourceError("write_text content must be a string")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            elif op == "delete":
                if target.exists() and target.is_file():
                    target.unlink()
                elif target.exists():
                    raise ResourceError(f"delete only supports files: {rel}")
            elif op == "mkdir":
                target.mkdir(parents=True, exist_ok=True)
            else:
                raise ResourceError(f"unsupported resource operation: {op}")
    except Exception:
        raise
    after = capture_snapshot(base, resource_id)
    before_map = {x["path"]: x["sha256"] for x in before.entries}
    after_map = {x["path"]: x["sha256"] for x in after.entries}
    changed = tuple(sorted(path for path in set(before_map) | set(after_map) if before_map.get(path) != after_map.get(path)))
    return ResourceChange(resource_id, before, after, changed)

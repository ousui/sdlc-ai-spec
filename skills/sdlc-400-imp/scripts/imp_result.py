"""Complete immutable Resource Snapshot members and deterministic Result readback."""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat

from packages.sdlc_artifact_store import CanonicalMember, compute_sha256
from packages.sdlc_resource import capture_snapshot

from imp_common import (
    STATE_MEMBER, canonical, exact_base, path_allowed, reject_secrets, require, safe_path,
)

SNAPSHOT_CONTRACT = "sdlc-ai-spec/imp-resource-snapshot/v1"


def member(identity, value, *, directory="evidence"):
    raw = canonical(value) if not isinstance(value, bytes) else value
    return CanonicalMember(identity, f"{directory}/{identity.lower()}.json",
                           "application/json", raw, compute_sha256(raw))


def read_state(stored):
    members = [item for item in stored.payload.members if item.member_id == STATE_MEMBER]
    require(len(members) == 1, "IMP_RESULT_INCOMPLETE", "IMP state member is missing or duplicated")
    value = json.loads(members[0].raw_bytes)
    require(isinstance(value, dict) and value.get("contract") == "sdlc-ai-spec/imp-state/v1",
            "IMP_RESULT_INCOMPLETE", "IMP state member is invalid")
    return value


def read_member(stored, identity):
    matches = [item for item in stored.payload.members if item.member_id == identity]
    require(len(matches) == 1, "IMP_RESULT_INCOMPLETE", f"Immutable member is missing: {identity}")
    return matches[0]


def registry(project_root, resource_rows, binding):
    require(isinstance(resource_rows, list) and resource_rows, "IMP_READINESS_FAILED",
            "Provide the exact project-relative root for every Claim Resource")
    expected = {item[9:] for item in binding.execution_scope if item.startswith("resource:")}
    result = {}
    root = Path(project_root).resolve()
    for item in resource_rows:
        require(isinstance(item, dict), "IMP_READINESS_FAILED", "Invalid Resource registration")
        resource = item.get("id")
        require(resource in expected and resource not in result, "IMP_READINESS_FAILED",
                "Resources must map one-to-one to Claim resource tokens", action="RETURN_TO_PLAN")
        relative = safe_path(item.get("root"), allow_root=True)
        target = root / relative
        for part in (target, *target.parents):
            if part == root.parent:
                break
            require(not part.is_symlink(), "IMP_SCOPE_VIOLATION", "Resource root cannot traverse a symlink")
        require(target.resolve().is_relative_to(root) and (not target.exists() or target.is_dir()),
                "IMP_SCOPE_VIOLATION", "Resource root must be a directory inside the Project Root")
        for previous in result.values():
            other = root / previous
            require(not target.is_relative_to(other) and not other.is_relative_to(target),
                    "IMP_READINESS_FAILED", "Resource roots overlap; use their common Resource",
                    action="RETURN_TO_PLAN")
        result[resource] = relative
    require(set(result) == expected, "IMP_READINESS_FAILED", "A Claim Resource root is missing")
    return dict(sorted(result.items()))


def capture(root, resource):
    """Foundation bytes plus file modes/directories make a complete retained snapshot."""
    root = Path(root)
    directories = []
    modes = {}
    if root.exists():
        require(root.is_dir() and not root.is_symlink(), "IMP_BASELINE_UNRESOLVED",
                "Resource root must be an ordinary directory")
        for current, dirs, files in os.walk(root, followlinks=False):
            require(Path(current) == root or not {".git", ".sdlc"}.intersection((*dirs, *files)),
                    "IMP_BASELINE_UNRESOLVED", "Nested control roots require a separate Resource")
            dirs[:] = sorted(name for name in dirs if name not in {".git", ".sdlc"})
            files = sorted(name for name in files if name not in {".git", ".sdlc"})
            for name in (*dirs, *files):
                path = Path(current) / name
                relative = path.relative_to(root).as_posix()
                info = path.lstat()
                require(not stat.S_ISLNK(info.st_mode), "IMP_BASELINE_UNRESOLVED",
                        "Symlink products require an explicit Resource adapter")
                if path.is_dir():
                    directories.append({"path": relative, "mode": stat.S_IMODE(info.st_mode)})
                else:
                    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
                            "IMP_BASELINE_UNRESOLVED", "Special or hard-linked files cannot be safely captured")
                    modes[relative] = stat.S_IMODE(info.st_mode)
    snapshot = capture_snapshot(root, resource)
    entries = []
    for entry in snapshot.entries:
        reject_secrets(bytes.fromhex(entry["content_hex"]))
        entries.append({**entry, "mode": modes[entry["path"]]})
    return {
        "contract": SNAPSHOT_CONTRACT, "resource": resource, "existed": root.exists(),
        "root_mode": stat.S_IMODE(root.stat().st_mode) if root.exists() else None,
        "entries": entries, "directories": sorted(directories, key=lambda item: item["path"]),
    }


def verify_snapshot(snapshot, resource):
    require(isinstance(snapshot, dict) and snapshot.get("contract") == SNAPSHOT_CONTRACT
            and snapshot.get("resource") == resource,
            "IMP_RESULT_INCOMPLETE", "Snapshot Resource or Contract mismatch")
    require(isinstance(snapshot.get("existed"), bool) and isinstance(snapshot.get("entries"), list)
            and isinstance(snapshot.get("directories"), list),
            "IMP_RESULT_INCOMPLETE", "Snapshot structure is incomplete")
    paths = []
    for item in snapshot["entries"]:
        path = safe_path(item["path"])
        raw = bytes.fromhex(item["content_hex"])
        require(item["sha256"] == compute_sha256(raw).split(":", 1)[1],
                "IMP_RESULT_INCOMPLETE", "Snapshot content hash mismatch")
        require(isinstance(item.get("mode"), int) and 0 <= item["mode"] <= 0o7777,
                "IMP_RESULT_INCOMPLETE", "Snapshot file mode is missing")
        reject_secrets(raw)
        paths.append(path)
    require(paths == sorted(set(paths)), "IMP_RESULT_INCOMPLETE", "Snapshot paths are duplicated or unsorted")
    for item in snapshot["directories"]:
        safe_path(item["path"])
        require(isinstance(item.get("mode"), int), "IMP_RESULT_INCOMPLETE", "Snapshot directory mode is missing")
    if not snapshot["existed"]:
        require(not paths and not snapshot["directories"] and snapshot["root_mode"] is None,
                "IMP_RESULT_INCOMPLETE", "Nonexistent Baseline cannot contain product files")
    return snapshot


def snapshot_from_member(stored, identity, resource):
    return verify_snapshot(json.loads(read_member(stored, identity).raw_bytes), resource)


def snapshot_reference(store, reference, resource, *, local=None):
    base, separator, identity = reference.partition("/")
    require(separator and identity and "/" not in identity, "IMP_RESULT_INCOMPLETE",
            "Result requires a complete immutable Snapshot Member Reference")
    artifact, revision = exact_base(base, "IMP")
    stored = local if local and (artifact, revision) == (
        local.control.artifact_id, local.control.revision,
    ) else store.read_revision(artifact, revision)
    if stored is not local:
        require(stored.control.state == "frozen", "IMP_RESULT_INCOMPLETE", "External Snapshot must be frozen")
    return snapshot_from_member(stored, identity, resource)


def retained_result_snapshot(stored, row):
    """Read one Result using only members retained by this IMP Revision."""
    resource = row["resource"]
    if row["result_reference"] == row["baseline_reference"]:
        return snapshot_from_member(stored, row["baseline_member"], resource)
    base, separator, identity = row["result_reference"].partition("/")
    require(separator and identity == row["result_member"] and "/" not in identity,
            "IMP_RESULT_INCOMPLETE", "Local Result does not name its retained Snapshot Member")
    artifact, revision = exact_base(base, "IMP")
    require((artifact, revision) == (stored.control.artifact_id, stored.control.revision),
            "IMP_RESULT_INCOMPLETE", "Local Result cannot follow another Artifact Revision")
    return snapshot_from_member(stored, identity, resource)


def changed_paths(before, after):
    old = {item["path"]: item for item in before["entries"]}
    new = {item["path"]: item for item in after["entries"]}
    return sorted(path for path in old.keys() | new.keys() if old.get(path) != new.get(path))


def changed_scope(resource, paths, scope):
    for path in paths:
        require(path_allowed(resource, path, scope), "IMP_SCOPE_VIOLATION",
                "Observed Changed Scope exceeds Claim Scope")
    if not paths:
        return []
    prefix = f"path:{resource}/"
    return [f"resource:{resource}", *(
        token for token in scope if token.startswith(prefix)
        and any(path == token[len(prefix):].rstrip("/") or
                path.startswith(token[len(prefix):].rstrip("/") + "/") for path in paths)
    )]


def verify_result_set(store, stored, state, *, local_candidate=False):
    scope = state["binding"]["execution_scope"]
    resources = [item[9:] for item in scope if item.startswith("resource:")]
    records = state["resources"]
    require([row["resource"] for row in records] == sorted(resources)
            and len({row["id"] for row in records}) == len(resources),
            "IMP_RESULT_INCOMPLETE", "Result Set must contain one stable row per Claim Resource")
    for row in records:
        before = snapshot_from_member(stored, row["baseline_member"], row["resource"])
        if row["baseline_reference"] == "N/A":
            require(not before["existed"], "IMP_BASELINE_UNRESOLVED", "Existing Resource cannot use N/A Baseline")
        elif not local_candidate:
            require(snapshot_reference(store, row["baseline_reference"], row["resource"], local=stored) == before,
                    "IMP_RESULT_INCOMPLETE", "Baseline source readback differs from its retained Snapshot")
        if state["stage"] == "prepared":
            require(row["result_reference"] == "N/A", "IMP_RESULT_INCOMPLETE", "Prepared Result cannot claim completion")
            continue
        after = (retained_result_snapshot(stored, row) if local_candidate else
                 snapshot_reference(store, row["result_reference"], row["resource"], local=stored))
        paths = changed_paths(before, after)
        require(row["changed_paths"] == paths and row["changed_scope"] == changed_scope(row["resource"], paths, scope),
                "IMP_SCOPE_VIOLATION", "Result Changed Scope does not match immutable readback")
        require(set(row["steps"]).issubset({item["id"] for item in state["method"]["steps"]}),
                "IMP_RESULT_INCOMPLETE", "Result refers to an unknown Method Step")
        if not paths:
            require(row["baseline_reference"] == row["result_reference"] and not row["steps"]
                    and row["change_reference"] == "N/A",
                    "IMP_RESULT_INCOMPLETE", "Unchanged Resource must retain Baseline=Result with no Change")
        else:
            require(row["steps"], "IMP_RESULT_INCOMPLETE", "Changed Resource requires Approach Steps")
            change = json.loads(read_member(stored, row["change_member"]).raw_bytes)
            require(change == {"resource": row["resource"], "changed_paths": paths},
                    "IMP_RESULT_INCOMPLETE", "Change Evidence disagrees with immutable Result")
    return records

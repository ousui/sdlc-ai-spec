"""Pre-Claim Candidate Material admission and exact Baseline replay."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import os
from pathlib import Path
import re
import subprocess

from imp_common import canonical, path_allowed, require, safe_path
from imp_result import (
    capture, changed_paths, read_member, snapshot_from_member, verify_snapshot,
)


def _directory_map(snapshot):
    return {row["path"]: row["mode"] for row in snapshot["directories"]}


def _delta_paths(baseline, candidate):
    files = set(changed_paths(baseline, candidate))
    before_dirs = _directory_map(baseline)
    after_dirs = _directory_map(candidate)
    directories = {
        path for path in before_dirs.keys() | after_dirs.keys()
        if before_dirs.get(path) != after_dirs.get(path)
    }
    return tuple(sorted(files | directories))


def _snapshot_digest(snapshot):
    return "sha256:" + hashlib.sha256(canonical(snapshot)).hexdigest()


def _git(project_root, *arguments, binary=False):
    environment = {
        **os.environ,
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_LITERAL_PATHSPECS": "1",
    }
    process = subprocess.run(
        ["git", "-C", str(project_root), *arguments],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=not binary,
        env=environment,
    )
    require(process.returncode == 0, "IMP_BASELINE_UNRESOLVED",
            "Candidate Material VCS Baseline cannot be resolved")
    return process.stdout


def _head_entry(project_root, head, repo_path):
    """Return one exact tree entry, or None when HEAD has no such path."""
    raw = _git(project_root, "ls-tree", "-z", head, "--", repo_path, binary=True)
    if not raw:
        return None
    rows = [row for row in raw.split(b"\0") if row]
    require(len(rows) == 1, "IMP_BASELINE_UNRESOLVED",
            "Candidate Material path does not resolve to one immutable VCS object")
    metadata, separator, encoded_path = rows[0].partition(b"\t")
    parts = metadata.decode("ascii").split()
    require(separator and encoded_path.decode("utf-8") == repo_path and len(parts) == 3,
            "IMP_BASELINE_UNRESOLVED",
            "Candidate Material VCS tree entry is ambiguous")
    return tuple(parts)


def _parent_paths(path):
    parent = Path(path).parent
    if parent == Path("."):
        return ()
    return tuple(
        item.as_posix()
        for item in (*reversed(parent.parents), parent)
        if item != Path(".")
    )


def _vcs_baseline(project_root, resource, relative_root, reference, paths, candidate):
    match = re.fullmatch(rf"vcs:{re.escape(resource)}@([0-9a-f]{{40}}|[0-9a-f]{{64}})",
                         reference or "")
    require(match is not None, "IMP_BASELINE_UNRESOLVED",
            "Candidate Material requires vcs:<resource>@<full immutable HEAD object>")
    root = Path(project_root).resolve()
    top = Path(_git(root, "rev-parse", "--show-toplevel").strip()).resolve()
    require(top == root, "IMP_BASELINE_UNRESOLVED",
            "Candidate Material VCS proof must belong to the exact Project Root")
    head = _git(root, "rev-parse", "--verify", "HEAD^{commit}").strip()
    require(head == match.group(1), "IMP_BASELINE_UNRESOLVED",
            "Candidate Material Baseline must equal the current immutable HEAD")

    prefix = "" if relative_root == "." else relative_root.rstrip("/") + "/"
    if relative_root != ".":
        root_entry = _head_entry(root, head, relative_root)
        require(root_entry is not None and root_entry[1] == "tree",
                "IMP_BASELINE_UNRESOLVED",
                "Candidate Material Resource root must already exist as an immutable VCS tree")
    require(candidate["existed"] and candidate["root_mode"] is not None,
            "IMP_BASELINE_UNRESOLVED",
            "Candidate Material cannot remove its immutable VCS Resource root")

    # Git proves ordinary file bytes and executable modes, but not ordinary
    # directory or Resource-root modes. Candidate Material declares file
    # deltas only; undeclared files and observed directory metadata remain the
    # actual workspace Baseline. Construct that split explicitly instead of
    # treating the complete Candidate snapshot as historical VCS evidence.
    baseline = {
        "contract": candidate["contract"],
        "resource": candidate["resource"],
        "existed": True,
        "root_mode": candidate["root_mode"],
        "entries": [deepcopy(row) for row in candidate["entries"]],
        "directories": [deepcopy(row) for row in candidate["directories"]],
    }
    entries = {row["path"]: row for row in baseline["entries"]}
    directories = _directory_map(candidate)
    for path in paths:
        # Git does not preserve ordinary directory/root modes or empty
        # directories. Such changes cannot be proven by this VCS adapter and
        # therefore cannot be admitted as pre-Claim Candidate Material.
        require(path not in directories, "IMP_BASELINE_UNRESOLVED",
                "Candidate Material directory changes require a non-VCS immutable Baseline adapter")
        parents = _parent_paths(path)
        for parent in parents:
            repo_parent = prefix + parent
            parent_entry = _head_entry(root, head, repo_parent)
            require(parent_entry is not None and parent_entry[1] == "tree",
                    "IMP_BASELINE_UNRESOLVED",
                    "Candidate Material cannot introduce an unproven directory structure")
        repo_path = prefix + path
        entry = _head_entry(root, head, repo_path)
        if entry is None:
            entries.pop(path, None)
            continue
        require(all(parent in directories for parent in parents),
                "IMP_BASELINE_UNRESOLVED",
                "Candidate Material cannot remove tracked parent directories without immutable metadata")
        mode, kind, object_id = entry
        require(kind == "blob" and mode in {"100644", "100755"},
                "IMP_BASELINE_UNRESOLVED",
                "Candidate Material supports ordinary VCS files only")
        content = _git(root, "cat-file", "blob", object_id, binary=True)
        entries[path] = {
            "path": path,
            "sha256": hashlib.sha256(content).hexdigest(),
            "content_hex": content.hex(),
            "mode": 0o755 if mode == "100755" else 0o644,
        }
    baseline["entries"] = [entries[path] for path in sorted(entries)]
    return verify_snapshot(baseline, resource)


def _validate_pair(item, binding, project_root, roots, observed):
    require(isinstance(item, dict), "IMP_READINESS_FAILED",
            "Candidate Material entries must be objects")
    require(set(item) == {"resource", "baseline_reference", "changed_paths",
                          "candidate_digest"},
            "IMP_READINESS_FAILED",
            "Candidate Material must use the immutable VCS evidence shape")
    resource = item.get("resource")
    require(resource in roots, "IMP_SCOPE_VIOLATION",
            "Candidate Material Resource is outside the exact Claim")
    candidate = verify_snapshot(deepcopy(observed[resource]), resource)
    require(item.get("candidate_digest") == _snapshot_digest(candidate),
            "IMP_BASELINE_UNRESOLVED",
            "Workspace does not equal the digest-bound Candidate Material")
    raw_paths = item.get("changed_paths")
    require(isinstance(raw_paths, list) and raw_paths,
            "IMP_READINESS_FAILED", "Candidate Material changed_paths is required")
    declared = tuple(safe_path(path) for path in raw_paths)
    require(declared == tuple(sorted(set(declared))), "IMP_READINESS_FAILED",
            "Candidate Material changed_paths must be sorted and unique")
    require(all(path_allowed(resource, path, binding.execution_scope) for path in declared),
            "IMP_SCOPE_VIOLATION",
            "Candidate Material contains changes outside the Claim Scope")
    baseline = _vcs_baseline(
        project_root, resource, roots[resource], item.get("baseline_reference"),
        declared, candidate,
    )
    require(baseline["root_mode"] == candidate["root_mode"],
            "IMP_READINESS_FAILED",
            "Candidate Material cannot ambiguously change the Resource root itself")
    paths = _delta_paths(baseline, candidate)
    require(paths == declared, "IMP_BASELINE_UNRESOLVED",
            "Immutable VCS Baseline does not prove the exact declared Candidate delta")
    return {
        "resource": resource,
        "baseline": baseline,
        "candidate": candidate,
        "changed_paths": paths,
        "baseline_reference": item["baseline_reference"],
        "candidate_digest": item["candidate_digest"],
    }


def resolve_candidate_material(
    raw, binding, project_root, roots, observed, *, stored=None, state=None,
):
    """Return locally closed Candidate records and the exact execution Baselines."""
    retained = (state or {}).get("candidate_material", [])
    records = {}
    if retained:
        require(stored is not None and raw in (None, []), "IMP_BINDING_MISMATCH",
                "An active Attempt cannot replace its retained Candidate Material")
        for row in retained:
            resource = row["resource"]
            require(resource in roots and resource not in records,
                    "IMP_RESULT_INCOMPLETE", "Retained Candidate Material is invalid")
            baseline = snapshot_from_member(stored, row["baseline_member"], resource)
            candidate = snapshot_from_member(stored, row["candidate_member"], resource)
            paths = _delta_paths(baseline, candidate)
            require(list(paths) == row["changed_paths"] and paths,
                    "IMP_RESULT_INCOMPLETE", "Retained Candidate Material digest changed")
            require(all(path_allowed(resource, path, binding.execution_scope) for path in paths),
                    "IMP_SCOPE_VIOLATION", "Retained Candidate Material exceeds Claim Scope")
            require(observed[resource] in (baseline, candidate),
                    "IMP_BASELINE_UNRESOLVED",
                    "Workspace is neither the retained Candidate nor its exact Baseline")
            records[resource] = {
                "resource": resource,
                "baseline": baseline,
                "candidate": candidate,
                "changed_paths": paths,
                "baseline_reference": row["baseline_reference"],
                "candidate_digest": row["candidate_digest"],
            }
    elif raw is not None:
        require(isinstance(raw, list) and raw, "IMP_READINESS_FAILED",
                "candidate_material must be a non-empty array")
        for item in raw:
            record = _validate_pair(item, binding, project_root, roots, observed)
            require(record["resource"] not in records, "IMP_READINESS_FAILED",
                    "Candidate Material Resource is duplicated")
            records[record["resource"]] = record

    baselines = dict(observed)
    if records and not (state and state.get("stage") == "executed"):
        for resource, record in records.items():
            baselines[resource] = record["baseline"]
    owned = {
        (resource, path)
        for resource, record in records.items()
        for path in record["changed_paths"]
    }
    restore = {
        resource: record for resource, record in records.items()
        if observed[resource] == record["candidate"]
        and not (state and state.get("stage") == "executed")
    }
    return records, baselines, owned, restore


def persisted_candidate_records(records, resource_rows):
    by_resource = {row["resource"]: row for row in resource_rows}
    return [
        {
            "resource": resource,
            "baseline_member": by_resource[resource]["baseline_member"],
            "candidate_member": "CANDIDATE-" + by_resource[resource]["id"],
            "changed_paths": list(record["changed_paths"]),
            "baseline_reference": record["baseline_reference"],
            "candidate_digest": record["candidate_digest"],
            "binding_digest": hashlib.sha256(canonical({
                "resource": resource,
                "baseline": record["baseline"],
                "candidate": record["candidate"],
                "changed_paths": record["changed_paths"],
                "baseline_reference": record["baseline_reference"],
                "candidate_digest": record["candidate_digest"],
            })).hexdigest(),
        }
        for resource, record in sorted(records.items())
    ]


def candidate_members(records, persisted, member_factory):
    return [
        member_factory(row["candidate_member"], records[row["resource"]]["candidate"],
                       directory="candidate")
        for row in persisted
    ]


def verify_persisted_candidates(stored, state, binding):
    records = state.get("candidate_material", [])
    require(isinstance(records, list), "IMP_RESULT_INCOMPLETE",
            "Candidate Material record set is invalid")
    resources = {row["resource"]: row for row in state["resources"]}
    seen = set()
    for row in records:
        require(isinstance(row, dict) and row.get("resource") in resources
                and row["resource"] not in seen,
                "IMP_RESULT_INCOMPLETE", "Candidate Material identity is invalid")
        seen.add(row["resource"])
        resource = row["resource"]
        baseline = snapshot_from_member(stored, row.get("baseline_member"), resource)
        candidate = snapshot_from_member(stored, row.get("candidate_member"), resource)
        paths = _delta_paths(baseline, candidate)
        require(row.get("candidate_digest") == _snapshot_digest(candidate),
                "IMP_RESULT_INCOMPLETE", "Candidate Material digest changed")
        expected = hashlib.sha256(canonical({
            "resource": resource,
            "baseline": baseline,
            "candidate": candidate,
            "changed_paths": paths,
            "baseline_reference": row.get("baseline_reference"),
            "candidate_digest": row.get("candidate_digest"),
        })).hexdigest()
        require(list(paths) == row.get("changed_paths") and paths
                and expected == row.get("binding_digest"),
                "IMP_RESULT_INCOMPLETE", "Candidate Material binding is incomplete")
        require(all(path_allowed(resource, path, binding.execution_scope) for path in paths),
                "IMP_SCOPE_VIOLATION", "Candidate Material exceeds Claim Scope")
        require(resources[resource]["baseline_member"] == row["baseline_member"],
                "IMP_RESULT_INCOMPLETE", "Candidate Material uses another Baseline")
        require(re.fullmatch(
            rf"vcs:{re.escape(resource)}@(?:[0-9a-f]{{40}}|[0-9a-f]{{64}})",
            row.get("baseline_reference", ""),
        ) is not None, "IMP_RESULT_INCOMPLETE",
                "Candidate Material immutable Baseline proof is missing")
    return records


def restore_declared_baselines(project_root, roots, records, guard):
    """Move only proven Candidate deltas back to their declared Baselines."""
    project_root = Path(project_root)
    for resource, record in sorted(records.items()):
        guard()
        root = project_root / roots[resource]
        require(capture(root, resource) == record["candidate"],
                "IMP_BASELINE_UNRESOLVED", "Candidate changed before Baseline replay")
        baseline_files = {row["path"]: row for row in record["baseline"]["entries"]}
        candidate_files = {row["path"]: row for row in record["candidate"]["entries"]}
        file_paths = set(changed_paths(record["baseline"], record["candidate"]))
        baseline_dirs = _directory_map(record["baseline"])
        candidate_dirs = _directory_map(record["candidate"])
        for path in sorted(baseline_dirs, key=lambda value: (value.count("/"), value)):
            target = root / path
            target.mkdir(parents=True, exist_ok=True)
            os.chmod(target, baseline_dirs[path])
        for path in sorted(file_paths):
            target = root / path
            before = baseline_files.get(path)
            if before is None:
                require(path in candidate_files and target.is_file(),
                        "IMP_BASELINE_UNRESOLVED", "Candidate file disappeared before replay")
                target.unlink()
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(bytes.fromhex(before["content_hex"]))
                os.chmod(target, before["mode"])
        for path in sorted(
            set(candidate_dirs) - set(baseline_dirs),
            key=lambda value: (value.count("/"), value), reverse=True,
        ):
            target = root / path
            try:
                target.rmdir()
            except OSError:
                pass
        require(capture(root, resource) == record["baseline"],
                "IMP_BASELINE_UNRESOLVED", "Declared Candidate Baseline was not restored exactly")


def verify_replayed_candidates(after, records):
    for resource, record in records.items():
        require(after[resource] == record["candidate"], "IMP_RESULT_INCOMPLETE",
                "Method replay does not reproduce the declared Candidate Result")

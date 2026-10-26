#!/usr/bin/env python3
"""Local, one-off sdlc-cut document operations. Python 3.9+ standard library."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
from typing import Any, Iterator


TOP = {"format_version", "operation_id", "project", "kind", "source", "source_files",
       "source_notice", "observed_code", "targets", "draft_files", "items", "task_mapping",
       "checklist_mapping", "carryover", "dependencies", "questions", "handoff", "decision", "content_review"}
KINDS = {"goal", "story", "requirement", "constraint", "acceptance", "task", "checklist", "question", "decision", "artifact"}
DISPOSITIONS = {"assigned", "shared", "baseline", "deferred", "excluded"}
SHA = re.compile(r"^[0-9a-f]{64}$")
KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
ANCHOR = re.compile(r"^(?:NFR|FR|SC|US|CHK)-?\d+[A-Za-z0-9_-]*$|^T\d{3,}$")
BOX = re.compile(r"^\s*[-*+]\s+\[([ xX])\]\s+")
TASK = re.compile(r"^\s*[-*+]\s+\[([ xX])\]\s+(T\d{3,})\b")
CHECKLIST = re.compile(r"^\s*[-*+]\s+\[([ xX])\]\s+(CHK-?\d+[A-Za-z0-9_-]*)(?![A-Za-z0-9_-])")


class CutError(Exception):
    def __init__(self, message: str, code: int = 3):
        super().__init__(message)
        self.code = code


def check(ok: Any, message: str, code: int = 3) -> None:
    if not ok:
        raise CutError(message, code)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def raw_file(path: Path) -> bytes:
    check(path.is_file() and not path.is_symlink(), f"普通文件无效或为链接：{path}")
    return path.read_bytes()


def file_digest(path: Path) -> str:
    return digest(raw_file(path))


def json_data(data: dict[str, Any]) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def load_json(path: Path) -> dict[str, Any]:
    try:
        obj = json.loads(raw_file(path).decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CutError(f"JSON 格式错误：{path}: {exc}", 2) from exc
    check(isinstance(obj, dict), f"JSON 顶层必须是对象：{path}", 2)
    return obj


def write_new(path: Path, data: bytes) -> None:
    check(not path.is_symlink(), f"目标是链接：{path}")
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def save_receipt(path: Path, obj: dict[str, Any]) -> None:
    fd, name = tempfile.mkstemp(prefix=".receipt-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(json_data(obj))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def rel(raw: Any, label: str) -> PurePosixPath:
    check(isinstance(raw, str) and raw and "\\" not in raw, f"{label} 路径无效", 2)
    check(not any(ord(c) < 32 or ord(c) == 127 for c in raw), f"{label} 包含控制字符", 2)
    p = PurePosixPath(raw)
    check(not p.is_absolute() and all(x not in ("", ".", "..") for x in raw.split("/")) and p.as_posix() == raw,
          f"{label} 必须为规范相对路径", 2)
    return p


def no_links(base: Path, path: Path) -> None:
    check(path == base or base in path.parents, f"路径越出允许范围：{path}")
    cur = base
    for part in path.relative_to(base).parts:
        cur /= part
        check(not cur.is_symlink(), f"路径包含符号链接：{cur}")


def within(base: Path, raw: Any, label: str) -> Path:
    path = base.joinpath(*rel(raw, label).parts)
    no_links(base, path)
    return path


def project_argument(project: Path, raw: str, label: str) -> str:
    path = Path(raw)
    if path.is_absolute():
        try:
            raw = path.relative_to(project).as_posix()
        except ValueError as exc:
            raise CutError(f"{label} 不属于当前项目：{path}", 2) from exc
    within(project, raw, label)
    return raw


def project_path(raw: str) -> Path:
    p = Path(raw).expanduser()
    check(p.is_dir(), f"项目目录不存在：{raw}", 2)
    return p.resolve(strict=True)


def operation_path(raw: str) -> Path:
    p = Path(raw).absolute()
    check(p.is_dir() and not p.is_symlink(), f"操作目录无效：{raw}", 2)
    return p.resolve(strict=True)


def disjoint(a: Path, b: Path, label: str) -> None:
    check(a != b and a not in b.parents and b not in a.parents, f"{label} 相互包含或重合：{a} / {b}")


def scope(project: Path, kind: str, operation: Path) -> Path:
    no_links(project, operation)
    if kind == "feature":
        root = project / ".sdlc" / "cuts"
        check(operation.parent == root and (project / ".sdlc" / "specs").is_dir(),
              "正式操作必须位于已初始化项目 .sdlc/cuts 的直接子目录")
        return root
    check(kind == "intake", "kind 必须是 feature 或 intake", 2)
    check(project / ".sdlc" not in operation.parents and operation != project / ".sdlc",
          "intake 不得位于 .sdlc 内")
    return operation


@contextlib.contextmanager
def locked(project: Path, kind: str, operation: Path) -> Iterator[None]:
    root = scope(project, kind, operation)
    if kind == "feature":
        root.mkdir(exist_ok=True)
    check(root.is_dir() and not root.is_symlink(), "CUT 锁目录无效")
    lock = root / ".apply.lock"
    check(not lock.is_symlink(), "CUT 锁为链接")
    with lock.open("a+b") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def regular_tree(root: Path) -> dict[str, Path]:
    check(root.is_dir() and not root.is_symlink(), f"目录无效：{root}")
    result: dict[str, Path] = {}
    for here, dirs, files in os.walk(root, followlinks=False):
        parent = Path(here)
        for name in dirs:
            check(not (parent / name).is_symlink(), f"目录链接不受支持：{parent / name}")
        for name in files:
            path = parent / name
            check(path.is_file() and not path.is_symlink(), f"特殊文件不受支持：{path}")
            result[path.relative_to(root).as_posix()] = path
    return result


def git_run(project: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    # Never ask Git to refresh the index on disk or invoke configured diff helpers.
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", LC_ALL="C")
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_PREFIX",
                "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_CEILING_DIRECTORIES"):
        env.pop(key, None)
    return subprocess.run(["git", "--literal-pathspecs", "-c", "core.fsmonitor=false",
                           "-C", str(project), *args],
                          env=env, capture_output=True, check=False)


def git_info(project: Path) -> tuple[dict[str, Any], list[str]]:
    try:
        root = git_run(project, "rev-parse", "--show-toplevel")
        if root.returncode:
            state = "no_repository" if b"not a git repository" in root.stderr.lower() else "query_failed"
            return {"state": state, "head": None, "branch": None}, [
                "无 Git 仓库；仅记录指定文件当前字节" if state == "no_repository" else
                "Git 仓库查询失败；版本状态未知，仅记录指定文件当前字节"]
        branch = git_run(project, "symbolic-ref", "--quiet", "--short", "HEAD")
        head = git_run(project, "rev-parse", "--verify", "HEAD")
        branch_name = branch.stdout.decode("utf-8", "surrogateescape").strip() if branch.returncode == 0 else None
        if head.returncode:
            full_ref = git_run(project, "symbolic-ref", "--quiet", "HEAD")
            if full_ref.returncode == 0:
                ref = full_ref.stdout.decode("utf-8", "surrogateescape").strip()
                exists = git_run(project, "show-ref", "--verify", "--quiet", ref)
                if exists.returncode == 1:
                    return {"state": "unborn", "head": None, "branch": branch_name}, [
                        "Git 尚无初始提交；不能把当前文件称为已提交实现"]
            return {"state": "query_failed", "head": None, "branch": branch_name}, [
                "Git HEAD 查询失败；不能假定这是空仓库或已提交实现"]
        return {"state": "head", "head": head.stdout.decode("ascii").strip(), "branch": branch_name,
                "root": str(Path(os.fsdecode(root.stdout.rstrip(b"\n"))).resolve()),
                "note": "仅观察指定相关文件；完成结论仍需核对实际后继基线"}, []
    except FileNotFoundError:
        return {"state": "git_unavailable", "head": None, "branch": None}, [
            "Git 命令不可用；仅记录指定文件当前字节"]
    except (OSError, UnicodeError) as exc:
        return {"state": "query_failed", "head": None, "branch": None}, [
            f"Git 不可用或查询失败（{type(exc).__name__}）；仅记录指定文件当前字节"]


def git_file_info(project: Path, name: str, git: dict[str, Any]) -> dict[str, Any]:
    if git["state"] != "head":
        return {"state": "unobserved", "reason": git["state"]}
    # The pathspec is literal and relative to project, while ls-tree needs a path from Git's root.
    pathspec = name
    tree_name = (project.resolve() / name).relative_to(Path(git["root"])).as_posix()
    commands = {
        "head": ("ls-tree", "--full-tree", "-z", "HEAD", "--", tree_name),
        "index": ("ls-files", "--stage", "-z", "--", pathspec),
        "head_to_index": ("diff", "--cached", "--name-status", "-z", "--no-renames",
                          "--no-ext-diff", "--no-textconv", "HEAD", "--", pathspec),
        "index_to_worktree": ("diff", "--name-status", "-z", "--no-renames",
                              "--no-ext-diff", "--no-textconv", "--", pathspec),
    }
    output = {}
    for key, args in commands.items():
        try:
            result = git_run(project, *args)
            if result.returncode:
                return {"state": "query_failed", "reason": f"{key} Git 查询失败（exit {result.returncode}）"}
            output[key] = result.stdout
        except OSError as exc:
            return {"state": "query_failed", "reason": f"{key} Git 查询失败（{type(exc).__name__}）"}
    # OIDs identify the actual HEAD and index blobs, including staged content that
    # a later unstaged edit may cancel in the final worktree bytes.
    head = [part.split(b"\t", 1)[0].decode("ascii") for part in output["head"].split(b"\0") if part]
    index = [part.split(b"\t", 1)[0].decode("ascii") for part in output["index"].split(b"\0") if part]
    def statuses(key: str) -> list[str]:
        parts = [part for part in output[key].split(b"\0") if part]
        return [parts[i].decode("ascii") for i in range(0, len(parts), 2)]
    staged = statuses("head_to_index")
    unstaged = statuses("index_to_worktree")
    state = "tracked" if head or index else "untracked"
    if len(index) > 1:
        state = "unmerged"
    return {"state": state, "head_entries": head, "index_entries": index,
            "head_to_index": staged, "index_to_worktree": unstaged}


def code_info(project: Path, names: list[str]) -> dict[str, Any]:
    git, limits = git_info(project)
    files = []
    seen: set[str] = set()
    for raw in names:
        path = within(project, raw, "observe-code")
        name = path.relative_to(project).as_posix()
        check(name not in seen, f"重复观察：{name}", 2)
        seen.add(name)
        vcs = git_file_info(project, name, git)
        check(path.is_file() or vcs["state"] in ("tracked", "unmerged"), f"观察文件不存在：{raw}", 2)
        check(not path.exists() or path.is_file(), f"观察对象不是普通文件：{raw}", 2)
        sha = file_digest(path) if path.is_file() else None
        if vcs["state"] in ("query_failed", "unmerged"):
            limits.append(f"{name} 的 Git 分层状态未能完整观察：{vcs.get('reason', vcs['state'])}")
        if sha is None:
            limits.append(f"{name} 当前不存在；不能将其视为已实现或无变化")
        vcs["worktree"] = "present" if sha is not None else "missing"
        files.append({"path": name, "sha256": sha, "reason": "本次承接依据；是否完成仍由 Agent 复核",
                      "vcs": vcs})
    if not files:
        limits.append("未观察代码文件；不能推断实现完成")
    return {"git": git, "files": files, "limitations": limits}


def snap_name(index: int, path: Path | None, generation: str) -> str:
    suffix = path.suffix if path and re.fullmatch(r"\.[A-Za-z0-9]{1,12}", path.suffix) else ".txt"
    return f"source/{generation}/S{index:03d}{suffix}"


def collect(project: Path, kind: str, names: list[str], operation: Path, generation: str) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, bytes]]:
    entries: list[dict[str, Any]] = []
    snapshots: dict[str, bytes] = {}
    if kind == "feature":
        check(len(names) == 1 and names[0] != "-", "feature 仅接受一个来源目录", 2)
        source = within(project, names[0], "source")
        check(source.is_dir() and source.parent == project / ".sdlc" / "specs", "正式来源须为 .sdlc/specs 的直接子目录", 2)
        disjoint(source, operation, "来源与操作目录")
        files = regular_tree(source)
        check(files, "正式来源没有普通文件")
        for index, (_, path) in enumerate(sorted(files.items()), 1):
            data = raw_file(path)
            snap = snap_name(index, path, generation)
            entries.append({"id": f"S{index:03d}", "path": path.relative_to(project).as_posix(), "input_id": None,
                            "sha256": digest(data), "snapshot_path": snap, "handling": "input",
                            "reason": "待 Agent 复核用途的正式来源材料"})
            snapshots[snap] = data
        return {"directory": source.relative_to(project).as_posix(), "inputs": []}, entries, snapshots
    check(kind == "intake" and names and names.count("-") <= 1, "intake 需要明确输入，stdin 最多一份", 2)
    inputs = []
    for index, raw in enumerate(names, 1):
        input_id = f"input-{index}"
        if raw == "-":
            data = sys.stdin.buffer.read()
            check(data, "stdin 输入为空", 2)
            path = None
        else:
            path = Path(raw).expanduser()
            if not path.is_absolute():
                path = project / path
            check(path.is_file() and not path.is_symlink(), f"intake 输入无效：{raw}", 2)
            path = path.resolve(strict=True)
            data = raw_file(path)
            if project in path.parents:
                disjoint(path, operation, "输入与操作目录")
        snap = snap_name(index, path, generation)
        entries.append({"id": f"S{index:03d}", "path": str(path) if path else None, "input_id": input_id,
                        "sha256": digest(data), "snapshot_path": snap, "handling": "input", "reason": "待 Agent 复核的原始输入"})
        inputs.append({"id": input_id, "path": str(path) if path else None})
        snapshots[snap] = data
    return {"directory": None, "inputs": inputs}, entries, snapshots


def save_snapshots(operation: Path, snapshots: dict[str, bytes]) -> None:
    for name, data in snapshots.items():
        path = within(operation, name, "snapshot_path")
        path.parent.mkdir(parents=True, exist_ok=True)
        write_new(path, data)


def notice_path(source: Path, operation_id: str) -> str:
    for name in ("cut.md", f"cut-{operation_id}.md"):
        if not (source / name).exists() and not (source / name).is_symlink():
            return name
    raise CutError("来源说明候选路径均被占用")


def initial_record(project: Path, kind: str, operation: Path, source: dict[str, Any],
                   files: list[dict[str, Any]], code: dict[str, Any]) -> dict[str, Any]:
    notice = None
    if kind == "feature":
        source_dir = within(project, source["directory"], "source.directory")
        name = notice_path(source_dir, operation.name)
        notice = {"path": (source_dir / name).relative_to(project).as_posix(),
                  "draft_path": "draft/source-notice.md", "sha256": ""}
    return {"format_version": 1, "operation_id": operation.name, "project": str(project), "kind": kind,
            "source": source, "source_files": files, "source_notice": notice, "observed_code": code,
            "targets": [], "draft_files": [], "items": [], "task_mapping": [], "checklist_mapping": [],
            "carryover": [], "dependencies": [], "questions": [],
            "handoff": {"first_target": None, "instruction": "由 Agent 确认后继与原版继续入口；CUT 不切换当前需求"},
            "decision": {"boundary_confirmed": False, "apply_authorized": False, "basis": ""},
            "content_review": {"completed": False, "summary": "", "limitations": ["待 Agent 复核"]}}


def existing_feature_ops(project: Path, source_rel: str) -> list[tuple[Path, dict[str, Any], Any]]:
    root = project / ".sdlc" / "cuts"
    if not root.exists():
        return []
    matches = []
    for child in sorted(root.iterdir()):
        if child.name == ".apply.lock":
            continue
        check(child.is_dir() and not child.is_symlink(), f"CUT 根存在未知条目：{child}")
        check((child / "cut.json").is_file(), f"CUT 操作记录缺失：{child}")
        record = load_json(child / "cut.json")
        check(record.get("project") == str(project) and record.get("kind") == "feature" and
              record.get("operation_id") == child.name, f"CUT 操作身份冲突：{child}")
        receipt = load_json(child / "receipt.json") if (child / "receipt.json").exists() else None
        if isinstance(record.get("source"), dict) and record["source"].get("directory") == source_rel:
            matches.append((child, record, receipt))
    return matches


def same_inventory(old: list[Any], new: list[Any]) -> bool:
    return [(x.get("path"), x.get("sha256")) for x in old] == [(x.get("path"), x.get("sha256")) for x in new]


def refresh_preview(project: Path, kind: str, operation: Path, names: list[str],
                    code_names: list[str], old: dict[str, Any]) -> dict[str, Any]:
    generation = dt.datetime.now(dt.timezone.utc).strftime("refresh-%Y%m%dT%H%M%S%f")
    source, files, snapshots = collect(project, kind, names, operation, generation)
    check(source == old.get("source"), "已有操作的来源身份不同")
    # Re-inspection must not silently discard a previously selected implementation scope.
    observed_names = code_names or [entry["path"] for entry in old.get("observed_code", {}).get("files", [])]
    current_code = code_info(project, observed_names)
    source_same = same_inventory(old.get("source_files", []), files)
    if source_same and old.get("observed_code") == current_code:
        return {"command": "inspect", "status": "existing_preview", "operation_directory": str(operation),
                "source_files": old["source_files"], "errors": [], "limitations": ["来源字节未变；预览保持原状"]}
    if not source_same:
        save_snapshots(operation, snapshots)
        old["source_files"] = files
    old["observed_code"] = current_code
    old["decision"]["apply_authorized"] = False
    old["content_review"]["completed"] = False
    (operation / "cut.json").write_bytes(json_data(old))
    return {"command": "inspect", "status": "refreshed_preview", "operation_directory": str(operation),
            "source_files": old["source_files"], "errors": [], "limitations": ["来源或代码观察已变化；草稿和边界须重新复核"]}


def create_preview(project: Path, kind: str, operation: Path, names: list[str], code_names: list[str],
                   reuse_empty_intake: bool = False) -> dict[str, Any]:
    if reuse_empty_intake:
        check(kind == "intake" and operation.is_dir() and not operation.is_symlink() and
              [p.name for p in operation.iterdir()] == [".apply.lock"], "intake 操作目录已被其他内容占用")
    else:
        check(not operation.exists() and not operation.is_symlink(), f"操作目录已占用：{operation}")
    source, files, snapshots = collect(project, kind, names, operation, "initial")
    record = initial_record(project, kind, operation, source, files, code_info(project, code_names))
    template = Path(__file__).resolve().parent.parent / "assets" / "cut-plan.md"
    template_data = raw_file(template)
    # Publish the initial record only after every input and file write succeeds.
    # A failed preview must not leave a recordless operation directory.
    stage_parent = operation.parent.parent if kind == "feature" else operation.parent
    with tempfile.TemporaryDirectory(prefix=".cut-preview-", dir=stage_parent) as tmp:
        stage = Path(tmp)
        save_snapshots(stage, snapshots)
        write_new(stage / "cut.json", json_data(record))
        write_new(stage / "cut.md", template_data)
        if kind == "intake" and not reuse_empty_intake:
            write_new(stage / ".apply.lock", b"")
        if reuse_empty_intake:
            check([p.name for p in operation.iterdir()] == [".apply.lock"],
                  "intake 操作目录在准备期间已改变")
            moved = []
            try:
                for name in ("source", "cut.md", "cut.json"):
                    if (stage / name).exists():
                        os.rename(stage / name, operation / name)
                        moved.append(name)
            except BaseException:
                for name in reversed(moved):
                    os.rename(operation / name, stage / name)
                raise
        else:
            check(not operation.exists() and not operation.is_symlink(), f"操作目录已占用：{operation}")
            os.rename(stage, operation)
    return {"command": "inspect", "status": "preview_created", "operation_directory": str(operation),
            "source_files": files, "errors": [], "limitations": record["observed_code"]["limitations"]}


def inspect(args: argparse.Namespace) -> dict[str, Any]:
    project = project_path(args.project)
    args.workspace = project_argument(project, args.workspace, "workspace")
    if args.kind == "feature":
        args.source = [project_argument(project, name, "source") for name in args.source]
    args.observe_code = [project_argument(project, name, "observe-code") for name in args.observe_code]
    operation = within(project, args.workspace, "workspace")
    scope(project, args.kind, operation)
    if args.kind == "feature":
        check(len(args.source) == 1 and args.source[0] != "-", "feature 只接受一个来源目录", 2)
        source = within(project, args.source[0], "source")
        check(source.is_dir(), "正式来源不存在", 2)
        source_rel = source.relative_to(project).as_posix()
        with locked(project, "feature", operation):
            matches = existing_feature_ops(project, source_rel)
            check(len(matches) <= 1, "同一正式来源存在多个 CUT 操作；需人工核查")
            if matches:
                old_op, old, receipt = matches[0]
                if receipt:
                    inspect_receipt(old_op, old, receipt, project)
                    return {"command": "inspect", "status": "already_applied" if receipt.get("applied_at") else "resume_required",
                            "operation_directory": str(old_op), "targets": old.get("targets", []), "errors": [], "limitations": []}
                if old_op != operation:
                    return {"command": "inspect", "status": "existing_preview", "operation_directory": str(old_op),
                            "targets": old.get("targets", []), "errors": [], "limitations": []}
                return refresh_preview(project, "feature", operation, args.source, args.observe_code, old)
            return create_preview(project, "feature", operation, args.source, args.observe_code)
    check(args.kind == "intake", "kind 无效", 2)
    if not operation.exists():
        operation.parent.mkdir(parents=True, exist_ok=True)
        return create_preview(project, "intake", operation, args.source, args.observe_code)
    with locked(project, "intake", operation):
        record_file = operation / "cut.json"
        if record_file.exists():
            old = load_json(record_file)
            check(old.get("project") == str(project) and old.get("kind") == "intake" and
                  old.get("operation_id") == operation.name, "intake 操作身份不符")
            if (operation / "receipt.json").exists():
                receipt = load_json(operation / "receipt.json")
                inspect_receipt(operation, old, receipt, project)
                return {"command": "inspect", "status": "already_applied" if receipt.get("applied_at") else "resume_required",
                        "operation_directory": str(operation), "targets": old.get("targets", []), "errors": [], "limitations": []}
            return refresh_preview(project, "intake", operation, args.source, args.observe_code, old)
        check(not any(operation.iterdir()) or [p.name for p in operation.iterdir()] == [".apply.lock"],
              "intake 操作目录已被其他内容占用")
        return create_preview(project, "intake", operation, args.source, args.observe_code, reuse_empty_intake=True)


class SourceChanged(CutError):
    pass


def object_fields(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    check(isinstance(value, dict), f"{label} 必须是对象", 2)
    check(set(value) == fields, f"{label} 字段缺失或未知：{sorted(set(value) ^ fields)}", 2)
    return value


def nonempty(value: Any, label: str) -> str:
    check(isinstance(value, str) and bool(value.strip()), f"{label} 必须是非空字符串", 2)
    return value


def hash_value(value: Any, label: str) -> str:
    check(isinstance(value, str) and SHA.fullmatch(value), f"{label} 不是 SHA-256", 2)
    return value


def array(value: Any, label: str) -> list[Any]:
    check(isinstance(value, list), f"{label} 必须是数组", 2)
    return value


def bool_value(value: Any, label: str) -> bool:
    check(type(value) is bool, f"{label} 必须是布尔值", 2)
    return value


def schema(record: dict[str, Any], operation: Path) -> None:
    object_fields(record, TOP, "cut.json")
    check(type(record["format_version"]) is int and record["format_version"] == 1, "format_version 不受支持", 2)
    check(record["operation_id"] == operation.name and KEY.fullmatch(nonempty(record["operation_id"], "operation_id")),
          "operation_id 与操作目录不符", 2)
    check(record["kind"] in ("feature", "intake"), "kind 无效", 2)
    check(isinstance(record["project"], str) and Path(record["project"]).is_absolute(), "project 必须是绝对路径", 2)
    source = object_fields(record["source"], {"directory", "inputs"}, "source")
    array(source["inputs"], "source.inputs")
    if record["kind"] == "feature":
        rel(source["directory"], "source.directory")
        check(not source["inputs"], "feature 不允许 source.inputs", 2)
        object_fields(record["source_notice"], {"path", "draft_path", "sha256"}, "source_notice")
    else:
        check(source["directory"] is None and record["source_notice"] is None and source["inputs"],
              "intake 不允许正式父目录或来源说明", 2)
    for key in ("source_files", "targets", "draft_files", "items", "task_mapping", "checklist_mapping", "carryover", "dependencies", "questions"):
        array(record[key], key)
    object_fields(record["observed_code"], {"git", "files", "limitations"}, "observed_code")
    array(record["observed_code"]["files"], "observed_code.files")
    array(record["observed_code"]["limitations"], "observed_code.limitations")
    object_fields(record["handoff"], {"first_target", "instruction"}, "handoff")
    nonempty(record["handoff"]["instruction"], "handoff.instruction")
    decision = object_fields(record["decision"], {"boundary_confirmed", "apply_authorized", "basis"}, "decision")
    bool_value(decision["boundary_confirmed"], "decision.boundary_confirmed")
    bool_value(decision["apply_authorized"], "decision.apply_authorized")
    check(isinstance(decision["basis"], str), "decision.basis 必须是字符串", 2)
    review = object_fields(record["content_review"], {"completed", "summary", "limitations"}, "content_review")
    bool_value(review["completed"], "content_review.completed")
    check(isinstance(review["summary"], str), "content_review.summary 必须是字符串", 2)
    array(review["limitations"], "content_review.limitations")


def target_paths(record: dict[str, Any], project: Path, operation: Path) -> dict[str, Path]:
    check(len(record["targets"]) >= 2, "至少需要两个后继目标")
    source_dir = within(project, record["source"]["directory"], "source.directory") if record["kind"] == "feature" else None
    targets: dict[str, Path] = {}
    drafts: set[str] = set()
    for target in record["targets"]:
        object_fields(target, {"key", "directory", "draft_directory", "outcome", "next_step"}, "target")
        key = nonempty(target["key"], "target.key")
        check(KEY.fullmatch(key) and key not in targets, f"目标 key 重复或无效：{key}", 2)
        path = within(project, target["directory"], "target.directory")
        check(path != project and path.parent.is_dir(), f"目标父目录不存在：{path}")
        check(not path.is_symlink(), f"目标目录是链接：{path}")
        if record["kind"] == "feature":
            check(path.parent == project / ".sdlc" / "specs", "正式后继必须为 .sdlc/specs 直接子目录")
        else:
            check(path.parts[len(project.parts)] not in {".sdlc", ".git", ".agents", "src", "app", "lib", "tests", "dist", "tools"},
                  f"intake 目标不能写入项目状态或源码位置：{path}")
        disjoint(path, operation, "目标与操作目录")
        if source_dir:
            disjoint(path, source_dir, "目标与来源")
        for old in targets.values():
            disjoint(path, old, "两个目标")
        draft_rel = rel(target["draft_directory"], "draft_directory")
        check(draft_rel.as_posix() == f"draft/{key}" and str(draft_rel) not in drafts,
              "草稿目录必须是 draft/<key>")
        drafts.add(str(draft_rel))
        nonempty(target["outcome"], "target.outcome")
        step = object_fields(target["next_step"], {"name", "reason"}, "next_step")
        nonempty(step["name"], "next_step.name")
        nonempty(step["reason"], "next_step.reason")
        targets[key] = path
    first = record["handoff"]["first_target"]
    check(first is None or first in targets, "handoff.first_target 无效")
    return targets


def source_files(record: dict[str, Any], project: Path, operation: Path, receipt: Any) -> dict[str, tuple[dict[str, Any], bytes]]:
    sources: dict[str, tuple[dict[str, Any], bytes]] = {}
    source = record["source"]
    expected_paths: set[str] = set()
    input_ids = set()
    if record["kind"] == "feature":
        source_dir = within(project, source["directory"], "source.directory")
        check(source_dir.is_dir() and source_dir.parent == project / ".sdlc" / "specs", "正式来源无效")
        actual = regular_tree(source_dir)
        if receipt and record["source_notice"]:
            notice = record["source_notice"]
            notice_path = within(project, notice["path"], "source_notice.path")
            if notice_path.exists():
                check(file_digest(notice_path) == notice["sha256"], "来源说明已被外部修改")
                actual.pop(notice_path.relative_to(source_dir).as_posix(), None)
        expected_paths = {p.relative_to(project).as_posix() for p in actual.values()}
    else:
        for inp in source["inputs"]:
            object_fields(inp, {"id", "path"}, "source.input")
            name = nonempty(inp["id"], "source.input.id")
            check(name not in input_ids, "输入 ID 重复", 2)
            input_ids.add(name)
            check(inp["path"] is None or (isinstance(inp["path"], str) and Path(inp["path"]).is_absolute()),
                  "intake 输入路径必须为绝对路径或 null", 2)
    seen_paths: set[str] = set()
    for entry in record["source_files"]:
        object_fields(entry, {"id", "path", "input_id", "sha256", "snapshot_path", "handling", "reason"}, "source_file")
        name = nonempty(entry["id"], "source_file.id")
        check(name not in sources, f"来源 ID 重复：{name}", 2)
        hash_value(entry["sha256"], "source_file.sha256")
        check(entry["handling"] in ("input", "history", "ignored"), "source_file.handling 无效", 2)
        nonempty(entry["reason"], "source_file.reason")
        if record["kind"] == "feature":
            check(entry["input_id"] is None, "feature source_file.input_id 应为 null", 2)
            path = within(project, entry["path"], "source_file.path")
            check(source_dir in path.parents, "来源文件不属于正式来源目录")
            check(entry["path"] not in seen_paths, "来源文件路径重复", 2)
            seen_paths.add(entry["path"])
            if not path.is_file() or file_digest(path) != entry["sha256"]:
                raise SourceChanged(f"来源文件已改变：{entry['path']}")
        else:
            check(entry["input_id"] in input_ids, "intake source_file.input_id 无效")
            check(entry["input_id"] not in seen_paths, "intake 输入重复", 2)
            seen_paths.add(entry["input_id"])
            inp = next(x for x in source["inputs"] if x["id"] == entry["input_id"])
            check(entry["path"] == inp["path"], "intake 来源路径与 input 不符")
            if entry["path"] is not None:
                path = Path(entry["path"])
                check(not path.is_symlink(), "intake 来源是链接")
                if not path.is_file() or file_digest(path) != entry["sha256"]:
                    raise SourceChanged(f"intake 来源文件已改变：{path}")
        if entry["snapshot_path"] is None:
            check(entry["handling"] in ("history", "ignored"), "参与分析的来源必须有快照")
            data = b""
        else:
            snap = within(operation, entry["snapshot_path"], "snapshot_path")
            check(snap.is_file() and not snap.is_symlink(), "来源快照不存在或为链接")
            data = raw_file(snap)
            check(digest(data) == entry["sha256"], "来源快照与登记摘要不符")
            if entry["path"] is not None:
                original = Path(entry["path"]) if record["kind"] == "intake" else within(project, entry["path"], "source_file.path")
                check(not (snap.stat().st_dev == original.stat().st_dev and snap.stat().st_ino == original.stat().st_ino),
                      "快照不能硬链接到原文件")
        sources[name] = (entry, data)
    if record["kind"] == "feature":
        if seen_paths != expected_paths:
            raise SourceChanged(f"正式来源文件集合已变化：新增 {sorted(expected_paths-seen_paths)}，删除 {sorted(seen_paths-expected_paths)}")
    else:
        check(seen_paths == input_ids, "intake 来源清单未覆盖所有输入")
    return sources


def check_code(record: dict[str, Any], project: Path, receipt: Any = None) -> None:
    observed = record["observed_code"]
    git = observed["git"]
    check(git is None or isinstance(git, dict), "observed_code.git 无效", 2)
    seen = set()
    names = []
    new_observation = isinstance(git, dict) and "state" in git
    for entry in observed["files"]:
        check(isinstance(entry, dict) and set(entry) in ({"path", "sha256", "reason"},
              {"path", "sha256", "reason", "vcs"}), "observed_code.file 字段缺失或未知", 2)
        path = within(project, entry["path"], "observed_code.file.path")
        check(entry["path"] not in seen, "代码观察路径重复", 2)
        seen.add(entry["path"])
        names.append(entry["path"])
        if entry["sha256"] is not None:
            hash_value(entry["sha256"], "observed_code.file.sha256")
        nonempty(entry["reason"], "observed_code.file.reason")
        if "vcs" not in entry:
            raise SourceChanged("旧代码观察缺少暂存区和工作区分层证据；请重新 inspect 并复核方案；"
                                + ("已开始发布的操作须保留回执并人工核查已写入范围" if receipt else "预览须重新确认"))
        check(isinstance(entry["vcs"], dict), "observed_code.file.vcs 无效", 2)
        if entry["sha256"] is not None and not path.is_file():
            raise SourceChanged(f"相关代码观察已改变：{entry['path']}")
    check(not names or new_observation, "observed_code.git 缺少与文件分层观察对应的状态", 2)
    if new_observation:
        current = code_info(project, names)
        if current["git"] != git:
            raise SourceChanged("相关 Git 基线或可用状态已改变；实现承接依据须复核")
        for old_file, new_file in zip(observed["files"], current["files"]):
            if old_file["sha256"] != new_file["sha256"] or old_file["vcs"] != new_file["vcs"]:
                raise SourceChanged(f"相关代码观察已改变：{old_file['path']}（含暂存区与工作区）")
    elif git is not None:
        # Records without selected files retain their original HEAD check.
        check(isinstance(git.get("head"), str), "observed_code.git 无效", 2)
        now, _ = git_info(project)
        if now.get("head") != git["head"]:
            raise SourceChanged("相关 Git HEAD 已改变；实现承接依据须复核")


def marker(record: dict[str, Any], target: str | None, operation: Path, project: Path) -> bytes:
    obj = {"operation_id": record["operation_id"]}
    if target is not None:
        obj["target"] = target
    obj["operation_directory"] = operation.relative_to(project).as_posix()
    tag = "sdlc-cut-origin" if target is not None else "sdlc-cut-source"
    return f"<!-- {tag} {json.dumps(obj, ensure_ascii=False, separators=(',', ':'))} -->".encode("utf-8")


def check_marker(path: Path, expected: bytes) -> None:
    check(raw_file(path).split(b"\n", 1)[0].rstrip(b"\r") == expected, f"CUT 归属标记不符：{path}")


def plan_manifest(operation: Path) -> tuple[str, list[str]]:
    files = {"cut.json": operation / "cut.json", "cut.md": operation / "cut.md"}
    draft_root = operation / "draft"
    check(draft_root.is_dir(), "draft 目录不存在")
    files.update({f"draft/{name}": path for name, path in regular_tree(draft_root).items()})
    lines = []
    for name in sorted(files):
        rel(name, "方案文件路径")
        lines.append(f"{file_digest(files[name])}  {name}\n")
    return digest("".join(lines).encode("utf-8")), list(sorted(files))


def draft_files(record: dict[str, Any], project: Path, operation: Path,
                targets: dict[str, Path]) -> tuple[str, list[str]]:
    expected: set[str] = set()
    by_target: dict[str, set[str]] = {key: set() for key in targets}
    for item in record["draft_files"]:
        object_fields(item, {"target", "path", "sha256"}, "draft_file")
        check(item["target"] in targets, "draft_file.target 无效")
        name = rel(item["path"], "draft_file.path").as_posix()
        check(name not in by_target[item["target"]], "草稿文件重复")
        by_target[item["target"]].add(name)
        hash_value(item["sha256"], "draft_file.sha256")
        actual = f"draft/{item['target']}/{name}"
        expected.add(actual)
        path = within(operation, actual, "草稿路径")
        check(file_digest(path) == item["sha256"], f"草稿摘要不符：{actual}")
    for key, files in by_target.items():
        check("cut.md" in files, f"后继 {key} 缺少归属 cut.md")
        check("brief.md" in files if record["kind"] == "intake" else "spec.md" in files,
              f"后继 {key} 缺少 {'brief.md' if record['kind']=='intake' else 'spec.md'}")
        check_marker(operation / "draft" / key / "cut.md", marker(record, key, operation, project))
    notice = record["source_notice"]
    if notice is not None:
        hash_value(notice["sha256"], "source_notice.sha256")
        path = within(project, notice["path"], "source_notice.path")
        source_dir = within(project, record["source"]["directory"], "source.directory")
        check(path.parent == source_dir and path.name.startswith("cut") and path.suffix == ".md",
              "来源说明必须位于正式来源直接子目录")
        notice_draft = within(operation, notice["draft_path"], "source_notice.draft_path")
        check(notice_draft.parent == operation / "draft", "来源说明草稿路径无效")
        check(file_digest(notice_draft) == notice["sha256"], "来源说明草稿摘要不符")
        check_marker(notice_draft, marker(record, None, operation, project))
        expected.add(notice["draft_path"])
    plan_sha, manifest = plan_manifest(operation)
    actual = {x for x in manifest if x.startswith("draft/")}
    check(actual == expected, f"草稿文件集合不符：额外 {sorted(actual-expected)}，缺少 {sorted(expected-actual)}")
    return plan_sha, manifest


def source_ref(value: Any, sources: dict[str, tuple[dict[str, Any], bytes]], label: str) -> tuple[str, int | str | None]:
    check(isinstance(value, dict), f"{label} 必须是对象", 2)
    check(set(value) in ({"file"}, {"file", "anchor"}, {"file", "lines"}), f"{label} 定位字段无效", 2)
    fid = nonempty(value.get("file"), f"{label}.file")
    check(fid in sources, f"{label} 引用未知来源文件：{fid}")
    entry, data = sources[fid]
    check(entry["snapshot_path"] is not None, f"{label} 引用的来源没有快照")
    if set(value) == {"file"}:
        return fid, None
    check(data, f"{label} 引用的来源没有可定位文本")
    try:
        text = data.decode("utf-8")
    except UnicodeError as exc:
        raise CutError(f"{label} 引用的文件不是 UTF-8 文本") from exc
    if "anchor" in value:
        anchor = nonempty(value["anchor"], f"{label}.anchor")
        check(ANCHOR.fullmatch(anchor), f"{label} 未支持的 anchor；请使用行段定位")
        pattern = r"(?<![A-Za-z0-9_-])" + re.escape(anchor) + r"(?![A-Za-z0-9_-])"
        check(re.search(pattern, text) is not None, f"{label} anchor 不存在：{anchor}")
        return fid, anchor
    if "lines" in value:
        lines = value["lines"]
        check(isinstance(lines, list) and len(lines) == 2 and all(type(x) is int for x in lines), f"{label}.lines 格式错误", 2)
        check(1 <= lines[0] <= lines[1] <= len(text.splitlines()), f"{label}.lines 越界")
        return fid, lines[0]
    raise CutError(f"{label} 定位字段无效", 2)


def check_items(record: dict[str, Any], sources: dict[str, tuple[dict[str, Any], bytes]],
                targets: dict[str, Path]) -> tuple[set[str], set[tuple[str, int | str | None, str]]]:
    ids: set[str] = set()
    refs: set[tuple[str, int | str | None, str]] = set()
    for item in record["items"]:
        object_fields(item, {"id", "source_ref", "kind", "targets", "disposition", "reason"}, "item")
        name = nonempty(item["id"], "item.id")
        check(name not in ids, f"item ID 重复：{name}", 2)
        ids.add(name)
        check(item["kind"] in KINDS and item["disposition"] in DISPOSITIONS,
              f"item 类别或处置无效：{name}", 2)
        ref = source_ref(item["source_ref"], sources, f"item {name}")
        refs.add((ref[0], ref[1], item["kind"]))
        values = array(item["targets"], f"item {name}.targets")
        check(len(values) == len(set(values)) and all(x in targets for x in values), f"item {name} 目标无效")
        if item["disposition"] in ("assigned", "deferred", "baseline"):
            check(values, f"item {name} 缺少承接目标")
        if item["disposition"] == "shared":
            check(len(values) >= 2, f"item {name} shared 须有两个后继")
        if item["kind"] == "task" and item["disposition"] == "assigned":
            check(len(values) == 1, f"建设任务 {name} 不能重复分配")
        nonempty(item["reason"], f"item {name}.reason")
    return ids, refs


def boxes(text: str, task_mode: bool) -> list[dict[str, Any]]:
    result = []
    fence = None
    comment = False
    example_level = None
    for number, raw in enumerate(text.splitlines(), 1):
        if fence is not None:
            stripped = raw.lstrip()
            opening = re.match(r"^(`{3,}|~{3,})", stripped)
            if opening:
                token = opening.group(1)
                if (token[0] == fence[0] and len(token) >= fence[1]
                        and not stripped[opening.end():].strip()):
                    fence = None
            continue
        visible = []
        pos = 0
        while pos < len(raw):
            if comment:
                end = raw.find("-->", pos)
                if end < 0:
                    break
                comment = False
                pos = end + 3
            else:
                start = raw.find("<!--", pos)
                if start < 0:
                    visible.append(raw[pos:])
                    break
                visible.append(raw[pos:start])
                comment = True
                pos = start + 4
        line = "".join(visible)
        stripped = line.lstrip()
        opening = re.match(r"^(`{3,}|~{3,})", stripped)
        if opening:
            token = opening.group(1)
            fence = (token[0], len(token))
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)", line)
        if heading:
            level = len(heading.group(1))
            if example_level is not None and level <= example_level:
                example_level = None
            if re.match(r"^(?:\d+[.)]\s*)?(?:parallel\s+examples?|usage\s+examples?|Examples?|示例|用法示例|并行示例)(?:\s|:|：|$)",
                        heading.group(2).strip(), re.I):
                example_level = level
            continue
        if example_level is not None:
            continue
        match = BOX.match(line)
        if not match:
            continue
        anchored = (TASK if task_mode else CHECKLIST).match(line)
        result.append({"line": number, "anchor": anchored.group(2) if anchored else None,
                       "checked": match.group(1).lower() == "x"})
    return result


def check_carryover(record: dict[str, Any], sources: dict[str, tuple[dict[str, Any], bytes]],
                    targets: dict[str, Path]) -> dict[str, tuple[str, int | str | None, set[str]]]:
    entries: dict[str, tuple[str, int | str | None, set[str]]] = {}
    for item in record["carryover"]:
        object_fields(item, {"id", "source_ref", "targets", "claim", "evidence", "applicability", "remaining"}, "carryover")
        name = nonempty(item["id"], "carryover.id")
        check(name not in entries, "carryover ID 重复", 2)
        source = source_ref(item["source_ref"], sources, f"carryover {name}")
        values = array(item["targets"], f"carryover {name}.targets")
        check(values and len(values) == len(set(values)) and all(x in targets for x in values),
              f"carryover {name} 目标无效")
        entries[name] = (source[0], source[1], set(values))
        for key in ("claim", "applicability", "remaining"):
            nonempty(item[key], f"carryover {name}.{key}")
        evidence = item["evidence"]
        check((isinstance(evidence, str) and evidence.strip()) or (isinstance(evidence, list) and evidence),
              f"carryover {name} 需要可定位证据")
        if isinstance(evidence, list):
            for value in evidence:
                if isinstance(value, dict):
                    source_ref(value, sources, f"carryover {name}.evidence")
                else:
                    nonempty(value, f"carryover {name}.evidence")
    return entries


def check_mappings(record: dict[str, Any], operation: Path,
                   sources: dict[str, tuple[dict[str, Any], bytes]], targets: dict[str, Path],
                   item_refs: set[tuple[str, int | str | None, str]],
                   carryovers: dict[str, tuple[str, int | str | None, set[str]]]) -> None:
    source_boxes: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for fid, (entry, data) in sources.items():
        path = entry["path"]
        if not isinstance(path, str) or not data:
            continue
        category = "task" if path.endswith("/tasks.md") else "checklist" if "/checklists/" in path else None
        if category:
            try:
                source_boxes[(fid, category)] = boxes(data.decode("utf-8"), category == "task")
            except UnicodeError as exc:
                raise CutError(f"任务或清单不是 UTF-8：{path}") from exc
    for (fid, category), rows in source_boxes.items():
        ids = [x["anchor"] for x in rows if x["anchor"]]
        check(len(ids) == len(set(ids)), f"来源 {fid} {category} ID 重复")
    covered: set[tuple[str, str, int]] = set()
    dest_cache: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for draft in record["draft_files"]:
        key, name = draft["target"], draft["path"]
        category = "task" if name == "tasks.md" else "checklist" if name.startswith("checklists/") and name.endswith(".md") else None
        if category:
            draft_name = f"draft/{key}/{name}"
            try:
                dest_cache[(key, name, category)] = boxes(raw_file(within(operation, draft_name, "draft_files.path")).decode("utf-8"),
                                                         category == "task")
            except UnicodeError as exc:
                raise CutError(f"目标任务或清单不是 UTF-8：{draft_name}") from exc
            ids = [x["anchor"] for x in dest_cache[(key, name, category)] if x["anchor"]]
            check(len(ids) == len(set(ids)), f"后继 {key}/{name} {category} ID 重复")
    checked_destinations: set[tuple[str, str, str, int]] = set()
    for category, rows in (("task", record["task_mapping"]), ("checklist", record["checklist_mapping"])):
        for row in rows:
            object_fields(row, {"source_ref", "source_checked", "destinations", "carryover_ids", "reason"}, f"{category}_mapping")
            fid, locator = source_ref(row["source_ref"], sources, f"{category}_mapping.source_ref")
            check(locator is not None, f"{category}_mapping 必须定位单个条目")
            entries = source_boxes.get((fid, category), [])
            found = [x for x in entries if x["anchor"] == locator or x["line"] == locator]
            check(len(found) == 1, f"{category}_mapping 来源条目未唯一定位：{fid}/{locator}")
            source_box = found[0]
            identity = (fid, category, source_box["line"])
            check(identity not in covered, f"{category}_mapping 来源条目重复")
            covered.add(identity)
            bool_value(row["source_checked"], f"{category}_mapping.source_checked")
            check(row["source_checked"] == source_box["checked"], f"{category}_mapping 来源勾选值不符")
            check((fid, locator, category) in item_refs or (fid, source_box["line"], category) in item_refs,
                  f"来源 {category} 条目缺少 items 处置：{fid}/{locator}")
            nonempty(row["reason"], f"{category}_mapping.reason")
            carry = array(row["carryover_ids"], f"{category}_mapping.carryover_ids")
            check(len(carry) == len(set(carry)) and all(x in carryovers for x in carry),
                  "mapping 引用未知或重复 carryover")
            for carry_id in carry:
                evidence_fid, evidence_locator, _ = carryovers[carry_id]
                check(evidence_fid == fid and evidence_locator is not None and
                      evidence_locator in (source_box["line"], source_box["anchor"]),
                      f"{category}_mapping 引用的 carryover {carry_id} 不对应来源条目")
            destinations = array(row["destinations"], f"{category}_mapping.destinations")
            for dest in destinations:
                check(isinstance(dest, dict) and set(dest) in ({"target", "path", "anchor", "checked"},
                                                             {"target", "path", "lines", "checked"}),
                      "mapping destination 字段无效", 2)
                key = dest["target"]
                check(key in targets, "mapping destination 目标无效")
                name = rel(dest["path"], "mapping destination.path").as_posix()
                draft_name = f"draft/{key}/{name}"
                path = within(operation, draft_name, "mapping destination.path")
                check(path.is_file(), f"mapping destination 文件不存在：{draft_name}")
                if category == "task":
                    check(name == "tasks.md", "任务目标必须定位 tasks.md")
                else:
                    check(name.startswith("checklists/") and name.endswith(".md"), "清单目标必须位于 checklists/")
                cache_key = (key, name, category)
                check(cache_key in dest_cache, f"mapping destination 未登记为草稿：{draft_name}")
                dest_boxes = dest_cache[cache_key]
                if "anchor" in dest:
                    anchor = nonempty(dest["anchor"], "destination.anchor")
                    check(ANCHOR.fullmatch(anchor), "目标 anchor 格式不受支持")
                    found_dest = [x for x in dest_boxes if x["anchor"] == anchor]
                else:
                    lines = dest["lines"]
                    check(isinstance(lines, list) and len(lines) == 2 and all(type(x) is int for x in lines),
                          "destination.lines 格式错误", 2)
                    found_dest = [x for x in dest_boxes if lines[0] <= x["line"] <= lines[1]]
                check(len(found_dest) == 1, f"目标 {category} 条目未唯一定位：{draft_name}")
                bool_value(dest["checked"], "destination.checked")
                check(dest["checked"] == found_dest[0]["checked"], "目标勾选值不符")
                if dest["checked"]:
                    check(any(key in carryovers[carry_id][2] for carry_id in carry),
                          f"后继 {key}/{name} 已勾选条目缺少适用的 carryover")
                    checked_destinations.add((key, name, category, found_dest[0]["line"]))
            if not destinations:
                item = [x for x in record["items"] if x["kind"] == category and x["source_ref"] == row["source_ref"]]
                check(item and item[0]["disposition"] == "excluded", "无目标的 mapping 须有明确排除决定")
    for (fid, category), rows in source_boxes.items():
        for row in rows:
            check((fid, category, row["line"]) in covered,
                  f"来源 {category} 复选框未映射：{fid} 第 {row['line']} 行")
    for (key, name, category), rows in dest_cache.items():
        for row in rows:
            if row["checked"]:
                check((key, name, category, row["line"]) in checked_destinations,
                      f"后继 {key}/{name} 第 {row['line']} 行已勾选但未映射或缺少 carryover")
        if category == "task":
            check(all(x["anchor"] for x in rows), f"后继 {key}/{name} 存在未知任务格式")


def check_dependencies(record: dict[str, Any], targets: dict[str, Path]) -> None:
    graphs: dict[str, dict[str, set[str]]] = {kind: {key: set() for key in targets} for kind in ("implementation", "release")}
    for edge in record["dependencies"]:
        object_fields(edge, {"from", "requires", "external", "kind", "reason"}, "dependency")
        check(edge["from"] in targets and edge["kind"] in ("implementation", "release", "sequence"),
              "dependency.from 或 kind 无效")
        bool_value(edge["external"], "dependency.external")
        nonempty(edge["reason"], "dependency.reason")
        if edge["external"]:
            nonempty(edge["requires"], "dependency.requires")
        else:
            check(edge["requires"] in targets, "内部依赖指向未知后继")
            if edge["kind"] in graphs:
                graphs[edge["kind"]][edge["from"]].add(edge["requires"])
    for kind, graph in graphs.items():
        active: set[str] = set()
        done: set[str] = set()
        def visit(node: str) -> None:
            check(node not in active, f"{kind} 依赖存在环")
            if node in done:
                return
            active.add(node)
            for nxt in graph[node]:
                visit(nxt)
            active.remove(node)
            done.add(node)
        for key in graph:
            visit(key)


def blockers(record: dict[str, Any], targets: dict[str, Path]) -> tuple[list[str], list[str]]:
    result = []
    if not record["decision"]["boundary_confirmed"]:
        result.append("拆分边界尚未确认")
    if not record["decision"]["apply_authorized"]:
        result.append("尚无落实方案的执行授权记录")
    if not record["decision"]["basis"].strip():
        result.append("缺少决定依据")
    if not record["content_review"]["completed"] or not record["content_review"]["summary"].strip():
        result.append("Agent 内容复核尚未完成")
    unresolved = []
    seen: set[str] = set()
    for q in record["questions"]:
        object_fields(q, {"id", "text", "affects_boundary", "targets", "resolved", "resolution", "next_step"}, "question")
        name = nonempty(q["id"], "question.id")
        check(name not in seen, "question ID 重复", 2)
        seen.add(name)
        nonempty(q["text"], "question.text")
        bool_value(q["affects_boundary"], "question.affects_boundary")
        bool_value(q["resolved"], "question.resolved")
        values = array(q["targets"], "question.targets")
        check(values and all(x in targets for x in values), "question 缺少有效归属")
        if q["resolved"]:
            nonempty(q["resolution"], "question.resolution")
        else:
            nonempty(q["next_step"], "question.next_step")
            if q["affects_boundary"]:
                unresolved.append(name)
    if unresolved:
        result.append("影响边界的未决问题：" + ", ".join(unresolved))
    return result, unresolved


def validate_bundle(operation: Path, receipt: Any = None) -> tuple[dict[str, Any], Path, str, list[str], list[str]]:
    record = load_json(operation / "cut.json")
    schema(record, operation)
    project = project_path(record["project"])
    check(str(project) == record["project"], "cut.json project 不是规范绝对路径")
    scope(project, record["kind"], operation)
    targets = target_paths(record, project, operation)
    sources = source_files(record, project, operation, receipt)
    check_code(record, project, receipt)
    plan_sha, manifest = draft_files(record, project, operation, targets)
    intended = write_intents(record, project, operation, plan_sha)
    if receipt:
        bind_receipt(receipt, intended)
    check_output_state(record, project, operation, targets, receipt)
    _, item_refs = check_items(record, sources, targets)
    carry_ids = check_carryover(record, sources, targets)
    check_mappings(record, operation, sources, targets, item_refs, carry_ids)
    check_dependencies(record, targets)
    application_blockers, unresolved = blockers(record, targets)
    return record, project, plan_sha, application_blockers, unresolved


def validate(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    operation = operation_path(args.operation)
    receipt = load_json(operation / "receipt.json") if (operation / "receipt.json").exists() else None
    result: dict[str, Any] = {"command": "validate", "operation_directory": str(operation), "plan_sha256": None,
                              "structural_errors": [], "errors": [], "source_changed": False,
                              "application_blockers": [], "unresolved_boundary_questions": [],
                              "semantic_completeness": "not_decided_by_program", "limitations": []}
    try:
        record, _, plan_sha, application_blockers, unresolved = validate_bundle(operation, receipt)
        result["plan_sha256"] = plan_sha
        result["application_blockers"] = application_blockers
        result["unresolved_boundary_questions"] = unresolved
        result["limitations"] = record["observed_code"]["limitations"] + [
            "程序只验证已登记条目；不能判定原文义务是否漏登或独立发布是否成立"]
        return result, 0
    except CutError as exc:
        result["structural_errors"].append(str(exc))
        result["errors"].append(str(exc))
        result["source_changed"] = isinstance(exc, SourceChanged)
        return result, exc.code


def write_intents(record: dict[str, Any], project: Path, operation: Path, plan_sha: str) -> dict[str, Any]:
    drafts = {(x["target"], x["path"]): x["sha256"] for x in record["draft_files"]}
    writes: list[dict[str, Any]] = []
    receipt_targets = []
    for target in record["targets"]:
        key = target["key"]
        directory = target["directory"]
        origin_sha = drafts[(key, "cut.md")]
        receipt_targets.append({"key": key, "directory": directory, "origin_path": f"{directory}/cut.md",
                                "origin_sha256": origin_sha})
        writes.append({"path": f"{directory}/cut.md", "sha256": origin_sha, "role": "successor-origin",
                       "target": key, "completed": False})
        for item in sorted((x for x in record["draft_files"] if x["target"] == key and x["path"] != "cut.md"),
                           key=lambda x: x["path"]):
            writes.append({"path": f"{directory}/{item['path']}", "sha256": item["sha256"],
                           "role": "successor-material", "target": key, "completed": False})
    if record["source_notice"] is not None:
        notice = record["source_notice"]
        writes.append({"path": notice["path"], "sha256": notice["sha256"], "role": "source-notice",
                       "target": None, "completed": False})
    for item in writes:
        path = within(project, item["path"], "receipt.write.path")
        check(path != operation and operation not in path.parents, "写入意图触及操作目录")
    return {"format_version": 1, "operation_id": record["operation_id"], "project": str(project),
            "kind": record["kind"], "source": record["source"], "plan_sha256": plan_sha,
            "targets": receipt_targets, "writes": writes, "applied_at": None}


def bind_receipt(receipt: dict[str, Any], intended: dict[str, Any]) -> None:
    object_fields(receipt, {"format_version", "operation_id", "project", "kind", "source", "plan_sha256",
                            "targets", "writes", "applied_at"}, "receipt")
    for key in ("format_version", "operation_id", "project", "kind", "source", "plan_sha256", "targets"):
        check(receipt[key] == intended[key], f"receipt.{key} 与原方案不符")
    check(isinstance(receipt["writes"], list) and len(receipt["writes"]) == len(intended["writes"]),
          "receipt.writes 长度不符")
    for got, want in zip(receipt["writes"], intended["writes"]):
        object_fields(got, {"path", "sha256", "role", "target", "completed"}, "receipt.write")
        bool_value(got["completed"], "receipt.write.completed")
        for key in ("path", "sha256", "role", "target"):
            check(got[key] == want[key], f"receipt.writes.{key} 与写入意图不符")
    check(receipt["applied_at"] is None or isinstance(receipt["applied_at"], str) and receipt["applied_at"],
          "receipt.applied_at 格式错误")
    if receipt["applied_at"]:
        check(all(x["completed"] for x in receipt["writes"]), "成功回执仍有未完成写入")


def inspect_receipt(operation: Path, record: dict[str, Any], receipt: dict[str, Any], project: Path) -> None:
    schema(record, operation)
    check(record["project"] == str(project), "已有 CUT 操作项目身份不符")
    plan_sha, _ = plan_manifest(operation)
    check(plan_sha == receipt.get("plan_sha256"), "已有 CUT 方案与回执摘要不符")
    bind_receipt(receipt, write_intents(record, project, operation, plan_sha))


def check_output_state(record: dict[str, Any], project: Path, operation: Path,
                       targets: dict[str, Path], receipt: Any) -> None:
    if receipt and receipt["applied_at"]:
        return
    for key, directory in targets.items():
        entries = [x for x in receipt["writes"] if x["target"] == key] if receipt else []
        if not directory.exists() and not directory.is_symlink():
            check(not any(x["completed"] for x in entries), f"回执记录已写目标但目录缺失：{directory}")
            continue
        check(receipt is not None, f"目标目录已占用：{directory}")
        check(directory.is_dir() and not directory.is_symlink(), f"目标不是普通目录：{directory}")
        origin = directory / "cut.md"
        check(origin.is_file() and not origin.is_symlink(), f"目标缺少归属说明：{directory}")
        check_marker(origin, marker(record, key, operation, project))
        check(file_digest(origin) == entries[0]["sha256"], f"目标归属说明摘要不符：{directory}")
        expected = {x["path"][len(record_target["directory"]) + 1:] for record_target in record["targets"]
                    if record_target["key"] == key for x in entries}
        actual = set(regular_tree(directory))
        check(actual <= expected, f"目标存在未登记文件：{directory}: {sorted(actual-expected)}")
        for item in entries:
            path = within(project, item["path"], "receipt.write.path")
            if path.exists() or path.is_symlink():
                check(path.is_file() and not path.is_symlink() and file_digest(path) == item["sha256"],
                      f"目标文件内容不符：{path}")
            else:
                check(not item["completed"], f"回执称已写目标文件但实际缺失：{path}")
    notice = record["source_notice"]
    if notice:
        path = within(project, notice["path"], "source_notice.path")
        item = next((x for x in receipt["writes"] if x["role"] == "source-notice"), None) if receipt else None
        if path.exists() or path.is_symlink():
            check(item is not None, f"来源说明路径已占用：{path}")
            check(path.is_file() and not path.is_symlink() and file_digest(path) == item["sha256"],
                  f"来源说明内容不符：{path}")
            check_marker(path, marker(record, None, operation, project))
        elif item:
            check(not item["completed"], f"回执称已写来源说明但实际缺失：{path}")


def write_status(receipt: dict[str, Any]) -> tuple[list[str], list[str]]:
    return ([x["path"] for x in receipt["writes"] if x["completed"]],
            [x["path"] for x in receipt["writes"] if not x["completed"]])


def current_target_files(directory: Path) -> set[str]:
    return set(regular_tree(directory))


def publish_target(record: dict[str, Any], project: Path, operation: Path,
                   receipt: dict[str, Any], key: str) -> None:
    target = next(x for x in record["targets"] if x["key"] == key)
    directory = within(project, target["directory"], "target.directory")
    intent = [x for x in receipt["writes"] if x["target"] == key]
    expected = {x["path"][len(target["directory"]) + 1:] for x in intent}
    if directory.exists():
        check(directory.is_dir() and not directory.is_symlink(), f"目标被其他对象占用：{directory}")
        origin = directory / "cut.md"
        check(origin.is_file() and not origin.is_symlink(), f"目标目录缺少本次归属说明，不能接管：{directory}")
        check_marker(origin, marker(record, key, operation, project))
        check(file_digest(origin) == intent[0]["sha256"], f"目标归属说明已变化：{origin}")
        existing = current_target_files(directory)
        check(existing <= expected, f"目标含未计划文件：{directory}: {sorted(existing-expected)}")
    else:
        directory.mkdir()
    for item in intent:
        path = within(project, item["path"], "receipt.write.path")
        if path.exists() or path.is_symlink():
            check(path.is_file() and not path.is_symlink() and file_digest(path) == item["sha256"],
                  f"已存在输出与回执不符：{path}")
            if item["role"] == "successor-origin":
                check_marker(path, marker(record, key, operation, project))
        else:
            check(not item["completed"], f"回执称已写入但文件不存在：{path}")
            path.parent.mkdir(parents=True, exist_ok=True)
            source_rel = item["path"][len(target["directory"]) + 1:]
            draft = within(operation, f"draft/{key}/{source_rel}", "draft_file")
            write_new(path, raw_file(draft))
            check(file_digest(path) == item["sha256"], f"刚写入的摘要不符：{path}")
        if not item["completed"]:
            item["completed"] = True
            save_receipt(operation / "receipt.json", receipt)


def publish_notice(record: dict[str, Any], project: Path, operation: Path,
                   receipt: dict[str, Any]) -> None:
    notice = record["source_notice"]
    if notice is None:
        return
    item = next(x for x in receipt["writes"] if x["role"] == "source-notice")
    path = within(project, notice["path"], "source_notice.path")
    if path.exists() or path.is_symlink():
        check(path.is_file() and not path.is_symlink() and file_digest(path) == item["sha256"],
              f"来源说明被占用或改变：{path}")
        check_marker(path, marker(record, None, operation, project))
    else:
        check(not item["completed"], "回执称来源说明已写入但文件不存在")
        draft = within(operation, notice["draft_path"], "source_notice.draft_path")
        write_new(path, raw_file(draft))
        check(file_digest(path) == item["sha256"], "来源说明写入后摘要不符")
    if not item["completed"]:
        item["completed"] = True
        save_receipt(operation / "receipt.json", receipt)


def apply(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    operation = operation_path(args.operation)
    hash_value(args.expected_plan_sha, "expected-plan-sha")
    record = load_json(operation / "cut.json")
    schema(record, operation)
    project = project_path(record["project"])
    result: dict[str, Any] = {"command": "apply", "operation_directory": str(operation), "status": "not_applied",
                              "plan_sha256": args.expected_plan_sha, "targets": [], "written": [], "pending": [],
                              "errors": [], "limitations": []}
    with locked(project, record["kind"], operation):
        receipt_file = operation / "receipt.json"
        receipt = load_json(receipt_file) if receipt_file.exists() else None
        if receipt and receipt.get("applied_at"):
            # A completed CUT is immutable as an operation, though successor work can continue.
            plan_sha, _ = plan_manifest(operation)
            check(plan_sha == args.expected_plan_sha == receipt.get("plan_sha256"),
                  "已完成方案摘要与命令或回执不一致")
            intended = write_intents(record, project, operation, plan_sha)
            bind_receipt(receipt, intended)
            result.update(status="already_applied", targets=receipt["targets"],
                          written=[x["path"] for x in receipt["writes"]], pending=[],
                          limitations=["后继当前内容未重新检查；成功重试不会回写旧草稿"])
            return result, 0
        try:
            record, project, plan_sha, application_blockers, _ = validate_bundle(operation, receipt)
            check(plan_sha == args.expected_plan_sha, "方案摘要与 expected-plan-sha 不一致")
            check(not application_blockers, "应用受阻：" + "；".join(application_blockers))
            intended = write_intents(record, project, operation, plan_sha)
            if record["kind"] == "feature":
                matches = existing_feature_ops(project, record["source"]["directory"])
                check(len(matches) == 1 and matches[0][0] == operation, "正式来源存在其他 CUT 操作")
            if receipt:
                bind_receipt(receipt, intended)
            else:
                for target in record["targets"]:
                    path = within(project, target["directory"], "target.directory")
                    check(not path.exists() and not path.is_symlink(), f"目标已占用：{path}")
                notice = record["source_notice"]
                if notice:
                    path = within(project, notice["path"], "source_notice.path")
                    check(not path.exists() and not path.is_symlink(), f"来源说明已占用：{path}")
                receipt = intended
                save_receipt(receipt_file, receipt)
            for target in record["targets"]:
                publish_target(record, project, operation, receipt, target["key"])
            publish_notice(record, project, operation, receipt)
            source_files(record, project, operation, receipt)
            check_code(record, project, receipt)
            for item in receipt["writes"]:
                check(item["completed"] and file_digest(within(project, item["path"], "receipt.write.path")) == item["sha256"],
                      f"最终输出不一致：{item['path']}")
            receipt["applied_at"] = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
            save_receipt(receipt_file, receipt)
            written, pending = write_status(receipt)
            result.update(status="applied", targets=receipt["targets"], written=written, pending=pending,
                          limitations=["CUT 只完成材料发布；原 SDLC 阶段、业务验收和独立上线尚未由程序判定"])
            return result, 0
        except (CutError, OSError) as exc:
            actual = load_json(receipt_file) if receipt_file.exists() else None
            written, pending = write_status(actual) if actual else ([], [])
            result.update(status="incomplete" if actual else "not_applied", written=written, pending=pending,
                          targets=actual["targets"] if actual else [], errors=[str(exc)],
                          limitations=["现场已保留；仅同次操作且归属和字节匹配时可接续"] if actual else [])
            return result, (4 if actual else exc.code if isinstance(exc, CutError) else 3)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="一次性 SDLC 需求材料拆分的确定性文件工具")
    subs = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subs.add_parser("inspect")
    inspect_parser.add_argument("--project", required=True)
    inspect_parser.add_argument("--kind", choices=("feature", "intake"), required=True)
    inspect_parser.add_argument("--source", action="append", required=True)
    inspect_parser.add_argument("--workspace", required=True)
    inspect_parser.add_argument("--observe-code", action="append", default=[])
    validate_parser = subs.add_parser("validate")
    validate_parser.add_argument("--operation", required=True)
    apply_parser = subs.add_parser("apply")
    apply_parser.add_argument("--operation", required=True)
    apply_parser.add_argument("--expected-plan-sha", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            response, code = inspect(args), 0
        elif args.command == "validate":
            response, code = validate(args)
        else:
            response, code = apply(args)
    except CutError as exc:
        response = {"command": args.command, "operation_directory": getattr(args, "operation", None),
                    "status": "error", "errors": [str(exc)], "limitations": []}
        code = exc.code
    except (OSError, ValueError, KeyError, TypeError) as exc:
        response = {"command": args.command, "operation_directory": getattr(args, "operation", None),
                    "status": "error", "errors": [f"输入或文件操作失败：{exc}"], "limitations": []}
        code = 3
    print(json.dumps(response, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())

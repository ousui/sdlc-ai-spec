"""Observable file and recovery contracts for the independent sdlc-cut skill."""

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src/skills/sdlc-cut/scripts/cut.py"
SPEC = importlib.util.spec_from_file_location("sdlc_cut", SCRIPT)
CUT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CUT)


def invoke(*args):
    proc = subprocess.run([sys.executable, "-B", str(SCRIPT), *map(str, args)],
                          text=True, capture_output=True, check=False)
    return proc.returncode, json.loads(proc.stdout)


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class CutContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sdlc-cut-test-")
        self.project = (Path(self.temp.name) / "project").resolve()
        self.project.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def _git(self, *args):
        proc = subprocess.run(["git", "-c", "user.name=CUT Test", "-c", "user.email=cut@example.invalid",
                               "-c", "core.hooksPath=/dev/null", "-C", str(self.project), *args],
                              capture_output=True, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))
        return proc.stdout

    def _git_base(self):
        self._git("init", "-q")
        write(self.project / "app.py", "base = 1\n")
        write(self.project / "other.txt", "unrelated\n")
        self._git("add", "app.py", "other.txt")
        self._git("commit", "-qm", "isolated baseline")

    def _code_entry(self, op):
        return self._record(op)["observed_code"]["files"][0]

    def test_distributed_skill_matches_source_and_runs_from_another_project(self):
        source = ROOT / "src/skills/sdlc-cut"
        packaged = ROOT / "dist/skills/sdlc-cut"
        source_files = {p.relative_to(source) for p in source.rglob("*") if p.is_file()}
        packaged_files = {p.relative_to(packaged) for p in packaged.rglob("*") if p.is_file()}
        self.assertEqual(packaged_files, source_files)
        for relative in source_files:
            self.assertEqual((packaged / relative).read_bytes(), (source / relative).read_bytes())
        self.assertFalse((ROOT / ".agents/skills/sdlc-cut").exists())
        for relative in ("UPSTREAM.json", "scripts/bash/common.sh",
                         "scripts/bash/create-new-feature.sh",
                         "references/workflows/sdlc-status.md"):
            self.assertTrue((packaged / "references" / "../../.." / relative).is_file())
        write(self.project / "input/requirements.md", "拆分为两项交付。\n")
        proc = subprocess.run([sys.executable, "-I", "-B", str(packaged / "scripts/cut.py"),
                               "inspect", "--project", str(self.project), "--kind", "intake",
                               "--source", "input/requirements.md", "--workspace", "cut-work/example"],
                              cwd=self.project, text=True, capture_output=True, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(Path(result["operation_directory"]).parent, self.project / "cut-work")

    def test_build_excludes_existing_independent_skill_python_cache(self):
        candidate = Path(self.temp.name) / "isolated-build"
        candidate.mkdir()
        for directory in ("src", "tools"):
            shutil.copytree(ROOT / directory, candidate / directory,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        (candidate / "docs").mkdir()
        shutil.copyfile(ROOT / "docs/naming-map.json", candidate / "docs/naming-map.json")
        for name in ("plugin-metadata.json", "upstream.lock.json", "CHANGELOG.md", "LICENSE",
                     "NOTICE", "pyproject.toml", "uv.lock", ".python-version"):
            shutil.copyfile(ROOT / name, candidate / name)
        cache = candidate / "src/skills/sdlc-cut/scripts/__pycache__"
        cache.mkdir()
        (cache / "cut.cpython-312.pyc").write_bytes(b"\x00\xff\x80 synthetic cache")
        (candidate / "src/skills/sdlc-cut/scripts/stray.pyc").write_bytes(b"\x00\xff stray cache")
        proc = subprocess.run([sys.executable, "-B", str(candidate / "tools/build.py")],
                              cwd=candidate, text=True, capture_output=True, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue((candidate / "dist/skills/sdlc-cut/scripts/cut.py").is_file())
        self.assertFalse(any("__pycache__" in p.parts or p.suffix == ".pyc"
                             for p in (candidate / "dist").rglob("*")))

    def _record(self, op):
        return json.loads((op / "cut.json").read_text())

    def _save(self, op, data):
        (op / "cut.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")

    def _draft(self, op, record, key, name, content):
        path = op / "draft" / key / name
        write(path, content)
        record["draft_files"].append({"target": key, "path": name,
                                      "sha256": CUT.digest(path.read_bytes())})

    def _replace_draft(self, op, record, key, name, content):
        path = op / "draft" / key / name
        write(path, content)
        entry = next(x for x in record["draft_files"] if x["target"] == key and x["path"] == name)
        entry["sha256"] = CUT.digest(path.read_bytes())

    def make_intake(self):
        write(self.project / "input/requirements.md", "先交付明细。\n后交付汇总并核对整体结果。\n")
        code, output = invoke("inspect", "--project", self.project, "--kind", "intake",
                              "--source", "input/requirements.md", "--workspace", "cut-work/cut-intake")
        self.assertEqual(code, 0, output)
        op = Path(output["operation_directory"])
        record = self._record(op)
        record["targets"] = [
            {"key": key, "directory": f"brief-{key.lower()}", "draft_directory": f"draft/{key}",
             "outcome": outcome, "next_step": {"name": "SPEC", "reason": "由简报创建正式需求"}}
            for key, outcome in (("A", "明细"), ("B", "汇总与整体核对"))]
        for key in ("A", "B"):
            mark = CUT.marker(record, key, op, self.project).decode()
            self._draft(op, record, key, "cut.md", mark + f"\n# {key} 来源\n")
            self._draft(op, record, key, "brief.md", f"# {key} 后继简报\n\n来源 S001；独立交付目标与验收。\n")
        record["items"] = [
            {"id": "I001", "source_ref": {"file": "S001", "lines": [1, 1]}, "kind": "requirement",
             "targets": ["A"], "disposition": "assigned", "reason": "A 承接明细"},
            {"id": "I002", "source_ref": {"file": "S001", "lines": [2, 2]}, "kind": "acceptance",
             "targets": ["B"], "disposition": "assigned", "reason": "B 承接整体结果"},
        ]
        record["handoff"] = {"first_target": "A", "instruction": "下次显式使用 brief-a 运行 SPEC"}
        record["decision"] = {"boundary_confirmed": True, "apply_authorized": True,
                              "basis": "合成测试副本中的既定执行决定"}
        record["content_review"] = {"completed": True, "summary": "测试输入的两个结果均已登记",
                                    "limitations": ["不代表真实业务验收"]}
        self._save(op, record)
        return op

    def make_feature(self, with_tasks=False, observe_code=(), task_suffix="", checklist_text=None,
                     binary_attachment=None):
        source = self.project / ".sdlc/specs/002-demo"
        source.mkdir(parents=True)
        write(source / "spec.md", "# 服务范围\nFR-001 明细查询。\nFR-002 汇总。\nSC-001 整体一致性。\n")
        write(self.project / ".sdlc/feature.json", '{"feature_directory":".sdlc/specs/002-demo"}\n')
        if binary_attachment is not None:
            path = source / "diagram.png"
            path.write_bytes(binary_attachment)
        if with_tasks:
            write(source / "tasks.md", "- [x] T001 已完成明细基础。\n- [ ] T002 汇总未完成。\n" + task_suffix)
            write(source / "checklists/review.md", checklist_text or
                  "- [x] 已核对明细条件。\n- [ ] 整体发布仍待评审。\n")
            write(source / "plan.md", "# 原方案\n明细与汇总共用数据接口。\n")
        code, output = invoke("inspect", "--project", self.project, "--kind", "feature",
                              "--source", ".sdlc/specs/002-demo", "--workspace", ".sdlc/cuts/cut-demo",
                              *(arg for name in observe_code for arg in ("--observe-code", name)))
        self.assertEqual(code, 0, output)
        op = Path(output["operation_directory"])
        record = self._record(op)
        record["targets"] = [
            {"key": key, "directory": f".sdlc/specs/{num}-{key.lower()}", "draft_directory": f"draft/{key}",
             "outcome": outcome, "next_step": {"name": "PLAN", "reason": "继续核对新边界方案"}}
            for key, num, outcome in (("A", "003", "明细"), ("B", "004", "汇总与整体验收"))]
        for key in ("A", "B"):
            mark = CUT.marker(record, key, op, self.project).decode()
            self._draft(op, record, key, "cut.md", mark + f"\n# {key} 来源\n")
            self._draft(op, record, key, "spec.md", f"# {key} 规格\n来源 002-demo；本范围验收可独立说明。\n")
        notice = CUT.marker(record, None, op, self.project).decode() + "\n# 来源保留\n"
        write(op / "draft/source-notice.md", notice)
        record["source_notice"]["sha256"] = CUT.digest((op / "draft/source-notice.md").read_bytes())
        record["items"] = [
            {"id": "I001", "source_ref": {"file": self._file_id(record, "spec.md"), "anchor": "FR-001"},
             "kind": "requirement", "targets": ["A"], "disposition": "assigned", "reason": "明细目标"},
            {"id": "I002", "source_ref": {"file": self._file_id(record, "spec.md"), "anchor": "FR-002"},
             "kind": "requirement", "targets": ["B"], "disposition": "deferred", "reason": "汇总仍由 B 完成"},
            {"id": "I003", "source_ref": {"file": self._file_id(record, "spec.md"), "anchor": "SC-001"},
             "kind": "acceptance", "targets": ["B"], "disposition": "assigned", "reason": "B 承接最终闭环"},
        ]
        if with_tasks:
            self._draft(op, record, "A", "tasks.md", "- [x] T001 承接明细基础。\n")
            self._draft(op, record, "B", "tasks.md", "- [ ] T001 实施汇总并验收整体。\n")
            self._draft(op, record, "A", "checklists/review.md", "- [x] 已核对明细条件。\n")
            self._draft(op, record, "B", "checklists/review.md", "- [ ] 整体发布仍待评审。\n")
            tasks_id = self._file_id(record, "tasks.md")
            check_id = self._file_id(record, "checklists/review.md")
            record["items"] += [
                {"id": "I004", "source_ref": {"file": tasks_id, "anchor": "T001"}, "kind": "task", "targets": ["A"],
                 "disposition": "assigned", "reason": "A 承接已有基础"},
                {"id": "I005", "source_ref": {"file": tasks_id, "anchor": "T002"}, "kind": "task", "targets": ["B"],
                 "disposition": "assigned", "reason": "B 承接剩余汇总"},
                {"id": "I006", "source_ref": {"file": check_id, "lines": [1, 1]}, "kind": "checklist", "targets": ["A"],
                 "disposition": "assigned", "reason": "A 条件仍适用"},
                {"id": "I007", "source_ref": {"file": check_id, "lines": [2, 2]}, "kind": "checklist", "targets": ["B"],
                 "disposition": "assigned", "reason": "B 仍待评审"},
            ]
            record["carryover"] = [
                {"id": "C001", "source_ref": {"file": tasks_id, "anchor": "T001"}, "targets": ["A"],
                 "claim": "已有明细基础", "evidence": ["合成测试中明确适用的既有完成依据"],
                 "applicability": "A 范围仍适用", "remaining": "仍需集成验证"},
                {"id": "C002", "source_ref": {"file": check_id, "lines": [1, 1]}, "targets": ["A"],
                 "claim": "已有明细评审", "evidence": ["合成测试的原评审记录"],
                 "applicability": "原评审条件未变", "remaining": "B 的清单尚未评审"},
            ]
            record["task_mapping"] = [
                {"source_ref": {"file": tasks_id, "anchor": "T001"}, "source_checked": True,
                 "destinations": [{"target": "A", "path": "tasks.md", "anchor": "T001", "checked": True}],
                 "carryover_ids": ["C001"], "reason": "A 仍适用"},
                {"source_ref": {"file": tasks_id, "anchor": "T002"}, "source_checked": False,
                 "destinations": [{"target": "B", "path": "tasks.md", "anchor": "T001", "checked": False}],
                 "carryover_ids": [], "reason": "B 仍需实施"},
            ]
            record["checklist_mapping"] = [
                {"source_ref": {"file": check_id, "lines": [1, 1]}, "source_checked": True,
                 "destinations": [{"target": "A", "path": "checklists/review.md", "lines": [1, 1], "checked": True}],
                 "carryover_ids": ["C002"], "reason": "评审条件仍适用"},
                {"source_ref": {"file": check_id, "lines": [2, 2]}, "source_checked": False,
                 "destinations": [{"target": "B", "path": "checklists/review.md", "lines": [1, 1], "checked": False}],
                 "carryover_ids": [], "reason": "B 后续评审"},
            ]
        record["dependencies"] = [{"from": "B", "requires": "A", "external": False,
                                   "kind": "release", "reason": "整体一致性需要明细口径"}]
        record["handoff"] = {"first_target": "A", "instruction": "显式选择 .sdlc/specs/003-a"}
        record["decision"] = {"boundary_confirmed": True, "apply_authorized": True,
                              "basis": "合成测试副本的既定执行决定"}
        record["content_review"] = {"completed": True, "summary": "测试范围已逐条登记",
                                    "limitations": ["不代表真实代码或发布验收"]}
        self._save(op, record)
        return op

    @staticmethod
    def _file_id(record, suffix):
        return next(x["id"] for x in record["source_files"] if x["path"].endswith("/" + suffix))

    def _validated_sha(self, op):
        code, result = invoke("validate", "--operation", op)
        self.assertEqual(code, 0, result)
        self.assertEqual(result["structural_errors"], [])
        self.assertEqual(result["semantic_completeness"], "not_decided_by_program")
        return result["plan_sha256"]

    def test_intake_publish_without_initialization(self):
        op = self.make_intake()
        original = (self.project / "input/requirements.md").read_bytes()
        plan_sha = self._validated_sha(op)
        code, result = invoke("apply", "--operation", op, "--expected-plan-sha", plan_sha)
        self.assertEqual((code, result["status"]), (0, "applied"))
        self.assertTrue((self.project / "brief-a/brief.md").is_file())
        self.assertTrue((self.project / "brief-b/brief.md").is_file())
        self.assertFalse((self.project / ".sdlc").exists())
        self.assertEqual((self.project / "input/requirements.md").read_bytes(), original)

    def test_feature_mapping_publish_and_successful_retry(self):
        op = self.make_feature(with_tasks=True)
        self.assertEqual(self._record(op)["source_notice"]["draft_path"], "draft/source-notice.md")
        source = self.project / ".sdlc/specs/002-demo"
        source_before = {p.relative_to(source).as_posix(): p.read_bytes() for p in source.rglob("*") if p.is_file()}
        selection_before = (self.project / ".sdlc/feature.json").read_bytes()
        plan_sha = self._validated_sha(op)
        code, result = invoke("apply", "--operation", op, "--expected-plan-sha", plan_sha)
        self.assertEqual((code, result["status"]), (0, "applied"), result)
        self.assertEqual({p.relative_to(source).as_posix(): p.read_bytes() for p in source.rglob("*")
                          if p.is_file() and p.name != "cut.md"}, source_before)
        self.assertEqual((self.project / ".sdlc/feature.json").read_bytes(), selection_before)
        child = self.project / ".sdlc/specs/003-a/spec.md"
        child.write_text(child.read_text() + "\n后续正常开发。\n")
        code, retry = invoke("apply", "--operation", op, "--expected-plan-sha", plan_sha)
        self.assertEqual((code, retry["status"]), (0, "already_applied"), retry)
        self.assertIn("后续正常开发", child.read_text())
        code, reuse = invoke("inspect", "--project", self.project, "--kind", "feature",
                             "--source", ".sdlc/specs/002-demo", "--workspace", ".sdlc/cuts/other-operation")
        self.assertEqual((code, reuse["status"]), (0, "already_applied"), reuse)
        self.assertFalse((self.project / ".sdlc/cuts/other-operation").exists())

    def test_shorter_fences_inside_code_examples_do_not_create_items(self):
        task_text = "\n".join([
            "````md", "```text", "- [ ] T999 示例任务", "```", "````",
            "- [ ] T001 真实任务", "",
        ])
        checklist_text = "\n".join([
            "~~~~md", "~~~text", "- [ ] 示例清单", "~~~", "~~~~",
            "- [ ] 真实清单", "",
        ])
        self.assertEqual(CUT.boxes(task_text, True),
                         [{"line": 6, "anchor": "T001", "checked": False}])
        self.assertEqual(CUT.boxes(checklist_text, False),
                         [{"line": 6, "anchor": None, "checked": False}])

    def test_checked_mapping_requires_matching_source_and_target_evidence(self):
        op = self.make_feature(with_tasks=True)
        record = self._record(op)
        self._replace_draft(op, record, "B", "tasks.md", "- [x] T001 汇总实现已承接。\n")
        record["task_mapping"][1]["destinations"][0]["checked"] = True
        tasks_id = self._file_id(record, "tasks.md")
        record["carryover"].append({
            "id": "C003", "source_ref": {"file": tasks_id, "anchor": "T002"}, "targets": ["A"],
            "claim": "汇总已实现", "evidence": ["合成证据"], "applicability": "仅 A", "remaining": "待核验"})
        record["task_mapping"][1]["carryover_ids"] = ["C003"]
        self._save(op, record)
        code, result = invoke("validate", "--operation", op)
        self.assertEqual(code, 3, result)
        self.assertIn("缺少适用的 carryover", result["errors"][0])

        record["carryover"][-1]["targets"] = ["B"]
        record["carryover"][-1]["source_ref"]["anchor"] = "T001"
        self._save(op, record)
        code, result = invoke("validate", "--operation", op)
        self.assertEqual(code, 3, result)
        self.assertIn("不对应来源条目", result["errors"][0])

        record["carryover"][-1]["source_ref"]["anchor"] = "T002"
        self._save(op, record)
        self._validated_sha(op)

    def test_explicitly_shared_carryover_can_support_two_successors(self):
        op = self.make_feature(with_tasks=True)
        record = self._record(op)
        self._replace_draft(op, record, "B", "checklists/review.md",
                            "- [ ] 整体发布仍待评审。\n- [x] 已核对明细条件。\n")
        record["items"][5]["targets"] = ["A", "B"]
        record["items"][5]["disposition"] = "shared"
        record["carryover"][1]["targets"] = ["A", "B"]
        record["checklist_mapping"][0]["destinations"].append({
            "target": "B", "path": "checklists/review.md", "lines": [2, 2], "checked": True})
        self._save(op, record)
        self._validated_sha(op)

    def test_unmapped_checked_successor_task_and_checklist_are_rejected(self):
        op = self.make_feature(with_tasks=True)
        record = self._record(op)
        self._replace_draft(op, record, "A", "tasks.md",
                            "- [x] T001 承接明细基础。\n- [x] T999 发布隔离已完成。\n")
        self._save(op, record)
        code, result = invoke("validate", "--operation", op)
        self.assertEqual(code, 3, result)
        self.assertIn("已勾选但未映射", result["errors"][0])
        code, result = invoke("apply", "--operation", op,
                              "--expected-plan-sha", CUT.plan_manifest(op)[0])
        self.assertEqual((code, result["status"]), (3, "not_applied"), result)
        self.assertFalse((self.project / ".sdlc/specs/003-a").exists())

        self._replace_draft(op, record, "A", "tasks.md", "- [x] T001 承接明细基础。\n")
        self._replace_draft(op, record, "A", "checklists/review.md",
                            "- [x] 已核对明细条件。\n- [x] 新增评审已通过。\n")
        self._save(op, record)
        code, result = invoke("validate", "--operation", op)
        self.assertEqual(code, 3, result)
        self.assertIn("已勾选但未映射", result["errors"][0])

    def test_inline_comment_and_story_heading_require_real_mapping(self):
        extra = "## User Story 3 - 示例 查询\n- [ ] T003 校验导出权限。 <!-- 后续补充说明 -->\n"
        op = self.make_feature(with_tasks=True, task_suffix=extra)
        record = self._record(op)
        code, result = invoke("validate", "--operation", op)
        self.assertEqual(code, 3, result)
        self.assertIn("未映射", result["errors"][0])

        self._replace_draft(op, record, "B", "tasks.md",
                            "- [ ] T001 实施汇总并验收整体。\n- [ ] T002 校验导出权限。\n")
        tasks_id = self._file_id(record, "tasks.md")
        record["items"].append({"id": "I008", "source_ref": {"file": tasks_id, "anchor": "T003"},
                                "kind": "task", "targets": ["B"], "disposition": "assigned",
                                "reason": "B 继续权限校验"})
        record["task_mapping"].append({
            "source_ref": {"file": tasks_id, "anchor": "T003"}, "source_checked": False,
            "destinations": [{"target": "B", "path": "tasks.md", "anchor": "T002", "checked": False}],
            "carryover_ids": [], "reason": "可见任务继续由 B 处理"})
        self._save(op, record)
        self._validated_sha(op)

    def test_multiline_comments_and_fences_preserve_only_visible_boxes(self):
        text = "\n".join([
            "- [ ] T001 可见 <!-- 行内说明 -->", "<!-- 多行注释", "- [x] T999 隐藏",
            "--> - [ ] T002 可见", "```md", "- [x] T998 代码示例", "```",
            "## Examples", "- [x] T997 文档示例", "## User Story 3 - 示例 查询",
            "- [ ] T003 真实任务 <!-- 说明", "延续说明 -->", "",
        ])
        self.assertEqual(CUT.boxes(text, True), [
            {"line": 1, "anchor": "T001", "checked": False},
            {"line": 4, "anchor": "T002", "checked": False},
            {"line": 11, "anchor": "T003", "checked": False},
        ])

    def test_numbered_checklist_anchors_and_line_fallback(self):
        numbered = "- [x] CHK001 已核对明细条件。\n- [ ] CHK002 整体发布仍待评审。\n"
        op = self.make_feature(with_tasks=True, checklist_text=numbered)
        record = self._record(op)
        self._replace_draft(op, record, "A", "checklists/review.md", "- [x] CHK001 已核对明细条件。\n")
        self._replace_draft(op, record, "B", "checklists/review.md", "- [ ] CHK002 整体发布仍待评审。\n")
        record["checklist_mapping"][0]["source_ref"] = {
            "file": self._file_id(record, "checklists/review.md"), "anchor": "CHK001"}
        record["checklist_mapping"][0]["destinations"][0].pop("lines")
        record["checklist_mapping"][0]["destinations"][0]["anchor"] = "CHK001"
        record["checklist_mapping"][1]["destinations"][0].pop("lines")
        record["checklist_mapping"][1]["destinations"][0]["anchor"] = "CHK002"
        record["carryover"][1]["source_ref"] = {
            "file": self._file_id(record, "checklists/review.md"), "anchor": "CHK001"}
        self._save(op, record)
        self._validated_sha(op)

        self._replace_draft(op, record, "A", "checklists/review.md",
                            "- [x] CHK001 已核对明细条件。\n- [ ] CHK001 重复编号。\n")
        self._save(op, record)
        code, result = invoke("validate", "--operation", op)
        self.assertEqual(code, 3, result)
        self.assertIn("ID 重复", result["errors"][0])

    def test_duplicate_source_checklist_id_is_rejected(self):
        op = self.make_feature(with_tasks=True,
                               checklist_text="- [x] CHK001 已核对。\n- [ ] CHK001 待评审。\n")
        code, result = invoke("validate", "--operation", op)
        self.assertEqual(code, 3, result)
        self.assertIn("ID 重复", result["errors"][0])

    def test_binary_attachment_whole_file_reference_only(self):
        op = self.make_feature(binary_attachment=b"\x89PNG\r\n\x1a\n\xff")
        record = self._record(op)
        fid = self._file_id(record, "diagram.png")
        record["items"].append({"id": "I999", "source_ref": {"file": fid}, "kind": "artifact",
                                "targets": ["A"], "disposition": "assigned", "reason": "A 承接原图"})
        self._save(op, record)
        self._validated_sha(op)
        for locator in ({"anchor": "FR-001"}, {"lines": [1, 1]}):
            with self.subTest(locator=locator):
                record["items"][-1]["source_ref"] = {"file": fid, **locator}
                self._save(op, record)
                code, result = invoke("validate", "--operation", op)
                self.assertEqual(code, 3, result)
                self.assertIn("不是 UTF-8 文本", result["errors"][0])

    def test_failed_initial_feature_preview_does_not_block_retries(self):
        for name in ("002-demo", "005-another"):
            write(self.project / ".sdlc/specs" / name / "spec.md", "# 合成来源\n")
        args = ("inspect", "--project", self.project, "--kind", "feature",
                "--source", ".sdlc/specs/002-demo", "--workspace", ".sdlc/cuts/cut-invalid")
        code, result = invoke(*args, "--observe-code", "missing.py")
        self.assertEqual(code, 2, result)
        self.assertFalse((self.project / ".sdlc/cuts/cut-invalid").exists())
        self.assertEqual([p.name for p in (self.project / ".sdlc/cuts").iterdir()], [".apply.lock"])
        code, result = invoke(*args)
        self.assertEqual((code, result["status"]), (0, "preview_created"), result)
        code, result = invoke("inspect", "--project", self.project, "--kind", "feature",
                              "--source", ".sdlc/specs/005-another", "--workspace", ".sdlc/cuts/cut-other")
        self.assertEqual((code, result["status"]), (0, "preview_created"), result)

    def test_failed_staged_preview_write_leaves_no_operation(self):
        write(self.project / ".sdlc/specs/002-demo/spec.md", "# 合成来源\n")
        op = self.project / ".sdlc/cuts/cut-failed-write"
        original = CUT.write_new

        def fail_template(path, data):
            if path.name == "cut.md":
                raise OSError("injected initial write failure")
            return original(path, data)

        with CUT.locked(self.project, "feature", op):
            with patch.object(CUT, "write_new", side_effect=fail_template):
                with self.assertRaises(OSError):
                    CUT.create_preview(self.project, "feature", op, [".sdlc/specs/002-demo"], [])
        self.assertFalse(op.exists())
        self.assertEqual(list((self.project / ".sdlc").glob(".cut-preview-*")), [])
        code, result = invoke("inspect", "--project", self.project, "--kind", "feature",
                              "--source", ".sdlc/specs/002-demo", "--workspace", ".sdlc/cuts/cut-retry")
        self.assertEqual((code, result["status"]), (0, "preview_created"), result)

    def test_drift_and_target_conflict(self):
        for change in ("source", "new-source", "draft", "target"):
            with self.subTest(change=change):
                with tempfile.TemporaryDirectory(prefix="cut-case-") as root:
                    old = self.project
                    self.project = (Path(root) / "project").resolve()
                    self.project.mkdir()
                    try:
                        op = self.make_feature()
                        plan_sha = self._validated_sha(op)
                        if change == "source":
                            (self.project / ".sdlc/specs/002-demo/spec.md").write_text("变动的规格\n")
                        elif change == "new-source":
                            write(self.project / ".sdlc/specs/002-demo/new.md", "新增附件\n")
                        elif change == "draft":
                            (op / "draft/A/spec.md").write_text("变动的草稿\n")
                        else:
                            write(self.project / ".sdlc/specs/003-a/user.md", "用户材料\n")
                        code, result = invoke("apply", "--operation", op, "--expected-plan-sha", plan_sha)
                        self.assertEqual(code, 3, result)
                        self.assertEqual(result["status"], "not_applied")
                        self.assertFalse((op / "receipt.json").exists())
                        if change == "target":
                            self.assertEqual((self.project / ".sdlc/specs/003-a/user.md").read_text(), "用户材料\n")
                    finally:
                        self.project = old

    def test_reconcile_written_files_before_receipt_update(self):
        op = self.make_feature()
        plan_sha = self._validated_sha(op)
        record = self._record(op)
        receipt = CUT.write_intents(record, self.project, op, plan_sha)
        CUT.save_receipt(op / "receipt.json", receipt)
        target = self.project / ".sdlc/specs/003-a"
        target.mkdir()
        for name in ("cut.md", "spec.md"):
            shutil.copyfile(op / "draft/A" / name, target / name)
        code, result = invoke("apply", "--operation", op, "--expected-plan-sha", plan_sha)
        self.assertEqual((code, result["status"]), (0, "applied"), result)
        self.assertTrue((self.project / ".sdlc/specs/004-b/spec.md").exists())
        self.assertTrue((self.project / ".sdlc/specs/002-demo/cut.md").exists())

    def test_second_successor_interruption_then_retry(self):
        op = self.make_feature()
        plan_sha = self._validated_sha(op)
        original_write = CUT.write_new

        def interrupt_second(path, data):
            if path == self.project / ".sdlc/specs/004-b/spec.md":
                raise OSError("injected interruption in second successor")
            return original_write(path, data)

        with patch.object(CUT, "write_new", side_effect=interrupt_second):
            failed, code = CUT.apply(SimpleNamespace(operation=str(op), expected_plan_sha=plan_sha))
        self.assertEqual((code, failed["status"]), (4, "incomplete"), failed)
        self.assertTrue((self.project / ".sdlc/specs/003-a/spec.md").exists())
        self.assertTrue((self.project / ".sdlc/specs/004-b/cut.md").exists())
        self.assertFalse((self.project / ".sdlc/specs/004-b/spec.md").exists())
        self.assertFalse((self.project / ".sdlc/specs/002-demo/cut.md").exists())
        code, resumed = invoke("apply", "--operation", op, "--expected-plan-sha", plan_sha)
        self.assertEqual((code, resumed["status"]), (0, "applied"), resumed)
        self.assertTrue((self.project / ".sdlc/specs/004-b/spec.md").exists())
        self.assertTrue((self.project / ".sdlc/specs/002-demo/cut.md").exists())

    def test_source_notice_gap_and_unowned_directory(self):
        op = self.make_feature()
        plan_sha = self._validated_sha(op)
        record = self._record(op)
        receipt = CUT.write_intents(record, self.project, op, plan_sha)
        CUT.save_receipt(op / "receipt.json", receipt)
        target = self.project / ".sdlc/specs/003-a"
        target.mkdir()
        code, result = invoke("apply", "--operation", op, "--expected-plan-sha", plan_sha)
        self.assertEqual(code, 4, result)
        self.assertEqual(result["status"], "incomplete")
        self.assertFalse((target / "cut.md").exists())

    def test_source_notice_written_before_receipt_update(self):
        op = self.make_feature()
        plan_sha = self._validated_sha(op)
        code, result = invoke("apply", "--operation", op, "--expected-plan-sha", plan_sha)
        self.assertEqual(code, 0, result)
        notice = self.project / ".sdlc/specs/002-demo/cut.md"
        original = notice.read_bytes()
        receipt = json.loads((op / "receipt.json").read_text())
        receipt["applied_at"] = None
        next(x for x in receipt["writes"] if x["role"] == "source-notice")["completed"] = False
        CUT.save_receipt(op / "receipt.json", receipt)
        code, result = invoke("apply", "--operation", op, "--expected-plan-sha", plan_sha)
        self.assertEqual((code, result["status"]), (0, "applied"), result)
        self.assertEqual(notice.read_bytes(), original)
        self.assertEqual(len(list(notice.parent.glob("cut*.md"))), 1)

    def test_truncated_file_and_changed_saved_plan_do_not_overwrite(self):
        op = self.make_feature()
        plan_sha = self._validated_sha(op)
        record = self._record(op)
        CUT.save_receipt(op / "receipt.json", CUT.write_intents(record, self.project, op, plan_sha))
        target = self.project / ".sdlc/specs/003-a"
        target.mkdir()
        shutil.copyfile(op / "draft/A/cut.md", target / "cut.md")
        write(target / "spec.md", "截断内容")
        code, result = invoke("apply", "--operation", op, "--expected-plan-sha", plan_sha)
        self.assertEqual(code, 4, result)
        self.assertEqual((target / "spec.md").read_text(), "截断内容")
        self.assertFalse((self.project / ".sdlc/specs/004-b").exists())
        (op / "cut.md").write_text("方案被外部改动\n")
        code, result = invoke("apply", "--operation", op, "--expected-plan-sha", plan_sha)
        self.assertNotEqual(code, 0, result)
        self.assertEqual((target / "spec.md").read_text(), "截断内容")

    def test_observed_code_reinspect_invalidates_review(self):
        source = self.project / ".sdlc/specs/002-demo"
        source.mkdir(parents=True)
        write(source / "spec.md", "# 范围\nFR-001 明细。\n")
        write(self.project / "app.py", "value = 1\n")
        args = ("inspect", "--project", self.project, "--kind", "feature",
                "--source", source, "--workspace", ".sdlc/cuts/cut-observe", "--observe-code", "app.py")
        code, output = invoke(*args)
        self.assertEqual(code, 0, output)
        op = Path(output["operation_directory"])
        record = self._record(op)
        record["decision"]["apply_authorized"] = True
        record["content_review"]["completed"] = True
        self._save(op, record)
        write(self.project / "app.py", "value = 2\n")
        code, output = invoke(*args)
        self.assertEqual((code, output["status"]), (0, "refreshed_preview"), output)
        record = self._record(op)
        self.assertFalse(record["decision"]["apply_authorized"])
        self.assertFalse(record["content_review"]["completed"])
        self.assertEqual(record["observed_code"]["files"][0]["sha256"], CUT.file_digest(self.project / "app.py"))

    def test_intake_stdin_and_illegal_parent_notice(self):
        run = subprocess.run([sys.executable, "-B", str(SCRIPT), "inspect", "--project", str(self.project),
                              "--kind", "intake", "--source", "-", "--workspace", "cut-work/stdin"],
                             input="原始输入\n", text=True, capture_output=True, check=False)
        self.assertEqual(run.returncode, 0, run.stdout)
        op = Path(json.loads(run.stdout)["operation_directory"])
        record = self._record(op)
        self.assertIsNone(record["source_files"][0]["path"])
        record["source_notice"] = {"path": "cut.md", "draft_path": "draft/source-notice.md", "sha256": "0" * 64}
        self._save(op, record)
        code, result = invoke("validate", "--operation", op)
        self.assertEqual(code, 2, result)
        self.assertIn("intake 不允许", result["errors"][0])

    def test_explicit_suffix_and_cross_kind_dependencies(self):
        op = self.make_feature()
        record = self._record(op)
        record["targets"][0]["directory"] = ".sdlc/specs/002-a"
        record["targets"][1]["directory"] = ".sdlc/specs/002-b"
        record["dependencies"].append({"from": "A", "requires": "B", "external": False,
                                       "kind": "implementation", "reason": "跨类型依赖测试"})
        self._save(op, record)
        plan_sha = self._validated_sha(op)
        code, result = invoke("apply", "--operation", op, "--expected-plan-sha", plan_sha)
        self.assertEqual((code, result["status"]), (0, "applied"), result)
        self.assertEqual([x["directory"] for x in result["targets"]], [".sdlc/specs/002-a", ".sdlc/specs/002-b"])

    def test_registered_items_do_not_prove_semantic_completeness(self):
        op = self.make_feature()
        record = self._record(op)
        record["items"] = [x for x in record["items"] if x["source_ref"].get("anchor") != "SC-001"]
        self._save(op, record)
        code, result = invoke("validate", "--operation", op)
        self.assertEqual(code, 0, result)
        self.assertEqual(result["semantic_completeness"], "not_decided_by_program")
        self.assertIn("SC-001", (self.project / ".sdlc/specs/002-demo/spec.md").read_text())

    def test_preview_reports_authorization_blockers(self):
        op = self.make_feature()
        record = self._record(op)
        record["decision"]["apply_authorized"] = False
        record["content_review"]["completed"] = False
        self._save(op, record)
        code, result = invoke("validate", "--operation", op)
        self.assertEqual(code, 0, result)
        self.assertTrue(result["plan_sha256"])
        self.assertEqual(len(result["application_blockers"]), 2)
        code, rejected = invoke("apply", "--operation", op, "--expected-plan-sha", result["plan_sha256"])
        self.assertEqual(code, 3, rejected)
        self.assertFalse((op / "receipt.json").exists())

    def test_unplanned_draft_and_invalid_receipt_identity(self):
        op = self.make_feature()
        write(op / "draft/A/extra.md", "未登记\n")
        code, result = invoke("validate", "--operation", op)
        self.assertEqual(code, 3, result)
        self.assertIn("草稿文件集合", result["errors"][0])
        (op / "draft/A/extra.md").unlink()
        plan_sha = self._validated_sha(op)
        code, result = invoke("apply", "--operation", op, "--expected-plan-sha", plan_sha)
        self.assertEqual(code, 0, result)
        receipt = json.loads((op / "receipt.json").read_text())
        receipt["source"]["directory"] = ".sdlc/specs/other"
        CUT.save_receipt(op / "receipt.json", receipt)
        code, retry = invoke("apply", "--operation", op, "--expected-plan-sha", plan_sha)
        self.assertEqual(code, 3, retry)
        code, revisit = invoke("inspect", "--project", self.project, "--kind", "feature",
                               "--source", ".sdlc/specs/002-demo", "--workspace", ".sdlc/cuts/new-one")
        self.assertEqual(code, 3, revisit)
        self.assertFalse((self.project / ".sdlc/cuts/new-one").exists())

    def test_original_status_still_lists_parent_and_keeps_selection(self):
        op = self.make_feature()
        plan_sha = self._validated_sha(op)
        code, result = invoke("apply", "--operation", op, "--expected-plan-sha", plan_sha)
        self.assertEqual(code, 0, result)
        selection = self.project / ".sdlc/feature.json"
        before = (selection.read_bytes(), selection.stat().st_mtime_ns)
        status_script = ROOT / "dist/scripts/python/project_status.py"
        proc = subprocess.run([sys.executable, "-I", "-B", str(status_script), "--project",
                               str(self.project), "--list", "--json"], text=True, capture_output=True)
        self.assertIn(proc.returncode, (0, 1), proc.stderr)
        report = json.loads(proc.stdout)
        names = {x["name"]: x["selected"] for x in report["features"]}
        self.assertEqual(names, {"002-demo": True, "003-a": False, "004-b": False})
        self.assertEqual((selection.read_bytes(), selection.stat().st_mtime_ns), before)

    def test_path_escape_and_symlink_are_rejected_without_external_write(self):
        op = self.make_intake()
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        record = self._record(op)
        record["targets"][0]["directory"] = "../outside/brief-a"
        self._save(op, record)
        code, result = invoke("validate", "--operation", op)
        self.assertNotEqual(code, 0, result)
        self.assertEqual(list(outside.iterdir()), [])
        record["targets"][0]["directory"] = "link/brief-a"
        self._save(op, record)
        (self.project / "link").symlink_to(outside, target_is_directory=True)
        code, result = invoke("validate", "--operation", op)
        self.assertNotEqual(code, 0, result)
        self.assertEqual(list(outside.iterdir()), [])

    def test_mapping_and_dependency_errors(self):
        op = self.make_feature(with_tasks=True)
        record = self._record(op)
        record["task_mapping"].pop()
        self._save(op, record)
        code, result = invoke("validate", "--operation", op)
        self.assertEqual(code, 3, result)
        self.assertIn("未映射", result["errors"][0])
        record["task_mapping"].append({"source_ref": {"file": self._file_id(record, "tasks.md"), "anchor": "T002"},
                                       "source_checked": False, "destinations": [{"target": "B", "path": "tasks.md",
                                       "anchor": "T001", "checked": False}], "carryover_ids": [], "reason": "恢复映射"})
        record["dependencies"].append({"from": "A", "requires": "B", "external": False,
                                       "kind": "release", "reason": "测试中的反向环"})
        self._save(op, record)
        code, result = invoke("validate", "--operation", op)
        self.assertEqual(code, 3, result)
        self.assertIn("依赖存在环", result["errors"][0])

    def test_related_git_layers_and_read_only_cut(self):
        self._git_base()
        index_path = Path(self._git("rev-parse", "--git-path", "index").decode().strip())
        if not index_path.is_absolute():
            index_path = self.project / index_path
        index_before = (index_path.read_bytes(), index_path.stat().st_mtime_ns)
        op = self.make_feature(observe_code=("app.py",))
        entry = self._code_entry(op)
        self.assertEqual(entry["vcs"]["state"], "tracked")
        self.assertEqual(entry["vcs"]["head_to_index"], [])
        self.assertEqual(entry["vcs"]["index_to_worktree"], [])
        self.assertEqual(entry["vcs"]["head_entries"][0].split()[2],
                         entry["vcs"]["index_entries"][0].split()[1])
        self.assertEqual(invoke("validate", "--operation", op)[0], 0)
        self.assertEqual((index_path.read_bytes(), index_path.stat().st_mtime_ns), index_before)
        for stage, work, expected in (
            ("staged = 1\n", "staged = 1\n", (["M"], [])),
            (None, "work = 1\n", ([], ["M"])),
            ("staged = 2\n", "work = 2\n", (["M"], ["M"])),
            ("staged = 3\n", "base = 1\n", (["M"], ["M"])),
        ):
            self._git("reset", "--hard", "-q", "HEAD")  # Fixture setup only.
            if stage is not None:
                write(self.project / "app.py", stage)
                self._git("add", "app.py")
            write(self.project / "app.py", work)
            observed = CUT.code_info(self.project, ["app.py"])["files"][0]
            self.assertEqual((observed["vcs"]["head_to_index"],
                              observed["vcs"]["index_to_worktree"]), expected)
            if stage == "staged = 3\n":
                self.assertEqual(observed["sha256"], entry["sha256"])
                self.assertNotEqual(observed["vcs"]["index_entries"], entry["vcs"]["index_entries"])
            code, report = invoke("validate", "--operation", op)
            self.assertTrue(report["source_changed"], report)
            self.assertNotEqual(code, 0)
        before = (self._git("rev-parse", "HEAD"), self._git("ls-files", "--stage", "-z"),
                  (self.project / "app.py").read_bytes())
        code, result = invoke("inspect", "--project", self.project, "--kind", "feature",
                              "--source", ".sdlc/specs/002-demo", "--workspace", ".sdlc/cuts/cut-demo")
        self.assertEqual((code, result["status"]), (0, "refreshed_preview"), result)
        self.assertEqual(invoke("validate", "--operation", op)[0], 0)
        self.assertEqual(before, (self._git("rev-parse", "HEAD"), self._git("ls-files", "--stage", "-z"),
                                  (self.project / "app.py").read_bytes()))

    def test_untracked_deleted_and_git_degradation(self):
        write(self.project / "app.py", "local = 1\n")
        no_git = CUT.code_info(self.project, ["app.py"])
        self.assertEqual(no_git["git"]["state"], "no_repository")
        self.assertEqual(no_git["files"][0]["vcs"]["state"], "unobserved")
        self.assertTrue(no_git["files"][0]["sha256"])
        self._git("init", "-q")
        unborn = CUT.code_info(self.project, ["app.py"])
        self.assertEqual(unborn["git"]["state"], "unborn")
        self.assertIsNone(unborn["git"]["head"])
        self.assertTrue(unborn["git"]["branch"])
        self._git("add", "app.py")
        self._git("commit", "-qm", "isolated baseline")
        write(self.project / "new binary.bin", "not committed\n")
        untracked = CUT.code_info(self.project, ["new binary.bin"])["files"][0]
        self.assertEqual(untracked["vcs"]["state"], "untracked")
        self.assertTrue(untracked["sha256"])
        (self.project / "app.py").unlink()
        deleted = CUT.code_info(self.project, ["app.py"])["files"][0]
        self.assertIsNone(deleted["sha256"])
        self.assertEqual(deleted["vcs"]["index_to_worktree"], ["D"])
        self.assertNotEqual(deleted["vcs"]["state"], "untracked")
        op = self.make_feature(observe_code=("app.py",))
        self.assertEqual(invoke("validate", "--operation", op)[0], 0)
        write(self.project / "app.py", "restored with new bytes\n")
        code, result = invoke("validate", "--operation", op)
        self.assertNotEqual(code, 0)
        self.assertTrue(result["source_changed"], result)

    def test_no_git_document_split_and_binary_observation(self):
        (self.project / "app.bin").write_bytes(b"\x00\xff\x10")
        op = self.make_feature(observe_code=("app.bin",))
        entry = self._code_entry(op)
        self.assertEqual(entry["vcs"]["state"], "unobserved")
        self.assertEqual(entry["sha256"], CUT.digest(b"\x00\xff\x10"))
        plan_sha = self._validated_sha(op)
        code, result = invoke("apply", "--operation", op, "--expected-plan-sha", plan_sha)
        self.assertEqual((code, result["status"]), (0, "applied"), result)
        self.assertEqual((self.project / "app.bin").read_bytes(), b"\x00\xff\x10")

    def test_git_query_failure_is_unknown_with_file_bytes(self):
        self._git_base()
        original = CUT.git_run
        def fail_index(project, *args):
            if args and args[0] == "ls-files":
                raise OSError("synthetic Git failure")
            return original(project, *args)
        with patch.object(CUT, "git_run", side_effect=fail_index):
            observed = CUT.code_info(self.project, ["app.py"])
        self.assertEqual(observed["git"]["state"], "head")
        self.assertEqual(observed["files"][0]["vcs"]["state"], "query_failed")
        self.assertEqual(observed["files"][0]["sha256"], CUT.file_digest(self.project / "app.py"))
        self.assertTrue(observed["limitations"])
        def fail_head(project, *args):
            if args == ("rev-parse", "--verify", "HEAD"):
                return subprocess.CompletedProcess([], 128, b"", b"synthetic HEAD error")
            return original(project, *args)
        with patch.object(CUT, "git_run", side_effect=fail_head):
            head_unknown = CUT.code_info(self.project, ["app.py"])
        self.assertEqual(head_unknown["git"]["state"], "query_failed")
        self.assertIsNone(head_unknown["git"]["head"])
        self.assertEqual(head_unknown["files"][0]["vcs"]["state"], "unobserved")

    def test_nested_project_and_inherited_git_dir_use_target_project(self):
        outer = Path(self.temp.name) / "outer"
        outer.mkdir()
        self.project = outer / "business"
        self.project.mkdir()
        proc = subprocess.run(["git", "-C", str(outer), "init", "-q"], capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        write(self.project / "code file.py", "answer = 1\n")
        self._git("add", "code file.py")
        self._git("commit", "-qm", "isolated nested baseline")
        with patch.dict(os.environ, {"GIT_DIR": str(ROOT / ".git")}):
            observed = CUT.code_info(self.project, ["code file.py"])
        self.assertEqual(observed["git"]["root"], str(outer.resolve()))
        self.assertEqual(observed["git"]["head"], self._git("rev-parse", "HEAD").decode().strip())
        self.assertEqual(observed["files"][0]["vcs"]["state"], "tracked")
        self.assertTrue(observed["files"][0]["vcs"]["head_entries"])
        self.assertTrue(observed["files"][0]["vcs"]["index_entries"])
        self.assertEqual(observed["files"][0]["vcs"]["head_to_index"], [])
        self.assertEqual(observed["files"][0]["vcs"]["index_to_worktree"], [])

    def test_selected_untracked_bytes_become_stale(self):
        self._git_base()
        write(self.project / "new.py", "first = 1\n")
        op = self.make_feature(observe_code=("new.py",))
        self.assertEqual(self._code_entry(op)["vcs"]["state"], "untracked")
        self.assertEqual(invoke("validate", "--operation", op)[0], 0)
        write(self.project / "new.py", "second = 2\n")
        code, result = invoke("validate", "--operation", op)
        self.assertNotEqual(code, 0)
        self.assertTrue(result["source_changed"], result)

    def test_index_change_with_unchanged_worktree_requires_new_review(self):
        self._git_base()
        op = self.make_feature(observe_code=("app.py",))
        original_sha = self._code_entry(op)["sha256"]
        old_plan_sha = CUT.plan_manifest(op)[0]
        write(self.project / "app.py", "stage = 1\n")
        self._git("add", "app.py")
        write(self.project / "app.py", "base = 1\n")
        self.assertEqual(CUT.file_digest(self.project / "app.py"), original_sha)
        code, report = invoke("validate", "--operation", op)
        self.assertNotEqual(code, 0)
        self.assertTrue(report["source_changed"], report)
        code, report = invoke("apply", "--operation", op, "--expected-plan-sha", old_plan_sha)
        self.assertNotEqual(code, 0)
        self.assertEqual(report["status"], "not_applied")
        self.assertFalse((self.project / ".sdlc/specs/003-a").exists())
        code, result = invoke("inspect", "--project", self.project, "--kind", "feature",
                              "--source", ".sdlc/specs/002-demo", "--workspace", ".sdlc/cuts/cut-demo")
        self.assertEqual((code, result["status"]), (0, "refreshed_preview"), result)
        refreshed = self._record(op)
        self.assertFalse(refreshed["decision"]["apply_authorized"])
        self.assertFalse(refreshed["content_review"]["completed"])
        self.assertNotEqual(old_plan_sha, CUT.plan_manifest(op)[0])
        self.assertEqual(refreshed["observed_code"]["files"][0]["vcs"]["head_to_index"], ["M"])

    def test_started_publication_retains_receipt_when_code_changes(self):
        self._git_base()
        op = self.make_feature(observe_code=("app.py",))
        plan_sha = self._validated_sha(op)
        record = self._record(op)
        receipt = CUT.write_intents(record, self.project, op, plan_sha)
        CUT.save_receipt(op / "receipt.json", receipt)
        CUT.publish_target(record, self.project, op, receipt, "A")
        first = self.project / ".sdlc/specs/003-a/spec.md"
        first_before = first.read_bytes()
        receipt_before = (op / "receipt.json").read_bytes()
        write(self.project / "app.py", "changed during publication\n")
        code, result = invoke("apply", "--operation", op, "--expected-plan-sha", plan_sha)
        self.assertEqual((code, result["status"]), (4, "incomplete"), result)
        self.assertIn("相关代码观察已改变", result["errors"][0])
        self.assertIn(".sdlc/specs/003-a/spec.md", result["written"])
        self.assertEqual(first.read_bytes(), first_before)
        self.assertEqual((op / "receipt.json").read_bytes(), receipt_before)
        self.assertFalse((self.project / ".sdlc/specs/004-b").exists())

    def test_unrelated_changes_and_successful_retry_do_not_republish(self):
        self._git_base()
        op = self.make_feature(observe_code=("app.py",))
        write(self.project / "other.txt", "unrelated changed\n")
        self.assertEqual(invoke("validate", "--operation", op)[0], 0)
        plan_sha = self._validated_sha(op)
        head_before = self._git("rev-parse", "HEAD")
        index_before = self._git("ls-files", "--stage", "-z")
        app_before = (self.project / "app.py").read_bytes()
        code, result = invoke("apply", "--operation", op, "--expected-plan-sha", plan_sha)
        self.assertEqual((code, result["status"]), (0, "applied"), result)
        self.assertEqual((head_before, index_before, app_before),
                         (self._git("rev-parse", "HEAD"), self._git("ls-files", "--stage", "-z"),
                          (self.project / "app.py").read_bytes()))
        child = self.project / ".sdlc/specs/003-a/spec.md"
        write(child, "# 后继继续开发\n")
        write(self.project / "app.py", "later = 1\n")
        code, result = invoke("apply", "--operation", op, "--expected-plan-sha", plan_sha)
        self.assertEqual((code, result["status"]), (0, "already_applied"), result)
        self.assertEqual(child.read_text(), "# 后继继续开发\n")
        self.assertEqual(self._git("rev-parse", "HEAD"), head_before)
        self.assertEqual(self._git("ls-files", "--stage", "-z"), index_before)

    def test_legacy_observation_requires_explicit_reinspection_without_rewriting(self):
        self._git_base()
        op = self.make_feature(observe_code=("app.py",))
        record = self._record(op)
        record["observed_code"]["files"][0].pop("vcs")
        record["observed_code"]["git"].pop("state")
        record["observed_code"]["git"].pop("root")
        self._save(op, record)
        before = (op / "cut.json").read_bytes()
        code, result = invoke("validate", "--operation", op)
        self.assertNotEqual(code, 0)
        self.assertTrue(result["source_changed"], result)
        self.assertIn("缺少暂存区", result["errors"][0])
        self.assertEqual((op / "cut.json").read_bytes(), before)
        code, result = invoke("inspect", "--project", self.project, "--kind", "feature",
                              "--source", ".sdlc/specs/002-demo", "--workspace", ".sdlc/cuts/cut-demo")
        self.assertEqual((code, result["status"]), (0, "refreshed_preview"), result)
        refreshed = self._record(op)
        self.assertFalse(refreshed["decision"]["apply_authorized"])
        self.assertFalse(refreshed["content_review"]["completed"])
        self.assertIn("vcs", refreshed["observed_code"]["files"][0])

    def test_legacy_interrupted_receipt_preserves_original_plan_and_written_scope(self):
        self._git_base()
        op = self.make_feature(observe_code=("app.py",))
        record = self._record(op)
        record["observed_code"]["files"][0].pop("vcs")
        record["observed_code"]["git"].pop("state")
        record["observed_code"]["git"].pop("root")
        self._save(op, record)
        plan_sha = CUT.plan_manifest(op)[0]
        receipt = CUT.write_intents(record, self.project, op, plan_sha)
        CUT.save_receipt(op / "receipt.json", receipt)
        CUT.publish_target(record, self.project, op, receipt, "A")
        before = ((op / "cut.json").read_bytes(), (op / "receipt.json").read_bytes())
        code, result = invoke("apply", "--operation", op, "--expected-plan-sha", plan_sha)
        self.assertEqual((code, result["status"]), (4, "incomplete"), result)
        self.assertIn("缺少暂存区", result["errors"][0])
        self.assertIn(".sdlc/specs/003-a/spec.md", result["written"])
        self.assertEqual(before, ((op / "cut.json").read_bytes(), (op / "receipt.json").read_bytes()))

    def test_legacy_successful_receipt_still_returns_already_applied(self):
        self._git_base()
        op = self.make_feature(observe_code=("app.py",))
        current_sha = self._validated_sha(op)
        self.assertEqual(invoke("apply", "--operation", op, "--expected-plan-sha", current_sha)[0], 0)
        record = self._record(op)
        record["observed_code"]["files"][0].pop("vcs")
        record["observed_code"]["git"].pop("state")
        record["observed_code"]["git"].pop("root")
        self._save(op, record)
        old_sha = CUT.plan_manifest(op)[0]
        receipt = CUT.write_intents(record, self.project, op, old_sha)
        for item in receipt["writes"]:
            item["completed"] = True
        receipt["applied_at"] = "2026-01-01T00:00:00Z"
        CUT.save_receipt(op / "receipt.json", receipt)
        child = self.project / ".sdlc/specs/003-a/spec.md"
        write(child, "# 后续工作\n")
        write(self.project / "app.py", "subsequent code\n")
        before = ((op / "cut.json").read_bytes(), (op / "receipt.json").read_bytes())
        code, result = invoke("apply", "--operation", op, "--expected-plan-sha", old_sha)
        self.assertEqual((code, result["status"]), (0, "already_applied"), result)
        self.assertEqual(child.read_text(), "# 后续工作\n")
        self.assertEqual(before, ((op / "cut.json").read_bytes(), (op / "receipt.json").read_bytes()))


if __name__ == "__main__":
    unittest.main()

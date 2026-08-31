from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
for candidate in (ROOT, ROOT / "packages"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from packages.sdlc_runtime.skill_args import (  # noqa: E402
    SkillArgumentError,
    parse_skill_arguments,
    render_help,
    skill_interface_from_mapping,
)

SPEC = skill_interface_from_mapping(
    {
        "contract": "sdlc-ai-spec/runtime/skill-interface/v1",
        "skill": "sdlc-000-ctx",
        "skill_version": "1.0.0",
        "default_command": "auto",
        "commands": [
            {"name": "auto", "description": "自动判断"},
            {"name": "create", "description": "创建"},
            {"name": "revise", "description": "修订"},
            {"name": "check", "description": "检查"},
            {"name": "help", "description": "帮助"},
            {"name": "version", "description": "版本"},
            {"name": "commands", "description": "命令"},
            {"name": "examples", "description": "示例"},
        ],
        "examples": ["/sdlc-000-ctx", "/sdlc-000-ctx create"],
    }
)


class SkillArgumentTests(unittest.TestCase):
    def test_default_is_auto(self):
        result = parse_skill_arguments("", SPEC)
        self.assertEqual(result.command, "auto")
        self.assertEqual(result.decision_policy, "user")
        self.assertEqual(result.write_policy, "auto")
        self.assertEqual(result.output, "summary")

    def test_all_supported_operation_forms(self):
        forms = (
            "--create",
            "create",
            "operation create",
            "op create",
            "operation=create",
            "--operation=create",
            "-o create",
            "-o=create",
        )
        for form in forms:
            with self.subTest(form=form):
                self.assertEqual(parse_skill_arguments(form, SPEC).command, "create")

    def test_common_options_and_free_text(self):
        result = parse_skill_arguments(
            "create -p /repo -r CTX-1@1 -d model -w confirm -n -f debug -- explain this",
            SPEC,
        )
        self.assertEqual(result.project_root, "/repo")
        self.assertEqual(result.artifact_reference, "CTX-1@1")
        self.assertEqual(result.decision_policy, "model")
        self.assertEqual(result.write_policy, "confirm")
        self.assertTrue(result.dry_run)
        self.assertEqual(result.output, "debug")
        self.assertEqual(result.request_text, "explain this")

    def test_help_and_topic(self):
        result = parse_skill_arguments("create --help", SPEC)
        self.assertEqual(result.command, "help")
        self.assertEqual(result.help_topic, "create")
        self.assertIn("Usage:", render_help(SPEC, result.help_topic))

    def test_same_duplicate_warns_and_conflict_fails(self):
        result = parse_skill_arguments("-p /repo --project-root=/repo", SPEC)
        self.assertEqual(result.warnings[0].code, "ARGUMENT_DUPLICATE")
        with self.assertRaises(SkillArgumentError) as captured:
            parse_skill_arguments("-p /one --project-root=/two", SPEC)
        self.assertEqual(captured.exception.code, "ARGUMENT_CONFLICT")

    def test_conflicting_operations_fail(self):
        with self.assertRaises(SkillArgumentError) as captured:
            parse_skill_arguments("create --check", SPEC)
        self.assertEqual(captured.exception.code, "ARGUMENT_CONFLICT")

    def test_unknown_and_quote_errors_fail(self):
        with self.assertRaises(SkillArgumentError) as captured:
            parse_skill_arguments("--creat", SPEC)
        self.assertEqual(captured.exception.code, "ARGUMENT_UNKNOWN")
        with self.assertRaises(SkillArgumentError) as captured:
            parse_skill_arguments("create 'unterminated", SPEC)
        self.assertEqual(captured.exception.code, "ARGUMENT_QUOTE_ERROR")

    def test_meta_command_is_side_effect_free_shape(self):
        result = parse_skill_arguments("--version", SPEC)
        self.assertEqual(result.command, "version")
        self.assertIsNone(result.project_root)
        self.assertFalse(result.dry_run)
        with self.assertRaises(SkillArgumentError):
            parse_skill_arguments("--version --dry-run", SPEC)

    def test_cli_emits_one_json_document(self):
        spec_path = ROOT / "skills/sdlc-000-ctx/references/interface.json"
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/sdlc_skill_interface.py"),
                "--spec",
                str(spec_path),
                "--",
                "--operation=create",
                "-p",
                "/repo",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertTrue(result["ok"])
        self.assertEqual(result["command"]["command"], "create")
        self.assertEqual(result["command"]["project_root"], "/repo")


if __name__ == "__main__":
    unittest.main()

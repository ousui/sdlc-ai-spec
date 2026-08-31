from __future__ import annotations

import unittest

from packages.sdlc_runtime.skill_args import skill_interface_from_mapping
from packages.sdlc_runtime.skill_command import parse_skill_command

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
        "examples": ["/sdlc-000-ctx"],
    }
)


class SkillCommandAliasTests(unittest.TestCase):
    def test_general_command_forms(self):
        forms = (
            "command create",
            "cmd create",
            "command=create",
            "--command=create",
            "-c create",
            "-c=create",
        )
        for form in forms:
            with self.subTest(form=form):
                self.assertEqual(parse_skill_command(form, SPEC).command, "create")

    def test_meta_command_through_general_command(self):
        self.assertEqual(parse_skill_command("--command help", SPEC).command, "help")

    def test_conflict_between_command_and_operation(self):
        with self.assertRaises(ValueError):
            parse_skill_command("--command create --operation check", SPEC)


if __name__ == "__main__":
    unittest.main()

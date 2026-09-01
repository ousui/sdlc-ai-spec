from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
for candidate in (ROOT, ROOT / "packages"):
    value = str(candidate)
    if value not in sys.path:
        sys.path.insert(0, value)

from packages.sdlc_runtime import SkillArgumentError, load_skill_interface
from packages.sdlc_runtime.skill_inputs import parse_skill_command_with_inputs


class DsnInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = load_skill_interface(
            ROOT / "skills/sdlc-200-dsn/references/interface.json"
        )

    def test_repeatable_input_forms_preserve_first_order(self):
        command = parse_skill_command_with_inputs(
            "create -i REQ-1@1 --input=REQ-2@1 input REQ-3@1",
            self.spec,
        )
        self.assertEqual(command.command.command, "create")
        self.assertEqual(
            command.input_references,
            ("REQ-1@1", "REQ-2@1", "REQ-3@1"),
        )

    def test_duplicate_input_is_deduplicated_with_warning(self):
        command = parse_skill_command_with_inputs(
            "create -i REQ-1@1 -i=REQ-1@1",
            self.spec,
        )
        self.assertEqual(command.input_references, ("REQ-1@1",))
        self.assertTrue(
            any(item.code == "INPUT_DUPLICATE" for item in command.command.warnings)
        )

    def test_meta_command_rejects_execution_input(self):
        with self.assertRaises(SkillArgumentError) as context:
            parse_skill_command_with_inputs(
                "--help -i REQ-1@1",
                self.spec,
            )
        self.assertEqual(context.exception.code, "ARGUMENT_CONFLICT")

    def test_input_requires_exact_token_value(self):
        with self.assertRaises(SkillArgumentError) as context:
            parse_skill_command_with_inputs("create --input", self.spec)
        self.assertEqual(context.exception.code, "ARGUMENT_VALUE_REQUIRED")

    def test_free_text_is_preserved_after_separator(self):
        command = parse_skill_command_with_inputs(
            "create -i REQ-1@1 -- prefer the simplest implementation",
            self.spec,
        )
        self.assertEqual(
            command.command.request_text,
            "prefer the simplest implementation",
        )


if __name__ == "__main__":
    unittest.main()

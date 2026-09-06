"""Durable inventory checks; manual Client feedback is not a machine certificate."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from tools.validate_skill_conformance import ROOT, SKILLS, file_path, validate


class SkillInventoryTests(unittest.TestCase):
    def test_all_eight_skills_bind_real_runtime_and_contract(self):
        result = validate()
        self.assertTrue(result["success"])
        self.assertEqual(list(SKILLS), [row["skill"] for row in result["skills"]])
        self.assertEqual("OUT_OF_SCOPE_MANUAL_FEEDBACK_NO_RECORDED_ATTESTATION", result["native_certification"])

    def test_missing_source_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError): file_path(Path(directory), "missing")

    def test_unsafe_relative_path_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for path in ("../secret", "/tmp/secret", "folder/../secret", "a\\b"):
                with self.subTest(path=path), self.assertRaises(ValueError): file_path(Path(directory), path)

    def test_linked_source_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "original").write_text("safe")
            (root / "link").symlink_to(root / "original")
            with self.assertRaises(ValueError): file_path(root, "link")

    def test_all_scoped_design_and_eval_plans_retained(self):
        index = json.loads((ROOT / "docs/plugin-development/SKILL-INVENTORY.json").read_text())
        self.assertEqual(8, len(index["skills"]))
        for row in index["skills"]:
            self.assertTrue(file_path(ROOT, row["design"]).stat().st_size)
            self.assertTrue(file_path(ROOT, row["eval_plan"]).stat().st_size)

    def test_no_native_ledger_required_for_runtime_validation(self):
        self.assertNotIn("required_native_missing", validate())
        self.assertFalse((ROOT / "docs/plugin-development/COMPATIBILITY.json").exists())

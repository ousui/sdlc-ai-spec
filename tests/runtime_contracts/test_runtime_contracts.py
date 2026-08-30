from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class RuntimeContractTests(unittest.TestCase):
    def test_validator_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools/validate_runtime_contracts.py")],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("runtime contract validation: PASS", result.stdout)

    def test_shared_schemas_parse(self) -> None:
        for relative in (
            "skills/_shared/schemas/invocation.schema.json",
            "skills/_shared/schemas/result.schema.json",
        ):
            with (ROOT / relative).open("r", encoding="utf-8") as handle:
                document = json.load(handle)
            self.assertEqual(document["$schema"], "https://json-schema.org/draft/2020-12/schema")

    def test_shared_directory_is_not_a_skill(self) -> None:
        self.assertFalse((ROOT / "skills/_shared/SKILL.md").exists())

    def test_legacy_work_item_removed(self) -> None:
        legacy_name = "sdlc-project-" "context"
        self.assertFalse(
            (ROOT / "docs/plugin-development/work-items" / legacy_name).exists()
        )


if __name__ == "__main__":
    unittest.main()

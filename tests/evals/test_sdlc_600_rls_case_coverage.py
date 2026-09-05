"""Fail-closed one-to-one coverage guard for RLS-E001..RLS-E087."""
from __future__ import annotations

import ast
import base64
import hashlib
import json
from pathlib import Path
import re
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[2]
MAP_PATH = Path(__file__).resolve().parent / "sdlc_600_rls_cases.json"
TEST_PATHS = tuple(sorted((ROOT / "tests/skill_rls").glob("test_critical_cases_*.py")))
EXPECTED_IDS = [f"RLS-E{index:03d}" for index in range(1, 88)]
REQUIRED_FIELDS = {
    "case_id", "title", "spec_clause", "design_clause", "polarity",
    "effect_class", "test_level", "module", "test_file", "primary_test",
    "depends_vfy_fixture", "depends_final_vfy", "requires_fake_target",
    "requires_real_project", "requires_effect_authorization",
    "blocks_artifact_gate", "fixture_authority", "expected",
}


def load_case_map() -> dict:
    envelope = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    if envelope.get("contract") != "sdlc-ai-spec/rls-final-case-map/v1":
        raise AssertionError("invalid RLS case-map contract")
    if envelope.get("provisional") is not False:
        raise AssertionError("final case map must use actual final VFY authority")
    if envelope.get("encoding") != "zlib+base64+utf8-json":
        raise AssertionError("unsupported deterministic case-map encoding")
    try:
        payload = zlib.decompress(base64.b64decode(envelope["payload_base64"], validate=True))
    except Exception as exc:
        raise AssertionError("case-map payload cannot be decoded") from exc
    if hashlib.sha256(payload).hexdigest() != envelope.get("payload_sha256"):
        raise AssertionError("case-map payload digest mismatch")
    decoded = json.loads(payload.decode("utf-8"))
    data = {
        "contract": envelope["contract"],
        "provisional": envelope["provisional"],
        "authority": envelope.get("authority"),
        "case_count": envelope.get("case_count"),
        "cases": decoded.get("cases"),
    }
    if not isinstance(data["cases"], list):
        raise AssertionError("decoded cases must be an array")
    return data


def test_functions() -> dict[str, tuple[Path, ast.FunctionDef]]:
    result: dict[str, tuple[Path, ast.FunctionDef]] = {}
    for path in TEST_PATHS:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                if node.name in result:
                    raise AssertionError(f"duplicate test function: {node.name}")
                result[node.name] = (path, node)
    return result


def decorator_names(node: ast.FunctionDef) -> set[str]:
    names: set[str] = set()
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(target, ast.Name):
            names.add(target.id)
        elif isinstance(target, ast.Attribute):
            names.add(target.attr)
    return names


ORACLE_FIELDS = ('case_id', 'title', 'spec_clause', 'design_clause', 'polarity', 'effect_class', 'expected')
ORIGINAL_ORACLE_SHA256 = '6c80b95b743d39aed2f512af4d4577aa08a1a2ecb9cbf36e69e2fbcc5052cccf'  # immutable 70e6f92 source semantics


def verify_original_oracles(cases):
    raw = json.dumps([{key: row[key] for key in ORACLE_FIELDS} for row in cases], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(raw).hexdigest() != ORIGINAL_ORACLE_SHA256:
        raise AssertionError("original 87 Case titles, clauses, polarity, effect and Expected changed")


class RlsCaseCoverageGuard(unittest.TestCase):
    def setUp(self):
        self.data = load_case_map()
        self.cases = self.data["cases"]
        self.functions = test_functions()

    def test_exact_ids_and_order(self):
        self.assertEqual([row["case_id"] for row in self.cases], EXPECTED_IDS)
        self.assertEqual(self.data.get("case_count"), 87)

    def test_original_oracles_are_unchanged(self):
        verify_original_oracles(self.cases)

    def test_required_metadata_is_complete(self):
        for row in self.cases:
            with self.subTest(case_id=row.get("case_id")):
                self.assertEqual(set(row), REQUIRED_FIELDS)
                for key in ("title", "spec_clause", "design_clause", "module", "test_file", "primary_test", "expected"):
                    self.assertIsInstance(row[key], str)
                    self.assertTrue(row[key].strip())
                self.assertIn(row["polarity"], {"positive", "negative"})
                self.assertIn(row["effect_class"], {"read-only", "mutation", "effect"})
                self.assertIn(row["test_level"], {"unit", "integration", "external"})
                self.assertEqual(row["fixture_authority"], "REAL_PERSISTED_ACCEPTED_VFY")

    def test_primary_tests_are_unique_and_exist(self):
        methods = [row["primary_test"] for row in self.cases]
        self.assertEqual(len(methods), len(set(methods)))
        for row in self.cases:
            with self.subTest(case_id=row["case_id"]):
                self.assertIn(row["primary_test"], self.functions)
                path, _node = self.functions[row["primary_test"]]
                self.assertEqual(row["test_file"], str(path.relative_to(ROOT)))
                numeric = row["case_id"].lower().replace("-", "_")
                self.assertTrue(row["primary_test"].startswith("test_" + numeric))

    def test_no_skipped_or_expected_failure_primary_tests(self):
        forbidden = {"skip", "skipIf", "skipUnless", "expectedFailure"}
        for row in self.cases:
            _path, node = self.functions[row["primary_test"]]
            with self.subTest(case_id=row["case_id"]):
                self.assertFalse(decorator_names(node) & forbidden)
                self.assertGreater(len(node.body), 0)
                self.assertFalse(len(node.body) == 1 and isinstance(node.body[0], ast.Pass))

    def test_no_case_id_is_claimed_by_multiple_test_names(self):
        source = "\n".join(path.read_text(encoding="utf-8") for path in TEST_PATHS)
        for case_id in EXPECTED_IDS:
            number = case_id[-3:]
            matches = re.findall(rf"def\s+(test_rls_e{number}_[a-z0-9_]+)\s*\(", source)
            with self.subTest(case_id=case_id):
                self.assertEqual(len(matches), 1)


if __name__ == "__main__":
    unittest.main()

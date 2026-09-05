import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tests.evals import run_sdlc_status_eval as evaluator


class StatusCoverageTests(unittest.TestCase):
    def test_registry_has_fourteen_unique_real_primaries(self):
        self.assertEqual(14, evaluator.build_suite(evaluator.load_cases()).countTestCases())

    def test_missing_duplicate_reordered_or_reused_mapping_fails(self):
        original = json.loads(evaluator.CASE_MAP.read_bytes())
        for mutation in ("missing", "duplicate", "reordered", "reused"):
            data = json.loads(json.dumps(original))
            if mutation == "missing": data["cases"].pop()
            if mutation == "duplicate": data["cases"][1] = data["cases"][0]
            if mutation == "reordered": data["cases"].reverse()
            if mutation == "reused": data["cases"][1]["primary_test"] = data["cases"][0]["primary_test"]
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/"map.json";path.write_text(json.dumps(data))
                with self.assertRaises(ValueError): evaluator.load_cases(path)

    def test_nonexistent_method_fails(self):
        rows=evaluator.load_cases();rows[0]["primary_test"]+="_missing"
        with self.assertRaises(ValueError): evaluator.build_suite(rows)

    def test_skip_and_expected_failure_do_not_become_pass(self):
        class Unavailable(unittest.TestCase):
            @unittest.skip("test of fail-closed guard")
            def test_skip(self): pass
            @unittest.expectedFailure
            def test_expected(self): self.fail("test of fail-closed guard")
        with patch.object(evaluator,"build_suite",return_value=unittest.defaultTestLoader.loadTestsFromTestCase(Unavailable)):
            result=evaluator.run()
        self.assertFalse(result["success"]);self.assertEqual(1,result["skipped"]);self.assertEqual(1,result["expected_failures"])

from copy import deepcopy
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from tests.evals.late_phase_eval import (
    ExecutedTestsResult, IMP_CASE_IDS, IMP_REQUIRED_FILES, preflight_imp,
    test_registry, unique_object, validate_critical_coverage, validate_execution,
)


class CaseCoverageTests(unittest.TestCase):
    def sample(self):
        def observed(self):
            self.assertEqual(2 + 2, 4)
        methods = {
            f'test_observed_{index:03d}': observed
            for index in range(len(IMP_CASE_IDS))
        }
        sample_type = type('Sample', (unittest.TestCase,), methods)
        tests = [sample_type(name) for name in methods]
        mapping = {'contract': 'sdlc-ai-spec/imp-critical-cases/v1',
                   'cases': [{'id': case, 'tests': [test.id()]}
                             for case, test in zip(IMP_CASE_IDS, tests)]}
        return tests, mapping

    def test_complete_manifest_accepts_real_collected_method(self):
        tests, mapping = self.sample()
        registry = {test.id(): test for test in tests}
        self.assertEqual(validate_critical_coverage(mapping, registry), set(registry))

    def test_one_unrelated_passing_method_cannot_cover_all_cases(self):
        tests, mapping = self.sample()
        target = tests[0].id()
        for case in mapping['cases']:
            case['tests'] = [target]
        with self.assertRaisesRegex(ValueError, 'primary test is already assigned'):
            validate_critical_coverage(mapping, {tests[0].id(): tests[0]})

    def test_missing_duplicate_extra_and_reordered_case_ids_fail(self):
        tests, mapping = self.sample()
        registry = {test.id(): test for test in tests}
        for kind in ('missing', 'duplicate', 'extra', 'order'):
            value = deepcopy(mapping)
            if kind == 'missing':
                value['cases'].pop()
            elif kind == 'duplicate':
                value['cases'].append(value['cases'][0])
            elif kind == 'extra':
                value['cases'].append({'id': 'IMP-E999', 'tests': [tests[0].id()]})
            else:
                value['cases'].reverse()
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                validate_critical_coverage(value, registry)

    def test_empty_or_nonexistent_test_target_fails_closed(self):
        tests, mapping = self.sample()
        registry = {test.id(): test for test in tests}
        for target in ([], ['tests.missing.Test.test_missing'], [tests[0].id(), tests[0].id()]):
            value = deepcopy(mapping)
            value['cases'][0]['tests'] = target
            with self.subTest(target=target), self.assertRaises(ValueError):
                validate_critical_coverage(value, registry)

    def test_skipped_methods_classes_and_expected_failures_cannot_cover_cases(self):
        for marker, on_class in (('__unittest_skip__', False), ('__unittest_skip__', True),
                                 ('__unittest_expecting_failure__', False)):
            tests, mapping = self.sample()
            test = tests[0]
            target = test.__class__ if on_class else getattr(test.__class__, test._testMethodName)
            setattr(target, marker, True)
            with self.subTest(marker=marker, on_class=on_class), self.assertRaisesRegex(ValueError, 'skipped or expected-failure'):
                validate_critical_coverage(mapping, {item.id(): item for item in tests})

    def test_duplicate_json_keys_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate JSON key'):
            json.loads('{"cases": [], "cases": []}', object_pairs_hook=unique_object)

    def test_duplicate_collected_tests_are_rejected(self):
        tests, _ = self.sample()
        test = tests[0]
        with self.assertRaisesRegex(ValueError, 'duplicate collected test'):
            test_registry(unittest.TestSuite([test, test]))

    def test_missing_gate_tool_directory_or_critical_file_never_skips(self):
        for missing in ('tools/validate_sdlc_400_imp_source_lock.py', 'tests/skill_imp',
                        'tests/skill_imp/test_lifecycle.py', 'packages/sdlc_resource/CONTRACT.md'):
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                for relative in IMP_REQUIRED_FILES:
                    path = root / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text('# gate existence fixture\n')
                preflight_imp(root)
                path = root / missing
                shutil.rmtree(path) if path.is_dir() else path.unlink()
                with self.assertRaisesRegex(FileNotFoundError, 'missing required IMP'):
                    preflight_imp(root)

    def test_unexecuted_mapping_cannot_be_reported_as_pass(self):
        tests, _ = self.sample()
        test = tests[0]
        result = unittest.TextTestRunner(stream=io.StringIO(), resultclass=ExecutedTestsResult).run(unittest.TestSuite())
        with self.assertRaisesRegex(ValueError, 'complete collected suite'):
            validate_execution(result, {test.id(): test}, {test.id()})

    def test_dynamic_skip_is_not_a_successful_execution(self):
        tests, _ = self.sample()
        test = tests[0]
        test.setUp = lambda: test.skipTest('dynamic skip fixture')
        result = unittest.TextTestRunner(stream=io.StringIO(), resultclass=ExecutedTestsResult).run(unittest.TestSuite([test]))
        with self.assertRaisesRegex(ValueError, 'skipped'):
            validate_execution(result, {test.id(): test}, {test.id()})

    def test_successful_execution_must_include_every_mapped_method(self):
        tests, mapping = self.sample()
        registry = {test.id(): test for test in tests}
        targets = validate_critical_coverage(mapping, registry)
        result = unittest.TextTestRunner(stream=io.StringIO(), resultclass=ExecutedTestsResult).run(unittest.TestSuite(tests))
        validate_execution(result, registry, targets)
        with self.assertRaisesRegex(ValueError, 'did not pass'):
            validate_execution(result, registry, targets | {'not.executed'})

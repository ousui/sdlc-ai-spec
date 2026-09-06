"""One collection, exact IDs, explicit registry bindings, and no inferred test PASS."""
from __future__ import annotations
import io
import json
from pathlib import Path
import time
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]


def collect(root: Path = ROOT) -> dict[str, unittest.TestCase]:
    from tests.evals.late_phase_eval import test_registry
    loader = unittest.TestLoader()
    suite = loader.discover(str(root/'tests'), pattern='test_*.py', top_level_dir=str(root))
    if loader.errors: raise ValueError('test collection failed: ' + '\n'.join(loader.errors))
    tests = test_registry(suite)
    if not tests: raise ValueError('empty test collection')
    return tests


def bindings(tests: dict) -> dict:
    from tests.evals.late_phase_eval import validate_critical_coverage, unique_object
    from tests.evals.test_sdlc_600_rls_case_coverage import load_case_map, verify_original_oracles
    from tests.evals.run_sdlc_status_eval import load_cases as status_cases
    from tests.evals.run_sdlc_500_vfy_eval import load_cases as vfy_cases
    imp = json.loads((ROOT/'tests/evals/sdlc_400_imp_cases.json').read_text(), object_pairs_hook=unique_object)
    validate_critical_coverage(imp, tests)
    rls = load_case_map()['cases']; verify_original_oracles(rls)
    rows = {'IMP':{row['id']:row['tests'] for row in imp['cases']},
            'RLS':{row['case_id']:['tests.skill_rls.test_critical_cases_final.RlsFinalCriticalCases.'+row['primary_test']] for row in rls},
            'STATUS':{row['id']:[row['primary_test']] for row in status_cases()},
            'VFY':{row['id']:['tests.skill_vfy.test_critical_cases.VfyCriticalCases.'+row['test']] for row in vfy_cases()}}
    for phase, cases in rows.items():
        primaries = [names[0] for names in cases.values()]
        if len(primaries) != len(set(primaries)): raise ValueError(phase + ': reused primary')
        for case, names in cases.items():
            for name in names:
                if name not in tests: raise ValueError(case + ': missing test ' + name)
                test = tests[name]; method = getattr(test, test._testMethodName)
                if any((getattr(test.__class__, '__unittest_skip__', False), getattr(method, '__unittest_skip__', False), getattr(method, '__unittest_expecting_failure__', False))):
                    raise ValueError(case + ': skipped/expected-failure mapping ' + name)
    return rows


class Result(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs); self.started_ids=[]; self.successful_ids=[]; self.timings=[]
    def startTest(self, test):
        self.started_ids.append(test.id()); self._started=time.monotonic(); super().startTest(test)
    def addSuccess(self, test):
        self.successful_ids.append(test.id()); super().addSuccess(test)
    def stopTest(self, test):
        self.timings.append({'id':test.id(),'seconds':round(time.monotonic()-self._started,6)}); super().stopTest(test)


def execute(tests: dict, *, strict: bool = False) -> dict:
    maps = bindings(tests); stream=io.StringIO(); observations={}
    from tests.skill_vfy import case_module
    from tests.evals.run_sdlc_500_vfy_eval import require_command_execution
    original = case_module.run_case
    def observed(case_id):
        result=original(case_id)
        if strict:
            require_command_execution(case_id, result)
            if result.get('status') != 'PASS': raise AssertionError(result)
            # Any extra harness calls are observations, not extra counted primary tests.
            observations[case_id]=result
        return result
    for names in maps['VFY'].values(): tests[names[0]].require_execution = strict
    with patch.object(case_module, 'run_case', side_effect=observed):
        result=unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Result).run(unittest.TestSuite(tests.values()))
    good=set(result.successful_ids)
    success=(result.wasSuccessful() and not result.skipped and not result.expectedFailures and not result.unexpectedSuccesses
             and len(result.started_ids)==len(tests) and set(result.started_ids)==set(tests) and good==set(tests))
    coverage={phase:{'total':len(rows), 'passed':sum(set(names)<=good for names in rows.values()),
                     'status':'PASS' if all(set(names)<=good for names in rows.values()) else 'FAIL'} for phase,rows in maps.items()}
    if not strict: coverage['VFY']['status']='PORTABLE_CONTRACT_TESTS_ONLY_NOT_STRICT_EVAL'
    elif set(observations)!=set(maps['VFY']): success=False; coverage['VFY']['status']='MISSING_EXECUTION_EVIDENCE'
    return {'success':success,'tests_run':result.testsRun,'unique_tests':len(set(result.started_ids)),
            'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
            'expected_failures':len(result.expectedFailures),'unexpected_successes':len(result.unexpectedSuccesses),
            'executed_ids':result.started_ids,'successful_ids':result.successful_ids,'coverage':coverage,
            'vfy_strict_observations':observations,'timings':result.timings,'log':stream.getvalue()}

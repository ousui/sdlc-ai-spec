"""Shared fixed-eval runner for late Phase Skills."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
CONFIG = {
    "PLN": {
        "suite": "skill_pln",
        "tools": (
            "tools/validate_sdlc_300_pln_source_lock.py",
            "tools/test_sdlc_300_pln_runtime_independence.py",
        ),
    },
    "IMP": {
        "suite": "skill_imp",
        "extra": ("late_foundations", "lifecycle", "skill_status"),
        "tools": (
            "tools/validate_sdlc_400_imp_source_lock.py",
            "tools/test_sdlc_400_imp_runtime_independence.py",
        ),
    },
    "VFY": {
        "suite": "skill_vfy",
        "tools": (
            "tools/validate_sdlc_500_vfy_source_lock.py",
            "tools/test_sdlc_500_vfy_runtime_independence.py",
        ),
    },
    "RLS": {
        "suite": "skill_rls",
        "extra": ("lifecycle",),
        "tools": (
            "tools/validate_sdlc_600_rls_source_lock.py",
            "tools/test_sdlc_600_rls_runtime_independence.py",
        ),
    },
}

IMP_CASE_IDS = tuple(f'IMP-F{index:03d}' for index in range(1, 21)) + tuple(
    f'IMP-E{index:03d}' for index in range(1, 63))
IMP_SUITE_DIRS = ('late_foundations', 'skill_imp', 'lifecycle', 'skill_status')
IMP_REQUIRED_FILES = (*CONFIG['IMP']['tools'],
    'tools/validate_late_phase_source_lock.py', 'tools/test_late_phase_runtime_independence.py',
    'tests/evals/sdlc_400_imp_cases.json', 'tests/evals/test_sdlc_400_imp_case_coverage.py',
    'tests/skill_imp/support.py',
    'skills/sdlc-400-imp/SKILL.md', 'skills/sdlc-400-imp/scripts/runtime.py',
    'skills/sdlc-400-imp/references/interface.json', 'skills/sdlc-400-imp/references/400-imp-spec.md',
    'skills/sdlc-400-imp/references/source-lock.json', 'skills/_shared/contracts/registry.json',
    'packages/sdlc_claim_provider/CONTRACT.md', 'packages/sdlc_resource/CONTRACT.md',
    *(f'tests/late_foundations/test_{name}.py' for name in (
        'claim_provider', 'claim_critical_cases', 'claim_read_only', 'execution_effects',
        'phasekit_cleanup', 'resource', 'resource_contract', 'imp_source_lock', 'runtime_independence_guard')),
    *(f'tests/skill_imp/test_{name}.py' for name in (
        'binding', 'cli', 'dependencies', 'method', 'resources', 'rework', 'state_machine',
        'lifecycle', 'critical_gaps', 'control_recovery', 'candidate_material')),
    'tests/lifecycle/test_query.py',
    *(f'tests/skill_status/test_{name}.py' for name in ('imp', 'runtime', 'summary')),
)


def preflight_imp(root=None):
    root = ROOT if root is None else root
    for directory in IMP_SUITE_DIRS:
        path = root / 'tests' / directory
        if not path.is_dir() or not list(path.glob('test_*.py')):
            raise FileNotFoundError(f'missing required IMP test directory or tests: {path}')
    for relative in IMP_REQUIRED_FILES:
        if not (root / relative).is_file():
            raise FileNotFoundError(f'missing required IMP gate file: {relative}')


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f'duplicate JSON key: {key}')
        value[key] = item
    return value


def test_registry(suite):
    result = {}
    for entry in suite:
        if isinstance(entry, unittest.TestSuite):
            entries = test_registry(entry)
        else:
            entries = {entry.id(): entry}
        for name, test in entries.items():
            if name in result:
                raise ValueError(f'duplicate collected test: {name}')
            result[name] = test
    return result


def validate_critical_coverage(value, collected):
    if not isinstance(value, dict) or set(value) != {'contract', 'cases'} or value['contract'] != 'sdlc-ai-spec/imp-critical-cases/v1':
        raise ValueError('invalid IMP Critical Case Coverage contract')
    cases = value['cases']
    if not isinstance(cases, list) or any(not isinstance(item, dict) or set(item) != {'id', 'tests'} for item in cases):
        raise ValueError('Critical Case entries require id and tests')
    ids = [item['id'] for item in cases]
    if any(not isinstance(item, str) for item in ids) or len(ids) != len(set(ids)):
        raise ValueError('duplicate or invalid Critical Case ID')
    if set(ids) != set(IMP_CASE_IDS):
        raise ValueError(f'Critical Case IDs differ: missing={sorted(set(IMP_CASE_IDS) - set(ids))}, extra={sorted(set(ids) - set(IMP_CASE_IDS))}')
    if tuple(ids) != IMP_CASE_IDS:
        raise ValueError('Critical Case IDs must use the fixed Foundation/IMP order')
    problems, targets, primaries, covered = [], set(), set(), 0
    for item in cases:
        names = item['tests']
        if not isinstance(names, list) or not names or any(not isinstance(name, str) for name in names):
            problems.append(f"{item['id']}: no executable test mapping")
            continue
        if len(names) != len(set(names)):
            problems.append(f"{item['id']}: duplicate test mapping")
            continue
        if names[0] in primaries:
            problems.append(
                f"{item['id']}: primary test is already assigned to another Critical Case: {names[0]}"
            )
            continue
        primaries.add(names[0])
        valid = True
        for name in names:
            test = collected.get(name)
            if test is None:
                problems.append(f"{item['id']}: test target does not exist: {name}")
                valid = False
                continue
            method = getattr(test, test._testMethodName)
            if (getattr(test.__class__, '__unittest_skip__', False) or getattr(method, '__unittest_skip__', False)
                    or getattr(method, '__unittest_expecting_failure__', False)):
                problems.append(f"{item['id']}: skipped or expected-failure test: {name}")
                valid = False
            targets.add(name)
        covered += valid
    if problems:
        raise ValueError(f'critical case IDs: {covered}/82; ' + '; '.join(problems))
    return targets


class ExecutedTestsResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.started_ids = []
        self.successful_ids = set()

    def startTest(self, test):
        self.started_ids.append(test.id())
        super().startTest(test)

    def addSuccess(self, test):
        self.successful_ids.add(test.id())
        super().addSuccess(test)


def validate_execution(result, collected, targets):
    if not result.wasSuccessful() or result.skipped or result.expectedFailures:
        raise ValueError('IMP Eval contains failed, skipped or expected-failure tests')
    if result.testsRun != len(collected) or set(result.started_ids) != set(collected):
        raise ValueError('IMP Eval did not execute the complete collected suite')
    if not targets.issubset(result.successful_ids):
        raise ValueError(f'Critical Case tests did not pass: {sorted(targets - result.successful_ids)}')


def run_tool(relative: str) -> bool:
    result = subprocess.run(
        [sys.executable, str(ROOT / relative)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode == 0


def suite_for(directory: str):
    # The existing focused IMP suite uses its local support.py, as does the
    # explicit unittest discover command. Keep that import visible in fixed Eval.
    if directory == 'skill_imp':
        sys.path.insert(0, str(ROOT / 'tests/skill_imp'))
    loader = unittest.TestLoader()
    path = ROOT / 'tests' / directory
    if not (path / '__init__.py').is_file():
        suite = unittest.TestSuite(loader.loadTestsFromName(
            'tests.' + directory + '.' + item.relative_to(path).with_suffix('').as_posix().replace('/', '.')
        ) for item in sorted(path.rglob('test_*.py')))
    else:
        suite = loader.discover(str(path), pattern='test_*.py', top_level_dir=str(ROOT))
    if loader.errors:
        raise ValueError('test collection failed: ' + '\n'.join(loader.errors))
    return suite


def imp_suite():
    suite = unittest.TestSuite(suite_for(directory) for directory in IMP_SUITE_DIRS)
    suite.addTests(unittest.defaultTestLoader.loadTestsFromName('tests.evals.test_sdlc_400_imp_case_coverage'))
    return suite


def run_phase(phase: str) -> int:
    config = CONFIG[phase]
    if phase == 'IMP':
        try:
            preflight_imp()
            suite = imp_suite()
            collected = test_registry(suite)
            value = json.loads((ROOT / 'tests/evals/sdlc_400_imp_cases.json').read_text(encoding='utf-8'), object_pairs_hook=unique_object)
            targets = validate_critical_coverage(value, collected)
        except (OSError, ValueError) as exc:
            print(f'sdlc-imp eval: FAIL: {exc}', file=sys.stderr)
            return 1
    if not all(run_tool(item) for item in config["tools"]):
        print(f"sdlc-{phase.lower()} eval: FAIL: deterministic gate", file=sys.stderr)
        return 1
    if phase != 'IMP':
        suite = unittest.TestSuite()
        suite.addTests(suite_for(config["suite"]))
        for extra in config.get("extra", ()):
            suite.addTests(suite_for(extra))
    result = unittest.TextTestRunner(verbosity=2, resultclass=ExecutedTestsResult).run(suite)
    if phase == 'IMP':
        try:
            validate_execution(result, collected, targets)
        except ValueError as exc:
            print(f'sdlc-imp eval: FAIL: {exc}', file=sys.stderr)
            return 1
        print('source lock: PASS')
        print('runtime independence: PASS')
        print('critical case IDs: 82/82')
        print(f'executed tests: {result.testsRun}')
        print('sdlc-imp eval: PASS')
        return 0
    if not result.wasSuccessful():
        print(f"sdlc-{phase.lower()} eval: FAIL", file=sys.stderr)
        return 1
    print(f"sdlc-{phase.lower()} eval: PASS")
    print("critical cases:", result.testsRun)
    print("runtime independence: PASS")
    return 0

from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from packages.sdlc_runtime import build_source_lock
from tools import validate_late_phase_source_lock as validator


class ImpSourceLockTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        source_root = validator.ROOT
        sources = validator.sources('IMP')
        paths = {item.resource for item in sources} | {'skills/_shared/contracts/registry.json'}
        for phase in ('PLN', 'IMP'):
            skill, filename, _ = validator.PHASES[phase]
            paths.update((f'skills/{skill}/references/source-lock.json', f'skills/{skill}/references/{filename}'))
        for relative in paths:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_root / relative, target)
        self.root_patch = patch.object(validator, 'ROOT', self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.lock_path = self.root / 'skills/sdlc-400-imp/references/source-lock.json'
        self.lock = json.loads(self.lock_path.read_text())

    def validate(self, phase='IMP'):
        with redirect_stdout(io.StringIO()):
            validator.validate(phase)

    def test_deterministic_constructor_and_read_only_validation(self):
        before = {p.relative_to(self.root): (p.read_bytes(), p.stat().st_mtime_ns)
                  for p in self.root.rglob('*') if p.is_file()}
        first = build_source_lock(self.root, validator.sources('IMP'))
        self.assertEqual(first, build_source_lock(self.root, validator.sources('IMP')))
        self.assertEqual(self.lock_path.read_text(), json.dumps(first, ensure_ascii=False, indent=2) + '\n')
        self.validate()
        self.validate()
        self.assertEqual(before, {p.relative_to(self.root): (p.read_bytes(), p.stat().st_mtime_ns)
                                  for p in self.root.rglob('*') if p.is_file()})

    def test_imp_foundations_are_documented_and_do_not_change_pln(self):
        pln = self.root / 'skills/sdlc-300-pln/references/source-lock.json'
        before = pln.read_bytes()
        self.validate('PLN')
        self.validate('IMP')
        self.assertEqual(len(validator.sources('PLN')), 13)
        self.assertEqual(len(validator.sources('IMP')), 16)
        for source in validator.PHASE_EXTRA_SOURCES['IMP']:
            self.assertIn(f'Contract ID: `{source.contract_id}`', (self.root / source.resource).read_text())
            self.assertNotIn(source.contract_id, {item.contract_id for item in validator.sources('PLN')})
        self.assertEqual(pln.read_bytes(), before)

    def test_missing_or_drifted_bundled_spec_fails_closed(self):
        bundled = self.root / 'skills/sdlc-400-imp/references/400-imp-spec.md'
        original = bundled.read_bytes()
        bundled.unlink()
        with self.assertRaises(OSError):
            self.validate()
        bundled.write_bytes(original + b'\nUnexpected drift\n')
        with self.assertRaisesRegex(ValueError, 'bundled contract drift'):
            self.validate()

    def test_every_missing_source_fails_closed(self):
        for source in validator.sources('IMP'):
            with self.subTest(contract=source.contract_id):
                path = self.root / source.resource
                raw = path.read_bytes()
                path.unlink()
                with self.assertRaises(ValueError):
                    self.validate()
                path.write_bytes(raw)

    def test_extra_missing_duplicate_unsorted_and_sha_drift_fail_closed(self):
        mutations = []
        missing = deepcopy(self.lock)
        missing['contracts'].pop()
        mutations.append(missing)
        extra = deepcopy(self.lock)
        extra['contracts'].append({**extra['contracts'][-1], 'contract_id': 'z-unexpected-contract'})
        mutations.append(extra)
        duplicate = deepcopy(self.lock)
        duplicate['contracts'].insert(1, duplicate['contracts'][0])
        mutations.append(duplicate)
        unsorted = deepcopy(self.lock)
        unsorted['contracts'].reverse()
        mutations.append(unsorted)
        drift = deepcopy(self.lock)
        drift['contracts'][0]['sha256'] = '0' * 64
        mutations.append(drift)
        for index, value in enumerate(mutations):
            with self.subTest(mutation=index):
                self.lock_path.write_text(json.dumps(value))
                with self.assertRaises(ValueError):
                    self.validate()

    def test_changed_foundation_bytes_fail_without_regenerating_lock(self):
        path = self.root / 'packages/sdlc_resource/CONTRACT.md'
        path.write_bytes(path.read_bytes() + b'\nContract drift\n')
        before = self.lock_path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'differs from current sources'):
            self.validate()
        self.assertEqual(self.lock_path.read_bytes(), before)

    def test_registry_order_and_duplicate_contract_ids_fail_closed(self):
        path = self.root / 'skills/_shared/contracts/registry.json'
        original = json.loads(path.read_text())
        for mode in ('order', 'duplicate', 'phase-duplicate'):
            value = deepcopy(original)
            if mode == 'order':
                value['contracts'].reverse()
            elif mode == 'duplicate':
                value['contracts'].insert(1, value['contracts'][0])
            else:
                source = validator.PHASE_EXTRA_SOURCES['IMP'][0]
                value['contracts'].append(vars(source))
                value['contracts'].sort(key=lambda item: item['contract_id'])
            with self.subTest(mode=mode):
                path.write_text(json.dumps(value))
                with self.assertRaises(ValueError):
                    self.validate()

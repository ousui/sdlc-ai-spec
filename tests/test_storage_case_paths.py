"""Filesystem case aliases cannot change document ownership or selection semantics."""
from __future__ import annotations

import base64
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

try:
    from tests import test_storage as storage
except ImportError:
    import test_storage as storage


class CasePathTests(unittest.TestCase):
    def setUp(self):
        self.f = storage.StorageTests('runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        probe = self.f.base / 'CaseProbe'
        probe.write_text('probe')
        insensitive = (self.f.base / 'caseprobe').exists()
        probe.unlink()
        if not insensitive:
            self.skipTest('Requires a case-insensitive filesystem')

    def local_copies(self):
        self.f.init(self.f.a, '--mode', 'local')
        self.f.init(self.f.b, '--mode', 'local')

    def control_alias(self, target):
        control = self.f.b / '.sdlc/transactions/pending/proposal.json'
        control.parent.mkdir(parents=True, exist_ok=True)
        control.symlink_to(target.with_name(target.name.upper()))
        return control

    def interrupted(self, plan, target, name):
        path = Path(plan['transaction']) / 'manifest.json'
        manifest = json.loads(path.read_text())
        manifest['published'] = {name: storage.changes.publish_data(
            target, b'partial', target.read_bytes() if target.exists() else None)}
        manifest.update(status='applying', after={name: base64.b64encode(b'partial').decode()})
        path.write_text(json.dumps(manifest))

    def test_case_alias_of_authority_root_is_rejected_by_resolver_status_and_init(self):
        (self.f.a / '.sdlc').symlink_to(self.f.main / '.SDLC', target_is_directory=True)
        before = storage.files(self.f.main)
        self.f.runpy('sdlc_store.py', 'resolve', project=self.f.a, ok=False)
        self.f.runpy('init_project.py', '--mode', 'local', project=self.f.a, ok=False)
        status = json.loads(self.f.runpy('project_status.py', project=self.f.a, ok=False).stdout)
        self.assertEqual(status['status'], 'error')
        self.assertTrue(status['warnings'])
        self.assertEqual(storage.files(self.f.main), before)

    def test_main_and_shared_control_writes_ignore_another_alias_of_the_same_store_root(self):
        (self.f.a / '.sdlc').symlink_to(self.f.main / '.SDLC', target_is_directory=True)
        self.f.feature(self.f.main)
        for project in (self.f.main, self.f.b):
            with self.subTest(project=project.name):
                self.f.runpy('sdlc_store.py', 'feature', '--value', '.sdlc/specs/001-one', '--persist', project=project)
                selection = Path(self.f.binding(project)['FEATURE_JSON'])
                before = selection.read_bytes(), selection.stat().st_mtime_ns
                self.f.runpy('sdlc_store.py', 'feature', '--value', '.sdlc/specs/001-one', '--persist', project=project)
                self.assertEqual((selection.read_bytes(), selection.stat().st_mtime_ns), before)

    def check_control_phases(self, missing):
        self.local_copies()
        name = 'specs/001-one/notes.md' if missing else 'memory/long-term.md'
        if missing:
            self.f.feature(self.f.main)
            self.f.feature(self.f.a)
        for kind in ('edit', 'import', 'collect'):
            for phase in ('prepare', 'apply', 'recover'):
                with self.subTest(kind=kind, phase=phase, missing=missing):
                    project = self.f.main if kind == 'collect' else self.f.a
                    target = project / '.sdlc' / name
                    target.unlink(missing_ok=True)
                    if not missing:
                        target.write_text('original')
                    if kind != 'edit':
                        source = (self.f.a if kind == 'collect' else self.f.main) / '.sdlc'
                        (source / name).write_text('source version')
                    control = None
                    args = ['prepare', '--kind', kind]
                    if kind == 'collect':
                        args += ['--source', str(source)]
                    if kind == 'edit':
                        args += ['--path', name]
                    elif missing:
                        args += ['--feature', '001-one']
                    try:
                        if phase == 'prepare':
                            control = self.control_alias(target)
                            self.f.runpy('store_changes.py', *args, project=project, ok=False)
                        else:
                            plan = self.f.runpy('store_changes.py', *args, project=project)
                            self.f.replace(plan, name, 'candidate')
                            if phase == 'recover':
                                self.interrupted(plan, target, name)
                            control = self.control_alias(target)
                            before = (target.read_bytes(), target.stat().st_mtime_ns) if target.exists() else None
                            action = 'recover' if phase == 'recover' else 'apply'
                            self.f.runpy('store_changes.py', action, '--transaction', plan['transaction'],
                                         project=project, ok=False)
                            after = (target.read_bytes(), target.stat().st_mtime_ns) if target.exists() else None
                            self.assertEqual(after, before)
                            manifest = json.loads((Path(plan['transaction']) / 'manifest.json').read_text())
                            self.assertEqual(manifest['status'], 'applying' if phase == 'recover' else 'prepared')
                        if phase == 'prepare':
                            self.assertEqual(target.read_text() if target.exists() else None,
                                             None if missing else 'original')
                    finally:
                        if control is not None:
                            control.unlink(missing_ok=True)

    def test_private_control_case_aliases_block_edit_import_collect_in_every_phase(self):
        self.check_control_phases(False)

    def test_dangling_case_aliases_block_new_edit_import_collect_targets_in_every_phase(self):
        self.check_control_phases(True)

    def test_authority_external_case_alias_is_checked_during_prepare_apply_and_recover(self):
        self.local_copies()
        feature = self.f.feature(self.f.a)
        for phase in ('prepare', 'apply', 'recover'):
            with self.subTest(phase=phase):
                target = feature / 'plan.md'
                target.write_text('original')
                alias = self.f.main / '.sdlc/specs/900-main/contracts/external.txt'
                alias.parent.mkdir(parents=True, exist_ok=True)
                try:
                    if phase == 'prepare':
                        alias.symlink_to(target.with_name('PLAN.MD'))
                        self.f.runpy('store_changes.py', 'prepare', '--kind', 'edit', '--path',
                                     'specs/001-one/plan.md', project=self.f.a, ok=False)
                    else:
                        plan = self.f.prepare(self.f.a, kind='edit', paths=['specs/001-one/plan.md'])
                        self.f.replace(plan, 'specs/001-one/plan.md', 'candidate')
                        if phase == 'recover':
                            self.interrupted(plan, target, 'specs/001-one/plan.md')
                        alias.symlink_to(target.with_name('PLAN.MD'))
                        before = target.read_bytes(), target.stat().st_mtime_ns
                        self.f.runpy('store_changes.py', phase, '--transaction', plan['transaction'],
                                     project=self.f.a, ok=False)
                        self.assertEqual((target.read_bytes(), target.stat().st_mtime_ns), before)
                finally:
                    alias.unlink(missing_ok=True)

    def test_dangling_authority_case_alias_protects_missing_descendants(self):
        self.local_copies()
        feature = self.f.feature(self.f.a)
        alias = self.f.main / '.sdlc/specs/900-main/contracts'
        alias.parent.mkdir(parents=True)
        alias.symlink_to(feature / 'MISSING', target_is_directory=True)
        self.f.runpy('store_changes.py', 'prepare', '--kind', 'edit', '--path',
                     'specs/001-one/missing/api.json', project=self.f.a, ok=False)
        self.assertFalse((feature / 'missing').exists())

    def test_import_recovery_checks_authority_alias_with_different_target_case(self):
        self.local_copies()
        main_feature = self.f.feature(self.f.main)
        local_feature = self.f.feature(self.f.a)
        target = local_feature / 'plan.md'
        target.write_text('original')
        (main_feature / 'plan.md').write_text('authority version')
        plan = self.f.prepare(self.f.a, kind='import', features=['001-one'])
        self.interrupted(plan, target, 'specs/001-one/plan.md')
        alias = main_feature / 'plan.md'
        alias.unlink()
        alias.symlink_to(target.with_name('PLAN.MD'))
        before = target.read_bytes(), target.stat().st_mtime_ns
        self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'], project=self.f.a, ok=False)
        self.assertEqual((target.read_bytes(), target.stat().st_mtime_ns), before)

    def test_case_aliases_cannot_create_duplicate_existing_or_missing_edit_targets(self):
        self.local_copies()
        feature = self.f.feature(self.f.a)
        target = feature / 'plan.md'
        (feature / 'notes.md').symlink_to(feature / 'PLAN.MD')
        for existing in (False, True):
            with self.subTest(existing=existing):
                if existing:
                    target.write_text('original')
                self.f.runpy('store_changes.py', 'prepare', '--kind', 'edit',
                             '--path', 'specs/001-one/plan.md', '--path', 'specs/001-one/notes.md',
                             project=self.f.a, ok=False)
                self.assertEqual(target.read_text() if target.exists() else None, 'original' if existing else None)

    def test_legal_external_case_alias_keeps_link_through_apply_and_recovery(self):
        self.local_copies()
        feature = self.f.feature(self.f.a)
        external = self.f.base / 'ExternalPlan.md'
        external.write_text('original')
        alias = feature / 'plan.md'
        alias.symlink_to(self.f.base / 'externalplan.md')
        inode = alias.lstat().st_ino
        plan = self.f.prepare(self.f.a, kind='edit', paths=['specs/001-one/plan.md'])
        self.f.replace(plan, 'specs/001-one/plan.md', 'candidate')
        self.f.apply(plan, self.f.a)
        self.assertEqual(external.read_text(), 'candidate')
        plan = self.f.prepare(self.f.a, kind='edit', paths=['specs/001-one/plan.md'])
        self.interrupted(plan, external, 'specs/001-one/plan.md')
        self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'], project=self.f.a)
        self.assertEqual(external.read_text(), 'candidate')
        self.assertTrue(alias.is_symlink())
        self.assertEqual(alias.lstat().st_ino, inode)

    def test_legal_internal_case_alias_keeps_its_artifact_namespace(self):
        self.local_copies()
        feature = self.f.feature(self.f.a)
        target = feature / 'notes.md'
        target.write_text('original')
        alias = feature / 'plan.md'
        alias.symlink_to(self.f.a / '.SDLC/SPECS/001-one/NOTES.MD')
        plan = self.f.prepare(self.f.a, kind='edit', paths=['specs/001-one/plan.md'])
        self.f.replace(plan, 'specs/001-one/plan.md', 'candidate')
        self.f.apply(plan, self.f.a)
        self.assertEqual(target.read_text(), 'candidate')
        self.assertTrue(alias.is_symlink())
        self.assertEqual(alias.readlink(), self.f.a / '.SDLC/SPECS/001-one/NOTES.MD')

    def test_explicit_case_spelling_priority_no_persist_and_noop_selection_are_preserved(self):
        self.local_copies()
        feature = self.f.feature(self.f.a)
        (feature / 'plan.md').write_text('existing plan')
        selection = self.f.a / '.sdlc/feature.json'
        selection.write_text('{invalid saved selection\n')
        value = '.sdlc/SPECS/001-one/.'
        env = dict(self.f.env, SDLC_FEATURE_DIRECTORY=value)
        script = storage.PACKAGE / 'scripts/bash/setup-plan.sh'
        def run(**extra):
            process = subprocess.run(['bash', str(script), '--json'], cwd=self.f.a,
                                     env=dict(env, **extra), text=True, capture_output=True, timeout=30)
            self.assertEqual(process.returncode, 0, process.stderr)
            return json.loads(process.stdout)
        before = selection.read_bytes(), selection.stat().st_mtime_ns
        self.assertEqual(run(SDLC_FEATURE_NO_PERSIST='1')['BRANCH'], '.')
        self.assertEqual((selection.read_bytes(), selection.stat().st_mtime_ns), before)
        run()
        self.assertEqual(json.loads(selection.read_text())['feature_directory'], value)
        control = self.f.b / '.sdlc/feature.json'
        control.symlink_to(self.f.a / '.sdlc/FEATURE.JSON')
        before = selection.read_bytes(), selection.stat().st_mtime_ns
        run()
        self.assertEqual((selection.read_bytes(), selection.stat().st_mtime_ns), before)
        self.f.feature(self.f.a, '002-two')
        self.f.runpy('sdlc_store.py', 'feature', '--value', '.sdlc/specs/002-two', '--persist',
                     project=self.f.a, ok=False)
        self.assertEqual((selection.read_bytes(), selection.stat().st_mtime_ns), before)

    def test_shared_absolute_case_alias_maps_to_authority_and_preserves_selection_spelling(self):
        for designated in (False, True):
            with self.subTest(designated=designated):
                if designated:
                    authority = self.f.base / 'designated authority'
                    (self.f.main / '.sdlc').rename(authority)
                    self.f.runpy('sdlc_store.py', 'register', '--authority', str(authority))
                feature = self.f.feature(self.f.main)
                selection = Path(self.f.binding(self.f.a)['FEATURE_JSON'])
                value = str(self.f.a.with_name(self.f.a.name.upper())) + '/.sdlc/specs/001-one/.'
                script = storage.PACKAGE / 'scripts/bash/setup-plan.sh'
                process = subprocess.run(['bash', str(script), '--json'], cwd=self.f.a,
                                         env=dict(self.f.env, SDLC_FEATURE_DIRECTORY=value, SDLC_FEATURE_NO_PERSIST='1'),
                                         text=True, capture_output=True, timeout=30)
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertEqual(Path(json.loads(process.stdout)['FEATURE_DIR']).resolve(), feature)
                self.assertFalse((self.f.a / '.sdlc').exists())
                if not designated:
                    self.assertFalse(selection.exists())
                for _ in range(2):
                    process = subprocess.run(['bash', str(script), '--json'], cwd=self.f.a,
                                             env=dict(self.f.env, SDLC_FEATURE_DIRECTORY=value),
                                             text=True, capture_output=True, timeout=30)
                    self.assertEqual(process.returncode, 0, process.stderr)
                    result = json.loads(process.stdout)
                    self.assertEqual(Path(result['FEATURE_DIR']).resolve(), feature)
                    self.assertEqual(result['BRANCH'], '.')
                    if _ == 0:
                        before = selection.read_bytes(), selection.stat().st_mtime_ns
                    else:
                        self.assertEqual((selection.read_bytes(), selection.stat().st_mtime_ns), before)
                self.assertEqual(json.loads(selection.read_text())['feature_directory'], value)
                followup = subprocess.run(['bash', str(storage.PACKAGE / 'scripts/bash/check-prerequisites.sh'),
                                           '--json', '--paths-only'], cwd=self.f.a, env=self.f.env,
                                          text=True, capture_output=True, timeout=30)
                self.assertEqual(followup.returncode, 0, followup.stderr)
                self.assertEqual(Path(json.loads(followup.stdout)['FEATURE_DIR']).resolve(), feature)
                self.assertEqual((selection.read_bytes(), selection.stat().st_mtime_ns), before)
                self.assertTrue((feature / 'plan.md').is_file())
                self.assertFalse((self.f.a / '.sdlc').exists())


class FilesystemLookupTests(unittest.TestCase):
    def test_missing_case_aliases_follow_the_observed_directory_lookup_rule(self):
        with tempfile.TemporaryDirectory(prefix='sdlc-case-lookup-') as name:
            directory = Path(name).resolve()
            probe = directory / 'CaseProbe'
            probe.write_text('probe')
            insensitive = (directory / 'caseprobe').exists()
            self.assertEqual(storage.store.same_path(directory / 'new-plan', directory / 'NEW-PLAN'), insensitive)
            with mock.patch.object(storage.store.sys, 'platform', 'metadata-only-test'):
                self.assertEqual(storage.store.same_path(directory / 'new-plan', directory / 'NEW-PLAN'), insensitive)

    def test_unknown_case_rule_stops_only_ambiguous_missing_addresses(self):
        with tempfile.TemporaryDirectory(prefix='sdlc-case-unknown-') as name:
            directory = Path(name).resolve()
            with mock.patch.object(storage.store.sys, 'platform', 'metadata-only-test'):
                with self.assertRaisesRegex(ValueError, 'Cannot verify case-distinct missing paths'):
                    storage.store.same_path(directory / 'plan', directory / 'PLAN')
                self.assertFalse(storage.store.same_path(directory / 'plan', directory / 'other'))
                self.assertTrue(storage.store.same_path(directory / 'plan', directory / 'plan'))


if __name__ == '__main__':
    unittest.main()

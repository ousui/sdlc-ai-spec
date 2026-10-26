"""Expert regressions: real writer descendants, Git failures, registration races and root aliases."""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import unittest
from unittest import mock

try:
    from tests import test_storage as storage
except ImportError:
    import test_storage as storage


class ExpertReviewTests(unittest.TestCase):
    def setUp(self):
        self.f = storage.StorageTests('runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def wait_for(self, predicate, description):
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.02)
        self.fail('Timed out waiting for ' + description)

    @contextmanager
    def paused_plan_writer(self):
        if os.name != 'posix':
            self.skipTest('Requires POSIX process signals and inherited descriptors')
        self.f.feature(self.f.main)
        ready, resume = self.f.base / 'ready', self.f.base / 'resume'
        bin_dir = self.f.base / 'writer-bin'
        bin_dir.mkdir()
        temporary = self.f.base / 'helper-temporary'
        temporary.mkdir()
        fake = bin_dir / 'mktemp'
        fake.write_text('#!/bin/sh\n'
                        'printf "%s\\n" "$$" > "$SDLC_TEST_READY"\n'
                        'while [ ! -e "$SDLC_TEST_RESUME" ]; do /bin/sleep 0.02; done\n'
                        'exec "$SDLC_TEST_MKTEMP" "$@"\n')
        fake.chmod(0o755)
        env = dict(self.f.env, PATH=str(bin_dir) + os.pathsep + self.f.env['PATH'],
                   TMPDIR=str(temporary), SDLC_TEST_READY=str(ready), SDLC_TEST_RESUME=str(resume),
                   SDLC_TEST_MKTEMP=shutil.which('mktemp'), SDLC_FEATURE_NO_PERSIST='1',
                   SDLC_FEATURE_DIRECTORY='.sdlc/specs/001-one')
        output = self.f.base / 'writer-output.txt'
        with output.open('w') as log:
            process = subprocess.Popen([sys.executable, '-I', '-B', str(storage.SCRIPTS / 'sdlc_store.py'),
                'run', '--project', str(self.f.main), '--script', 'setup-plan.sh', '--', '--json'],
                cwd=self.f.main, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                self.wait_for(lambda: ready.exists() or process.poll() is not None, 'helper checkpoint')
                self.assertTrue(ready.exists(), output.read_text())
                self.assertEqual(int((self.f.main / '.sdlc/.write-lock/pid').read_text()), process.pid)
                yield process, resume, output
            finally:
                resume.touch()
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=10)

    def recover_after_writer_exit(self):
        deadline = time.monotonic() + 15
        while True:
            result = subprocess.run(
                [sys.executable, '-I', '-B', str(storage.SCRIPTS / 'sdlc_store.py'), 'recover-lock',
                 '--project', str(self.f.main)], cwd=self.f.main, env=self.f.env,
                capture_output=True, text=True, timeout=20)
            if result.returncode == 0:
                return json.loads(result.stdout)
            self.assertIn('active writer', result.stderr)
            if time.monotonic() >= deadline:
                self.fail(result.stderr)
            time.sleep(0.02)

    def publish_new_plan(self):
        plan = self.f.prepare(kind='edit', paths=['specs/001-one/plan.md'])
        self.f.replace(plan, 'specs/001-one/plan.md', 'New reviewed plan from second writer\n')
        self.assertEqual(self.f.apply(plan)['status'], 'applied')

    def test_orphan_helper_cannot_overwrite_a_later_successful_plan(self):
        with self.paused_plan_writer() as (process, resume, output):
            process.kill()
            process.wait(timeout=10)
            recovered = subprocess.run([sys.executable, '-I', '-B', str(storage.SCRIPTS / 'sdlc_store.py'),
                'recover-lock', '--project', str(self.f.main)], cwd=self.f.main, env=self.f.env,
                capture_output=True, text=True, timeout=20)
            if recovered.returncode == 0:
                # Exercise the original failure all the way to the lost document.
                self.publish_new_plan()
                resume.touch()
                self.wait_for(lambda: '"IMPL_PLAN":' in output.read_text(), 'orphan helper completion')
            else:
                self.assertIn('active writer', recovered.stderr)
                blocked = self.f.runpy('store_changes.py', 'prepare', '--kind', 'edit',
                    '--path', 'specs/001-one/plan.md', ok=False)
                self.assertIn('write lock', blocked.stderr)
                resume.touch()
                self.wait_for(lambda: '"IMPL_PLAN":' in output.read_text(), 'orphan helper completion')
                self.assertEqual(self.recover_after_writer_exit()['status'], 'stale_lock_released')
                self.publish_new_plan()
            target = self.f.main / '.sdlc/specs/001-one/plan.md'
            self.assertEqual(target.read_text(), 'New reviewed plan from second writer\n')

    def test_wrapper_finally_cannot_release_a_live_descendant_lease(self):
        with self.paused_plan_writer() as (process, resume, output):
            os.kill(process.pid, signal.SIGINT)
            process.wait(timeout=10)
            result = self.f.runpy('sdlc_store.py', 'recover-lock', ok=False)
            self.assertIn('active writer', result.stderr)
            self.assertTrue((self.f.main / '.sdlc/.write-lock').is_dir())
            resume.touch()
            self.assertEqual(self.recover_after_writer_exit()['status'], 'stale_lock_released')

    def test_legacy_pid_only_lock_is_not_recovered_without_writer_evidence(self):
        lock = self.f.main / '.sdlc/.write-lock'
        lock.mkdir()
        (lock / 'owner').write_text('legacy-owner')
        (lock / 'pid').write_text('2147483647')
        before = storage.files(self.f.main)
        result = self.f.runpy('sdlc_store.py', 'recover-lock', ok=False)
        self.assertIn('Incomplete lock ownership', result.stderr)
        self.assertEqual(storage.files(self.f.main), before)

    def test_nonzero_git_identity_stops_init_without_changing_shared_binding(self):
        before = self.f.binding(self.f.a)
        config = self.f.main / '.git/config'
        original = config.read_bytes()
        self.f.git('config', 'core.repositoryformatversion', '999')
        try:
            diagnostic = subprocess.run(['git', 'rev-parse', '--show-toplevel'], cwd=self.f.a,
                env=self.f.env, capture_output=True, text=True)
            self.assertNotEqual(diagnostic.returncode, 0)
            result = self.f.runpy('init_project.py', project=self.f.a, ok=False)
            self.assertIn('Cannot discover Git workspace identity', result.stderr)
            self.assertFalse((self.f.a / '.sdlc').exists())
            status = self.f.runpy('project_status.py', project=self.f.a, ok=False)
            self.assertEqual(json.loads(status.stdout)['status'], 'error')
        finally:
            config.write_bytes(original)
        self.assertEqual(self.f.binding(self.f.a), before)

    def test_missing_git_with_marker_stops_but_standalone_init_still_works(self):
        bin_dir = self.f.base / 'without-git'
        bin_dir.mkdir()
        (bin_dir / 'bash').symlink_to(shutil.which('bash'))
        self.f.env['PATH'] = str(bin_dir)
        result = self.f.runpy('init_project.py', project=self.f.a, ok=False)
        self.assertIn('Cannot discover Git workspace identity', result.stderr)
        self.assertFalse((self.f.a / '.sdlc').exists())
        standalone = self.f.base / 'standalone'
        standalone.mkdir()
        self.assertEqual(self.f.init(standalone)['status'], 'initialized')

    def test_interleaved_source_registrations_keep_both_successful_updates(self):
        source_a, source_b = self.f.base / 'source-a', self.f.base / 'source-b'
        source_a.mkdir()
        source_b.mkdir()
        context = storage.store.resolve(self.f.main)
        original_lock = storage.store.write_lock
        entered = False
        @contextmanager
        def interleave(state):
            nonlocal entered
            if not entered:
                entered = True
                with mock.patch.object(storage.store, 'write_lock', original_lock):
                    storage.store.register(context, None, [source_a])
            with original_lock(state) as token:
                yield token
        with mock.patch.object(storage.store, 'write_lock', interleave):
            data = storage.store.register(context, None, [source_b])
        self.assertEqual(set(data['sources']), {str(source_a), str(source_b)})
        self.assertEqual(set(json.loads((self.f.main / '.sdlc/store.json').read_text())['sources']),
                         {str(source_a), str(source_b)})

    def test_registration_rechecks_authority_after_interleaved_init(self):
        project = self.f.base / 'uninitialized-project'
        project.mkdir()
        context = storage.store.resolve(project, missing=True)
        target = self.f.base / 'redirected-authority'
        original_lock = storage.store.write_lock
        initialized = {}
        @contextmanager
        def interleave(state):
            with mock.patch.object(storage.store, 'write_lock', original_lock):
                initialized.update(self.f.init(project))
            with original_lock(state) as token:
                yield token
        with mock.patch.object(storage.store, 'write_lock', interleave):
            with self.assertRaisesRegex(ValueError, 'Existing authority cannot be redirected'):
                storage.store.register(context, target, [])
        self.assertEqual(initialized['status'], 'completed')
        self.assertFalse((project / '.sdlc/store.json').exists())
        self.assertTrue((project / '.sdlc/memory/constitution.md').is_file())
        self.assertEqual(self.f.binding(project)['AUTHORITY_DIR'], str(project / '.sdlc'))

    def local_root_alias(self):
        self.f.init(self.f.a, '--mode', 'local')
        logical, actual = self.f.a / '.sdlc', self.f.base / 'local-state'
        logical.rename(actual)
        logical.symlink_to(actual, target_is_directory=True)
        return logical, actual

    def test_explicit_local_init_completes_the_resolved_root_alias(self):
        logical, actual = self.local_root_alias()
        identity = (os.readlink(logical), logical.lstat().st_ino, logical.lstat().st_mtime_ns)
        self.assertEqual(self.f.init(self.f.a)['status'], 'unchanged')
        self.assertEqual(self.f.init(self.f.a, '--mode', 'local')['status'], 'unchanged')
        (actual / 'README.md').unlink()
        completed = self.f.init(self.f.a, '--mode', 'local')
        self.assertEqual(completed['status'], 'completed')
        self.assertEqual(completed['SDLC_DIR'], str(actual))
        self.assertTrue((actual / 'README.md').is_file())
        self.assertEqual((os.readlink(logical), logical.lstat().st_ino, logical.lstat().st_mtime_ns), identity)

    def test_root_alias_import_and_interrupted_recovery_use_the_same_store(self):
        logical, actual = self.local_root_alias()
        source = self.f.main / '.sdlc'
        names = ['memory/constitution.md', 'memory/long-term.md']
        before = {name: (actual / name).read_bytes() for name in names}
        for name in names:
            (source / name).write_text('New authority version: ' + name)
        plan = self.f.prepare(self.f.a, kind='import')
        folder = Path(plan['transaction'])
        self.assertEqual(json.loads((folder / 'manifest.json').read_text())['target'], str(actual))
        for name in names:
            self.f.replace(plan, name, 'New authority version: ' + name)
        published = storage.changes.publish_data
        count = 0
        def stop_second(path, data, expected):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError('Stop second publication')
            return published(path, data, expected)
        with mock.patch.object(storage.changes, 'publish_data', side_effect=stop_second), \
                mock.patch.object(storage.changes, 'rollback', side_effect=OSError('Interrupt rollback')):
            with self.assertRaisesRegex(OSError, 'Stop second publication'):
                storage.changes.apply(self.f.a, folder)
        self.assertEqual(json.loads((folder / 'manifest.json').read_text())['status'], 'applying')
        offline = self.f.base / 'offline-authority'
        source.rename(offline)
        try:
            result = self.f.runpy('store_changes.py', 'recover', '--transaction', str(folder), project=self.f.a)
            self.assertEqual(result['status'], 'recovered')
        finally:
            offline.rename(source)
        self.assertTrue(logical.is_symlink())
        for name in names:
            self.assertEqual((actual / name).read_bytes(), before[name])
        refresh = self.f.prepare(self.f.a, kind='import')
        for name in names:
            self.f.replace(refresh, name, 'New authority version: ' + name)
        self.assertEqual(self.f.apply(refresh, self.f.a)['status'], 'applied')
        self.assertEqual((actual / names[0]).read_text(), 'New authority version: ' + names[0])


if __name__ == '__main__':
    unittest.main()

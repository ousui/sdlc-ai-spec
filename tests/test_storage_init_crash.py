"""Real process exits cannot publish a new local store without its import intent."""
from __future__ import annotations

import errno
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

try:
    from tests import test_storage as storage, test_storage_init_retry as retry
except ImportError:
    import test_storage as storage
    import test_storage_init_retry as retry

initializer = retry.initializer

CHILD = r'''
import os, sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, sys.argv[1])
import init_project as initializer
project, phase, feature = Path(sys.argv[2]), sys.argv[3], sys.argv[4]
publish, publish_directory = initializer.publish, initializer.publish_new_directory
def interrupted(path, data, expected):
    if phase == 'before-intent' and path.name == '.init-pending.json':
        os._exit(73)
    if phase == 'under-lock' and path == project / '.sdlc/init-options.json':
        os._exit(73)
    result = publish(path, data, expected)
    if phase == 'intent-written' and path.name == '.init-pending.json':
        os._exit(73)
    return result
def interrupted_directory(source, target):
    publish_directory(source, target)
    if phase == 'directory-visible':
        os._exit(73)
initializer.publish, initializer.publish_new_directory = interrupted, interrupted_directory
initializer.initialize_selected(SimpleNamespace(
    project=project, mode='local', seed='knowledge', feature=[feature] if feature else [],
    feature_numbering=None, discover=False, dry_run=False))
'''


class InitProcessCrashTests(unittest.TestCase):
    def setUp(self):
        self.f = storage.StorageTests('runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.f.feature(self.f.main)

    def crash_matrix(self, equivalent):
        if equivalent:
            if not (self.f.main / '.SDLC/MEMORY/CONSTITUTION.MD').exists():
                self.skipTest('Requires case-equivalent filesystem lookup')
            memory = self.f.main / '.sdlc/memory'
            for path in memory.iterdir():
                path.rename(path.with_name(path.name.upper()))
            memory.rename(memory.with_name('MEMORY'))
        sequence = 0
        for phase in ('before-intent', 'intent-written', 'directory-visible', 'under-lock'):
            for selected in (False, True):
                with self.subTest(phase=phase, selected=selected, equivalent=equivalent):
                    sequence += 1
                    project = self.f.base / ('crash-' + str(sequence))
                    self.f.git('worktree', 'add', '-q', '-b', 'crash-' + str(sequence), str(project))
                    if equivalent:
                        gitdir = Path(self.f.git('rev-parse', '--absolute-git-dir', cwd=project).stdout.strip())
                        (gitdir / 'gitdir').write_text(str(project.with_name(project.name.upper()) / '.GIT') + '\n')
                    source = self.f.main / '.sdlc'
                    source_before = storage.files(source)
                    process = subprocess.run([sys.executable, '-I', '-B', '-c', CHILD, str(storage.SCRIPTS),
                                              str(project), phase, '001-one' if selected else ''],
                                             cwd=project, env=self.f.env, capture_output=True, text=True, timeout=30)
                    self.assertEqual(process.returncode, 73, process.stdout + process.stderr)
                    state = project / '.sdlc'
                    visible = phase in ('directory-visible', 'under-lock')
                    self.assertEqual(state.exists(), visible)
                    self.assertEqual((state / '.init-pending.json').is_file(), visible)
                    leftovers = list(project.glob('.sdlc-init-*'))
                    self.assertEqual(bool(leftovers), not visible)
                    # Invisible staging is not discovered as a local copy. Visible
                    # intent blocks normal work until INIT completes the snapshot.
                    discovery = self.f.init(project, '--discover')
                    self.assertEqual(discovery['local_exists'], visible)
                    self.assertNotIn(str(leftovers[0]) if leftovers else '', discovery['sources'])
                    if phase == 'under-lock':
                        self.assertTrue((state / '.write-lock').is_dir())
                        self.f.runpy('sdlc_store.py', 'recover-lock', project=project)
                    old_memory = (source / 'memory/long-term.md').read_bytes()
                    (source / 'memory/long-term.md').write_text('new source after process exit')
                    flags = ['--mode', 'local'] + (['--feature', '001-one'] if selected else [])
                    caller = project.with_name(project.name.upper()) if equivalent else project
                    result = self.f.init(caller, *flags)
                    self.assertEqual((state / 'memory/long-term.md').read_bytes(),
                                     old_memory if visible else b'new source after process exit')
                    self.assertEqual((state / 'memory/constitution.md').read_bytes(),
                                     (source / 'memory/constitution.md').read_bytes())
                    self.assertEqual((state / 'memory/.constitution-template.json').read_bytes(),
                                     (source / 'memory/.constitution-template.json').read_bytes())
                    self.assertEqual((state / 'specs/001-one/spec.md').exists(), selected)
                    if selected:
                        self.assertEqual((state / 'specs/001-one/spec.md').read_bytes(),
                                         (source / 'specs/001-one/spec.md').read_bytes())
                    self.assertFalse((state / 'feature.json').exists())
                    self.assertFalse((state / '.init-pending.json').exists())
                    self.assertEqual(result['constitution_source'], 'authority-import')
                    before = {str(p.relative_to(state)): (p.read_bytes(), p.stat().st_mtime_ns)
                              for p in state.rglob('*') if p.is_file()}
                    self.assertEqual(self.f.init(caller, *flags)['status'], 'unchanged')
                    self.assertEqual(before, {str(p.relative_to(state)): (p.read_bytes(), p.stat().st_mtime_ns)
                                              for p in state.rglob('*') if p.is_file()})
                    self.assertEqual(list(project.glob('.sdlc-init-*')), leftovers)
                    (source / 'memory/long-term.md').write_bytes(old_memory)
                    self.assertEqual(storage.files(source), source_before)

    def test_real_process_exits_before_and_after_intent_publication(self):
        self.crash_matrix(False)

    def test_equivalent_knowledge_and_git_backlink_survive_real_process_exits(self):
        self.crash_matrix(True)


class NewStorePublicationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='sdlc-intent-publication-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.state = self.root / '.sdlc'
        self.content = b'{"fixture":"complete intent"}\n'

    def test_native_publication_refuses_existing_empty_nonempty_and_aliased_targets(self):
        for kind in ('empty', 'nonempty', 'file', 'symlink', 'case-alias'):
            with self.subTest(kind=kind):
                root = self.root / kind
                root.mkdir()
                source, target = root / 'stage', root / 'store'
                source.mkdir()
                (source / '.init-pending.json').write_bytes(self.content)
                actual = target.with_name('STORE') if kind == 'case-alias' else target
                if kind == 'file':
                    actual.write_bytes(b'keep')
                elif kind == 'symlink':
                    other = root / 'other'
                    other.mkdir()
                    actual.symlink_to(other, target_is_directory=True)
                else:
                    actual.mkdir()
                    if kind == 'nonempty':
                        (actual / 'user').write_bytes(b'keep')
                if kind == 'case-alias' and not target.exists():
                    continue  # This collision does not exist on case-sensitive volumes.
                identity = actual.lstat()
                with self.assertRaises(OSError) as raised:
                    initializer.publish_new_directory(source, target)
                self.assertIn(raised.exception.errno, (errno.EEXIST, errno.ENOTEMPTY))
                self.assertEqual(actual.lstat(), identity)
                self.assertEqual((source / '.init-pending.json').read_bytes(), self.content)
                if kind == 'nonempty':
                    self.assertEqual((actual / 'user').read_bytes(), b'keep')
                elif kind == 'file':
                    self.assertEqual(actual.read_bytes(), b'keep')

    def test_success_only_exposes_a_directory_containing_complete_intent(self):
        def validate():
            self.assertFalse(self.state.exists())
            staged, = self.root.glob('.sdlc-init-*')
            self.assertEqual((staged / '.init-pending.json').read_bytes(), self.content)
        identity = initializer.create_store_with_intent(self.state, self.content, validate)
        self.assertEqual(self.state.stat().st_ino, identity.st_ino)
        self.assertEqual((self.state / '.init-pending.json').read_bytes(), self.content)
        self.assertEqual(list(self.root.glob('.sdlc-init-*')), [])

    def test_validation_failure_and_unsupported_publication_never_create_active_store(self):
        for phase in ('validation', 'publication'):
            with self.subTest(phase=phase):
                failure = OSError(errno.ENOTSUP, 'unavailable')
                validate = mock.Mock(side_effect=failure if phase == 'validation' else None)
                with mock.patch.object(initializer, 'publish_new_directory', side_effect=failure):
                    with self.assertRaises(OSError):
                        initializer.create_store_with_intent(self.state, self.content, validate)
                self.assertFalse(self.state.exists())
                self.assertEqual(list(self.root.glob('.sdlc-init-*')), [])

    def test_concurrent_target_is_preserved_and_only_owned_stage_is_removed(self):
        def concurrent():
            self.state.mkdir()
            (self.state / 'user').write_bytes(b'keep')
        with self.assertRaises(FileExistsError):
            initializer.create_store_with_intent(self.state, self.content, concurrent)
        self.assertEqual((self.state / 'user').read_bytes(), b'keep')
        self.assertFalse((self.state / '.init-pending.json').exists())
        self.assertEqual(list(self.root.glob('.sdlc-init-*')), [])

    def test_failed_staging_cleanup_preserves_concurrent_files_and_replacement_directories(self):
        for replacement in (False, True):
            with self.subTest(replacement=replacement):
                root = self.root / str(replacement)
                root.mkdir()
                target = root / '.sdlc'
                def concurrent():
                    staged, = root.glob('.sdlc-init-*')
                    if replacement:
                        staged.rename(root / 'original-stage')
                        staged.mkdir()
                    (staged / 'user').write_bytes(b'keep')
                    raise OSError('stop before visibility')
                with self.assertRaisesRegex(OSError, 'stop before visibility'):
                    initializer.create_store_with_intent(target, self.content, concurrent)
                staged, = root.glob('.sdlc-init-*')
                self.assertEqual((staged / 'user').read_bytes(), b'keep')
                self.assertFalse(target.exists())
                if replacement:
                    self.assertEqual((root / 'original-stage/.init-pending.json').read_bytes(), self.content)


if __name__ == '__main__':
    unittest.main()

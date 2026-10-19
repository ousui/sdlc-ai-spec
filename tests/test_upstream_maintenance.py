"""Reviewed source moves and names preserve provenance and machine behavior."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from naming import identifiers
from upgrade import candidate_lock, blob, source_digest


MOVES = (
    ('src/specify_cli/commands/init.py', 'src/specify_cli/command_init.py'),
    ('src/specify_cli/events.py', 'src/specify_cli/events/__init__.py'),
)

# Independent expected scope: these are also used for core-only initialization.
CORE_INIT_SOURCES = (
    'src/specify_cli/__init__.py',
    'src/specify_cli/_agent_config.py',
    'src/specify_cli/_assets.py',
    'src/specify_cli/_utils.py',
    'src/specify_cli/extensions/__init__.py',
    'src/specify_cli/presets/__init__.py',
    'src/specify_cli/presets/_manager.py',
    'src/specify_cli/presets/_resolver.py',
    'src/specify_cli/presets/_registry.py',
    'src/specify_cli/presets/_manifest.py',
    'src/specify_cli/integrations/__init__.py',
    'src/specify_cli/integrations/_helpers.py',
    'src/specify_cli/integrations/_commands.py',
)


class UpstreamMaintenanceTests(unittest.TestCase):
    def fixture(self, root: Path):
        upstream = root / 'upstream'
        shutil.copytree(ROOT / 'src/upstream', upstream)
        (upstream / 'templates/commands/taskstoissues.md').write_text('excluded\n')
        return upstream, json.loads((ROOT / 'upstream.lock.json').read_text())

    def move(self, root: Path, old: str, new: str):
        (root / new).parent.mkdir(parents=True, exist_ok=True)
        (root / old).rename(root / new)

    def test_source_moves_record_both_real_paths_even_with_identical_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            upstream, lock = self.fixture(Path(temp))
            original_lock = json.dumps(lock, sort_keys=True)
            for old, new in MOVES:
                self.move(upstream, old, new)
            before = source_digest(upstream)
            updated, changes = candidate_lock(upstream, lock, '1' * 40, 'reviewed-target')
            self.assertEqual({item['path'] for item in changes}, {p for move in MOVES for p in move})
            self.assertTrue(all(item['review_required'] for item in changes))
            for old, new in MOVES:
                self.assertNotIn(old, updated['watch_files'])
                self.assertEqual(updated['watch_files'][new], lock['watch_files'][old])
                removed = next(item for item in changes if item['path'] == old)
                added = next(item for item in changes if item['path'] == new)
                self.assertIsNone(removed['after'])
                self.assertIsNone(added['before'])
            self.assertEqual(before, source_digest(upstream))
            self.assertEqual(original_lock, json.dumps(lock, sort_keys=True))
            # A subsequent same-layout review must retain the actual new paths.
            replay, changes = candidate_lock(upstream, updated, '1' * 40, 'reviewed-target')
            self.assertEqual(replay, updated)
            self.assertEqual(changes, [])

    def test_ambiguous_missing_and_unreviewed_moves_still_fail_closed(self):
        for old, new in MOVES:
            for case in ('both', 'neither', 'unknown'):
                with self.subTest(path=old, case=case), tempfile.TemporaryDirectory() as temp:
                    upstream, lock = self.fixture(Path(temp))
                    if case == 'both':
                        (upstream / new).parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(upstream / old, upstream / new)
                    elif case == 'neither':
                        (upstream / old).unlink()
                    else:
                        self.move(upstream, old, new + '.unreviewed')
                    before = source_digest(upstream)
                    with self.assertRaisesRegex(ValueError, 'exactly one reviewed watched source'):
                        candidate_lock(upstream, lock, '1' * 40, 'target')
                    self.assertEqual(before, source_digest(upstream))

    def test_other_watches_cannot_be_silently_dropped(self):
        with tempfile.TemporaryDirectory() as temp:
            upstream, lock = self.fixture(Path(temp))
            path = 'src/specify_cli/integrations/base.py'
            self.move(upstream, path, path + '.moved')
            with self.assertRaisesRegex(ValueError, 'Watched source missing'):
                candidate_lock(upstream, lock, '1' * 40, 'target')

    def test_reorganized_producer_dependencies_are_added_and_remain_required(self):
        with tempfile.TemporaryDirectory() as temp:
            upstream, lock = self.fixture(Path(temp))
            for old, new in MOVES:
                self.move(upstream, old, new)
            dependency = 'src/specify_cli/integrations/_capture.py'
            (upstream / dependency).write_text('# synthetic generator dependency\n')
            updated, changes = candidate_lock(upstream, lock, '1' * 40, 'target')
            self.assertEqual(updated['watch_files'][dependency], blob((upstream / dependency).read_bytes()))
            addition = next(item for item in changes if item['path'] == dependency)
            self.assertIsNone(addition['before'])
            self.assertTrue(addition['review_required'])
            (upstream / dependency).unlink()
            with self.assertRaisesRegex(ValueError, 'Watched source missing'):
                candidate_lock(upstream, updated, '2' * 40, 'next-target')

    def test_legacy_layout_does_not_acquire_future_watch_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            upstream, lock = self.fixture(Path(temp))
            dependency = upstream / 'src/specify_cli/integrations/_capture.py'
            dependency.write_text('# outside the legacy producer profile\n')
            updated, changes = candidate_lock(upstream, lock, lock['commit'], lock['tag'])
            self.assertEqual(updated, lock)
            self.assertEqual(changes, [])


    def core_fixture(self, root: Path):
        upstream, lock = self.fixture(root)
        for old, new in MOVES:
            self.move(upstream, old, new)
        for relative in CORE_INIT_SOURCES:
            path = upstream / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('# synthetic core initialization dependency\n')
        return upstream, lock

    def test_core_only_init_sources_are_added_to_review_without_enabling_ecosystem(self):
        with tempfile.TemporaryDirectory() as temp:
            upstream, lock = self.core_fixture(Path(temp))
            before = source_digest(upstream)
            updated, changes = candidate_lock(upstream, lock, '1' * 40, 'target')
            for relative in CORE_INIT_SOURCES:
                self.assertEqual(updated['watch_files'][relative], blob((upstream / relative).read_bytes()))
                addition = next(item for item in changes if item['path'] == relative)
                self.assertIsNone(addition['before'])
                self.assertTrue(addition['review_required'])
            for name in ('script', 'events', 'presets', 'extensions'):
                self.assertEqual(updated[name], lock[name])
            self.assertEqual(before, source_digest(upstream))

    def test_each_core_init_source_change_requires_its_own_review(self):
        with tempfile.TemporaryDirectory() as temp:
            upstream, lock = self.core_fixture(Path(temp))
            baseline, _ = candidate_lock(upstream, lock, '1' * 40, 'target')
            for relative in CORE_INIT_SOURCES:
                with self.subTest(path=relative):
                    path = upstream / relative
                    original = path.read_bytes()
                    path.write_bytes(original + b'# changed initialization behavior\n')
                    updated, changes = candidate_lock(upstream, baseline, '2' * 40, 'next')
                    self.assertEqual([item['path'] for item in changes], [relative])
                    self.assertEqual(changes[0]['before'], baseline['watch_files'][relative])
                    self.assertEqual(changes[0]['after'], blob(path.read_bytes()))
                    self.assertTrue(changes[0]['review_required'])
                    self.assertNotEqual(updated['watch_files'][relative], baseline['watch_files'][relative])
                    path.write_bytes(original)

    def test_core_materializer_behavior_change_is_not_an_empty_review(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            upstream, lock = self.core_fixture(base)
            relative = 'src/specify_cli/presets/_manager.py'
            path = upstream / relative
            original = 'def materialize(target):\n    target.write_bytes(b"core constitution")\n'
            path.write_text(original)
            baseline, _ = candidate_lock(upstream, lock, '1' * 40, 'target')
            target = base / 'constitution.md'
            scope = {}
            exec(compile(original, relative, 'exec'), scope)
            scope['materialize'](target)
            before = target.read_bytes()
            changed = original.replace('core constitution', 'changed constitution')
            path.write_text(changed)
            exec(compile(changed, relative, 'exec'), scope)
            scope['materialize'](target)
            self.assertNotEqual(target.read_bytes(), before)
            _, changes = candidate_lock(upstream, baseline, '2' * 40, 'next')
            self.assertEqual([item['path'] for item in changes], [relative])
            self.assertTrue(changes[0]['review_required'])

    def test_locked_core_source_disappearance_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            upstream, lock = self.core_fixture(Path(temp))
            baseline, _ = candidate_lock(upstream, lock, '1' * 40, 'target')
            for relative in CORE_INIT_SOURCES:
                with self.subTest(path=relative):
                    path = upstream / relative
                    original = path.read_bytes()
                    path.unlink()
                    with self.assertRaisesRegex(ValueError, 'Watched source missing'):
                        candidate_lock(upstream, baseline, '2' * 40, 'next')
                    path.write_bytes(original)

    def test_core_init_facade_rebinding_is_reviewed_and_disappearance_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            upstream, lock = self.core_fixture(base)
            relative = 'src/specify_cli/integrations/_commands.py'
            facade = upstream / relative
            # Synthetic relative export matching init's existing facade route;
            # this tests source monitoring, not full upstream CLI installation.
            original = 'from ._helpers import _write_integration_json\n'
            facade.write_text(original)
            baseline, _ = candidate_lock(upstream, lock, '1' * 40, 'target')
            package = types.ModuleType('core_init_fixture')
            package.__path__ = []
            helper = types.ModuleType('core_init_fixture._helpers')
            helper._write_integration_json = lambda target: target.write_bytes(b'core integration state')

            def invoke(source, target):
                scope = {'__package__': 'core_init_fixture'}
                with patch.dict(sys.modules, {package.__name__: package, helper.__name__: helper}):
                    exec(compile(source, relative, 'exec'), scope)
                    scope['_write_integration_json'](target)

            before = base / 'before-integration.json'
            invoke(original, before)
            self.assertEqual(before.read_bytes(), b'core integration state')
            changed = original + 'def _write_integration_json(target):\n    return None\n'
            facade.write_text(changed)
            after = base / 'after-integration.json'
            invoke(changed, after)
            self.assertFalse(after.exists())
            updated, changes = candidate_lock(upstream, baseline, '2' * 40, 'next')
            self.assertEqual([item['path'] for item in changes], [relative])
            self.assertEqual(changes[0]['before'], baseline['watch_files'][relative])
            self.assertEqual(changes[0]['after'], blob(facade.read_bytes()))
            self.assertTrue(changes[0]['review_required'])
            facade.unlink()
            with self.assertRaisesRegex(ValueError, 'Watched source missing'):
                candidate_lock(upstream, updated, '3' * 40, 'removed')

    def test_identifier_projection_does_not_accept_similar_unknown_names(self):
        for name in ('SPECIFY_FEATURE_NO_PERSIST_EXTRA', 'SPECKIT_PYTHON_EXECUTABLE_EXTRA',
                     'SPECKIT_PYTHON_OTHER'):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'Unmapped runtime identifier'):
                identifiers(name + '=1')
        self.assertEqual(identifiers('OTHER_SPECIFY_FEATURE_NO_PERSIST=1'),
                         'OTHER_SPECIFY_FEATURE_NO_PERSIST=1')


if __name__ == '__main__':
    unittest.main()

"""Project-only bootstrap integration tests on disposable directories, never Agents."""
from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'dist'
sys.path.insert(0, str(ROOT / 'tools'))
from build import ALL_COMMANDS, HOSTS, init_body, split
spec = importlib.util.spec_from_file_location('sdlc_init', PACKAGE / 'scripts/python/init_project.py')
initializer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(initializer)


def snapshot(root):
    return {str(p.relative_to(root)): (p.read_bytes(), p.stat().st_mtime_ns, p.stat().st_mode)
            for p in root.rglob('*') if p.is_file() and '.git' not in p.parts}


class InitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='sdlc-init-test-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.project = self.base / 'project'
        self.project.mkdir()

    def run_init(self, *args, project=None, package=PACKAGE, success=True, env=None):
        result = subprocess.run([sys.executable, '-I', '-B',
            str(package / 'scripts/python/init_project.py'), '--project', str(project or self.project),
            '--json', *args], cwd=self.base, text=True, capture_output=True, env=env)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(result.stdout)
        return result

    def test_new_project_only_data_no_feature_no_tool_copies(self):
        (self.project / 'server.go').write_text('user code')
        before = snapshot(PACKAGE)
        result = self.run_init()
        self.assertEqual(result['status'], 'initialized')
        self.assertFalse(result['feature_created'])
        state = self.project / '.sdlc'
        self.assertEqual({p.name for p in state.iterdir()},
            {'init-options.json', 'README.md', '.gitignore', 'memory', 'specs'})
        self.assertEqual((state / 'memory/constitution.md').read_bytes(),
                         (PACKAGE / 'templates/constitution-template.md').read_bytes())
        opts = json.loads((state / 'init-options.json').read_text())
        self.assertEqual(opts, {'script': 'sh', 'feature_numbering': 'sequential',
            'speckit_version': '1.0.5', 'sdlc_layout': 1, 'sdlc_version': '1.0.0-beta'})
        self.assertFalse((state / 'feature.json').exists())
        self.assertEqual((self.project / 'server.go').read_text(), 'user code')
        self.assertEqual(snapshot(PACKAGE), before)
        self.assertFalse((self.project / '.git').exists())

    def test_repeat_is_byte_mode_and_mtime_noop(self):
        self.run_init()
        original = snapshot(self.project)
        result = self.run_init()
        self.assertEqual(result['status'], 'unchanged')
        self.assertFalse(result['created'] or result['updated'])
        self.assertEqual(original, snapshot(self.project))

    def test_complete_manual_state_preserves_active_work(self):
        state = self.project / '.sdlc'
        feature = state / 'specs/001-health'
        feature.mkdir(parents=True)
        (state / 'memory').mkdir()
        (state / 'memory/constitution.md').write_text('Already confirmed by the user\n')
        for name in ('spec.md', 'plan.md', 'tasks.md'):
            (feature / name).write_text('Human ' + name)
        (state / 'feature.json').write_text('{"feature_directory":".sdlc/specs/001-health"}')
        original = snapshot(self.project)
        result = self.run_init()
        self.assertEqual(result['status'], 'completed')
        current = snapshot(self.project)
        for path, value in original.items():
            self.assertEqual(current[path], value)

    def test_merge_only_missing_options_without_host_binding(self):
        state = self.project / '.sdlc'
        state.mkdir()
        (state / 'init-options.json').write_text('{"feature_numbering":"timestamp","custom":"retain"}')
        result = self.run_init()
        self.assertEqual(result['updated'], ['.sdlc/init-options.json'])
        options = json.loads((state / 'init-options.json').read_text())
        self.assertEqual(options['feature_numbering'], 'timestamp')
        self.assertEqual(options['custom'], 'retain')
        for field in ('ai', 'integration', 'ai_skills', 'plugin_root', 'host'):
            self.assertNotIn(field, options)
        before = snapshot(self.project)
        self.run_init('--feature-numbering', 'sequential', success=False)
        self.assertEqual(snapshot(self.project), before)

    def test_timestamp_opt_in_and_deprecated_numbering_preserved(self):
        self.run_init('--feature-numbering', 'timestamp')
        options = self.project / '.sdlc/init-options.json'
        self.assertEqual(json.loads(options.read_text())['feature_numbering'], 'timestamp')
        other = self.base / 'other'; (other / '.sdlc').mkdir(parents=True)
        (other / '.sdlc/init-options.json').write_text('{"branch_numbering":"timestamp"}')
        self.run_init(project=other)
        result = json.loads((other / '.sdlc/init-options.json').read_text())
        self.assertEqual(result['feature_numbering'], result['branch_numbering'])

    def test_dry_run_has_no_filesystem_side_effects(self):
        before = snapshot(self.project)
        result = self.run_init('--dry-run')
        self.assertTrue(result['dry_run'])
        self.assertEqual(result['status'], 'initialized')
        self.assertFalse((self.project / '.sdlc').exists())
        self.assertEqual(snapshot(self.project), before)

    def test_explicit_nested_project_not_parent_git_root(self):
        subprocess.run(['git', 'init', '-q', str(self.project)], check=True)
        child = self.project / 'helloserver'; child.mkdir()
        self.run_init(project=child)
        self.assertFalse((self.project / '.sdlc').exists())
        self.assertTrue((child / '.sdlc').is_dir())

    def test_git_is_read_only_and_ignore_includes_itself(self):
        subprocess.run(['git', 'init', '-q', str(self.project)], check=True)
        (self.project / 'AGENTS.md').write_text('Do not modify')
        config = (self.project / '.git/config').read_bytes()
        self.run_init()
        self.assertEqual((self.project / '.git/config').read_bytes(), config)
        status = subprocess.check_output(['git', '-C', str(self.project), 'status', '--porcelain'], text=True)
        self.assertEqual(status.strip(), '?? AGENTS.md')
        self.assertFalse((self.project / '.git/refs/heads/main').exists())
        self.assertEqual((self.project / 'AGENTS.md').read_text(), 'Do not modify')

    def test_tracked_state_warns_without_untracking(self):
        subprocess.run(['git', 'init', '-q', str(self.project)], check=True)
        (self.project / '.sdlc/memory').mkdir(parents=True)
        (self.project / '.sdlc/memory/constitution.md').write_text('keep')
        subprocess.run(['git', '-C', str(self.project), 'add', '.sdlc'], check=True)
        index = (self.project / '.git/index').read_bytes()
        result = self.run_init()
        self.assertEqual(result['git_tracking'], 'tracked')
        self.assertIn('already tracked', ' '.join(result['warnings']))
        self.assertEqual((self.project / '.git/index').read_bytes(), index)

    def test_no_specify_uv_or_pip_available_or_called(self):
        bin_dir = self.base / 'bin'; bin_dir.mkdir()
        (bin_dir / 'bash').symlink_to(shutil.which('bash'))
        trap = self.base / 'CALLED'
        for name in ('specify', 'uv', 'pip'):
            path = bin_dir / name
            path.write_text('#!/bin/sh\ntouch "' + str(trap) + '"\nexit 99\n'); path.chmod(0o755)
        env = dict(os.environ, PATH=str(bin_dir))
        result = self.run_init(env=env)
        self.assertEqual(result['git_tracking'], 'not-checked')
        self.assertFalse(trap.exists())

    def test_missing_bash_fails_before_writes(self):
        env = dict(os.environ, PATH=str(self.base))
        self.run_init(env=env, success=False)
        self.assertFalse((self.project / '.sdlc').exists())

    def test_plugin_boundary_and_symlinks_rejected(self):
        copy = self.base / 'installed'; shutil.copytree(PACKAGE, copy)
        before = snapshot(copy)
        self.run_init(project=copy, package=copy, success=False)
        self.assertEqual(snapshot(copy), before)
        (self.project / '.sdlc').symlink_to(copy, target_is_directory=True)
        self.run_init(success=False)
        self.assertEqual(snapshot(copy), before)

    def test_symlink_leaf_and_parent_rejected(self):
        for kind in ('memory', 'init-options.json'):
            with self.subTest(kind=kind):
                project = self.base / kind; (project / '.sdlc').mkdir(parents=True)
                outside = self.base / (kind + '-target')
                if kind == 'memory': outside.mkdir()
                else: outside.write_text('{}')
                (project / '.sdlc' / kind).symlink_to(outside)
                before = snapshot(outside) if outside.is_dir() else outside.read_bytes()
                self.run_init(project=project, success=False)
                self.assertEqual(snapshot(outside) if outside.is_dir() else outside.read_bytes(), before)

    def test_malformed_json_and_unsupported_profiles_do_not_write(self):
        for data in ('{', '[]', '{"script":"ps"}', '{"sdlc_layout":2}',
                     '{"sdlc_layout":true}', '{"feature_numbering":"random"}',
                     '{"script":"sh","script":"ps"}'):
            with self.subTest(data=data):
                project = self.base / ('case-' + str(len(list(self.base.iterdir()))))
                (project / '.sdlc').mkdir(parents=True)
                (project / '.sdlc/init-options.json').write_text(data)
                before = snapshot(project)
                self.run_init(project=project, success=False)
                self.assertEqual(snapshot(project), before)
                self.assertFalse((project / '.sdlc/memory').exists())

    def test_legacy_and_existing_specify_are_not_converted(self):
        for layout in ('.specify', '.sdlc/artifacts', '.sdlc/extensions', '.sdlc/scripts'):
            project = self.base / ('legacy-' + str(len(list(self.base.iterdir()))))
            (project / layout).mkdir(parents=True)
            self.run_init(project=project, success=False)
            self.assertFalse((project / '.sdlc/init-options.json').exists())

    def test_corrupt_feature_and_plugin_feature_fail(self):
        for value in ([], {'feature_directory': ''}, {'feature_directory': str(PACKAGE)}):
            project = self.base / ('feature-' + str(len(list(self.base.iterdir()))))
            (project / '.sdlc').mkdir(parents=True)
            (project / '.sdlc/feature.json').write_text(json.dumps(value))
            before = snapshot(project)
            self.run_init(project=project, success=False)
            self.assertEqual(snapshot(project), before)

    def test_constitution_override_and_existing_ignore_are_preserved(self):
        state = self.project / '.sdlc'
        overrides = state / 'templates/overrides'; overrides.mkdir(parents=True)
        (overrides / 'constitution-template.md').write_text('Project-specific seed\n')
        (state / '.gitignore').write_text('my-own-rule\n')
        result = self.run_init()
        self.assertEqual(result['constitution_source'], 'project-override')
        self.assertEqual((state / 'memory/constitution.md').read_text(), 'Project-specific seed\n')
        self.assertEqual((state / '.gitignore').read_text(), 'my-own-rule\n')

    def test_relocated_readonly_plugin_and_quoted_unicode_project(self):
        copy = self.base / 'plugin new version'; shutil.copytree(PACKAGE, copy)
        for path in copy.rglob('*'):
            if path.is_file(): path.chmod(0o444)
        before = snapshot(copy)
        project = self.base / "中文 ' $(touch INJECTED)"; project.mkdir()
        self.run_init(project=project, package=copy)
        self.assertFalse((self.base / 'INJECTED').exists())
        self.assertEqual(snapshot(copy), before)
        text = (project / '.sdlc/init-options.json').read_text()
        self.assertNotIn(str(copy), text)

    def test_missing_template_and_wrong_file_types_fail(self):
        copy = self.base / 'incomplete'; shutil.copytree(PACKAGE, copy)
        (copy / 'templates/constitution-template.md').unlink()
        self.run_init(package=copy, success=False)
        self.assertFalse((self.project / '.sdlc').exists())
        (self.project / '.sdlc').write_text('not a directory')
        self.run_init(success=False)
        self.assertEqual((self.project / '.sdlc').read_text(), 'not a directory')

    def test_partial_io_failure_recoverable_without_reset(self):
        original = initializer.publish
        counter = [0]
        def fail_once(*args):
            counter[0] += 1
            if counter[0] == 2: raise OSError('synthetic disk failure')
            return original(*args)
        with mock.patch.object(initializer, 'publish', side_effect=fail_once):
            with self.assertRaises(OSError): initializer.initialize(PACKAGE, self.project)
        before = snapshot(self.project)
        result = self.run_init()
        self.assertEqual(result['status'], 'completed')
        for key, data in before.items(): self.assertEqual(snapshot(self.project)[key], data)
        self.assertFalse(list(self.project.rglob('.sdlc-init-*')))

    def test_atomic_create_never_overwrites_unexpected_file(self):
        path = self.project / 'existing'; path.write_bytes(b'user data')
        with self.assertRaises(OSError): initializer.publish(path, b'replacement', None)
        self.assertEqual(path.read_bytes(), b'user data')
        self.assertFalse(list(self.project.glob('.sdlc-init-*')))

    def test_all_host_init_entries_and_loader_do_not_require_state(self):
        for host in HOSTS:
            entry = PACKAGE / 'adapters' / host / 'skills/sdlc-init/SKILL.md'
            meta, body = split(entry.read_text())
            self.assertEqual(meta['name'], 'sdlc-init')
            self.assertEqual(meta['metadata']['author'], 'Blade')
            self.assertIn('--host ' + host + ' --skill init', body)
            proc = subprocess.run([sys.executable, '-I', '-B', str(PACKAGE / 'scripts/python/load_workflow.py'),
                '--host', host, '--skill', 'init'], cwd=self.project, capture_output=True, text=True, check=True)
            self.assertEqual(proc.stdout, init_body(host))
            self.assertNotIn('project-paths.sh', proc.stdout)
            self.assertFalse((self.project / '.sdlc').exists())

    def test_initialized_data_supports_all_host_core_scripts(self):
        for host in HOSTS:
            project = self.base / host; project.mkdir()
            self.run_init(project=project)
            env = dict(os.environ, SDLC_HOST=host, SPECIFY_INIT_DIR=str(project))
            script = PACKAGE / 'scripts/bash'
            def run(name, *args):
                return subprocess.run(['bash', str(script / name), *args], env=env,
                    cwd=project, text=True, capture_output=True, check=True)
            paths = json.loads(run('project-paths.sh').stdout)
            self.assertEqual(paths['PROJECT_ROOT'], str(project))
            run('create-new-feature.sh', '--short-name', 'health', 'Health endpoint')
            feature = json.loads((project / '.sdlc/feature.json').read_text())['feature_directory']
            directory = project / feature
            self.assertTrue((directory / 'spec.md').exists())
            plan = json.loads(run('setup-plan.sh', '--json').stdout)
            self.assertEqual(plan['FEATURE_DIR'], str(directory))
            task_setup = json.loads(run('setup-tasks.sh', '--json').stdout)
            # Upstream returns a template; Agent authoring is outside this test.
            (directory / 'tasks.md').write_text(task_setup['TASKS_TEMPLATE_CONTENT'])
            run('check-prerequisites.sh', '--json', '--require-tasks', '--include-tasks')
            before = snapshot(project)
            self.run_init(project=project)
            self.assertEqual(snapshot(project), before)

    def test_unknown_arguments_and_nonexistent_target_fail(self):
        self.run_init('--force', success=False)
        self.run_init(project=self.base / 'absent', success=False)
        self.assertFalse((self.base / 'absent').exists())
        self.assertFalse((self.project / '.sdlc').exists())


if __name__ == '__main__':
    unittest.main()

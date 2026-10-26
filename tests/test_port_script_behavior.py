"""Offline raw-source/production-port differentials on disposable projects.

These fixtures are not installed-CLI baselines or a target-version candidate.
The normal verifier still uses three fresh projects from the locked upstream CLI.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import port
from differential import normalize_project_paths
from naming_check import reverse_names

FIXTURE = ROOT / 'tests/fixtures/spec-kit-maintenance'
SOURCE_SHA = '9dca9bf42a031765ee5e5f2371137f2f26967e11'
SOURCE_FILES = {
    'scripts/bash/common.sh': '53cb1c23e349db4586c272436ce35c6e2f36a9c0b5351a85e0b216d9887a26b7',
    'scripts/bash/create-new-feature.sh': '972f03ed8ca5ee17b7baad6d56d821d46269d77abc337496beafb0fe85a725f2',
    'scripts/bash/check-prerequisites.sh': '38f5e2c8150ee35ee62a5ae3aec66be8bdb15a9805ba20cc3974acdecb6c5e10',
    'LICENSE': '2510b446bc1f0cf9702453075d20cd88631e20e5642658edb7325d9c1eb534f7',
}


class PortScriptBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='sdlc-port-behavior-')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.shell = shutil.which('bash')
        self.assertIsNotNone(self.shell)
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith(('SPECIFY_', 'SPECKIT_', 'SDLC_', 'PYTHON'))}
        self.env['PYTHONDONTWRITEBYTECODE'] = '1'
        self.sequence = 0

    def test_raw_fixture_identity_and_provenance(self):
        metadata = json.loads((FIXTURE / 'SOURCE.json').read_text())
        self.assertEqual(metadata['repository'], 'https://github.com/github/spec-kit')
        self.assertEqual(metadata['commit'], SOURCE_SHA)
        self.assertEqual(metadata['files'], SOURCE_FILES)
        for name, expected in SOURCE_FILES.items():
            self.assertEqual(hashlib.sha256((FIXTURE / name).read_bytes()).hexdigest(), expected, name)
        self.assertEqual({p.name for p in (FIXTURE / 'scripts/bash').glob('*.sh')},
                         {Path(name).name for name in SOURCE_FILES if name.endswith('.sh')})

    def package(self):
        self.sequence += 1
        package = self.base / ('package-' + str(self.sequence))
        (package / 'scripts/bash').mkdir(parents=True)
        (package / 'scripts/python').mkdir()
        (package / 'templates').mkdir()
        for helper in ('path_guard.py', 'sdlc_store.py'):
            shutil.copyfile(ROOT / 'src/scripts/python' / helper, package / 'scripts/python' / helper)
        for raw in (FIXTURE / 'scripts/bash').glob('*.sh'):
            # Always exercise the production entry point, including its adapters.
            (package / 'scripts/bash' / raw.name).write_text(port.port_script(raw.name, raw.read_text()))
        for template in (ROOT / 'src/templates').glob('*.md'):
            shutil.copyfile(template, package / 'templates' / template.name)
        return package

    def normalize(self, text, project):
        text = reverse_names(text)
        text = normalize_project_paths(text, project)
        return text.replace('.sdlc/specs/', 'specs/').replace('.sdlc/', '.specify/')

    def assert_selected_feature(self, record, project, feature):
        # Validate stored state before any display/path projection can hide it.
        payload = json.loads(record.read_text())
        self.assertEqual(payload['feature_directory'], feature.relative_to(project).as_posix(),
                         'feature.json stored path contract')
        self.assertEqual((project / payload['feature_directory']).resolve(), feature.resolve(),
                         'feature.json selected directory contract')
        self.assertTrue(feature.is_dir())

    def no_persist_case(self, operation, value, expected_preserved, host='claude', initial_record=None):
        package = self.package()
        observations = []
        for ported in (False, True):
            project = self.base / ('project-' + str(self.sequence) + ('-port' if ported else '-raw'))
            state = project / ('.sdlc' if ported else '.specify')
            feature = project / ('.sdlc/specs/001-selected' if ported else 'specs/001-selected')
            feature.mkdir(parents=True)
            state.mkdir(exist_ok=True)
            (state / 'init-options.json').write_text('{"script":"sh","feature_numbering":"sequential"}\n')
            (feature / 'spec.md').write_text('Synthetic spec\n')
            (feature / 'plan.md').write_text('Synthetic plan\n')
            record = state / 'feature.json'
            record.write_text(initial_record.replace('<feature>', feature.relative_to(project).as_posix())
                              if initial_record is not None else '{"feature_directory":"previous"}\n')
            before = record.read_bytes(), record.stat().st_mtime_ns
            if not ported:
                shutil.copytree(ROOT / 'src/upstream/templates', state / 'templates')
            prefix = 'SDLC_' if ported else 'SPECIFY_'
            env = dict(self.env, SDLC_HOST=host, **{prefix + 'INIT_DIR': str(project)})
            if value is not None:
                env[prefix + 'FEATURE_NO_PERSIST'] = value
            scripts = package / 'scripts/bash' if ported else FIXTURE / 'scripts/bash'
            if operation == 'create':
                args = ['create-new-feature.sh', '--json', '--number', '2', '--short-name', 'auth', 'Auth feature']
            else:
                env[prefix + 'FEATURE_DIRECTORY'] = str(feature)
                args = ['check-prerequisites.sh', '--json']
                if operation == 'paths-only':
                    args.append('--paths-only')
            result = subprocess.run([self.shell, str(scripts / args[0]), *args[1:]], cwd=project,
                                    env=env, text=True, capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 0, (operation, value, ported, result.stderr))
            preserved = (record.read_bytes(), record.stat().st_mtime_ns) == before
            self.assertEqual(preserved, expected_preserved, 'feature.json persistence contract')
            specs = state / 'specs' if ported else project / 'specs'
            selected = specs / '002-auth' if operation == 'create' else feature
            if not expected_preserved:
                self.assert_selected_feature(record, project, selected)
            files = {str(p.relative_to(specs)): self.normalize(p.read_text(), project)
                     for p in sorted(specs.rglob('*')) if p.is_file()}
            followup = None
            if not expected_preserved:
                if operation == 'create':
                    (selected / 'plan.md').write_text('Synthetic followup plan\n')
                # A new session must recover the selection from persisted state.
                env.pop(prefix + 'FEATURE_DIRECTORY', None)
                before_followup = record.read_bytes(), record.stat().st_mtime_ns
                reread = subprocess.run(
                    [self.shell, str(scripts / 'check-prerequisites.sh'), '--json'], cwd=project,
                    env=env, text=True, capture_output=True, timeout=20)
                self.assertEqual(reread.returncode, 0,
                                 'persisted feature followup contract: ' + reread.stderr)
                self.assertEqual(Path(json.loads(reread.stdout)['FEATURE_DIR']).resolve(),
                                 selected.resolve(), 'persisted feature followup contract: directory')
                self.assertEqual((record.read_bytes(), record.stat().st_mtime_ns), before_followup,
                                 'persisted followup changed feature.json')
                followup = (reread.returncode, self.normalize(reread.stdout, project),
                            self.normalize(reread.stderr, project))
            observations.append((result.returncode, self.normalize(result.stdout, project),
                                 self.normalize(result.stderr, project),
                                 self.normalize(record.read_text(), project), files, preserved, followup))
        self.assertEqual(observations[1], observations[0], 'raw source / port_script differential')

    def test_real_scripts_preserve_writes_values_and_readonly_calls_for_all_hosts(self):
        for host in ('codex', 'claude', 'cursor'):
            for operation in ('prerequisites', 'paths-only', 'create'):
                for value in (None, '', '0', '1', 'true', 'TRUE', 'yes'):
                    with self.subTest(host=host, operation=operation, value=value):
                        preserved = operation == 'paths-only' or value in ('1', 'true')
                        self.no_persist_case(operation, value, preserved, host)

    def test_explicit_selection_and_new_feature_ignore_malformed_previous_selection(self):
        for host in ('codex', 'claude', 'cursor'):
            for operation in ('prerequisites', 'paths-only', 'create'):
                for value in (None, '1'):
                    with self.subTest(host=host, operation=operation, value=value):
                        self.no_persist_case(operation, value, operation == 'paths-only' or value == '1',
                                             host, initial_record='{invalid\n')

    def test_unchanged_selection_preserves_upstream_parser_fallback_noop(self):
        for host in ('codex', 'claude', 'cursor'):
            with self.subTest(host=host):
                self.no_persist_case('prerequisites', None, True, host,
                                     initial_record='{"feature_directory":"<feature>"\n')

    def test_explicit_feature_spelling_and_saved_followup_match_upstream(self):
        for host in ('codex', 'claude', 'cursor'):
            for spelling in ('<feature>/.', './<feature>/.', '<feature>/', '<feature>//', '<absolute>/.'):
                with self.subTest(host=host, spelling=spelling):
                    package = self.package()
                    observations = []
                    for ported in (False, True):
                        project = self.base / (str(self.sequence) + ('-port' if ported else '-raw'))
                        state = project / ('.sdlc' if ported else '.specify')
                        relative = ('.sdlc/' if ported else '') + 'specs/001-selected'
                        feature = project / relative
                        feature.mkdir(parents=True)
                        state.mkdir(exist_ok=True)
                        (state / 'init-options.json').write_text('{"script":"sh"}\n')
                        (feature / 'spec.md').write_text('Selected specification\n')
                        (feature / 'plan.md').write_text('Selected plan\n')
                        pointer = state / 'feature.json'
                        pointer.write_text('{"feature_directory":"previous"}\n')
                        prefix = 'SDLC_' if ported else 'SPECIFY_'
                        value = spelling.replace('<feature>', relative).replace('<absolute>', str(feature))
                        env = dict(self.env, SDLC_HOST=host, **{prefix + 'INIT_DIR': str(project),
                                   prefix + 'FEATURE_DIRECTORY': value})
                        scripts = package / 'scripts/bash' if ported else FIXTURE / 'scripts/bash'
                        command = [self.shell, str(scripts / 'check-prerequisites.sh'), '--json']
                        results = []
                        # Explicit input wins the old selection; read-only and no-persist leave it intact.
                        for mode in ('paths', 'no-persist', 'persist', 'saved'):
                            args = command + (['--paths-only'] if mode in ('paths', 'saved') else [])
                            current = dict(env)
                            if mode == 'no-persist':
                                current[prefix + 'FEATURE_NO_PERSIST'] = '1'
                            if mode == 'saved':
                                current.pop(prefix + 'FEATURE_DIRECTORY')
                            before = pointer.read_bytes(), pointer.stat().st_mtime_ns
                            result = subprocess.run(args, cwd=project, env=current, capture_output=True,
                                                    text=True, timeout=20)
                            self.assertEqual(result.returncode, 0, result.stderr)
                            if mode != 'persist':
                                self.assertEqual((pointer.read_bytes(), pointer.stat().st_mtime_ns), before)
                            self.assertEqual(Path(json.loads(result.stdout)['FEATURE_DIR']).resolve(), feature.resolve())
                            results.append((self.normalize(result.stdout, project),
                                            self.normalize(result.stderr, project),
                                            self.normalize(pointer.read_text(), project)))
                        observations.append(results)
                    self.assertEqual(observations[1], observations[0], 'path spelling / selection differential')

    def test_absolute_alias_selection_preserves_upstream_noop_and_explicit_prefix_rules(self):
        for host in ('codex', 'claude', 'cursor'):
            for override, spelling, logical_cwd in (
                    (None, 'alias', False), ('physical', 'alias', False),
                    ('alias', 'alias', False), ('alias', 'physical', False),
                    (None, 'alias', True), (None, 'physical', True)):
                for initial in ('same', 'previous'):
                    with self.subTest(host=host, override=override, spelling=spelling, logical_cwd=logical_cwd, initial=initial):
                        package = self.package()
                        observations = []
                        for ported in (False, True):
                            project = (self.base / (str(self.sequence) + ('-port' if ported else '-raw'))).resolve()
                            state = project / ('.sdlc' if ported else '.specify')
                            relative = ('.sdlc/' if ported else '') + 'specs/001-selected'
                            feature = project / relative
                            feature.mkdir(parents=True)
                            state.mkdir(exist_ok=True)
                            (state / 'init-options.json').write_text('{"script":"sh"}\n')
                            (feature / 'spec.md').write_text('Selected specification\n')
                            (feature / 'plan.md').write_text('Selected plan\n')
                            alias = project.with_name(project.name + '-alias')
                            alias.symlink_to(project, target_is_directory=True)
                            value = str((alias if spelling == 'alias' else project) / relative) + '/.'
                            pointer = state / 'feature.json'
                            pointer.write_text(json.dumps({'feature_directory': value if initial == 'same' else initial}) + '\n')
                            prefix = 'SDLC_' if ported else 'SPECIFY_'
                            env = dict(self.env, SDLC_HOST=host, PWD=str(alias if logical_cwd else project),
                                       **{prefix + 'FEATURE_DIRECTORY': value})
                            if override:
                                env[prefix + 'INIT_DIR'] = str(alias if override == 'alias' else project)
                            scripts = package / 'scripts/bash' if ported else FIXTURE / 'scripts/bash'
                            results = []
                            for mode in ('paths', 'no-persist', 'persist', 'saved'):
                                current = dict(env)
                                if mode == 'no-persist':
                                    current[prefix + 'FEATURE_NO_PERSIST'] = '1'
                                if mode == 'saved':
                                    current.pop(prefix + 'FEATURE_DIRECTORY')
                                before = pointer.read_bytes(), pointer.stat().st_mtime_ns
                                result = subprocess.run([self.shell, str(scripts / 'check-prerequisites.sh'), '--json',
                                                         *(['--paths-only'] if mode in ('paths', 'saved') else [])],
                                                        cwd=project, env=current, capture_output=True, text=True, timeout=20)
                                self.assertEqual(result.returncode, 0, result.stderr)
                                after = pointer.read_bytes(), pointer.stat().st_mtime_ns
                                if mode != 'persist':
                                    self.assertEqual(before, after)
                                selection_root = alias if override == 'alias' or (not override and logical_cwd) else project
                                if mode == 'persist' and initial == 'same' and not value.startswith(str(selection_root) + '/'):
                                    self.assertEqual(before, after, 'identical absolute alias selection must be a no-op')
                                self.assertEqual(Path(json.loads(result.stdout)['FEATURE_DIR']).resolve(), feature)
                                def normalized(text):
                                    return self.normalize(text.replace(str(alias), str(project)), project)
                                results.append((normalized(result.stdout), normalized(result.stderr),
                                                normalized(pointer.read_text()), before == after))
                            observations.append(results)
                        self.assertEqual(observations[1], observations[0], 'absolute alias / raw source persistence differential')

    def interpreter(self, directory, name, *, reject_yaml=False, invalid=False, launcher=False, log=None):
        path = directory / name
        body = '#!/bin/sh\n'
        if log is not None:
            # Observe only the upstream interpreter probes/Unicode transform;
            # local path_guard and unrelated JSON parsing are separate calls.
            body += ('case "${2:-}" in\n'
                     '  *"sys.version_info.major != 3"*) action=version ;;\n'
                     '  *"import yaml"*) action=yaml ;;\n'
                     '  *"value = sys.stdin.buffer.read"*) action=unicode ;;\n'
                     '  *) action= ;;\n'
                     'esac\n'
                     'if [ -n "$action" ]; then\n'
                     "  printf '%s:%s\\n' " + shlex.quote(name) + ' "$action" >> '
                     + shlex.quote(str(log)) + '\nfi\n')
        if invalid:
            body += 'exit 1\n'
        else:
            if reject_yaml:
                body += 'case "$*" in *"import yaml"*) exit 1 ;; esac\n'
            if launcher:
                body += 'if [ "$1" = "-3" ]; then shift; fi\n'
            body += 'exec ' + shlex.quote(sys.executable) + ' "$@"\n'
        path.write_text(body)
        path.chmod(0o755)
        return str(path)

    def python_case(self, primary, legacy, *, fallback='python3', expected='primary'):
        package = self.package()
        directory = self.base / ('interpreter paths ' + str(self.sequence))
        directory.mkdir()
        primary_path = self.interpreter(directory, 'chosen python', reject_yaml=primary == 'no-yaml',
                                        invalid=primary == 'invalid')
        legacy_path = self.interpreter(directory, 'legacy python')
        bin_dir = directory / 'bin'
        bin_dir.mkdir()
        if fallback:
            self.interpreter(bin_dir, fallback, launcher=fallback == 'py')
        values = {'valid': primary_path, 'invalid': primary_path, 'no-yaml': primary_path,
                  'missing': str(directory / 'missing python'), 'empty': '', None: None}
        selected = {'primary': primary_path, 'legacy': legacy_path, 'python3': 'python3',
                    'python': 'python', 'py': 'py\n-3', None: ''}
        observations = []
        for ported in (False, True):
            prefix = 'SDLC_' if ported else 'SPECKIT_'
            env = dict(self.env, PATH=str(bin_dir))
            for suffix, value in (('PYTHON_EXECUTABLE', values[primary]),
                                  ('PYTHON', legacy_path if legacy else None)):
                if value is not None:
                    env[prefix + suffix] = value
            scripts = package / 'scripts/bash' if ported else FIXTURE / 'scripts/bash'
            result = subprocess.run([self.shell, '-c', 'source "$1"; _python3_command', 'fixture',
                                     str(scripts / 'common.sh')], env=env,
                                    text=True, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0 if expected else 1)
            self.assertEqual(result.stdout.strip(), selected[expected], 'Python interpreter selection contract')
            observations.append((result.returncode, result.stdout, result.stderr))
        self.assertEqual(observations[1], observations[0], 'raw source / port_script interpreter differential')

    def test_real_interpreter_priority_empty_values_spaces_and_probe_failures(self):
        cases = (
            ('valid', True, 'python3', 'primary'),
            (None, True, 'python3', 'legacy'),
            ('empty', True, 'python3', 'legacy'),
            ('missing', True, 'python3', 'python3'),
            ('invalid', True, 'python3', 'python3'),
            ('no-yaml', True, 'python3', 'python3'),
            (None, False, 'python3', 'python3'),
            (None, False, 'python', 'python'),
            (None, False, 'py', 'py'),
            (None, False, None, None),
        )
        for primary, legacy, fallback, expected in cases:
            with self.subTest(primary=primary, legacy=legacy, fallback=fallback):
                self.python_case(primary, legacy, fallback=fallback, expected=expected)

    def unicode_create_case(self, primary, legacy, expected, host='claude'):
        package = self.package()
        observations = []
        for ported in (False, True):
            side = 'port' if ported else 'raw'
            project = self.base / ('unicode-' + str(self.sequence) + '-' + side)
            state = project / ('.sdlc' if ported else '.specify')
            state.mkdir(parents=True)
            (state / 'init-options.json').write_text('{"script":"sh","feature_numbering":"sequential"}\n')
            if not ported:
                shutil.copytree(ROOT / 'src/upstream/templates', state / 'templates')
            choices = self.base / ('unicode interpreter paths ' + str(self.sequence) + ' ' + side)
            choices.mkdir()
            trace = choices / 'calls.log'
            primary_path = self.interpreter(choices, 'primary python', reject_yaml=primary == 'no-yaml',
                                            invalid=primary == 'invalid', log=trace)
            legacy_path = self.interpreter(choices, 'legacy python', log=trace)
            bin_dir = choices / 'bin'
            bin_dir.mkdir()
            self.interpreter(bin_dir, 'python3', log=trace)
            values = {'valid': primary_path, 'no-yaml': primary_path, 'invalid': primary_path,
                      'missing': str(choices / 'missing python'), 'empty': '', None: None}
            feature_prefix = 'SDLC_' if ported else 'SPECIFY_'
            python_prefix = 'SDLC_' if ported else 'SPECKIT_'
            env = dict(self.env, SDLC_HOST=host, PATH=str(bin_dir) + os.pathsep + self.env.get('PATH', os.defpath),
                       **{feature_prefix + 'INIT_DIR': str(project)})
            for suffix, value in (('PYTHON_EXECUTABLE', values[primary]),
                                  ('PYTHON', legacy_path if legacy else None)):
                if value is not None:
                    env[python_prefix + suffix] = value
            scripts = package / 'scripts/bash' if ported else FIXTURE / 'scripts/bash'
            result = subprocess.run(
                [self.shell, str(scripts / 'create-new-feature.sh'), '--json', '--number', '2',
                 '--short-name', '鉴权', 'Unicode auth feature'], cwd=project, env=env,
                text=True, capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 0, ('Unicode creation contract', result.stderr))
            calls = trace.read_text().splitlines() if trace.exists() else []
            selected = {'primary': 'primary python', 'legacy': 'legacy python', 'fallback': 'python3'}[expected]
            self.assertEqual([call for call in calls if call.endswith(':unicode')], [selected + ':unicode'],
                             'Unicode interpreter selection contract')
            if expected != 'fallback':
                # Unlike _python3_command, this real fast path needs Python 3
                # only; a working canonical interpreter need not have PyYAML.
                self.assertEqual(calls, [selected + ':version', selected + ':unicode'],
                                 'Unicode fast path probe contract')
            feature = (state / 'specs' if ported else project / 'specs') / '002-鉴权'
            self.assertEqual(Path(json.loads(result.stdout)['SPEC_FILE']).resolve(),
                             (feature / 'spec.md').resolve())
            self.assert_selected_feature(state / 'feature.json', project, feature)
            observations.append((result.returncode, self.normalize(result.stdout, project),
                                 self.normalize(result.stderr, project),
                                 self.normalize((feature / 'spec.md').read_text(), project),
                                 self.normalize((state / 'feature.json').read_text(), project), calls))
        self.assertEqual(observations[1], observations[0], 'raw source / port_script Unicode differential')

    def test_real_unicode_creation_observes_override_priority_and_distinct_probe(self):
        cases = (('valid', True, 'primary'), ('no-yaml', True, 'primary'),
                 (None, True, 'legacy'), ('empty', True, 'legacy'),
                 ('missing', True, 'fallback'), ('invalid', True, 'fallback'),
                 (None, False, 'fallback'))
        for host in ('codex', 'claude', 'cursor'):
            for primary, legacy, expected in cases:
                with self.subTest(host=host, primary=primary, legacy=legacy):
                    self.unicode_create_case(primary, legacy, expected, host)

    def test_wrong_persisted_feature_path_mutation_is_detected(self):
        original = port.port_script

        def broken(name, text):
            result = original(name, text)
            if name == 'common.sh':
                anchor = '    _sdlc_store feature --project "$repo_root" --value "$feature_dir_value" --persist >/dev/null'
                self.assertEqual(result.count(anchor), 1)
                result = result.replace(anchor, '    _sdlc_store feature --project "$repo_root" --value ".sdlc/specs/wrong" --persist >/dev/null')
            return result

        for operation in ('prerequisites', 'create'):
            with self.subTest(operation=operation), patch.object(port, 'port_script', broken):
                with self.assertRaisesRegex(AssertionError, 'feature.json stored path contract'):
                    self.no_persist_case(operation, None, False)

    def test_persisted_selection_read_mutation_is_detected(self):
        original = port.port_script

        def broken(name, text):
            result = original(name, text)
            if name == 'common.sh':
                anchor = '    elif [[ -f "$(_sdlc_feature_json "$repo_root")" ]]; then'
                self.assertEqual(result.count(anchor), 1)
                result = result.replace(anchor, '    elif false; then')
            return result

        for operation in ('prerequisites', 'create'):
            with self.subTest(operation=operation), patch.object(port, 'port_script', broken):
                with self.assertRaisesRegex(AssertionError, 'persisted feature followup contract'):
                    self.no_persist_case(operation, None, False)

    def test_unicode_creation_priority_mutation_is_detected(self):
        original = port.port_script

        def broken(name, text):
            result = original(name, text)
            if name == 'create-new-feature.sh':
                anchor = '${SDLC_PYTHON_EXECUTABLE:-${SDLC_PYTHON:-}}'
                self.assertEqual(result.count(anchor), 1)
                result = result.replace(anchor, '${SDLC_PYTHON:-${SDLC_PYTHON_EXECUTABLE:-}}')
            return result

        with patch.object(port, 'port_script', broken):
            with self.assertRaisesRegex(AssertionError, 'Unicode interpreter selection contract'):
                self.unicode_create_case('no-yaml', True, 'primary')

    def test_no_persist_projection_mutation_is_detected(self):
        original = port.port_script

        def broken(name, text):
            return original(name, text).replace(
                '${SDLC_FEATURE_NO_PERSIST:-}', '${SDLC_FEATURE_NO_PERSIST_IGNORED:-}')

        for operation in ('prerequisites', 'create'):
            with self.subTest(operation=operation), patch.object(port, 'port_script', broken):
                with self.assertRaisesRegex(AssertionError, 'feature.json persistence contract'):
                    self.no_persist_case(operation, '1', True)

    def test_interpreter_priority_projection_mutation_is_detected(self):
        original = port.port_script

        def broken(name, text):
            return original(name, text).replace(
                '${SDLC_PYTHON_EXECUTABLE:-${SDLC_PYTHON:-}}',
                '${SDLC_PYTHON:-${SDLC_PYTHON_EXECUTABLE:-}}')

        with patch.object(port, 'port_script', broken):
            with self.assertRaisesRegex(AssertionError, 'Python interpreter selection contract'):
                self.python_case('valid', True)

    def test_missing_yaml_probe_mutation_is_detected(self):
        original = port.port_script

        def broken(name, text):
            return original(name, text).replace(
                '"$override" -c \'import yaml\' >/dev/null 2>&1', 'true')

        with patch.object(port, 'port_script', broken):
            with self.assertRaisesRegex(AssertionError, 'Python interpreter selection contract'):
                self.python_case('no-yaml', True, expected='python3')


if __name__ == '__main__':
    unittest.main()

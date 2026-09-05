"""One native Codex CLI surface, disposable installations, pre-archive redaction."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tomllib

SOURCE = Path('/private/tmp/sdlc-post-integration-01a07250')
EVIDENCE = Path('/private/tmp/sdlc-conformance-evidence-01a07250')
LAB = Path('/private/tmp/sdlc-native-lab-01a07250')
SHA = 'fb1d8fb989e5e31d75cd6f311c0e5e663437262d'
CLI = '/Applications/ChatGPT.app/Contents/Resources/codex'
sys.path.insert(0, str(SOURCE))
from tools.rls_validation_support import run_step, source_state, write_json, now, digest
from tools.validate_skill_conformance import SKILLS, runtime_snapshot


def snapshot(project):
    rows = []
    for path in sorted(project.rglob('*')):
        if path.is_symlink():
            rows.append([path.relative_to(project).as_posix(), 'symlink', os.readlink(path)])
        elif path.is_file():
            rows.append([path.relative_to(project).as_posix(), stat.S_IMODE(path.stat().st_mode), digest(path.read_bytes())])
    return rows


def environment(skill):
    # The parent process and the user's real configuration remain unchanged.
    # This child-only Codex state location is a disposable installation fixture.
    client_state_root = LAB / skill / 'client-state'
    child = {k: v for k, v in os.environ.items() if not k.startswith('CODEX_') and k != 'PYTHONPATH'}
    child['CODEX_HOME'] = str(client_state_root)
    child['PYTHONDONTWRITEBYTECODE'] = '1'
    return child


def prepare(skill):
    state = source_state(SOURCE)
    assert state['sha'] == SHA and state['status'] == '', state
    assert json.loads((EVIDENCE / 'portable.json').read_text())['success']
    assert json.loads((EVIDENCE / 'strict.json').read_text())['success']
    base = LAB / skill
    assert not base.exists(), 'Never overwrite an earlier native attempt'
    plugin = base / 'marketplace'
    roots = ['packages', 'scripts', 'skills/_shared', 'skills/' + skill, '.codex-plugin', '.agents/plugins']
    excluded = shutil.ignore_patterns('__pycache__', '*.pyc', 'evals', 'AGENTS.md', 'CLAUDE.md', 'README.md')
    for relative in roots:
        shutil.copytree(SOURCE / relative, plugin / relative, ignore=excluded)
    expected = runtime_snapshot(SOURCE, skill, 'codex-cli', source_sha=SHA)
    assert runtime_snapshot(plugin, skill, 'codex-cli') == expected
    project = base / 'project'
    project.mkdir()
    (project / 'README.md').write_text('# Conformance Fixture\n\n这是一个仅含说明文件的一次性本地验证项目，没有业务代码，没有已记录的研发阶段。\n', encoding='utf-8')
    init = subprocess.run(['git', 'init', '--quiet', str(project)], capture_output=True, text=True)
    assert init.returncode == 0, init.stderr
    client_state_root = base / 'client-state'
    client_state_root.mkdir()
    real_config_root = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))
    inherited = tomllib.loads((real_config_root / 'config.toml').read_text())
    config = '\n'.join([
        'model = ' + json.dumps(inherited['model']),
        'model_reasoning_effort = ' + json.dumps(inherited['model_reasoning_effort']),
        'approval_policy = "never"',
        'sandbox_mode = "read-only"',
        'web_search = "disabled"',
        '[features]',
        'apps = false',
        'remote_plugin = false',
        'memories = false',
        'chronicle = false',
        'multi_agent = false',
        'multi_agent_v2 = false',
        'browser_use = false',
        'computer_use = false',
        'image_generation = false',
        'workspace_dependencies = false',
        'shell_snapshot = false',
        'unbounded_connection_retries = false',
        '',
    ])
    (client_state_root / 'config.toml').write_text(config)
    # Reference the existing CLI authentication without reading/copying its bytes.
    # This private state directory is never included in any evidence archive.
    (client_state_root / 'auth.json').symlink_to(real_config_root / 'auth.json')
    prefix = 'REQ' if skill == 'sdlc-status' else skill.rsplit('-', 1)[1].upper()
    reference = prefix + '-20260906000000-01@1'
    out = EVIDENCE / 'native' / skill
    fixture = {
        'contract': 'sdlc-ai-spec/native-fixture-plan/v1', 'skill': skill,
        'source_sha': SHA, 'frozen_at': now(), 'project': str(project),
        'reference': reference, 'runtime_snapshot_sha256': expected,
        'project_before': snapshot(project), 'configuration': config,
        'scope': 'Native discovery, explicit read-only missing-authority check, negative invocation, and no-write/installed independence. No positive create/execute/finalize or production approval claim.',
        'oracle': {
            'phase_check': 'Structured failure with no artifact for an exact nonexistent reference in an absent Store; no fallback, creation, or sibling invocation.',
            'status_auto': 'Successful not_started overview, null artifact, one next action, no write.',
            'status_exact': 'Structured failure for exact missing REQ; must not report a successful not_started overview.',
            'negative': 'No Skill/Runtime invocation and no project mutations.',
            'permissions': 'Native read-only sandbox, approval_policy never; project file bytes and modes unchanged.',
            'independence': 'Only the installed current Skill and shared Runtime may supply Skill behavior; no source checkout, development docs/tests/Handoff or sibling Skills.',
        },
        'real_target_effects': 0,
    }
    write_json(out / 'fixture-plan.json', fixture)
    print(json.dumps({'skill': skill, 'prepared': True, 'runtime_snapshot_sha256': expected}))


def execute(skill, action, attempt):
    base = LAB / skill
    project = base / 'project'
    out = EVIDENCE / 'native' / skill
    fixture = json.loads((out / 'fixture-plan.json').read_text())
    env = environment(skill)
    before = snapshot(project)
    timeout = 600
    if action == 'marketplace':
        argv = [CLI, 'plugin', 'marketplace', 'add', str(base / 'marketplace'), '--json']
    elif action == 'install':
        argv = [CLI, 'plugin', 'add', 'sdlc-ai-spec@sdlc-ai-spec', '--json']
    else:
        cache = base / 'client-state/plugins/cache/sdlc-ai-spec/sdlc-ai-spec/0.1.0'
        assert cache.is_dir(), 'Native installation cache is absent'
        assert runtime_snapshot(cache, skill, 'codex-cli') == fixture['runtime_snapshot_sha256']
        boundary = ('这是本地一次性验证。当前目录是唯一项目。只使用本次显式选择的已安装 Skill；'
                    '不得调用其他 Skill、插件、子代理、网络或安装依赖，不得读取开发仓库、开发文档、测试、Handoff、用户配置或认证文件。'
                    '业务输入和内部调用方式由已安装 Skill 合约决定。不要宣称测试通过或给自己评分。')
        if action == 'discovery':
            argv = [CLI, 'debug', 'prompt-input', '$sdlc-ai-spec:' + skill + ' help']
        elif action == 'negative':
            prompt = '只根据当前项目 README.md，用一句中文说明这个项目目前已记录的研发阶段。缺少事实时说明未知。不要修改文件。'
            argv = [CLI, 'exec', '--ephemeral', '--json', '--color', 'never', prompt]
        elif action == 'behavior':
            command = 'inspect' if skill == 'sdlc-status' else 'check'
            prompt = ('$sdlc-ai-spec:' + skill + ' ' + command + ' -r ' + fixture['reference']
                      + ' -p ' + str(project) + ' --write-policy=deny --output=json\n' + boundary)
            argv = [CLI, 'exec', '--ephemeral', '--json', '--color', 'never', prompt]
        elif action == 'status-auto':
            assert skill == 'sdlc-status'
            prompt = '$sdlc-ai-spec:sdlc-status --output=json\n' + boundary
            argv = [CLI, 'exec', '--ephemeral', '--json', '--color', 'never', prompt]
        else:
            raise ValueError(action)
    receipt = run_step(project, action, argv, out / 'logs', timeout=timeout, attempt=attempt,
                       environment=env, track_source=False)
    after = snapshot(project)
    observation = {'action': action, 'attempt': attempt, 'exit_code': receipt['exit_code'],
                   'project_before': before, 'project_after': after, 'project_unchanged': before == after,
                   'store_exists': (project / '.sdlc').exists(), 'source_state': source_state(SOURCE),
                   'observed_at': now(), 'real_target_effects': 0}
    if action == 'install' and receipt['exit_code'] == 0:
        caches = list((base / 'client-state/plugins/cache').glob('*/sdlc-ai-spec/*'))
        observation['caches'] = [str(p) for p in caches]
        observation['installed_snapshot_sha256'] = runtime_snapshot(caches[0], skill, 'codex-cli') if len(caches) == 1 else None
        observation['snapshot_matches_source'] = observation['installed_snapshot_sha256'] == fixture['runtime_snapshot_sha256']
    write_json(out / f'{action}-attempt-{attempt}.observation.json', observation)
    print(json.dumps({k: observation[k] for k in ('action', 'attempt', 'exit_code', 'project_unchanged', 'store_exists')}))
    print(receipt['stdout'][-2500:])
    print(receipt['stderr'][-1200:])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('skill', choices=SKILLS)
    parser.add_argument('action', choices=['prepare', 'marketplace', 'install', 'discovery', 'negative', 'behavior', 'status-auto'])
    parser.add_argument('--attempt', type=int, default=1)
    args = parser.parse_args()
    if args.action == 'prepare': prepare(args.skill)
    else: execute(args.skill, args.action, args.attempt)

"""Package producer observations without changing runtime source or certification."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import shutil

spec = importlib.util.spec_from_file_location('harness', str(Path(__file__).with_name('native_harness.py')))
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
from tools.rls_validation_support import digest, now, source_state, write_json
from tools.validate_skill_conformance import DIMENSIONS, runtime_snapshot

STAGE = Path('/private/tmp/sdlc-conformance-delivery-stage-01a07250')
WORK_ITEM = Path('docs/plugin-development/work-items/post-integration-conformance')
OPERATOR = 'Codex producer validator / 01a07250-d15b-73a0-a586-f8dbddabee17'
assert source_state(h.SOURCE)['status'] == ''
assert not STAGE.exists(), 'Do not overwrite a delivery stage'
package = STAGE / WORK_ITEM
common = package / 'client-evidence'
common.mkdir(parents=True)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence(path):
    assert path.is_file() and path.stat().st_size > 0
    return {'path': path.relative_to(STAGE).as_posix(), 'sha256': sha(path)}


def events(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def completed(rows, kind):
    return [r['item'] for r in rows if r.get('type') == 'item.completed' and r.get('item', {}).get('type') == kind]


def decode_output(text):
    decoder = json.JSONDecoder()
    for start in [m.start() for m in re.finditer(r'\{', text)]:
        try:
            result, _ = decoder.raw_decode(text[start:])
            if isinstance(result, dict) and ('ok' in result or 'error' in result):
                return result
        except ValueError:
            pass
    return None


def error_codes(value):
    if not isinstance(value, dict): return []
    return [e.get('code') for e in value.get('errors', [])] + ([value['error'].get('code')] if isinstance(value.get('error'), dict) else [])


for path in sorted(h.EVIDENCE.iterdir()):
    if path.name in ('native', 'protocol-schema', 'package_client_evidence.py'):
        continue
    target = common / path.name
    if path.is_dir(): shutil.copytree(path, target)
    else: shutil.copy2(path, target)
shutil.copy2(Path(__file__), common / Path(__file__).name)
schema = common / 'native-protocol-schema'
schema.mkdir()
for name in ('v1/InitializeParams.json', 'v2/SkillsListParams.json', 'v2/SkillsListResponse.json'):
    shutil.copy2(h.EVIDENCE / 'protocol-schema' / name, schema / Path(name).name)

rows = []
for skill in h.SKILLS:
    original = h.EVIDENCE / 'native' / skill
    dest = package / 'native-candidates/codex-cli' / skill
    shutil.copytree(original, dest)
    fixture = json.loads((dest / 'fixture-plan.json').read_text())
    cache = h.LAB / skill / 'client-state/plugins/cache/sdlc-ai-spec/sdlc-ai-spec/0.1.0'
    expected_snapshot = runtime_snapshot(h.SOURCE, skill, 'codex-cli', source_sha=h.SHA)
    installed_snapshot = runtime_snapshot(cache, skill, 'codex-cli')
    assert installed_snapshot == fixture['runtime_snapshot_sha256'] == expected_snapshot
    project_after = h.snapshot(h.LAB / skill / 'project')
    assert project_after == fixture['project_before']
    assert not (h.LAB / skill / 'project/.sdlc').exists()
    registry = json.loads((dest / 'logs/registry-discovery-attempt-1.stdout.log').read_text())
    registered = [s for d in registry['response']['data'] for s in d['skills'] if s['name'] == 'sdlc-ai-spec:' + skill]
    assert len(registered) == 1 and registered[0]['enabled']
    assert registered[0]['path'] == str(cache / 'skills' / skill / 'SKILL.md')
    assert registered[0]['pluginId'] == 'sdlc-ai-spec@sdlc-ai-spec'
    behavior = events(dest / 'logs/behavior-attempt-1.stdout.log')
    negative = events(dest / 'logs/negative-attempt-1.stdout.log')
    commands = completed(behavior, 'command_execution')
    negative_commands = completed(negative, 'command_execution')
    messages = completed(behavior, 'agent_message')
    final = json.loads(messages[-1]['text'])
    expected_code = 'LIFECYCLE_STORE_UNAVAILABLE' if skill == 'sdlc-status' else 'STORE_NOT_FOUND'
    assert expected_code in error_codes(final), (skill, final)
    assert final.get('ok') is False or (skill == 'sdlc-100-req' and final.get('status') == 'failed')
    assert final.get('artifact') is None
    assert all('/skills/' not in c['command'] and 'runtime.py' not in c['command'] for c in negative_commands)
    assert all(str(h.SOURCE) not in c['command'] for c in commands)
    sibling_paths = sorted({name for c in commands for name in re.findall(r'/skills/(sdlc-[a-z0-9-]+)/', c['command']) if name != skill})
    assert not sibling_paths
    unexpected_tools = [r['item'] for r in behavior + negative if r.get('type') == 'item.completed' and r.get('item', {}).get('type') not in ('command_execution', 'agent_message', 'reasoning', 'error')]
    assert not unexpected_tools, (skill, unexpected_tools)
    runtime_name = 'runtime_final.py' if skill == 'sdlc-100-req' else 'runtime.py'
    entry = str(cache / 'skills' / skill / 'scripts' / runtime_name)
    runtime_calls = [c for c in commands if entry in c['command'] and 'python' in c['command'] and decode_output(c['aggregated_output']) is not None]
    if skill == 'sdlc-100-req':
        assert not runtime_calls and final['runtime_executed'] is False
    else:
        assert runtime_calls, skill
        assert expected_code in error_codes(decode_output(runtime_calls[-1]['aggregated_output'])), skill
    last_runtime = decode_output(runtime_calls[-1]['aggregated_output']) if runtime_calls else None
    raw_errors = completed(behavior, 'error')
    additional = None
    if skill == 'sdlc-status':
        auto = events(dest / 'logs/status-auto-attempt-1.stdout.log')
        additional = json.loads(completed(auto, 'agent_message')[-1]['text'])
        assert additional['ok'] is True and additional['state'] == 'not_started'
        assert additional['effective_write_policy'] == 'deny'
        assert len(additional['overview']['next_actions']) == 1
        assert additional['next_action']['skill_available'] is False
    findings = {
        'missing_authority_semantics': 'PASS',
        'formal_runtime_invocations_with_structured_result': len(runtime_calls),
        'formal_runtime_execution': 'NOT_RUN_PRECHECK_REFUSAL' if not runtime_calls else 'OBSERVED',
        'final_json': final,
        'final_json_equals_last_runtime_result': None if last_runtime is None else final == last_runtime,
        'intermediate_host_messages': [m['text'] for m in messages[:-1]],
        'nonzero_commands': [{'id': c['id'], 'exit_code': c['exit_code'], 'command': c['command'], 'output': c['aggregated_output']} for c in commands if c['exit_code'] != 0],
        'host_error_items': raw_errors,
        'installed_snapshot_after': installed_snapshot,
        'project_after': project_after,
        'project_bytes_and_modes_unchanged': True,
        'store_created': False,
        'sibling_skill_paths_observed': sibling_paths,
        'unexpected_tool_items': unexpected_tools,
        'status_auto_result': additional,
        'limits': ['Only the frozen missing-authority/read-only fixture and negative invocation were exercised.',
                   'No positive create/revise/run/execute/finalize lifecycle certification.',
                   'No human business approval, Effect Authorization, or Final Confirmation was generated.',
                   'Progress messages and any rewritten final JSON are preserved for independent output-contract review.',
                   'CLI background curated-catalog traffic is present in stderr; it is not Skill Runtime network execution and is not claimed to be zero host traffic.'],
    }
    write_json(dest / 'native-observation-audit.json', findings)
    (dest / 'fixture').mkdir()
    shutil.copy2(h.LAB / skill / 'project/README.md', dest / 'fixture/README.md')
    behavior_result = 'PARTIAL' if not runtime_calls else 'PASS'
    sources = {
        'installation': ['logs/install-attempt-1.stdout.log', 'install-attempt-1.observation.json'],
        'discovery': ['logs/registry-discovery-attempt-1.stdout.log'],
        'explicit_invocation': ['logs/behavior-attempt-1.receipt.json', 'logs/behavior-attempt-1.stdout.log'],
        'negative_invocation': ['logs/negative-attempt-1.stdout.log', 'negative-attempt-1.observation.json'],
        'behavior': ['logs/behavior-attempt-1.stdout.log', 'native-observation-audit.json'],
        'permissions': ['logs/discovery-attempt-1.stdout.log', 'behavior-attempt-1.observation.json', 'native-observation-audit.json'],
        'installed_independence': ['fixture-plan.json', 'logs/behavior-attempt-1.stdout.log', 'native-observation-audit.json'],
    }
    if skill == 'sdlc-status': sources['behavior'].append('logs/status-auto-attempt-1.stdout.log')
    checks = [{'id': dimension, 'result': behavior_result if dimension == 'behavior' else 'PASS',
               'evidence': [evidence(dest / relative) for relative in sources[dimension]]} for dimension in DIMENSIONS]
    candidate = {
        'contract': 'sdlc-ai-spec/native-skill-receipt/v1', 'observation_source': 'native_host',
        'skill': skill, 'surface': 'codex-cli', 'source_sha': h.SHA,
        'client_version': 'codex-cli 0.153.4',
        'observed_at': json.loads((dest / 'behavior-attempt-1.observation.json').read_text())['observed_at'],
        'operator': OPERATOR, 'runtime_snapshot_sha256': expected_snapshot, 'checks': checks,
        'classification': 'UNREVIEWED_CANDIDATE_NOT_ACCEPTED',
        'scope': 'Frozen missing-authority/read-only fixture, installation and invocation controls; not full lifecycle compatibility.',
        'independent_review_required': True,
        'formal_runtime_execution': findings['formal_runtime_execution'],
        'open_observations': ['JSON-mode progress messages are present; assess the host output boundary independently.'] +
                             (['REQ stopped at Authority preflight. Formal Runtime behavior remains NOT_RUN and is not replaced by the shared-API preflight trace.'] if not runtime_calls else []) +
                             (['Host final JSON differs from the last Runtime JSON; the original and final result are both retained.'] if last_runtime is not None and final != last_runtime else []),
        'real_target_effects': 0,
    }
    write_json(dest / 'native-receipt.json', candidate)
    for check in checks:
        for item in check['evidence']: assert sha(STAGE / item['path']) == item['sha256']
    rows.append({'skill': skill, 'behavior_result': behavior_result, 'formal_runtime_execution': findings['formal_runtime_execution'],
                 'runtime_invocation_count': len(runtime_calls), 'final_json_rewritten': last_runtime is not None and final != last_runtime,
                 'nonzero_command_count': len(findings['nonzero_commands']), 'host_error_count': len(raw_errors),
                 'candidate': (dest / 'native-receipt.json').relative_to(STAGE).as_posix(),
                 'runtime_snapshot_sha256': expected_snapshot})
    print(skill, behavior_result, findings['formal_runtime_execution'])

write_json(package / 'CLIENT-NATIVE-SUMMARY.json', {
    'contract': 'sdlc-ai-spec/client-native-observation-summary/v1', 'source_sha': h.SHA,
    'surface': 'codex-cli', 'observed_skills': len(rows), 'candidates': rows,
    'native_accepted_cells': [], 'compatibility_ledger': 'UNCHANGED_40_NOT_RUN',
    'independent_review_required': True, 'real_target_effects': 0,
})
print('STAGED', str(package))

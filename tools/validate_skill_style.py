#!/usr/bin/env python3
"""Check the v2 Skill interface against the one public Runtime contract."""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from packages.sdlc.protocol import PAYLOADS, READ_COMMANDS
from tools.build_plugin import SKILLS

HEADINGS = ['适用范围', '约定与边界', '子命令', '参数', '执行流程', '输出与完成条件', '资源索引']
FLAGS = ['--root', '--request', '--contract', '--version', '--help']


def require(value, message):
    if not value:
        raise ValueError(message)


def table(text, heading):
    section = text.split('## '+heading+'\n', 1)[1].split('\n## ', 1)[0]
    return [[part.strip().strip('`') for part in line.strip('|').split('|')]
            for line in section.splitlines() if line.startswith('| `')]


def validate(root=ROOT):
    actual = {p.parent.name for p in (root/'skills').glob('*/SKILL.md')}
    require(actual == set(SKILLS), 'Expected exactly the registered v2 Skill entrypoints')
    results = []
    for name in SKILLS:
        base = root/'skills'/name
        text = (base/'SKILL.md').read_text()
        require(text.startswith('---\n') and '\nname: '+name+'\n' in text, name+': identity differs')
        require('disable-model-invocation: true' in text, name+': explicit invocation policy missing')
        require(re.findall(r'^## (.+)$', text, re.M) == HEADINGS, name+': seven sections differ')
        require(len(text.splitlines()) <= 200, name+': entry exceeds 200 lines')
        title = re.findall(r'^# (.+)$', text, re.M)
        require(len(title) == 1 and title[0].startswith('SDLC '), name+': title differs')
        interface = json.loads((base/'references/interface.json').read_text())
        require(interface['api_version'] == '2' and interface['skill'] == name, name+': interface identity differs')
        rows = table(text, '子命令')
        expected = []
        for command in interface['commands']:
            require(command['name'] in PAYLOADS, name+': undeclared Runtime command')
            require(command['writes'] == (command['name'] not in READ_COMMANDS), name+': command effect declaration differs')
            expected.append([command['name'], command['description'], '是，须满足本阶段授权' if command['writes'] else '否'])
        require(rows == expected, name+': command table differs from interface')
        require([r[0] for r in table(text, '参数')] == FLAGS, name+': CLI parameter table differs')
        for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', text):
            path = (base/target).resolve()
            require(path.is_relative_to((root/'skills').resolve()) and path.is_file(), name+': missing bundled link '+target)
        policy = (base/'agents/openai.yaml').read_text()
        require('allow_implicit_invocation: false' in policy and json.dumps(title[0], ensure_ascii=False) in policy, name+': metadata differs')
        short = json.loads(re.search(r'short_description: (".*")', policy).group(1))
        require(25 <= len(short) <= 64, name+': short description outside range')
        results.append({'skill': name, 'commands': len(rows), 'lines': len(text.splitlines())})
    return {'success': True, 'skills': results, 'scope': 'Formatting and public-interface consistency; not native discovery or Agent behavior certification'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json-out', type=Path)
    args = parser.parse_args()
    try:
        result = validate()
    except (OSError, ValueError, KeyError, IndexError, AttributeError) as exc:
        result = {'success': False, 'error': str(exc)}
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['success'] else 1)

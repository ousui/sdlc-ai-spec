#!/usr/bin/env python3
"""Enforce this repository's small, uniform Skill presentation contract."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
HEADINGS = ('适用范围', '约定与边界', '子命令', '参数', '执行流程', '输出与完成条件', '资源索引')
COMMON = ('--command', '--project-root', '--reference', '--decision-policy', '--write-policy', '--dry-run', '--output')
EXTENSIONS = {
    'sdlc-200-dsn': ('--input',), 'sdlc-300-pln': ('--input',),
    'sdlc-400-imp': ('--input', '--binding', '--owner'),
    'sdlc-500-vfy': ('--input', '--method'),
    'sdlc-600-rls': ('--input', '--item', '--target', '--release-reference'),
}


def require(condition: bool, message: str) -> None:
    if not condition: raise ValueError(message)


def table(text: str, heading: str) -> list[list[str]]:
    section = text.split('## ' + heading + '\n', 1)[1].split('\n## ', 1)[0]
    return [[cell.strip().strip('`') for cell in line.strip().strip('|').split('|')]
            for line in section.splitlines() if re.match(r'^\| `', line)]


def validate_text(root: Path, skill: str, text: str) -> dict:
    base = root / 'skills' / skill
    front = re.match(r'\A---\n(.*?)\n---\n', text, re.S)
    require(front is not None, skill + ': YAML frontmatter missing')
    fields = dict(re.findall(r'^([a-z-]+):\s*(.+)$', front.group(1), re.M))
    require(fields.get('name') == skill and fields.get('description', '').strip(), skill + ': invalid identity/description')
    require(fields.get('disable-model-invocation') == 'true', skill + ': explicit-only policy missing')
    require(re.findall(r'^## (.+)$', text, re.M) == list(HEADINGS), skill + ': missing/duplicate/reordered sections')
    titles = re.findall(r'^# (.+)$', text, re.M)
    require(len(titles) == 1 and titles[0].startswith('SDLC '), skill + ': invalid title')
    require(len(text.splitlines()) <= 200, skill + ': entry exceeds local 200-line budget; split references')
    spec = json.loads((base / 'references/interface.json').read_text(encoding='utf-8'))
    rows = table(text, '子命令')
    require([row[0] for row in rows] == [c['name'] for c in spec['commands']], skill + ': command table differs from interface')
    for row, command in zip(rows, spec['commands']):
        require(len(row) == 3 and row[1] == command['description'], skill + ': command semantics drift')
        require(row[2] == ('是，须满足本阶段授权' if command['writes'] else '否'), skill + ': command write flag drift')
    params = table(text, '参数')
    require([row[0] for row in params] == list(COMMON + EXTENSIONS.get(skill, ())), skill + ': parameter table incomplete or invented')
    aliases = {'--decision-policy':'-d', '--write-policy':'-w', '--dry-run':'-n', '--output':'-f', '--command':'-c', '--project-root':'-p', '--reference':'-r', '--input':'-i', '--binding':'-b', '--method':'-m'}
    for row in params:
        require(len(row) == 3 and row[1] == aliases.get(row[0], '—') and row[2], skill + ': parameter alias/description missing')
    for link in re.findall(r'\[[^\]]+\]\(([^)]+)\)', text):
        require(not re.match(r'^[a-z]+:', link) and not link.startswith('/'), skill + ': runtime entry should use bundled relative links')
        target = (base / link.split('#', 1)[0]).resolve()
        require(target.is_relative_to((root / 'skills').resolve()) and target.is_file(), skill + ': missing/out-of-bundle link: ' + link)
    policy = (base / 'agents/openai.yaml').read_text(encoding='utf-8')
    require('allow_implicit_invocation: false' in policy, skill + ': Codex explicit-only policy missing')
    require(json.dumps(titles[0], ensure_ascii=False) in policy, skill + ': UI title differs')
    for marker in ('decision_policy', 'write_policy', 'scripts/sdlc_skill_interface.py', 'references/interface.json', 'Final Confirmation', 'Gate'):
        require(marker in text, skill + ': essential boundary not documented: ' + marker)
    return {'skill':skill, 'commands':len(rows), 'parameters':len(params), 'lines':len(text.splitlines()), 'status':'PASS'}


def validate(root: Path = ROOT) -> dict:
    from tools.validate_skill_conformance import SKILLS
    rows = [validate_text(root, s, (root/'skills'/s/'SKILL.md').read_text(encoding='utf-8')) for s in SKILLS]
    return {'contract':'sdlc-ai-spec/skill-style-result/v1', 'success':True, 'skills':rows,
            'scope':'Local presentation and interface agreement; not native behavior certification'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--json-out', type=Path)
    args = parser.parse_args()
    try: result = validate()
    except (OSError, ValueError, KeyError, IndexError) as exc: result = {'success':False, 'error':str(exc)}
    if args.json_out:
        from tools.rls_validation_support import write_json
        write_json(args.json_out, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['success'] else 1)

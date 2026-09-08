#!/usr/bin/env python3
"""Build-time projections of existing input constants; not a runtime validator.

This small renderer deliberately does not interpret JSON Schema, execute runtime
modules or derive test expectations. Semantic guidance remains in contract.md.
"""
from __future__ import annotations
import argparse
import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'sdlc-000-ctx': ('runtime.py', ('COLLECTIONS', 'COLLECTION_ENUMS', 'ALLOWED_BASIS', 'ENGINEERING_PURPOSE_ALIASES', 'EVIDENCE_FIELDS')),
    'sdlc-100-req': ('runtime.py', ('PROFILE_VALUES', 'REQ_TYPES', 'SOURCE_TYPES', 'DISPOSITIONS', 'LIFECYCLE_PHASES')),
    'sdlc-200-dsn': ('dsn_common.py', ('PROFILE_VALUES', 'CHANGE_TYPES', 'CHANGE_VALUES', 'DISPOSITIONS', 'LIFECYCLE_PHASES')),
    'sdlc-300-pln': ('pln_common.py', ('PHASE_RANK', 'DISPOSITIONS', 'WORK_ALLOWED')),
    'sdlc-400-imp': ('imp_method.py', ('BLOCKS', 'BLOCK_TABLES')),
}

def literal(node: ast.AST):
    if isinstance(node, ast.Dict):
        return {literal(k): literal(v) for k, v in zip(node.keys, node.values)}
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return [literal(v) for v in node.elts]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ('set', 'frozenset', 'tuple'):
        if len(node.args) != 1 or node.keywords:
            raise ValueError('unsupported constant expression')
        return literal(node.args[0])
    return ast.literal_eval(node)

def constants(path: Path, names: tuple[str, ...]) -> dict:
    result = {}
    for node in ast.parse(path.read_text(encoding='utf-8')).body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            for target in (node.targets if isinstance(node, ast.Assign) else [node.target]):
                if isinstance(target, ast.Name) and target.id in names:
                    result[target.id] = literal(node.value)
    if set(result) != set(names):
        raise ValueError(f'missing input constants in {path.name}: {set(names)-set(result)}')
    return result

def tokens(values) -> str:
    return ', '.join('`'+str(item)+'`' for item in sorted(values))

def render(root: Path = ROOT) -> dict[str, str]:
    output = {}
    for skill, (filename, names) in SOURCES.items():
        c = constants(root/'skills'/skill/'scripts'/filename, names)
        lines = [f'# {skill} 标准输入字段速查', '',
                 '由 `tools/generate_input_reference.py` 从现有 Runtime 常量生成；勿手工编辑。',
                 '本表不是新协议；结构之外的语义、来源及授权见 [contract.md](contract.md)。', '']
        if skill == 'sdlc-000-ctx':
            lines += ['## 集合行（位于 inputs.context）', '', '| 集合 / ID 前缀 | 行字段 |', '|---|---|']
            for collection, (prefix, fields, check) in c['COLLECTIONS'].items():
                lines.append(f'| `{collection}` / `{prefix}` | '+', '.join('`'+key+'`' for key, _ in fields)+' |')
            lines += ['', '## 固定枚举', '', '| 字段 | 标准值 |', '|---|---|', '| `basis` | '+tokens(c['ALLOWED_BASIS'])+' |']
            for collection, fields in c['COLLECTION_ENUMS'].items():
                for field, allowed in fields.items():
                    lines.append(f'| `{collection}.{field}` | {tokens(allowed)} |')
            lines += ['', '## engineering_entries.purpose 的无歧义别名', '', '| 输入 | 标准值 |', '|---|---|']
            lines += [f'| `{alias}` | `{value}` |' for alias, value in sorted(c['ENGINEERING_PURPOSE_ALIASES'].items())]
            lines += ['', '仅描述性枚举接受标准值大小写及首尾空白整理；不改写命令、引用、摘要、权限或事实。', '',
                      '## Evidence 输入字段', '', ', '.join('`'+k+'`' for k, _ in c['EVIDENCE_FIELDS'] if k != 'empty_reason'), '',
                      '`empty_reason` 是 Canonical 输出字段，不是输入字段。']
        elif skill == 'sdlc-400-imp':
            lines += ['## Method blocks', '', '| consideration | ID 前缀 | 必填字段 | 数组元素字段 |', '|---|---|---|---|']
            for name, (prefix, fields) in c['BLOCKS'].items():
                lines.append(f'| {name} | `{prefix}` | {tokens(fields)} | {tokens(c["BLOCK_TABLES"].get(name, ())) or "非空文本字段"} |')
            lines += ['', '每个 Block 还需 `id`、`consideration`。`rules/transitions/mappings` 为数组，其余字段为非空字符串。',
                      '这些是 Method 的条件必填内容，不要求每个 Step 都具有全部七类 Block。']
        else:
            fieldnames = {
                'PROFILE_VALUES': 'profile', 'REQ_TYPES': 'requirements[].type', 'SOURCE_TYPES': 'sources[].type',
                'DISPOSITIONS': 'disposition', 'LIFECYCLE_PHASES': 'lifecycle_applicability[].phase',
                'CHANGE_TYPES': 'change_type', 'CHANGE_VALUES': 'changes[].change',
                'PHASE_RANK': 'work_items[].target_phase', 'WORK_ALLOWED': 'work_items[] 字段',
            }
            lines += ['| 字段 | 标准值 / 字段集合 |', '|---|---|']
            for name in names:
                lines.append(f'| `{fieldnames[name]}` | {tokens(c[name])} |')
        output[f'skills/{skill}/references/input-reference.md'] = '\n'.join(lines)+'\n'
    return output

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='write the generated projections')
    args = parser.parse_args(argv)
    drift = []
    for relative, content in render().items():
        path = ROOT/relative
        if args.write:
            path.write_text(content, encoding='utf-8')
        elif not path.is_file() or path.read_text(encoding='utf-8') != content:
            drift.append(relative)
    if drift:
        print('INPUT_REFERENCE_DRIFT: '+', '.join(drift), file=sys.stderr)
        return 1
    print('INPUT_REFERENCES = PASS (5 bundled projections)')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""Deterministic, reviewed zh-CN projection of already-rendered English workflows.

English-dependent upstream rendering happens BEFORE translation. Host invocations
become named, finite placeholders, then translations are bound back per host.
No network/model calls and no translation during plugin installation/runtime.
The catalog binds source input AND translated bytes; hashes are not semantic proof.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from render import ROOT, COMMANDS, HOSTS, render_source, relocate_body
from naming import invocation

LOCALES = ROOT / 'src/locales/zh-CN'
TEMPLATES = ('checklist-template', 'constitution-template', 'plan-template', 'spec-template', 'tasks-template')
RESOURCES = ('binding', 'init', 'output-language', 'status', 'project-readme')
TOKEN = re.compile(r'\{\{SDLC:[A-Z_]+\}\}')


class LocalizationError(ValueError):
    """Missing/stale translation: block the new candidate, not the accepted package."""


def sha(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def replacements(host: str) -> dict[str, str]:
    if host not in HOSTS:
        raise ValueError('Unsupported explicit host: ' + host)
    prefix = '$' if host == 'codex' else '/sdlc-ai-spec:' if host == 'claude' else '/'
    return dict({'{{SDLC:HOST}}': host, '{{SDLC:HOOK_EXAMPLE}}': prefix + 'sdlc-git-commit'},
                **{'{{SDLC:' + name.upper() + '}}': invocation(name, host) for name in COMMANDS})


def english_body(name: str, host: str) -> str:
    if name not in COMMANDS:
        raise ValueError('Unknown source command: ' + name)
    raw = (ROOT / 'src/upstream/templates/commands' / (name + '.md')).read_text(encoding='utf-8')
    return relocate_body(render_source(raw, name, host)[1], host)


def canonical_source(name: str) -> str:
    """All hosts must yield the SAME complete input after finite name substitution."""
    sources = []
    for host in HOSTS:
        text = english_body(name, host)
        if TOKEN.search(text):
            raise LocalizationError('Source collides with localization placeholders: ' + name)
        for token, value in replacements(host).items():
            if token == '{{SDLC:HOST}}':
                text = text.replace('SDLC_HOST=' + value, 'SDLC_HOST=' + token)
            else:
                text = re.sub(re.escape(value) + r'(?![\w-])', lambda m: token, text)
        sources.append(text)
    if len(set(sources)) != 1:
        raise LocalizationError('Host rendering diverged; review localization adapter: ' + name)
    return sources[0]


def _fenced_blocks(text: str) -> tuple[tuple[str, str, str, str], ...]:
    """Return Markdown fenced blocks and fail closed on an unclosed fence.

    The tuple contains indentation, fence marker, language/info string and body.
    Natural-language fenced examples may be localized, but fence structure and
    explicitly executable/data fence bodies remain part of the machine contract.
    """
    blocks = []
    current = None
    for line in text.splitlines():
        if current is None:
            match = re.match(r'^([ \t]*)(`{3,}|~{3,})([^\n]*)$', line)
            if match:
                current = [match[1], match[2], match[3].strip(), []]
            continue
        indent, marker, info, body = current
        if re.match(r'^' + re.escape(indent) + re.escape(marker[0])
                    + r'{' + str(len(marker)) + r',}\s*$', line):
            blocks.append((indent, marker, info, '\n'.join(body)))
            current = None
        else:
            body.append(line)
    if current is not None:
        raise LocalizationError('Unclosed Markdown fence in localization input')
    return tuple(blocks)


def _fence_languages(text: str) -> tuple[str, ...]:
    return tuple(block[2] for block in _fenced_blocks(text))


MACHINE_ENUMS = (
    'PASS', 'FAIL', 'ERROR', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW',
    'LOCALIZATION_REQUIRED', 'missing', 'partial', 'contradicts', 'unrequested',
    'converged', 'tasks_appended', 'EXECUTE_COMMAND',
)
MACHINE_FENCE_LANGUAGES = frozenset(('sh', 'bash', 'shell', 'python', 'py', 'json', 'yaml', 'yml', 'toml'))
MACHINE_MARKERS = ('EXECUTE_COMMAND', 'LOCALIZATION_REQUIRED')


def _machine_atoms(text: str, *, include_contextual_values: bool = False) -> tuple[str, ...]:
    """Extract machine-significant atoms while ignoring surrounding human prose."""
    found = []
    patterns = (
        r'\{\{SDLC:[A-Z_]+\}\}',
        r'(?<![\w/])(?:\.sdlc|src|tests|backend|frontend|ios|android|api|docs|contracts)/(?:[A-Za-z0-9_./\[\]#-]*)',
        r'(?<![\w./-])(?:spec|plan|tasks|research|data-model|quickstart|requirements|constitution)\.md\b',
        r'(?<![\w-])sdlc-(?:\d{3}-[a-z0-9-]+|status)\b',
        r'(?<![\w-])--[a-z][a-z0-9-]*',
        r'\$\{?[A-Z][A-Z0-9_]*\}?|(?<![A-Z0-9_])(?:FEATURE_DIR|FEATURE_SPEC|IMPL_PLAN|AVAILABLE_DOCS|SDLC_HOST|SDLC_PROJECT_ROOT|SDLC_PLUGIN_ROOT|SDLC_FEATURE_DIRECTORY|SDLC_FEATURE)\b',
        r'\bhooks\.(?:before|after)_[a-z0-9_]+\b',
        r'\b(?:T\d{3,}|TXXX|CHK\d{3,}|FR-\d+|SC-\d+)\b',
        r'\[(?:US\d+|P|ID|TaskID|P\?|Story\??)\]',
        r'\[NEEDS CLARIFICATION(?=[:\]])',
    )
    for pattern in patterns:
        found.extend(re.findall(pattern, text))
    for value in MACHINE_ENUMS:
        found.extend(re.findall(r'(?<![A-Za-z0-9_])' + re.escape(value)
                                + r'(?![A-Za-z0-9_])', text))
    found.extend(re.findall(r'\b(?:exit|return)\s+[0-9]+\b', text))
    if include_contextual_values:
        found.extend(value.lower() for value in re.findall(
            r'(?<![A-Za-z0-9_])(?:true|false|null)(?![A-Za-z0-9_])', text, re.I))
    return tuple(found)


def _machine_inline(text: str) -> Counter:
    """Protect machine atoms inside inline code without freezing translated prose."""
    items = []
    lines = text.splitlines()
    in_fence = False
    marker = None
    indent = ''
    for line in lines:
        if not in_fence:
            match = re.match(r'^([ \t]*)(`{3,}|~{3,})([^\n]*)$', line)
            if match:
                in_fence = True; indent = match[1]; marker = match[2]
                continue
        else:
            if re.match(r'^' + re.escape(indent) + re.escape(marker[0])
                        + r'{' + str(len(marker)) + r',}\s*$', line):
                in_fence = False; marker = None; indent = ''
            continue
        for raw in re.findall(r'`([^`\n]+)`', line):
            atoms = _machine_atoms(raw, include_contextual_values=True)
            if atoms:
                items.append(atoms)
    return Counter(items)


def _shell_executable_lines(body: str) -> tuple[str, ...]:
    """Keep actual shell examples exact while allowing comments/pseudo-task prose to translate."""
    commands = ('git', 'python', 'python3', 'bash', 'sh', 'uv', 'exit', 'return',
                'test', 'cd', 'mkdir', 'rm', 'cp', 'mv', 'cat', 'grep', 'sed',
                'awk', 'jq', 'curl', 'wget', 'printf', 'echo')
    result = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        candidate = re.sub(r'^(?:[A-Z_][A-Z0-9_]*=(?:"[^"]*"|\'[^\']*\'|[^ ]+)\s+)+', '', stripped)
        if any(re.match(r'^' + re.escape(command) + r'(?:\s|$)', candidate) for command in commands):
            result.append(stripped)
    return tuple(result)


def _machine_fences(text: str) -> tuple[tuple, ...]:
    """Protect machine-bearing fence content without freezing translated pseudo examples."""
    result = []
    for _indent, _marker, info, body in _fenced_blocks(text):
        language = info.split(None, 1)[0].lower() if info else ''
        if language not in MACHINE_FENCE_LANGUAGES:
            continue
        atoms = _machine_atoms(body, include_contextual_values=True)
        if language in ('sh', 'bash', 'shell'):
            result.append((language, atoms, _shell_executable_lines(body)))
        else:
            # Structured/code fences are executable/data contracts. Fail closed
            # until a reviewed presentation rule explicitly allows prose inside.
            result.append((language, atoms, sha(body)))
    return tuple(result)


def _structured_scalars(text: str) -> Counter:
    """Bind JSON-style machine scalar values to their keys, not just global counts."""
    pairs = []
    pattern = (r'"([A-Za-z_][A-Za-z0-9_-]*)"\s*:\s*'
               r'(true|false|null|-?\d+(?:\.\d+)?|"[A-Z][A-Z0-9_.:-]*")')
    for match in re.finditer(pattern, text):
        pairs.append((match[1], match[2]))
    return Counter(pairs)


def _table_machine_rows(text: str) -> Counter:
    """Preserve machine values in Markdown tables together with a stable row anchor."""
    rows = []
    for line in text.splitlines():
        if '|' not in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if not cells or all(re.fullmatch(r':?-{3,}:?', cell or '') for cell in cells):
            continue
        anchor = cells[0] if re.fullmatch(r'[A-Za-z0-9_.:/#-]+', cells[0] or '') else ''
        values = []
        for cell in cells:
            if re.fullmatch(r'-?\d+(?:\.\d+)?', cell):
                values.append(('number', cell))
            for enum in MACHINE_ENUMS:
                if re.search(r'(?<![A-Za-z0-9_])' + re.escape(enum)
                             + r'(?![A-Za-z0-9_])', cell):
                    values.append(('enum', enum))
            for value in re.findall(r'(?<![A-Za-z0-9_])(?:true|false|null)(?![A-Za-z0-9_])', cell, re.I):
                values.append(('scalar', value.lower()))
            values.extend(('ref', value) for value in re.findall(
                r'\b(?:T\d{3,}|TXXX|CHK\d{3,}|FR-\d+|SC-\d+)\b', cell))
            values.extend(('file', value) for value in re.findall(
                r'\b[A-Za-z0-9_.-]+\.(?:md|json|yml|yaml|sh|py)\b', cell))
        if values:
            rows.append((anchor, tuple(values)))
    return Counter(rows)


def machine_contract(text: str) -> dict:
    """Finite machine/structure contract shared by workflows and templates.

    Human-language labels and examples may be localized. Machine identifiers,
    fenced executable/data bodies, structured scalar associations, table status
    values and Markdown structure must remain equivalent.
    """
    blocks = _fenced_blocks(text)
    return {
        'tokens': Counter(TOKEN.findall(text)),
        'curly_slots': Counter(re.findall(r'\{[a-z_][a-z0-9_]*\}', text)),
        'machine_slots': Counter(re.findall(r'\[[A-Z][A-Z0-9_ ?-]*\]|\[NEEDS CLARIFICATION(?=[:\]])', text)),
        'story_markers': Counter(re.findall(r'\[(?:US\d+|P|ID|TaskID|P\?|Story\??)\]', text)),
        'checkboxes': Counter(re.findall(r'(?m)^\s*- \[[ xX]\](?: (?:T\d+|TXXX|CHK\d+)(?: \[[A-Z0-9]+\])*)?', text)),
        'refs': Counter(re.findall(r'\b(?:T\d{3,}|TXXX|CHK\d{3,}|FR-\d+|SC-\d+)\b', text)),
        'paths': Counter(re.findall(r'(?<![\w/])(?:\.sdlc|src|tests|backend|frontend|ios|android|api|docs|contracts)/(?:[A-Za-z0-9_./\[\]#-]*)', text)),
        'files': Counter(re.findall(r'(?<![\w./-])(?:spec|plan|tasks|research|data-model|quickstart|requirements|constitution)\.md\b', text)),
        'commands': Counter(re.findall(r'(?<![\w-])sdlc-(?:\d{3}-[a-z0-9-]+|status)\b', text)),
        'cli_args': Counter(re.findall(r'(?<![\w-])--[a-z][a-z0-9-]*', text)),
        'variables': Counter(re.findall(r'\$\{?[A-Z][A-Z0-9_]*\}?|(?<![A-Z0-9_])(?:FEATURE_DIR|FEATURE_SPEC|IMPL_PLAN|AVAILABLE_DOCS|SDLC_HOST|SDLC_PROJECT_ROOT|SDLC_PLUGIN_ROOT|SDLC_FEATURE_DIRECTORY|SDLC_FEATURE)\b', text)),
        'hook_keys': Counter(re.findall(r'\bhooks\.(?:before|after)_[a-z0-9_]+\b', text)),
        'json_keys': Counter(re.findall(r'"([A-Za-z_][A-Za-z0-9_-]*)"\s*:', text)),
        'machine_markers': Counter(re.findall(
            r'(?<![A-Za-z0-9_])(?:' + '|'.join(map(re.escape, MACHINE_MARKERS))
            + r')(?![A-Za-z0-9_])', text)),
        'inline_machine': _machine_inline(text),
        'structured_scalars': _structured_scalars(text),
        'table_machine_rows': _table_machine_rows(text),
        'machine_fences': _machine_fences(text),
        'fence_shape': tuple((indent, marker, info) for indent, marker, info, _body in blocks),
        'levels': tuple(re.findall(r'(?m)^(#{1,6}) ', text)),
    }


def validate_translation_contract(name: str, source: str, translated: str) -> None:
    if machine_contract(source) != machine_contract(translated):
        raise LocalizationError('Workflow machine/structure contract changed: ' + name)
    if not re.search(r'[\u4e00-\u9fff]', translated):
        raise LocalizationError('Missing Chinese workflow prose: ' + name)

def validate_translation(name: str, source: str, translated: str, record: dict) -> None:
    if record.get('status') != 'reviewed' or not record.get('reviewer'):
        raise LocalizationError('Translation requires review: ' + name)
    if record.get('source_sha256') != sha(source):
        raise LocalizationError('Stale translation input: ' + name + '; run tools/localize.py export')
    if record.get('translation_sha256') != sha(translated):
        raise LocalizationError('Translation bytes changed without review: ' + name)
    validate_translation_contract(name, source, translated)


def catalog() -> dict:
    try:
        data = json.loads((LOCALES / 'catalog.json').read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise LocalizationError('Missing or invalid zh-CN catalog') from error
    if data.get('schema_version') != 2 or set(data.get('commands', {})) != set(COMMANDS):
        raise LocalizationError('Localization inventory differs from upstream core profile')
    contract = data.get('contract', {})
    if contract.get('version') != 2 or contract.get('canonical_locale') != 'zh-CN':
        raise LocalizationError('Missing localization contract v2')
    aliases = contract.get('structural_aliases', {})
    for source, entry in aliases.items():
        if not source or not isinstance(entry, dict) or not entry.get('canonical') or not isinstance(entry.get('legacy'), list):
            raise LocalizationError('Invalid structural alias contract: ' + str(source))
    return data


def translate_body(name: str, host: str) -> str:
    source = canonical_source(name)
    translated = (LOCALES / 'workflows' / (name + '.md')).read_text(encoding='utf-8')
    record = catalog()['commands'][name]
    validate_translation(name, source, translated, record)
    # Only the reviewed document-example fragment may change inside a fence.
    # All executable/JSON fences above remain protected byte-for-byte.
    if name == 'specify':
        original = presentation_source('requirements')
        localized = presentation('requirements')
        old = '\n'.join('      ' + line if line else '' for line in original.rstrip('\n').split('\n'))
        new = '\n'.join('      ' + line if line else '' for line in localized.rstrip('\n').split('\n'))
        if translated.count(old) != 1:
            raise LocalizationError('Built-in requirements example anchor changed')
        translated = translated.replace(old, new, 1)
    values = replacements(host)
    result = TOKEN.sub(lambda m: values[m[0]], translated)
    if '{{SDLC:' in result:
        raise LocalizationError('Unresolved localization token: ' + name)
    return result


def translated_metadata(name: str, source_meta: dict) -> dict:
    record = catalog()['commands'][name]
    meta = dict(source_meta)
    # Generated entries no longer publish UI hints. Do not make an unused
    # upstream hint a localization gate; raw source metadata remains verified.
    expected = {k: source_meta[k] for k in ('description',) if k in source_meta}
    for key, original in expected.items():
        entry = record.get('metadata', {}).get(key)
        if not entry or entry.get('source') != original or not entry.get('zh_CN'):
            raise LocalizationError('Missing/stale metadata translation: ' + name + '/' + key)
        meta[key] = entry['zh_CN']
    return meta



RESOURCE_SOURCE_EQUIVALENT = frozenset(('binding', 'init', 'project-readme'))
RESOURCE_REQUIRED_CLAUSES = {
    'status': (
        'python3 -I -B "${SDLC_PLUGIN_ROOT:?}/scripts/python/project_status.py" --json',
        '没有 `--write`、`--fix` 或输出文件参数。',
        '参考入口只提供建议和事实依据，不执行。',
        '正常、异常、重复查询均不更改项目文件、Git 索引、配置、分支、任务勾选、当前需求、缓存或报告；',
    ),
    'output-language': (
        '不得为了翻译新增写入或重写其他已有内容。',
        '机器契约保持原样',
        '新增别名不得改变问题数量、等待用户确认、停止条件或写入权限。',
        '此语言约定只改变呈现，不改变后续步骤、条件、数量限制、权限、停止条件或上游既有缺陷；',
    ),
}


def _normalized_prose(text: str) -> str:
    return re.sub(r'\s+', '', text)


def validate_resource_contract(name: str, text: str) -> None:
    """Validate local-resource machine/authority boundaries before hashes are recorded.

    Source-equivalent resources preserve the same finite machine contract as the
    English adapter source. STATUS and output-language are local authored policies,
    so their high-risk clauses are independently pinned instead of pretending an
    upstream translation source exists.
    """
    if name not in RESOURCES:
        raise LocalizationError('Unknown local resource: ' + name)
    rec = catalog().get('resources', {}).get(name, {})
    if name in RESOURCE_SOURCE_EQUIVALENT:
        source_path = rec.get('source')
        if not source_path:
            raise LocalizationError('Localized resource is missing its source: ' + name)
        source = (ROOT / source_path).read_text(encoding='utf-8')
        if machine_contract(source) != machine_contract(text):
            raise LocalizationError('Resource machine/structure contract changed: ' + name)
    clauses = RESOURCE_REQUIRED_CLAUSES.get(name, ())
    normalized = _normalized_prose(text)
    for clause in clauses:
        if _normalized_prose(clause) not in normalized:
            raise LocalizationError('Critical localized resource clause changed: ' + name)
    if not re.search(r'[\u4e00-\u9fff]', text):
        raise LocalizationError('Missing Chinese localized resource: ' + name)


def precheck_review(name: str, *, is_resource: bool = False, is_presentation: bool = False) -> dict:
    """Read-only contract validation before an explicit review record is written."""
    if is_presentation:
        source = presentation_source(name)
        translated = presentation_file(name).read_text(encoding='utf-8')
        validate_presentation_contract(name, source, translated)
        kind = 'presentation'
    elif is_resource:
        translated = (LOCALES / (name + '.md')).read_text(encoding='utf-8')
        validate_resource_contract(name, translated)
        kind = 'resource'
    else:
        if name not in COMMANDS:
            raise LocalizationError('Unknown core command')
        source = canonical_source(name)
        translated = (LOCALES / 'workflows' / (name + '.md')).read_text(encoding='utf-8')
        validate_translation_contract(name, source, translated)
        kind = 'command'
    return {
        'status': 'PASS', 'kind': kind, 'name': name,
        'scope': 'read-only machine/structure and critical-boundary precheck; not semantic approval',
    }

def resource(name: str) -> str:
    if name not in RESOURCES:
        raise LocalizationError('Unknown local resource: ' + name)
    rec = catalog().get('resources', {}).get(name, {})
    text = (LOCALES / (name + '.md')).read_text(encoding='utf-8')
    validate_resource_contract(name, text)
    if rec.get('status') != 'reviewed' or not rec.get('reviewer') or rec.get('translation_sha256') != sha(text):
        raise LocalizationError('Unreviewed localized resource: ' + name)
    if 'source' in rec and rec.get('source_sha256') != sha((ROOT / rec['source']).read_text(encoding='utf-8')):
        raise LocalizationError('Stale localized resource: ' + name)
    return text


def presentation_source(name: str) -> str:
    """Read presentation inputs AFTER source path/name projection; never edit upstream."""
    if name in TEMPLATES:
        return (ROOT / 'src/templates' / (name + '.md')).read_text(encoding='utf-8')
    if name == 'requirements':
        source = canonical_source('specify')
        match = re.search(r'(?m)^( +)```markdown\n\1(# Specification Quality Checklist:[\s\S]*?)^\1```', source)
        if match is None:
            raise LocalizationError('Upstream built-in requirements example changed')
        # First line indentation was consumed by the match; strip only the
        # exact fence indentation from subsequent lines, not semantic whitespace.
        prefix, body = match[1], match[2]
        return '\n'.join(line[len(prefix):] if line.startswith(prefix) else line
                         for line in body.split('\n'))
    raise LocalizationError('Unknown presentation: ' + name)


def presentation_file(name: str) -> Path:
    if name in TEMPLATES:
        return LOCALES / 'templates' / (name + '.md')
    if name == 'requirements':
        return LOCALES / 'fragments/requirements.md'
    raise LocalizationError('Unknown presentation: ' + name)


def presentation_contract(text: str) -> dict:
    """Presentation structure plus machine identifiers, independent of language.

    Human-readable headings, field labels and example prose may be localized after
    source review. The exact source and translated bytes are still hash-bound.
    """
    return machine_contract(text)


def validate_presentation_contract(name: str, source: str, text: str) -> None:
    if presentation_contract(source) != presentation_contract(text):
        raise LocalizationError('Presentation machine/structure contract changed: ' + name)
    if not re.search(r'[\u4e00-\u9fff]', text):
        raise LocalizationError('Missing Chinese presentation: ' + name)
    if re.search(r'中文(?:注释|说明|版本)', text) or '\ufffc' in text:
        raise LocalizationError('Language label/object character in presentation: ' + name)


def validate_presentation(name: str, source: str, text: str, record: dict) -> None:
    if record.get('status') != 'reviewed' or not record.get('reviewer'):
        raise LocalizationError('Presentation requires review: ' + name)
    if record.get('source_sha256') != sha(source):
        raise LocalizationError('Stale presentation input: ' + name)
    if record.get('translation_sha256') != sha(text):
        raise LocalizationError('Presentation bytes changed without review: ' + name)
    validate_presentation_contract(name, source, text)


def presentation(name: str) -> str:
    source = presentation_source(name)
    text = presentation_file(name).read_text(encoding='utf-8')
    record = catalog().get('presentations', {}).get(name, {})
    validate_presentation(name, source, text, record)
    return text


def restore_template(name: str, actual: str) -> str:
    """Exact, whole-artifact comparison adapter; never rewrite arbitrary prose.

    A mismatch is a failure, not a candidate for substring translation or an
    ignore rule. The original English artifact still undergoes independent CLI
    baseline comparison after this presentation-only projection.
    """
    if name not in TEMPLATES or actual != presentation(name):
        raise LocalizationError('Deployed template differs from reviewed bytes: ' + name)
    return presentation_source(name)


def localized_binding(host: str) -> str:
    if host not in HOSTS:
        raise LocalizationError('Unknown host: ' + host)
    detail = ('优先使用宿主替换的 `${CLAUDE_PLUGIN_ROOT}`，或已加载 SKILL.md 的绝对路径。'
              if host == 'claude' else '使用已加载 SKILL.md 的绝对路径，不假定宿主专用环境变量存在。')
    return resource('binding').replace('@HOST@', host).replace('@ROOT_DETAIL@', detail)


def localized_workflow(name: str, host: str) -> str:
    return localized_binding(host) + resource('output-language') + translate_body(name, host)


def check_all() -> dict:
    data = catalog()
    for item in RESOURCES:
        resource(item)
    expected_presentations = set(TEMPLATES) | {'requirements'}
    if set(data.get('presentations', {})) != expected_presentations:
        raise LocalizationError('Presentation inventory differs from reviewed templates')
    for name in sorted(expected_presentations):
        presentation(name)
    checked = []
    for name in COMMANDS:
        for host in HOSTS:
            translate_body(name, host)
            from naming import product_prose
            meta,_ = render_source((ROOT/'src/upstream/templates/commands'/(name+'.md')).read_text(),name,host)
            for key in ('description','argument-hint'):
                if key in meta:meta[key]=product_prose(meta[key])
            translated_metadata(name,meta)
        checked.append(name)
    return {'status': 'PASS', 'locale': 'zh-CN', 'commands': checked, 'templates': list(TEMPLATES), 'fragments': ['requirements'],
            'scope': 'source freshness, reviewed bytes and localization-contract-v2 machine/structure checks; not proof of model behavior'}


def record_review(name: str, reviewer: str, *, is_resource: bool = False, is_presentation: bool = False) -> dict:
    """Explicit authoring step only; never called by build, install or upgrade.

    This records a maintainer/AI review declaration, not an authenticated identity.
    Machine/structure contracts and metadata input correspondences are still enforced.
    """
    if not reviewer.strip():
        raise LocalizationError('A nonempty review declaration is required')
    data = catalog()
    if is_presentation:
        source = presentation_source(name)
        text = presentation_file(name).read_text(encoding='utf-8')
        rec = dict(data.get('presentations', {}).get(name, {}))
        rec.update(source_sha256=sha(source),translation_sha256=sha(text),status='reviewed',reviewer=reviewer)
        validate_presentation(name,source,text,rec)
        data.setdefault('presentations', {})[name] = rec
    elif is_resource:
        if name not in RESOURCES:
            raise LocalizationError('Unknown local resource')
        rec = dict(data['resources'][name])
        text = (LOCALES / (name + '.md')).read_text(encoding='utf-8')
        validate_resource_contract(name, text)
        if 'source' in rec:
            rec['source_sha256'] = sha((ROOT / rec['source']).read_text(encoding='utf-8'))
        rec.update(translation_sha256=sha(text),status='reviewed',reviewer=reviewer)
        data['resources'][name] = rec
    else:
        if name not in COMMANDS:
            raise LocalizationError('Unknown core command')
        rec = dict(data['commands'][name])
        source = canonical_source(name)
        text = (LOCALES / 'workflows' / (name + '.md')).read_text(encoding='utf-8')
        rec.update(source_sha256=sha(source),translation_sha256=sha(text),status='reviewed',reviewer=reviewer)
        validate_translation(name,source,text,rec)
        # Changed metadata requires deliberate source/value editing too; do not
        # silently attach an old Chinese description to a new English meaning.
        from naming import product_prose
        original,_ = render_source((ROOT / 'src/upstream/templates/commands' / (name+'.md')).read_text(),name,'claude')
        for key in ('description',):
            if key in original:
                entry = rec.get('metadata',{}).get(key,{})
                if entry.get('source') != product_prose(original[key]) or not entry.get('zh_CN'):
                    raise LocalizationError('Review changed metadata before recording: ' + name + '/' + key)
        data['commands'][name] = rec
    (LOCALES / 'catalog.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return rec


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    sub.add_parser('check')
    ex = sub.add_parser('export', help='Write current English inputs to an external directory for incremental review')
    ex.add_argument('--out', type=Path, required=True)
    pre = sub.add_parser('precheck', help='Read-only machine/structure validation before recording a review')
    pre_group = pre.add_mutually_exclusive_group(required=True)
    pre_group.add_argument('--command', choices=COMMANDS)
    pre_group.add_argument('--resource', choices=RESOURCES)
    pre_group.add_argument('--presentation', choices=(*TEMPLATES, 'requirements'))
    review = sub.add_parser('record', help='Record an explicit completed translation review; never auto-called')
    group = review.add_mutually_exclusive_group(required=True)
    group.add_argument('--command', choices=COMMANDS)
    group.add_argument('--resource', choices=RESOURCES)
    group.add_argument('--presentation', choices=(*TEMPLATES, 'requirements'))
    review.add_argument('--reviewer', required=True)
    review.add_argument('--reviewed', action='store_true', required=True)
    args = p.parse_args()
    if args.action == 'precheck':
        print(json.dumps(precheck_review(args.command or args.resource or args.presentation,
            is_resource=bool(args.resource), is_presentation=bool(args.presentation)),
            ensure_ascii=False, indent=2))
        return 0
    if args.action == 'record':
        print(json.dumps(record_review(args.command or args.resource or args.presentation,args.reviewer,is_resource=bool(args.resource),is_presentation=bool(args.presentation)),ensure_ascii=False,indent=2))
        return 0
    if args.action == 'check':
        print(json.dumps(check_all(), ensure_ascii=False, indent=2))
    else:
        out = args.out.resolve()
        if out == ROOT or ROOT in out.parents or out.exists():
            p.error('Select a NEW external output directory')
        out.mkdir(parents=True)
        for name in COMMANDS:
            text = canonical_source(name)
            (out / (name + '.md')).write_text(text, encoding='utf-8')
        (out/'templates').mkdir()
        for name in (*TEMPLATES,'requirements'):
            (out/'templates'/(name+'.md')).write_text(presentation_source(name),encoding='utf-8')
        print('Exported current inputs; no catalog or accepted translation was changed:', out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

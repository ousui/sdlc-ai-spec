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


def protected_spans(text: str) -> Counter:
    """Keep code fences and inline-code contracts byte-for-byte, including order counts."""
    spans = []
    def fence(match):
        spans.append(('fence', match[0]))
        return '\n'
    rest = re.sub(r'(?m)^([ \t]*)```[^\n]*\n[\s\S]*?^\1```[^\n]*(?:\n|$)', fence, text)
    spans.extend(('inline', x) for x in re.findall(r'`[^`\n]+`', rest))
    spans.extend(('token', x) for x in TOKEN.findall(text))
    return Counter(spans)


def validate_translation(name: str, source: str, translated: str, record: dict) -> None:
    if record.get('status') != 'reviewed' or not record.get('reviewer'):
        raise LocalizationError('Translation requires review: ' + name)
    if record.get('source_sha256') != sha(source):
        raise LocalizationError('Stale translation input: ' + name + '; run tools/localize.py export')
    if record.get('translation_sha256') != sha(translated):
        raise LocalizationError('Translation bytes changed without review: ' + name)
    fences = r'(?m)^([ \t]*)```[^\n]*\n[\s\S]*?^\1```[^\n]*(?:\n|$)'
    if [m[0] for m in re.finditer(fences,source)] != [m[0] for m in re.finditer(fences,translated)]:
        raise LocalizationError('Protected code block order changed: ' + name)
    if protected_spans(source) != protected_spans(translated):
        raise LocalizationError('Protected code/placeholder mismatch: ' + name)
    source_levels = re.findall(r'(?m)^(#{1,6}) ', source)
    target_levels = re.findall(r'(?m)^(#{1,6}) ', translated)
    if source_levels != target_levels:
        raise LocalizationError('Workflow heading hierarchy changed: ' + name)
    if not re.search(r'[\u4e00-\u9fff]', translated):
        raise LocalizationError('Missing Chinese workflow prose: ' + name)


def catalog() -> dict:
    try:
        data = json.loads((LOCALES / 'catalog.json').read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise LocalizationError('Missing or invalid zh-CN catalog') from error
    if data.get('schema_version') != 1 or set(data.get('commands', {})) != set(COMMANDS):
        raise LocalizationError('Localization inventory differs from upstream core profile')
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


def resource(name: str) -> str:
    if name not in RESOURCES:
        raise LocalizationError('Unknown local resource: ' + name)
    rec = catalog().get('resources', {}).get(name, {})
    text = (LOCALES / (name + '.md')).read_text(encoding='utf-8')
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
    """Structural/machine constraints, independent of a translation's stored digest.

    This is not semantic equivalence proof. Natural-language conditions are
    reviewed against the bound source; no blanket normalization of runtime output.
    """
    code = []
    for match in re.finditer(r'(?m)^```([^\n]*)\n([\s\S]*?)^```\s*$', text):
        payload = []
        for line in match[2].splitlines():
            # Here only template/example comments are presentation, not code.
            line = re.split(r'(?<!\S)#', line, maxsplit=1)[0].rstrip()
            if re.fullmatch(r'[│ └─├]*\[[^\]]+\]', line):
                line = '<human-tree-placeholder>'
            payload.append(line)
        code.append((match[1], payload))
    return {
        'tokens': Counter(TOKEN.findall(text)),
        'machine_slots': Counter(re.findall(r'\[[A-Z][A-Z0-9_ ?-]*\]|\[NEEDS CLARIFICATION(?=[:\]])', text)),
        'inline': Counter(re.findall(r'`[^`\n]+`', text)),
        'labels': re.findall(r'\*\*([^*\n]+)\*\*:', text),
        'checkboxes': re.findall(r'(?m)^\s*- \[[ xX]\](?: (?:T\d+|TXXX|CHK\d+)(?: \[[A-Z0-9]+\])*)?', text),
        'paths': Counter(re.findall(r'(?<![\w/])(?:\.sdlc|src|tests|backend|frontend|ios|android|api|docs|contracts)/(?:[A-Za-z0-9_./\[\]#-]*)', text)),
        'task_refs': Counter(re.findall(r'\b(?:T\d{3,}|TXXX|CHK\d{3,}|FR-\d+|SC-\d+)\b', text)),
        'code': code,
        'levels': re.findall(r'(?m)^(#{1,6}) ', text),
    }


def validate_presentation(name: str, source: str, text: str, record: dict) -> None:
    if record.get('status') != 'reviewed' or not record.get('reviewer'):
        raise LocalizationError('Presentation requires review: ' + name)
    if record.get('source_sha256') != sha(source):
        raise LocalizationError('Stale presentation input: ' + name)
    if record.get('translation_sha256') != sha(text):
        raise LocalizationError('Presentation bytes changed without review: ' + name)
    if presentation_contract(source) != presentation_contract(text):
        raise LocalizationError('Presentation machine/structure contract changed: ' + name)
    def headings(value):
        value = re.sub(r'(?m)^```[^\n]*\n[\s\S]*?^```[^\n]*$', '', value)
        return re.findall(r'(?m)^#{1,6} (.+)', value)
    originals = headings(source)
    translated = headings(text)
    if any(not new.startswith(old) for old,new in zip(originals, translated)):
        raise LocalizationError('Template heading anchor changed: ' + name)
    if not re.search(r'[\u4e00-\u9fff]', text):
        raise LocalizationError('Missing Chinese presentation: ' + name)
    if re.search(r'中文(?:注释|说明|版本)', text) or '\ufffc' in text:
        raise LocalizationError('Language label/object character in presentation: ' + name)


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
            'scope': 'source freshness, reviewed bytes, protected spans and structural checks; not proof of model behavior'}


def record_review(name: str, reviewer: str, *, is_resource: bool = False, is_presentation: bool = False) -> dict:
    """Explicit authoring step only; never called by build, install or upgrade.

    This records a maintainer/AI review declaration, not an authenticated identity.
    All protected spans and metadata input correspondences are still enforced.
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
    review = sub.add_parser('record', help='Record an explicit completed translation review; never auto-called')
    group = review.add_mutually_exclusive_group(required=True)
    group.add_argument('--command', choices=COMMANDS)
    group.add_argument('--resource', choices=RESOURCES)
    group.add_argument('--presentation', choices=(*TEMPLATES, 'requirements'))
    review.add_argument('--reviewer', required=True)
    review.add_argument('--reviewed', action='store_true', required=True)
    args = p.parse_args()
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

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
    values = replacements(host)
    result = TOKEN.sub(lambda m: values[m[0]], translated)
    if '{{SDLC:' in result:
        raise LocalizationError('Unresolved localization token: ' + name)
    return result


def translated_metadata(name: str, source_meta: dict) -> dict:
    record = catalog()['commands'][name]
    meta = dict(source_meta)
    expected = {k: source_meta[k] for k in ('description', 'argument-hint') if k in source_meta}
    for key, original in expected.items():
        entry = record.get('metadata', {}).get(key)
        if not entry or entry.get('source') != original or not entry.get('zh_CN'):
            raise LocalizationError('Missing/stale metadata translation: ' + name + '/' + key)
        meta[key] = entry['zh_CN']
    return meta


def resource(name: str) -> str:
    if name not in ('binding', 'init', 'output-language'):
        raise LocalizationError('Unknown local resource: ' + name)
    rec = catalog().get('resources', {}).get(name, {})
    text = (LOCALES / (name + '.md')).read_text(encoding='utf-8')
    if rec.get('status') != 'reviewed' or not rec.get('reviewer') or rec.get('translation_sha256') != sha(text):
        raise LocalizationError('Unreviewed localized resource: ' + name)
    if 'source' in rec and rec.get('source_sha256') != sha((ROOT / rec['source']).read_text(encoding='utf-8')):
        raise LocalizationError('Stale localized resource: ' + name)
    return text


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
    for item in ('binding', 'init', 'output-language'):
        resource(item)
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
    return {'status': 'PASS', 'locale': 'zh-CN', 'commands': checked,
            'scope': 'source freshness, reviewed bytes, protected spans and structural checks; not proof of model behavior'}


def record_review(name: str, reviewer: str, *, is_resource: bool = False) -> dict:
    """Explicit authoring step only; never called by build, install or upgrade.

    This records a maintainer/AI review declaration, not an authenticated identity.
    All protected spans and metadata input correspondences are still enforced.
    """
    if not reviewer.strip():
        raise LocalizationError('A nonempty review declaration is required')
    data = catalog()
    if is_resource:
        if name not in ('binding', 'init', 'output-language'):
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
        for key in ('description','argument-hint'):
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
    group.add_argument('--resource', choices=('binding','init','output-language'))
    review.add_argument('--reviewer', required=True)
    review.add_argument('--reviewed', action='store_true', required=True)
    args = p.parse_args()
    if args.action == 'record':
        print(json.dumps(record_review(args.command or args.resource,args.reviewer,is_resource=bool(args.resource)),ensure_ascii=False,indent=2))
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
        print('Exported current inputs; no catalog or accepted translation was changed:', out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

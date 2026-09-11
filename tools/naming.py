"""Deterministic naming projection; see docs/NAMING.md before upstream upgrades.

Raw upstream bytes/IDs remain provenance. Only generated product surfaces use
this mapping. Never substitute a whole English word with a product identifier,
normalize away business prose, or infer a new stage name from an unknown ID.
The installed runtime does not read docs/ or import this build-time module.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / 'docs/naming-map.json').read_text(encoding='utf-8'))
PRODUCT_ID = CONTRACT['product']['target_plugin_id']
DISPLAY_NAME = CONTRACT['product']['display_name']
SKILL_IDS = {s['source_id']: s['target_id'] for s in CONTRACT['skills'] if s['existing_capability']}
if (len(SKILL_IDS) != 10 or len(set(SKILL_IDS.values())) != 10
        or any(not re.fullmatch(r'sdlc-\d{3}-[a-z]{4}', value) for value in SKILL_IDS.values())):
    raise ValueError('Invalid approved skill inventory; review docs/NAMING.md')

IDENTIFIERS = dict(CONTRACT['identifier_examples'],
    format_speckit_command='format_sdlc_command',
    SPECKIT_EXTENSIONS='SDLC_EXTENSIONS', SPECKIT_REGISTRY='SDLC_REGISTRY',
    SPECKIT_MANIFEST='SDLC_MANIFEST', SPECKIT_TMPL='SDLC_TMPL')


def skill_id(source: str) -> str:
    try:
        return SKILL_IDS[source]
    except KeyError as error:
        raise ValueError('Unmapped source capability: ' + source) from error


def invocation(source: str, host: str) -> str:
    if host not in ('codex', 'claude', 'cursor'):
        raise ValueError('Unsupported host: ' + host)
    prefix = '$' if host == 'codex' else '/' + (PRODUCT_ID + ':' if host == 'claude' else '')
    return prefix + skill_id(source)


def identifiers(text: str) -> str:
    pattern = r'(?<![\w])(' + '|'.join(map(re.escape, sorted(IDENTIFIERS, key=len, reverse=True))) + r')(?![\w])'
    text = re.sub(pattern, lambda m: IDENTIFIERS[m[0]], text)
    unknown = re.search(r'\b(?:SPECIFY|SPECKIT)_[A-Z_]+\b|\b\w*specify\w*\(\)', text)
    if unknown:
        raise ValueError('Unmapped runtime identifier: ' + unknown[0])
    return text


def product_prose(text: str) -> str:
    # Finite phrases, not a case-insensitive substitution of every English verb.
    for old, new in (
        ('Spec Kit', DISPLAY_NAME), ('spec-kit', PRODUCT_ID),
        ('[specify]', '[sdlc]'),
        ('before_specify', 'before_spec'), ('after_specify', 'after_spec'),
        ('the specify command', 'the sdlc-100-spec command'),
        ('by specify command', 'by sdlc-100-spec command'),
        ('or specify a different number', 'or choose a different number'),
        ('did not specify certain details', 'did not define certain details'),
        ('feature you want to specify', 'feature you want to define'),
    ):
        text = text.replace(old, new)
    return text


def capability_references(text: str) -> str:
    # Only known public aliases are rewritten. Unknown new upstream capabilities
    # must fail in source placeholder rendering, not silently become new skills.
    names = '|'.join(map(re.escape, sorted(SKILL_IDS, key=len, reverse=True)))
    return re.sub(r'(?<![\w-])sdlc-(' + names + r')(?![\w-])',
                  lambda m: skill_id(m[1]), text)


def template_references(text: str) -> str:
    return re.sub(r'__SPECKIT_COMMAND_([A-Z][A-Z0-9_-]*)__',
                  lambda m: skill_id(m[1].lower().replace('_', '-')), product_prose(text))


def script_projection(text: str) -> str:
    text = identifiers(text)
    text = re.sub(r'\bformat_sdlc_command ([a-z][a-z-]*)',
                  lambda m: 'format_sdlc_command ' + skill_id(m[1]), text)
    return capability_references(product_prose(text))


def invocation_adapter() -> str:
    template = (ROOT / 'adapters/invocation-functions.sh').read_text(encoding='utf-8')
    if template.count('@SKILL_CASES@') != 1:
        raise ValueError('Invocation adapter mapping anchor changed')
    cases = '|'.join(SKILL_IDS.values())
    return template.replace('@SKILL_CASES@', cases).replace('@PLUGIN_ID@', PRODUCT_ID)


def audit_package(package: Path) -> None:
    """Reject residual product markers, allowing only documented provenance lines."""
    import yaml
    legacy = re.compile(r'specify|spec[- ]kit|speckit', re.I)
    old_command = re.compile(r'(?<![\w.-])sdlc-(?:' + '|'.join(SKILL_IDS) + r')(?![\w-])')
    exceptions = {
        'scripts/python/init_project.py': {
            "    if (root / '.specify').exists() or (root / '.specify').is_symlink():",
            "        raise ValueError('Existing .specify requires explicit migration; no files were changed')",
            "                'speckit_version': provenance['version'],",
        },
        'scripts/bash/common.sh': {
            '    for legacy in ${!SPECIFY_@}; do',
            '            echo "ERROR: Obsolete $legacy; use SDLC_${legacy#SPECIFY_} instead" >&2',
        },
        'README.md': {
            'Based on Spec Kit by GitHub, Inc. (MIT), an independent source port. See LICENSE, NOTICE, UPSTREAM.json and BUILD.json.',
        },
    }
    for path in package.rglob('*'):
        if not path.is_file():
            continue
        relative = path.relative_to(package).as_posix()
        if relative in ('LICENSE', 'NOTICE', 'UPSTREAM.json', 'BUILD.json'):
            continue  # origin/lock/build records, never executable instructions
        text = path.read_text(encoding='utf-8')
        if path.name == 'SKILL.md':
            _, front, body = text.split('---', 2)
            meta = yaml.safe_load(front)
            origin = meta.get('metadata', {})
            meta['metadata'] = {k: v for k, v in origin.items() if k not in ('author', 'source')}
            text = yaml.safe_dump(meta) + body
        for line in text.splitlines():
            if line in exceptions.get(relative, set()):
                continue
            if legacy.search(line) or old_command.search(line):
                raise ValueError(f'Residual product name in {relative}: {line[:180]}')

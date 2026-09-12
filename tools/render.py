#!/usr/bin/env python3
"""Render original source and explicit host address adaptations.

The renderer is the sh/SkillsIntegration subset of upstream base.py and
agents.py. verify.py independently checks it against installed-CLI outputs.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

import yaml
from naming import (skill_id, invocation, identifiers, product_prose, capability_references)

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = ('constitution', 'specify', 'clarify', 'plan', 'tasks', 'analyze',
            'checklist', 'implement', 'converge')
HOSTS = ('codex', 'claude', 'cursor')
LOCK = json.loads((ROOT / 'upstream.lock.json').read_text(encoding='utf-8'))
UPSTREAM_SHA = LOCK['commit']
# Product metadata is independent from upstream provenance and Git transport.
METADATA = json.loads((ROOT / 'plugin-metadata.json').read_text(encoding='utf-8'))
REPOSITORY = METADATA['repository']
VERSION = METADATA['version']
AUTHOR = METADATA['author']
HINTS = {
    'specify': 'Describe the feature you want to specify',
    'plan': 'Optional guidance for the planning phase',
    'tasks': 'Optional task generation constraints',
    'implement': 'Optional implementation guidance or task filter',
    'analyze': 'Optional focus areas for analysis',
    'clarify': 'Optional areas to clarify in the spec',
    'constitution': 'Principles or values for the project constitution',
    'checklist': 'Domain or focus area for the checklist',
}
HOOK_NOTE = ('- When constructing command invocations from hook command names, '
             'replace dots (`.`) with hyphens (`-`). '
             'For example, `speckit.git.commit` → `{prefix}speckit-git-commit`.\n')


def split(text: str) -> tuple[dict, str]:
    match = re.match(r'\A---\r?\n(.*?)\r?\n---(\r?\n.*)\Z', text, re.S)
    if not match:
        raise ValueError('Missing or malformed frontmatter')
    meta = yaml.safe_load(match[1])
    if not isinstance(meta, dict):
        raise ValueError('Frontmatter must be a mapping')
    return meta, match[2].replace('\r\n', '\n')


def command_refs(text: str, host: str, *, ported: bool = False) -> str:
    for source in re.findall(r'__SPECKIT_COMMAND_([A-Z][A-Z0-9_-]*)__', text):
        if source == 'STATUS':
            raise ValueError('STATUS is local, not an upstream reference')
        skill_id(source.lower().replace('_', '-'))  # unknown upstream reference fails closed
    prefix = '$' if host == 'codex' else '/'
    namespace = METADATA['name'] + ':sdlc-' if ported and host == 'claude' else ('sdlc-' if ported else 'speckit-')
    return re.sub(r'__SPECKIT_COMMAND_([A-Z][A-Z0-9_-]*)__',
                  lambda m: (invocation(m[1].lower().replace('_', '-'), host) if ported else prefix + namespace + m[1].lower().replace('_', '-')), text)


def upstream_paths(text: str) -> str:
    # Literal copy of the relevant upstream path boundary rules.
    for part in ('memory', 'scripts', 'templates'):
        text = text.replace('../../' + part + '/', '.specify/' + part + '/')
        text = re.sub(r'''(^|[\s`"'(])(?:\.?/)?''' + part + '/',
                      lambda m: m[1] + '.specify/' + part + '/', text)
    return text.replace('.specify/.specify/', '.specify/').replace('.specify.specify/', '.specify/')


def render_source(raw: str, name: str, host: str) -> tuple[dict, str]:
    """Render original English source independently of specify-cli."""
    fm, body = split(raw)
    scripts = fm.get('scripts', {})
    if scripts:
        if 'sh' not in scripts:
            raise ValueError(f'{name}: no reviewed sh variant')
        body = body.replace('{SCRIPT}', scripts['sh'])
    body = body.replace('{ARGS}', '$ARGUMENTS').replace('__AGENT__', 'cursor-agent' if host == 'cursor' else host)
    body = upstream_paths(body)
    body = command_refs(body, host)
    prefix = '$' if host == 'codex' else '/'
    note = HOOK_NOTE.format(prefix=prefix).rstrip('\n')
    body = re.sub(r'(?m)^([ \t]*)(- For each executable hook, output the following[^\r\n]*)(\n|$)',
                  lambda m: m[1] + note + '\n' + m[1] + m[2] + (m[3] or '\n'), body)
    meta = {
        'name': 'speckit-' + name,
        'description': fm['description'],
        'compatibility': 'Requires spec-kit project structure with .specify/ directory',
        'metadata': {'author': 'github-spec-kit', 'source': 'templates/commands/' + name + '.md'},
    }
    if host == 'claude':
        meta.update({'user-invocable': True, 'disable-model-invocation': False})
        if name in HINTS:
            meta['argument-hint'] = HINTS[name]
    # Upstream's SkillsIntegration adds one newline after rebuilding frontmatter.
    return meta, '\n' + body


def relocate_body(body: str, host: str) -> str:
    """Only name/path/executable-reference changes; preserve all prose."""
    # Alias replacement is deliberately scoped, never replace the English word 'specify'.
    body = body.replace('$speckit-', '$sdlc-')
    for old in ('/speckit-', '/speckit.'):
        prefix = '/' + METADATA['name'] + ':sdlc-' if host == 'claude' else '/sdlc-'
        body = body.replace(old, prefix)
    body = body.replace('`speckit.git.commit`', '`sdlc.git.commit`')
    body = body.replace('/skill:speckit-', '/skill:sdlc-')
    body = body.replace('.specify/', '.sdlc/')
    # specs is a project data path, not an install resource.
    body = re.sub(r'(?<![\w./])/?specs/', '.sdlc/specs/', body)
    script_prefix = (f'SDLC_HOST={host} SPECIFY_INIT_DIR="${{SDLC_PROJECT_ROOT:?}}" '
                     'bash "${SDLC_PLUGIN_ROOT:?}/scripts/bash/')
    body = re.sub(r'\.sdlc/scripts/bash/([a-z-]+\.sh)', lambda m: script_prefix + m[1] + '"', body)
    body = body.replace('`specify preset resolve spec-template`',
                        '`' + script_prefix + 'resolve-template-path.sh" spec-template`')
    body = re.sub(r'\.sdlc/templates/(?!overrides/)([a-z-]+\.md)',
                  r'${SDLC_PLUGIN_ROOT}/templates/\1', body)
    return capability_references(product_prose(identifiers(body)))


def binding(host: str) -> str:
    template = (ROOT/'adapters'/'BINDING.md').read_text()
    detail = ('Use the host-provided `${CLAUDE_PLUGIN_ROOT}` or the absolute path of this loaded SKILL.md.'
              if host == 'claude' else
              'Use the absolute path of this loaded SKILL.md; do not assume a host-specific plugin-root environment variable exists.')
    return template.replace('@HOST@', host).replace('@ROOT_DETAIL@', detail)

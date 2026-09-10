#!/usr/bin/env python3
"""Build nine skills from source; no specify-cli or initialized project is used.

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

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = ('constitution', 'specify', 'clarify', 'plan', 'tasks', 'analyze',
            'checklist', 'implement', 'converge')
HOSTS = ('codex', 'claude', 'cursor')
UPSTREAM_SHA = 'a4e25ce6b96dc8e85f84206c6a54353fa9c5260b'
REPOSITORY = 'https://github.com/ousui/sdlc-ai-spec'
VERSION = '0.0.0-engineering.1'
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
    prefix = '$' if host == 'codex' else '/'
    namespace = 'sdlc:sdlc-' if ported and host == 'claude' else ('sdlc-' if ported else 'speckit-')
    return re.sub(r'__SPECKIT_COMMAND_([A-Z][A-Z0-9_-]*)__',
                  lambda m: prefix + namespace + m[1].lower().replace('_', '-'), text)


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
        prefix = '/sdlc:sdlc-' if host == 'claude' else '/sdlc-'
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
                        '`' + script_prefix + 'resolve-template.sh" spec-template`')
    body = re.sub(r'\.sdlc/templates/(?!overrides/)([a-z-]+\.md)',
                  r'${SDLC_PLUGIN_ROOT}/templates/\1', body)
    return body


def binding(host: str) -> str:
    template = (ROOT/'adapters'/'BINDING.md').read_text()
    detail = ('Use the host-provided `${CLAUDE_PLUGIN_ROOT}` or the absolute path of this loaded SKILL.md.'
              if host == 'claude' else
              'Use the absolute path of this loaded SKILL.md; do not assume a host-specific plugin-root environment variable exists.')
    return template.replace('@HOST@', host).replace('@ROOT_DETAIL@', detail)


def build(destination: Path) -> None:
    destination = destination.resolve()
    if destination == ROOT or destination == ROOT/'src' or ROOT.is_relative_to(destination):
        raise ValueError('Refusing unsafe build destination')
    if destination.exists():
        # Only remove directories previously produced by this builder.
        marker = destination/'.sdlc-build'
        if not marker.is_file() or marker.read_text().strip() != UPSTREAM_SHA:
            raise ValueError(f'Refusing to replace unmarked directory: {destination}')
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    (destination/'.sdlc-build').write_text(UPSTREAM_SHA+'\n')
    for host in HOSTS:
        package = destination/host
        (package/'skills').mkdir(parents=True)
        shutil.copytree(ROOT/'src/scripts', package/'scripts', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        (package/'templates').mkdir()
        for template in sorted((ROOT/'src/templates').glob('*.md')):
            text = command_refs(template.read_text(), host, ported=True)
            (package/'templates'/template.name).write_text(text, encoding='utf-8')
        for name in COMMANDS:
            raw = (ROOT/'src/commands'/f'{name}.md').read_text()
            meta, body = render_source(raw, name, host)
            meta['name'] = 'sdlc-' + name
            meta['compatibility'] = 'Requires an initialized .sdlc project, Bash and Python 3.9+; INIT is not included in this engineering build'
            ported = relocate_body(body, host)
            skill = package/'skills'/('sdlc-'+name)/'SKILL.md'
            skill.parent.mkdir()
            front = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False, width=1000).rstrip()
            skill.write_text('---\n'+front+'\n---\n'+binding(host)+ported, encoding='utf-8')
        manifest = {
            'name': 'sdlc', 'version': VERSION,
            'description': 'Spec Kit core user-scoped source port (engineering build; no INIT skill)',
            'repository': REPOSITORY, 'license': 'MIT',
        }
        if host == 'claude':
            manifest_path = package/'.claude-plugin/plugin.json'
        else:
            manifest['$schema'] = 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json'
            manifest_path = package/'plugin.json'
        manifest_path.parent.mkdir(exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2)+'\n')
        shutil.copyfile(ROOT/'src/LICENSE', package/'LICENSE')
        (package/'UPSTREAM.json').write_text(json.dumps({
            'repository':'https://github.com/github/spec-kit', 'tag':'v1.0.5', 'commit':UPSTREAM_SHA,
            'port_repository':REPOSITORY, 'port_version':VERSION,
            'profile':{'script':'sh','events':False,'extensions':[],'presets':[]},
            'included_commands':list(COMMANDS), 'excluded_commands':['taskstoissues'],
            'init_implemented':False, 'native_host_verified':False,
        }, indent=2)+'\n')
        (package/'README.md').write_text(
            '# SDLC engineering package\n\n'
            'Fixed repository: '+REPOSITORY+'\n\n'
            'Source port of Spec Kit v1.0.5. Nine local skills; no INIT, GitHub, '
            'translation, workflow engine or event hooks. This package is not yet an '
            'end-user release. Only engineering/fixture checks are claimed. Native '
            'host discovery and real-project behavior have not been tested.\n\n'
            'Requires Bash and Python 3.9+ plus standard POSIX tools. Core resources '
            'stay in this package; project data belongs in .sdlc. No uv/specify-cli '
            'is needed at runtime. Plugin location must be obtained from the loaded '
            'skill path (or the documented Claude plugin variable), never stored in '
            'project metadata. Missing project state is an error, not automatic init.\n'
        )
        for script in (package/'scripts').rglob('*.sh'):
            script.chmod(0o755)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'dist')
    args=parser.parse_args()
    build(args.out)
    print('Built:',args.out)

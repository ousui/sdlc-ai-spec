#!/usr/bin/env python3
"""Materialize source files from a reviewed pinned upstream; no CLI invocation.

This is a build-time maintainer tool, never shipped as a runtime initializer.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path
from build import ROOT,COMMANDS,UPSTREAM_SHA
import shutil
import tempfile
from naming import script_projection, template_references, invocation_adapter


def replace_once(text: str, old: str, new: str, count: int = 1) -> str:
    actual=text.count(old)
    if actual!=count:
        raise ValueError(f'Patch anchor changed ({actual} != {count}): {old[:90]}')
    return text.replace(old,new)


def function(text: str, name: str, replacement: str) -> str:
    pattern=r'(?ms)^'+re.escape(name)+r'\(\) \{.*?^\}\n'
    matches=list(re.finditer(pattern,text))
    if len(matches)!=1:
        raise ValueError(f'Expected one function {name}, got {len(matches)}')
    return text[:matches[0].start()]+replacement.rstrip()+'\n'+text[matches[0].end():]


def port_script(name: str,text: str) -> str:
    text=text.replace('.specify','.sdlc')
    if name=='common.sh':
        text=function(text,'get_repo_root',(ROOT/'src/adapters/path-functions.sh').read_text())
        text=function(text,'get_invoke_separator','')
        text=function(text,'format_speckit_command',invocation_adapter())
        text=replace_once(text,'    local fj="$repo_root/.sdlc/feature.json"\n\n    # Strip',
            '    local fj="$repo_root/.sdlc/feature.json"\n    _sdlc_validate_paths "$repo_root" "$feature_dir_value" || return 1\n\n    # Strip')
        text=replace_once(text,'            _persist_feature_json "$repo_root" "$SPECIFY_FEATURE_DIRECTORY"',
            '            _persist_feature_json "$repo_root" "$SPECIFY_FEATURE_DIRECTORY" || return 1')
        text=replace_once(text,'    # When no branch context exists',
            '    _sdlc_validate_paths "$repo_root" "$feature_dir" || return 1\n\n    # When no branch context exists')
        text=replace_once(text,'local core="$base/${template_name}.md"',
            'local core="$(_sdlc_plugin_root)/templates/${template_name}.md"',count=2)
    elif name=='create-new-feature.sh':
        text=replace_once(text,'SPECS_DIR="$REPO_ROOT/specs"','SPECS_DIR="$REPO_ROOT/.sdlc/specs"')
        text=replace_once(text,'SPEC_FILE="$FEATURE_DIR/spec.md"',
            'SPEC_FILE="$FEATURE_DIR/spec.md"\n_sdlc_validate_paths "$REPO_ROOT" "$FEATURE_DIR" || exit 1')
    elif name=='setup-tasks.sh':
        text=replace_once(text,"or run 'specify init' / reinstall shared infra to restore the core .sdlc/templates/tasks-template.md template.",
            'or reinstall the SDLC AI SPEC plugin to restore its templates/tasks-template.md template.')
    # docs/NAMING.md: preserve raw inputs; project all declarations and callers.
    return script_projection(text)


WATCHED = (
    'pyproject.toml', 'src/specify_cli/integrations/base.py', 'src/specify_cli/agents.py',
    'src/specify_cli/integrations/codex/__init__.py',
    'src/specify_cli/integrations/claude/__init__.py',
    'src/specify_cli/integrations/cursor_agent/__init__.py',
    'src/specify_cli/_invocation_style.py', 'src/specify_cli/events.py',
    'src/specify_cli/commands/init.py', 'src/specify_cli/shared_infra.py',
)


def record(data: bytes) -> dict:
    return {'git_blob': hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest(),
            'sha256': hashlib.sha256(data).hexdigest()}


def materialize(upstream: Path) -> dict:
    """Validate ALL inputs before staging; never rewrite the accepted lock."""
    upstream = upstream.resolve()
    lock = json.loads((ROOT/'upstream.lock.json').read_text())
    selected = set(lock['files'])
    discovered = {'templates/commands/'+name+'.md' for name in COMMANDS}
    discovered.update('templates/'+f.name for f in (upstream/'templates').glob('*.md'))
    discovered.update('scripts/bash/'+f.name for f in (upstream/'scripts/bash').glob('*.sh'))
    discovered.add('LICENSE')
    if selected != discovered:
        raise ValueError('Upstream source inventory changed; prepare an upgrade candidate')
    inputs = {}
    for source, expected in {**lock['files'], **lock.get('watch_files', {})}.items():
        data = (upstream/source).read_bytes()
        if record(data) != expected:
            raise ValueError('Pinned upstream source mismatch: '+source)
        inputs[source] = data
    # Start with non-upstream helpers; stale imported resources are eliminated.
    with tempfile.TemporaryDirectory(prefix='.sdlc-port-', dir=ROOT.parent) as temp:
        staging = Path(temp)/'src'
        shutil.copytree(ROOT/'src', staging, ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        previous_scripts = list((staging/'upstream/scripts/bash').glob('*.sh'))
        for prior in previous_scripts:
            (staging/'scripts/bash'/prior.name).unlink(missing_ok=True)
        for path in ('upstream', 'commands', 'templates'):
            if (staging/path).exists(): shutil.rmtree(staging/path)
        # Drop removed imported scripts, but keep local helpers. Source inventory
        # is already validated; only known upstream-owned paths may be removed.
        for source in lock['files']:
            if source.startswith('scripts/bash/'):
                (staging/source).unlink(missing_ok=True)
        original = staging/'upstream'
        for source, data in inputs.items():
            target = original/source
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            if source.endswith('.sh'): target.chmod(0o755)
        for source in sorted(selected):
            if source.startswith('templates/commands/'):
                continue
            text = inputs[source].decode('utf-8')
            if source.startswith('scripts/bash/'):
                text = port_script(Path(source).name, text)
            elif source.startswith('templates/'):
                text = template_references(re.sub(r'(?<![\w./])/?specs/', '.sdlc/specs/', text))
            target = staging/source
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding='utf-8')
            if target.suffix == '.sh': target.chmod(0o755)
        backup = Path(temp)/'previous'
        (ROOT/'src').rename(backup)
        try:
            staging.rename(ROOT/'src')
        except BaseException:
            backup.rename(ROOT/'src')
            raise
    return lock


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--upstream',type=Path,required=True)
    args=p.parse_args()
    materialize(args.upstream)
    print('Source port materialized:',ROOT/'src')

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
    # Explicit storage extension: code root stays local; only state addresses move.
    if name == 'common.sh':
        text = text.replace('local fj="$repo_root/.sdlc/feature.json"',
                            'local fj\n    fj=$(_sdlc_feature_json "$repo_root") || return 1')
        text = text.replace('[[ -f "$repo_root/.sdlc/feature.json" ]]',
                            '[[ -f "$(_sdlc_feature_json "$repo_root")" ]]')
        text = replace_once(text, '[[ "$feature_dir" != /* ]] && feature_dir="$repo_root/$feature_dir"',
                            'feature_dir=$(_sdlc_feature_path "$repo_root" "$feature_dir") || return 1', count=2)
        text = replace_once(text, 'mkdir -p "$repo_root/.sdlc"', 'mkdir -p "$(dirname -- "$fj")"')
    if name == 'common.sh':
        text = function(text, '_persist_feature_json', '''_persist_feature_json() {
    local repo_root="$1"
    local feature_dir_value="$2"
    _sdlc_validate_paths "$repo_root" "$feature_dir_value" || return 1
    feature_dir_value=$(_sdlc_store feature --project "$repo_root" --value "$feature_dir_value" --field FEATURE_VALUE) || return 1
    # Preserve upstream parser fallback and unchanged-selection no-op semantics.
    local current_val
    current_val=$(read_feature_json_feature_directory "$repo_root")
    if [[ "$current_val" == "$feature_dir_value" ]]; then
        return 0
    fi
    _sdlc_store feature --project "$repo_root" --value "$feature_dir_value" --persist >/dev/null
}''')
    for var in ('repo_root', 'REPO_ROOT'):
        text = text.replace('$' + var + '/.sdlc', '$(_sdlc_state_dir "$' + var + '")')
    if name in ('create-new-feature.sh', 'setup-plan.sh', 'setup-tasks.sh'):
        if name == 'create-new-feature.sh':
            # This value was generated from the canonical code root, rather than
            # supplied by the caller. Retain upstream's project-relative record.
            text = replace_once(text, '_persist_feature_json "$REPO_ROOT" "$FEATURE_DIR"',
                                '_persist_feature_json "$REPO_ROOT" "${FEATURE_DIR#"$REPO_ROOT/"}"')
        # The child re-enters only with a lock token issued by the packaged runner.
        marker = 'source "$SCRIPT_DIR/common.sh"'
        wrapper = marker + '\n\nif [[ -z "${SDLC_STORE_LOCK_TOKEN:-}" ]]; then\n    exec python3 -I -B "$(_sdlc_plugin_root)/scripts/python/sdlc_store.py" run --script ' + name + ' -- "$@"\nfi\n_sdlc_store check-lock || exit 1'
        if name == 'create-new-feature.sh':
            wrapper = marker + '\n\nif [[ "$DRY_RUN" != true ]]; then' + wrapper[len(marker):] + '\nfi'
        text = replace_once(text, marker, wrapper)

    # docs/NAMING.md: preserve raw inputs; project all declarations and callers.
    return script_projection(text)


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

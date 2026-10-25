#!/usr/bin/env python3
"""Read-only path checks required by moving resources out of the project.

No project creation or state persistence. Worktree discovery uses read-only Git.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sdlc_store import resolve, feature_path as resolve_feature, validate_state, document_path


def inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def validate(plugin: Path, project: Path, feature: str | None = None) -> dict:
    if sys.version_info < (3, 9):
        raise ValueError('Python 3.9+ is required')
    plugin = plugin.resolve(strict=True)
    project = project.resolve(strict=True)
    if not project.is_dir() or inside(project, plugin):
        raise ValueError('Project must be a business directory outside the plugin')
    context = resolve(project, plugin=plugin)
    validate_state(context, selection=False, knowledge_aliases=True)
    state = Path(context['SDLC_DIR'])
    if not state.is_dir():
        raise ValueError('Missing initialized .sdlc directory; run sdlc-000-init explicitly for a new project')
    paths = [state, Path(context['FEATURE_JSON']), state/'init-options.json',
             state/'memory', state/'memory/constitution.md', state/'specs']
    feature_path = None
    documents = []
    if feature is not None:
        supplied = Path(feature)
        feature_path = resolve_feature(context, str(supplied))
        documents = [feature_path, *(feature_path/n for n in (
            'spec.md','plan.md','tasks.md','research.md','data-model.md',
            'quickstart.md','contracts','checklists'))]
        paths += documents
    for path in documents:
        document_path(context, path)
    for path in paths:
        # Artifact aliases must obey the same authority boundary as their directory,
        # including dangling links that a shell writer would otherwise create through.
        resolved = resolve_feature(context, str(path))
        if inside(resolved, plugin):
            raise ValueError(f'Project data path resolves inside the plugin: {path}')
        # A hardlink has no path relationship to the plugin, so resolve() cannot
        # detect it. Reject shared regular-file inodes before later workflow writes.
        if path.exists() and path.is_file() and path.stat().st_nlink != 1:
            raise ValueError(f'Refusing hardlinked project data: {path}')
    result = dict(context, PLUGIN_ROOT=str(plugin))
    if feature_path is not None:
        result['FEATURE_DIR'] = str(feature_path.resolve())
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plugin-root',required=True,type=Path)
    parser.add_argument('--project-root',required=True,type=Path)
    parser.add_argument('--feature')
    parser.add_argument('--json',action='store_true')
    args=parser.parse_args()
    try:
        result=validate(args.plugin_root,args.project_root,args.feature)
    except (OSError,ValueError,RuntimeError) as error:
        print(f'ERROR: {error}',file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result,ensure_ascii=False))
    return 0


if __name__=='__main__':
    raise SystemExit(main())

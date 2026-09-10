#!/usr/bin/env python3
"""Read-only path checks required by moving resources out of the project.

No project creation, state persistence, subprocess, network or package imports.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path


def inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def validate(plugin: Path, project: Path, feature: str | None = None) -> dict:
    if sys.version_info < (3, 9):
        raise ValueError('Python 3.9+ is required')
    plugin = plugin.resolve(strict=True)
    project = project.resolve(strict=True)
    if not project.is_dir() or inside(project, plugin):
        raise ValueError('Project must be a business directory outside the plugin')
    state = project/'.sdlc'
    if not state.is_dir() or state.is_symlink():
        raise ValueError('Missing initialized .sdlc directory or unsupported symlink; INIT is not included yet')
    paths = [state, state/'feature.json', state/'init-options.json',
             state/'memory', state/'memory/constitution.md', state/'specs']
    feature_path = None
    if feature is not None:
        supplied = Path(feature)
        feature_path = supplied if supplied.is_absolute() else project/supplied
        paths += [feature_path, *(feature_path/n for n in (
            'spec.md','plan.md','tasks.md','research.md','data-model.md',
            'quickstart.md','contracts','checklists'))]
    for path in paths:
        resolved = path.resolve()
        if inside(resolved, plugin):
            raise ValueError(f'Project data path resolves inside the plugin: {path}')
    result = {'PROJECT_ROOT':str(project),'PLUGIN_ROOT':str(plugin)}
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

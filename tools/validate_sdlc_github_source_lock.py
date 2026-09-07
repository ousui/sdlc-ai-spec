#!/usr/bin/env python3
"""Build-time only: approved GitHub design and installed-source lock."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from packages.sdlc_runtime import ContractSource, build_source_lock, verify_source_lock
LOCK='skills/sdlc-github/references/source-lock.json'


def sources(root=ROOT):
    explicit={
        'approved-design': 'docs/plugin-development/work-items/sdlc-github/DESIGN.md',
        'approved-eval': 'docs/plugin-development/work-items/sdlc-github/EVAL-PLAN.md',
        'shared-interface': 'skills/_shared/contracts/skill-interface.md',
        'shared-execution': 'skills/_shared/contracts/skill-execution.md',
        'github-runtime': 'skills/_shared/contracts/github-runtime.md',
        'github-result': 'skills/_shared/schemas/github-result.schema.json',
        'local-paths': 'packages/sdlc_runtime/local_paths.py',
        'shared-parser': 'packages/sdlc_runtime/skill_args.py',
        'stdio-entry': 'scripts/sdlc_github_mcp.py',
        'codex-manifest': '.codex-plugin/plugin.json',
        'cursor-manifest': '.cursor-plugin/plugin.json',
        'claude-manifest': '.claude-plugin/plugin.json',
    }
    rows=[ContractSource('sdlc-ai-spec/github/source/'+key+'/v1','1',value) for key,value in explicit.items()]
    for relative in ('packages/sdlc_github','skills/sdlc-github','config/github'):
        for path in sorted((root/relative).rglob('*')):
            if '__pycache__' in path.parts or path.suffix in {'.pyc','.pyo'}:
                continue
            if path.is_symlink():raise ValueError('Linked source cannot be locked')
            if not path.is_file() or path.relative_to(root).as_posix()==LOCK:continue
            name=path.relative_to(root).as_posix()
            rows.append(ContractSource('sdlc-ai-spec/github/source/'+name+'/v1','1',name))
    return tuple(rows)


def validate(root=ROOT):
    verify_source_lock(root,json.loads((root/LOCK).read_text()),sources(root))
    return {'success':True,'skill':'sdlc-github','sources':len(sources(root))}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');a=p.parse_args()
    try:
        if a.write:
            (ROOT/LOCK).write_text(json.dumps(build_source_lock(ROOT,sources()),ensure_ascii=False,indent=2)+'\n')
            print('SOURCE_LOCK_GENERATED; run validation separately')
        else:print(json.dumps(validate()))
        return 0
    except (ValueError,OSError):
        print('GITHUB_SOURCE_LOCK_FAILED',file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())

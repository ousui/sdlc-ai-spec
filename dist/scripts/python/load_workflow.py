#!/usr/bin/env python3
"""Read-only, stdlib-only binding of precompiled workflow fragments.

Not an installer, interpreter for arbitrary templates, or workflow executor.
No subprocesses, network, project reads, file writes or AI calls.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

HOSTS = ('codex', 'claude', 'cursor')
SKILLS = ('constitution', 'specify', 'clarify', 'plan', 'tasks', 'analyze',
          'checklist', 'implement', 'converge')
TOKEN = re.compile(r'@@SDLC_BIND_\d{4}@@')


def contained_file(root: Path, relative: str) -> Path:
    file = (root / relative).resolve(strict=True)
    if root not in file.parents or not file.is_file():
        raise ValueError('Resource escapes plugin or is not a file: ' + relative)
    return file


def load(root: Path, host: str, skill: str) -> str:
    if host not in HOSTS or skill not in SKILLS:
        raise ValueError('Unsupported explicit host or skill')
    root = root.resolve(strict=True)
    text = contained_file(root, 'references/workflows/' + skill + '.md').read_text(encoding='utf-8')
    bindings = json.loads(contained_file(root, 'bindings/' + host + '.json').read_text(encoding='utf-8'))
    values = bindings[skill]
    if not isinstance(values, dict) or not all(isinstance(v, str) for v in values.values()):
        raise ValueError('Malformed binding values')
    if set(TOKEN.findall(text)) != set(values):
        raise ValueError('Missing or unexpected binding keys')
    result = TOKEN.sub(lambda m: values[m[0]], text)
    if '@@SDLC_BIND_' in result:
        raise ValueError('Unresolved/reserved binding token')
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', choices=HOSTS, required=True)
    parser.add_argument('--skill', choices=SKILLS, required=True)
    parser.add_argument('--offset', type=int, default=0, help='Zero-based line offset')
    parser.add_argument('--limit', type=int, help='Bounded page size if the host truncates tool output')
    args = parser.parse_args()
    if args.offset < 0 or (args.limit is not None and args.limit < 1):
        parser.error('offset must be >= 0 and limit must be > 0')
    try:
        text = load(Path(__file__).resolve().parents[2], args.host, args.skill)
        lines = text.splitlines(keepends=True)
        if args.offset > len(lines):
            raise ValueError('Offset exceeds total line count')
        end = len(lines) if args.limit is None else min(len(lines), args.offset + args.limit)
        print(f'WORKFLOW {args.host}/{args.skill}; lines {args.offset}:{end}/{len(lines)}', file=sys.stderr)
        sys.stdout.write(''.join(lines[args.offset:end]))
        return 0
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        print('ERROR: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""Read task numbering history without restoring retired business text."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from project_status import Reader, meaningful_lines
from sdlc_store import PLUGIN, document_path, feature_path, resolve

LEDGER = '.task-ids.json'


def identifiers(data: bytes | None) -> set[int]:
    if data is None:
        return set()
    result = set()
    for _, line in meaningful_lines(data.decode('utf-8-sig')):
        match = re.match(r'^ *(?:[-+*]|\d+[.)])\s+\[[ xX]\]\s+T(\d{3,})\s+\S', line)
        if match:
            result.add(int(match[1]))
    return result


def high_water(data: bytes | None) -> int:
    if data is None:
        return 0
    record = json.loads(data)
    if (not isinstance(record, dict) or record.get('schema') != 1 or
            type(record.get('high_water')) is not int or record['high_water'] < 0):
        raise ValueError('Invalid task ID history; preserve it and resolve before allocating IDs')
    return record['high_water']


def transition(before: bytes | None, after: bytes | None, history: bytes | None) -> bytes | None:
    old, new = identifiers(before), identifiers(after)
    maximum = max(high_water(history), max(old, default=0))
    # No metadata is introduced for an ordinary first generation or unchanged
    # task set. Once IDs are retired, the reservation survives even file deletion.
    if history is None and not old - new:
        return None
    reused = {value for value in new - old if value <= maximum}
    if reused:
        raise ValueError('Retired task IDs cannot be reused: ' + ', '.join(f'T{n:03d}' for n in sorted(reused)))
    return (json.dumps({'schema': 1, 'high_water': max(maximum, max(new, default=0))},
                       indent=2) + '\n').encode()


def inspect(project: Path, feature: str) -> dict:
    context = resolve(project, missing=True)
    directory = feature_path(context, feature)
    reader = Reader(PLUGIN)
    values = []
    missing = []
    for name in ('tasks.md', LEDGER):
        path = directory / name
        document_path(context, path)
        info, data = reader.raw(path)
        if info['state'] not in ('present', 'empty', 'missing'):
            raise ValueError('Cannot read task numbering input: ' + name + ' (' + info['state'] + ')')
        if info['state'] == 'missing':
            missing.append(path)
        values.append(data)
    if reader.changed() or any(path.exists() or path.is_symlink() for path in missing):
        raise ValueError('Task numbering inputs changed; read again')
    maximum = max(high_water(values[1]), max(identifiers(values[0]), default=0))
    return {'feature': str(directory), 'high_water': maximum, 'next_id': f'T{maximum + 1:03d}',
            'history_present': values[1] is not None}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--feature', required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(inspect(args.project, args.feature), ensure_ascii=False))
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        print('ERROR: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

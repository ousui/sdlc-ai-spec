#!/usr/bin/env python3
"""Build-time projection of the bundled producer/consumer contract."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from packages.sdlc.common import canonical
from packages.sdlc.protocol import contract

p = argparse.ArgumentParser()
p.add_argument('--check', action='store_true')
a = p.parse_args()
target = Path(__file__).resolve().parents[1]/'contracts/v2.json'
raw = canonical(contract())+b'\n'
if a.check:
    if not target.exists() or target.read_bytes() != raw:
        raise SystemExit('Contract projection is stale: run tools/build_v2_contract.py')
    print('Contract projection matches bundled definitions')
else:
    target.parent.mkdir(exist_ok=True)
    target.write_bytes(raw)
    print(target)

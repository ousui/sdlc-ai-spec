#!/usr/bin/env python3
"""Retired campaign entry; preserved history can reproduce its original source/evidence pair."""
import sys
if __name__=='__main__':
    print('VFY campaign runner retired. Use tools/validate.py --profile strict (or e2e for full local sandbox chains); see docs/TESTING.md.',file=sys.stderr)
    raise SystemExit(2)

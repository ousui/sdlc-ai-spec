#!/usr/bin/env python3
"""Retired campaign entry. Use tools/validate.py; old S/E logs cannot attest new source."""
import sys
if __name__=='__main__':
    print('RLS campaign runner retired. Run tools/validate.py --profile e2e on an exact clean source with local project caches; see docs/TESTING.md.',file=sys.stderr)
    raise SystemExit(2)

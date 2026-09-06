#!/usr/bin/env python3
"""Compatibility entry: portable maps to one full suite; strict to strict. No repeated profiles."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.validate import validate
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',choices=('portable','strict'),required=True)
    parser.add_argument('--source-sha',required=True);parser.add_argument('--json-out',type=Path,required=True)
    args=parser.parse_args()
    result=validate('full' if args.profile=='portable' else 'strict',args.source_sha,args.json_out)
    raise SystemExit(0 if result['success'] else 1)

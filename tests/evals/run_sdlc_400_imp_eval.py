#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.evals.late_phase_eval import run_phase

if __name__ == '__main__':
    raise SystemExit(run_phase('IMP'))

#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
raise SystemExit(subprocess.run([sys.executable,str(ROOT/'tools/test_late_phase_runtime_independence.py'),'PLN'],cwd=ROOT).returncode)

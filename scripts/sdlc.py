#!/usr/bin/env python3
"""Installed SDLC v2 entry; requires the bundled packages, never repository docs."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from packages.sdlc.cli import main

if __name__ == '__main__':
    sys.exit(main())

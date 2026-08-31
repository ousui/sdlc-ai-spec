#!/usr/bin/env python3
"""Final reviewed entry point for the sdlc-100-req Runtime."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def _load_entry():
    module_name = "sdlc_100_req_reviewed_entry"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    path = SCRIPT_DIR / "runtime_entry.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load REQ runtime entry: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


entry = _load_entry()
from review_fixes import apply_review_fixes  # noqa: E402

apply_review_fixes(entry.base)

RequirementHandler = entry.base.RequirementHandler
RequirementVerifier = entry.base.RequirementVerifier
RequirementAnalyzer = entry.base.RequirementAnalyzer
RequirementRuntimeError = entry.base.RequirementRuntimeError
execute_phase = entry.base.execute_phase
base = entry.base


def main() -> int:
    return entry.base.main()


if __name__ == "__main__":
    raise SystemExit(main())

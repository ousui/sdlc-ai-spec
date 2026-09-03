#!/usr/bin/env python3
"""Fixed read-only local checks; never imports or executes project code."""
import ast
import hashlib
import json
from pathlib import Path
import sys


def evaluate(kind, raw, expected):
    text = raw.decode("utf-8")
    if kind == "contains":
        passed = expected in text
    elif kind == "equals":
        passed = expected == text
    elif kind == "python_syntax":
        ast.parse(text)
        passed = True
    elif kind == "json":
        json.loads(text)
        passed = True
    else:
        raise ValueError("Unsupported local check")
    return passed


def main():
    kind, filename, expected = sys.argv[1:]
    raw = Path(filename).read_bytes()
    passed = evaluate(kind, raw, expected)
    print(json.dumps({"kind": kind, "sha256": hashlib.sha256(raw).hexdigest(), "passed": passed}))
    return 0 if passed else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, SyntaxError, OSError, UnicodeError) as exc:
        print(json.dumps({"passed": False, "error": type(exc).__name__}))
        raise SystemExit(1)

#!/usr/bin/env python3
"""Validate the shared lifecycle query package and its read-only boundary."""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "packages/sdlc_lifecycle"
REQUIRED = (
    PACKAGE / "__init__.py",
    PACKAGE / "CONTRACT.md",
    PACKAGE / "errors.py",
    PACKAGE / "models.py",
    PACKAGE / "query.py",
    PACKAGE / "query_dsn.py",
    PACKAGE / "query_pln.py",
    PACKAGE / "query_imp.py",
    ROOT / "tests/lifecycle/test_query.py",
    ROOT / "tests/skill_imp/test_lifecycle.py",
)
FORBIDDEN_CALLS = {
    "initialize",
    "allocate_artifact",
    "allocate_revision",
    "write_open_revision",
    "freeze_revision",
    "abandon_revision",
    "open_read_write",
    "acquire",
    "complete",
    "abandon",
    "apply_operations",
    "restore_snapshot",
}
FORBIDDEN_TEXT = (
    "sqlite3.connect",
    "INSERT INTO",
    "UPDATE revisions",
    "DELETE FROM",
    "CREATE TABLE",
    "current_requirement",
)


def fail(message: str) -> None:
    print(f"lifecycle query validation: FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    for path in REQUIRED:
        if not path.is_file():
            fail(f"missing {path.relative_to(ROOT)}")

    for path in sorted(PACKAGE.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in FORBIDDEN_CALLS:
                    fail(f"{path.name}: read-only package calls {node.func.attr}")
        for token in FORBIDDEN_TEXT:
            if token in source:
                fail(f"{path.name}: forbidden read-only token: {token}")

    contract = (PACKAGE / "CONTRACT.md").read_text(encoding="utf-8")
    for phrase in (
        "严格只读",
        "不提供 Artifact Authority",
        "创建 `.sdlc`",
        "准确 REQ Revision",
        "context / scope_input / control_input / return / issue",
    ):
        if phrase not in contract:
            fail(f"contract missing boundary: {phrase}")

    print("lifecycle query validation: PASS")
    print("projection contract: sdlc-ai-spec/lifecycle-status/v1")
    print("writes: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

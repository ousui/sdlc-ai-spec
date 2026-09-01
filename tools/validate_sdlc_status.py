#!/usr/bin/env python3
"""Static quality gate for the sdlc-status Skill."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/sdlc-status"
REQUIRED = (
    SKILL / "SKILL.md",
    SKILL / "agents/openai.yaml",
    SKILL / "references/interface.json",
    SKILL / "references/contract.md",
    SKILL / "references/status-result.schema.json",
    SKILL / "scripts/runtime.py",
    ROOT / "tests/skill_status/test_runtime.py",
)
FORBIDDEN_CALLS = {
    "initialize",
    "allocate_artifact",
    "allocate_revision",
    "write_open_revision",
    "freeze_revision",
    "abandon_revision",
}
FORBIDDEN_SQL = (
    "INSERT INTO",
    "UPDATE ",
    "DELETE FROM",
    "CREATE TABLE",
    "ALTER TABLE",
    "DROP TABLE",
)


def fail(message: str):
    print(f"sdlc-status validation: FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    for path in REQUIRED:
        if not path.is_file():
            fail(f"missing {path.relative_to(ROOT)}")
    interface = json.loads((SKILL / "references/interface.json").read_text())
    expected = {"auto", "list", "inspect", "help", "version", "commands", "examples"}
    actual = {item["name"] for item in interface["commands"]}
    if actual != expected or any(item.get("writes") is not False for item in interface["commands"]):
        fail("command surface or write flags are invalid")
    source = (SKILL / "scripts/runtime.py").read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            modules = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
            )
            if any(name == "sqlite3" or name.startswith("sqlite3.") for name in modules):
                fail("read-only Skill imports sqlite3 directly")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in FORBIDDEN_CALLS:
                fail(f"read-only Skill calls {node.func.attr}")
            if (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "sqlite3"
                and node.func.attr == "connect"
            ):
                fail("read-only Skill calls sqlite3.connect directly")
    for token in ("current_requirement", "invoke_skill", *FORBIDDEN_SQL):
        if token in source:
            fail(f"forbidden runtime token: {token}")
    skill = (SKILL / "SKILL.md").read_text()
    for token in ("scripts/sdlc_skill_interface.py", "references/interface.json", "decision_policy", "write_policy"):
        if token not in skill:
            fail(f"SKILL.md missing interface binding: {token}")
    print("sdlc-status validation: PASS")
    print("commands: 7")
    print("writes: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

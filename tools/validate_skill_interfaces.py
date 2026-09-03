#!/usr/bin/env python3
"""Validate every formal Skill against the shared user-interface contract."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTERFACE_CONTRACT = "sdlc-ai-spec/runtime/skill-interface/v1"
SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
PHASE_RE = re.compile(r"^sdlc-[0-9]{3}-")
META = {"help", "version", "commands", "examples"}
PHASE_REQUIRED_COMMANDS = {"auto", "create", "revise", "check", *META}
RESERVED_PARAMETERS = {
    "command", "operation", "project-root", "reference", "decision-policy",
    "write-policy", "dry-run", "output",
}
REQUIRED_RUNTIME_TOKENS = (
    "scripts/sdlc_skill_interface.py",
    "references/interface.json",
    "decision_policy",
    "write_policy",
)


class InterfaceValidationError(ValueError):
    pass


def fail(message: str) -> None:
    raise InterfaceValidationError(message)


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"invalid JSON {path.relative_to(ROOT)}: {exc}")


def validate_spec(path: Path, skill_name: str) -> None:
    data = load_json(path)
    if not isinstance(data, dict):
        fail(f"interface spec must be an object: {path.relative_to(ROOT)}")
    if data.get("contract") != INTERFACE_CONTRACT:
        fail(f"interface contract mismatch: {skill_name}")
    if data.get("skill") != skill_name:
        fail(f"interface skill mismatch: {skill_name}")
    if not SEMVER_RE.fullmatch(str(data.get("skill_version", ""))):
        fail(f"interface skill_version must be SemVer: {skill_name}")
    commands = data.get("commands")
    if not isinstance(commands, list) or not commands:
        fail(f"interface commands missing: {skill_name}")
    names: list[str] = []
    for item in commands:
        if not isinstance(item, dict):
            fail(f"interface command must be an object: {skill_name}")
        name = item.get("name")
        description = item.get("description")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", name):
            fail(f"invalid command name in {skill_name}: {name}")
        if name in names:
            fail(f"duplicate command in {skill_name}: {name}")
        if not isinstance(description, str) or not description.strip():
            fail(f"command description missing in {skill_name}: {name}")
        if "writes" in item and not isinstance(item["writes"], bool):
            fail(f"command writes must be boolean in {skill_name}: {name}")
        names.append(name)
    if data.get("default_command") not in names:
        fail(f"default command is not declared: {skill_name}")
    if not META.issubset(names):
        fail(f"meta commands missing in {skill_name}: {sorted(META - set(names))}")
    if PHASE_RE.match(skill_name):
        if not PHASE_REQUIRED_COMMANDS.issubset(names):
            fail(f"Phase Skill core commands missing: {skill_name}: {names}")
        for item in commands:
            if item["name"] in PHASE_REQUIRED_COMMANDS:
                continue
            if item["name"] in RESERVED_PARAMETERS or not isinstance(item.get("writes"), bool):
                fail(f"invalid Phase command extension: {skill_name}: {item['name']}")
    examples = data.get("examples")
    if not isinstance(examples, list) or not examples or any(
        not isinstance(item, str) or not item.strip() for item in examples
    ):
        fail(f"interface examples missing: {skill_name}")


def main() -> int:
    required = (
        ROOT / "skills/_shared/contracts/skill-interface.md",
        ROOT / "skills/_shared/schemas/skill-interface.schema.json",
        ROOT / "skills/_shared/schemas/skill-command.schema.json",
        ROOT / "packages/sdlc_runtime/skill_args.py",
        ROOT / "packages/sdlc_runtime/skill_command.py",
        ROOT / "scripts/sdlc_skill_interface.py",
    )
    for path in required:
        if not path.is_file():
            fail(f"missing shared Skill Interface resource: {path.relative_to(ROOT)}")

    formal = 0
    for directory in sorted((ROOT / "skills").iterdir()):
        if not directory.is_dir() or directory.name.startswith("_"):
            continue
        formal += 1
        interface_path = directory / "references/interface.json"
        if not interface_path.is_file():
            fail(f"formal Skill missing references/interface.json: {directory.name}")
        validate_spec(interface_path, directory.name)
        skill_text = (directory / "SKILL.md").read_text(encoding="utf-8")
        for token in REQUIRED_RUNTIME_TOKENS:
            if token not in skill_text:
                fail(f"{directory.name} does not bind {token}")
        for token in ("help", "version", "commands", "examples"):
            if token not in skill_text:
                fail(f"{directory.name} does not document {token}")

    if formal == 0:
        fail("no formal Skills found")
    print("skill interface validation: PASS")
    print("formal skills:", formal)
    print("interface contract:", INTERFACE_CONTRACT)
    print("authority source locks: unchanged")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except InterfaceValidationError as exc:
        print(f"skill interface validation: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)

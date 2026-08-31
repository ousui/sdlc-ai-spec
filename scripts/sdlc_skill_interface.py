#!/usr/bin/env python3
"""Normalize a Skill invocation tail and render standard meta commands."""

from __future__ import annotations

import json
from pathlib import Path
import sys

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
PACKAGES = PLUGIN_ROOT / "packages"
for candidate in (PLUGIN_ROOT, PACKAGES):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from sdlc_runtime.skill_args import (  # noqa: E402
    SkillArgumentError,
    load_skill_interface,
    render_commands,
    render_examples,
    render_help,
    render_version,
)
from sdlc_runtime.skill_command import parse_skill_command  # noqa: E402


def _parse_own_args(argv: list[str]) -> tuple[Path, list[str]]:
    if not argv:
        raise SkillArgumentError(
            "INTERFACE_CLI_USAGE",
            "usage: sdlc_skill_interface.py --spec PATH -- [skill arguments]",
        )
    spec_path: str | None = None
    tail: list[str] = []
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--":
            tail = argv[index + 1 :]
            break
        if token == "--spec":
            if index + 1 >= len(argv):
                raise SkillArgumentError(
                    "INTERFACE_CLI_USAGE", "--spec requires a path"
                )
            index += 1
            spec_path = argv[index]
        elif token.startswith("--spec="):
            spec_path = token.split("=", 1)[1]
        else:
            raise SkillArgumentError(
                "INTERFACE_CLI_USAGE", f"unknown interface CLI option: {token}"
            )
        index += 1
    if not spec_path:
        raise SkillArgumentError("INTERFACE_CLI_USAGE", "--spec is required")
    return Path(spec_path), tail


def main(argv: list[str] | None = None) -> int:
    try:
        spec_path, tail = _parse_own_args(list(sys.argv[1:] if argv is None else argv))
        spec = load_skill_interface(spec_path)
        command = parse_skill_command(tail, spec)
        display: str | None = None
        if command.command == "help":
            display = render_help(spec, command.help_topic)
        elif command.command == "version":
            display = render_version(spec)
        elif command.command == "commands":
            display = render_commands(spec)
        elif command.command == "examples":
            display = render_examples(spec)
        print(
            json.dumps(
                {
                    "ok": True,
                    "command": command.to_dict(),
                    "display": display,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    except (OSError, json.JSONDecodeError, SkillArgumentError) as exc:
        error = (
            exc.to_dict()
            if isinstance(exc, SkillArgumentError)
            else {
                "code": "INTERFACE_SPEC_INVALID",
                "message": str(exc),
                "details": {},
            }
        )
        print(
            json.dumps(
                {"ok": False, "error": error},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

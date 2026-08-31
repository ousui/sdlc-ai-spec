"""General command aliases layered on top of the Phase argument parser."""

from __future__ import annotations

import shlex
from typing import Sequence

from .skill_args import META_COMMANDS, SkillCommand, SkillInterfaceSpec, parse_skill_arguments


def _tokens(arguments: str | Sequence[str]) -> list[str]:
    if isinstance(arguments, str):
        return shlex.split(arguments, posix=True)
    return list(arguments)


def _command_value(value: str, spec: SkillInterfaceSpec) -> list[str]:
    if value in META_COMMANDS:
        return [value]
    return ["--operation", value]


def normalize_command_aliases(
    arguments: str | Sequence[str], spec: SkillInterfaceSpec
) -> list[str]:
    """Map general command/cmd/-c/--command syntax to the stable parser surface."""

    tokens = _tokens(arguments)
    result: list[str] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token == "--":
            result.extend(tokens[i:])
            break
        if token in {"--command", "-c", "command", "cmd"}:
            if i + 1 >= len(tokens):
                result.append("--operation")
                i += 1
                continue
            i += 1
            result.extend(_command_value(tokens[i], spec))
            i += 1
            continue
        matched = False
        for prefix in ("--command=", "-c=", "command=", "cmd="):
            if token.startswith(prefix):
                result.extend(_command_value(token[len(prefix) :], spec))
                matched = True
                break
        if matched:
            i += 1
            continue
        result.append(token)
        i += 1
    return result


def parse_skill_command(
    arguments: str | Sequence[str], spec: SkillInterfaceSpec
) -> SkillCommand:
    return parse_skill_arguments(normalize_command_aliases(arguments, spec), spec)

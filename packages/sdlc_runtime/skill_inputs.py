"""Optional repeatable input-reference extension for shared Skill commands."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import shlex
from typing import Any, Mapping, Sequence

from .skill_args import (
    ArgumentWarning,
    META_COMMANDS,
    SkillArgumentError,
    SkillCommand,
    SkillInterfaceSpec,
)
from .skill_command import parse_skill_command


@dataclass(frozen=True)
class SkillCommandWithInputs:
    contract: str
    skill: str
    skill_version: str
    command: str
    project_root: str | None
    artifact_reference: str | None
    input_references: tuple[str, ...]
    decision_policy: str
    write_policy: str
    dry_run: bool
    output: str
    request_text: str
    help_topic: str | None
    warnings: tuple[ArgumentWarning, ...]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["input_references"] = list(self.input_references)
        result["warnings"] = [asdict(item) for item in self.warnings]
        return result


def _tokens(arguments: str | Sequence[str]) -> list[str]:
    if isinstance(arguments, str):
        try:
            return shlex.split(arguments, posix=True)
        except ValueError as exc:
            raise SkillArgumentError("ARGUMENT_QUOTE_ERROR", str(exc)) from exc
    if not isinstance(arguments, Sequence) or isinstance(
        arguments, (bytes, bytearray)
    ):
        raise SkillArgumentError(
            "ARGUMENT_TYPE_INVALID", "arguments must be text or a token sequence"
        )
    if any(not isinstance(item, str) for item in arguments):
        raise SkillArgumentError(
            "ARGUMENT_TYPE_INVALID", "every argument token must be a string"
        )
    return list(arguments)


def parse_skill_command_with_inputs(
    arguments: str | Sequence[str],
    spec: SkillInterfaceSpec,
) -> SkillCommandWithInputs:
    """Parse the shared command surface plus repeatable ``--input/-i`` references."""

    tokens = _tokens(arguments)
    filtered: list[str] = []
    values: list[str] = []
    warnings: list[ArgumentWarning] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            filtered.extend(tokens[index:])
            break

        key_matched = False
        value: str | None = None
        if token in {"--input", "-i", "input"}:
            if index + 1 >= len(tokens):
                raise SkillArgumentError(
                    "ARGUMENT_VALUE_REQUIRED", f"{token} requires a value"
                )
            index += 1
            value = tokens[index]
            key_matched = True
        else:
            for prefix in ("--input=", "-i=", "input="):
                if token.startswith(prefix):
                    value = token[len(prefix) :]
                    key_matched = True
                    break

        if key_matched:
            assert value is not None
            value = value.strip()
            if not value:
                raise SkillArgumentError(
                    "ARGUMENT_VALUE_INVALID", "input reference must not be empty"
                )
            if value in values:
                warnings.append(
                    ArgumentWarning(
                        "ARGUMENT_DUPLICATE_INPUT",
                        f"duplicate input reference ignored: {value}",
                    )
                )
            else:
                values.append(value)
            index += 1
            continue

        filtered.append(token)
        index += 1

    base: SkillCommand = parse_skill_command(filtered, spec)
    if base.command in META_COMMANDS and values:
        raise SkillArgumentError(
            "ARGUMENT_CONFLICT",
            f"{base.command} cannot be combined with input references",
            details={"command": base.command, "input_references": values},
        )
    return SkillCommandWithInputs(
        contract=base.contract,
        skill=base.skill,
        skill_version=base.skill_version,
        command=base.command,
        project_root=base.project_root,
        artifact_reference=base.artifact_reference,
        input_references=tuple(values),
        decision_policy=base.decision_policy,
        write_policy=base.write_policy,
        dry_run=base.dry_run,
        output=base.output,
        request_text=base.request_text,
        help_topic=base.help_topic,
        warnings=tuple((*base.warnings, *warnings)),
    )


def parse_skill_command_with_extensions(
    arguments: str | Sequence[str],
    spec: SkillInterfaceSpec,
    extensions: Mapping[str, tuple[str, ...]],
) -> tuple[SkillCommandWithInputs, dict[str, str]]:
    """Register single-value Phase parameters on the shared command grammar."""

    aliases = {alias: name for name, names in extensions.items() for alias in names}
    if len(aliases) != sum(len(names) for names in extensions.values()):
        raise SkillArgumentError("INTERFACE_SPEC_INVALID", "extension aliases overlap")
    tokens = _tokens(arguments)
    filtered: list[str] = []
    values: dict[str, str] = {}
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            filtered.extend(tokens[index:])
            break
        option, separator, value = token.partition("=")
        if option not in aliases:
            filtered.append(token)
            index += 1
            continue
        if not separator:
            if index + 1 >= len(tokens) or tokens[index + 1].startswith("-"):
                raise SkillArgumentError("ARGUMENT_VALUE_REQUIRED", f"{option} requires a value")
            index += 1
            value = tokens[index]
        if not value.strip():
            raise SkillArgumentError("ARGUMENT_VALUE_INVALID", f"{option} must not be empty")
        name = aliases[option]
        if name in values and values[name] != value:
            raise SkillArgumentError("ARGUMENT_CONFLICT", f"conflicting {option} values")
        values[name] = value
        index += 1
    command = parse_skill_command_with_inputs(filtered, spec)
    if command.command in META_COMMANDS and values:
        raise SkillArgumentError("ARGUMENT_CONFLICT", "meta commands cannot take execution parameters")
    return command, values

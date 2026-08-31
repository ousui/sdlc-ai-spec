"""Deterministic user-facing argument normalization for sdlc-ai-spec Skills."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import shlex
from typing import Any, Mapping, Sequence

INTERFACE_CONTRACT = "sdlc-ai-spec/runtime/skill-interface/v1"
META_COMMANDS = ("help", "version", "commands", "examples")
DECISION_POLICIES = ("user", "model", "experiment")
WRITE_POLICIES = ("auto", "confirm", "deny")
OUTPUT_MODES = ("summary", "json", "debug")


class SkillArgumentError(ValueError):
    """Raised when a user-facing Skill command cannot be normalized safely."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = dict(details or {})

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


@dataclass(frozen=True)
class ArgumentWarning:
    code: str
    message: str


@dataclass(frozen=True)
class SkillInterfaceSpec:
    contract: str
    skill: str
    skill_version: str
    default_command: str
    commands: tuple[Mapping[str, Any], ...]
    examples: tuple[str, ...]

    @property
    def command_names(self) -> tuple[str, ...]:
        return tuple(str(item["name"]) for item in self.commands)


@dataclass(frozen=True)
class SkillCommand:
    contract: str
    skill: str
    skill_version: str
    command: str
    project_root: str | None
    artifact_reference: str | None
    decision_policy: str
    write_policy: str
    dry_run: bool
    output: str
    request_text: str
    help_topic: str | None
    warnings: tuple[ArgumentWarning, ...]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["warnings"] = [asdict(item) for item in self.warnings]
        return result


def _validate_spec(data: Mapping[str, Any]) -> SkillInterfaceSpec:
    if data.get("contract") != INTERFACE_CONTRACT:
        raise SkillArgumentError(
            "INTERFACE_SPEC_INVALID", "interface contract is invalid"
        )
    skill = data.get("skill")
    version = data.get("skill_version")
    default = data.get("default_command")
    commands = data.get("commands")
    examples = data.get("examples", [])
    if not isinstance(skill, str) or not skill:
        raise SkillArgumentError("INTERFACE_SPEC_INVALID", "skill is required")
    if not isinstance(version, str) or not version:
        raise SkillArgumentError(
            "INTERFACE_SPEC_INVALID", "skill_version is required"
        )
    if not isinstance(commands, list) or not commands:
        raise SkillArgumentError(
            "INTERFACE_SPEC_INVALID", "commands must be a non-empty array"
        )
    names: list[str] = []
    normalized: list[Mapping[str, Any]] = []
    for item in commands:
        if not isinstance(item, Mapping):
            raise SkillArgumentError(
                "INTERFACE_SPEC_INVALID", "each command must be an object"
            )
        name = item.get("name")
        description = item.get("description")
        if not isinstance(name, str) or not name or name.lower() != name:
            raise SkillArgumentError(
                "INTERFACE_SPEC_INVALID", "command names must be lowercase"
            )
        if not isinstance(description, str) or not description:
            raise SkillArgumentError(
                "INTERFACE_SPEC_INVALID", f"command {name} needs a description"
            )
        if name in names:
            raise SkillArgumentError(
                "INTERFACE_SPEC_INVALID", f"duplicate command: {name}"
            )
        names.append(name)
        normalized.append(dict(item))
    if default not in names:
        raise SkillArgumentError(
            "INTERFACE_SPEC_INVALID", "default_command must be declared"
        )
    if any(not isinstance(item, str) or not item for item in examples):
        raise SkillArgumentError(
            "INTERFACE_SPEC_INVALID", "examples must be non-empty strings"
        )
    return SkillInterfaceSpec(
        contract=INTERFACE_CONTRACT,
        skill=skill,
        skill_version=version,
        default_command=str(default),
        commands=tuple(normalized),
        examples=tuple(examples),
    )


def load_skill_interface(path: Path | str) -> SkillInterfaceSpec:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, Mapping):
        raise SkillArgumentError(
            "INTERFACE_SPEC_INVALID", "interface spec must be an object"
        )
    return _validate_spec(data)


def skill_interface_from_mapping(data: Mapping[str, Any]) -> SkillInterfaceSpec:
    return _validate_spec(data)


def _parse_bool(value: str, name: str) -> bool:
    lowered = value.lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise SkillArgumentError(
        "ARGUMENT_VALUE_INVALID", f"{name} must be true or false"
    )


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


def parse_skill_arguments(
    arguments: str | Sequence[str],
    spec: SkillInterfaceSpec,
) -> SkillCommand:
    """Normalize shell-style and conversational aliases into one command model."""

    tokens = _tokens(arguments)
    supported = set(spec.command_names)
    operations = supported - set(META_COMMANDS)
    warnings: list[ArgumentWarning] = []
    values: dict[str, Any] = {
        "project_root": None,
        "artifact_reference": None,
        "decision_policy": "user",
        "write_policy": "auto",
        "dry_run": False,
        "output": "summary",
    }
    explicit: dict[str, Any] = {}
    operation_values: list[str] = []
    meta_values: list[str] = []
    help_topic: str | None = None
    remainder: list[str] = []

    def set_value(name: str, value: Any) -> None:
        if name in explicit:
            if explicit[name] != value:
                raise SkillArgumentError(
                    "ARGUMENT_CONFLICT",
                    f"conflicting values for {name}: {explicit[name]!r} and {value!r}",
                    details={
                        "parameter": name,
                        "values": [explicit[name], value],
                    },
                )
            warnings.append(
                ArgumentWarning(
                    "ARGUMENT_DUPLICATE", f"duplicate {name} ignored"
                )
            )
            return
        explicit[name] = value
        values[name] = value

    def set_operation(value: str) -> None:
        if value not in operations:
            raise SkillArgumentError(
                "COMMAND_UNKNOWN",
                f"unsupported operation: {value}",
                details={"supported": sorted(operations)},
            )
        operation_values.append(value)

    def set_meta(value: str) -> None:
        if value not in META_COMMANDS or value not in supported:
            raise SkillArgumentError(
                "COMMAND_UNKNOWN", f"unsupported meta command: {value}"
            )
        meta_values.append(value)

    options_with_values = {
        "--operation": "operation",
        "--op": "operation",
        "-o": "operation",
        "--project-root": "project_root",
        "--project_root": "project_root",
        "-p": "project_root",
        "--reference": "artifact_reference",
        "--artifact-reference": "artifact_reference",
        "-r": "artifact_reference",
        "--decision-policy": "decision_policy",
        "-d": "decision_policy",
        "--write-policy": "write_policy",
        "-w": "write_policy",
        "--output": "output",
        "--output-format": "output",
        "-f": "output",
    }
    relaxed_keys = {
        "operation": "operation",
        "op": "operation",
        "project-root": "project_root",
        "project_root": "project_root",
        "reference": "artifact_reference",
        "artifact-reference": "artifact_reference",
        "decision-policy": "decision_policy",
        "write-policy": "write_policy",
        "output": "output",
        "output-format": "output",
        "dry-run": "dry_run",
        "dry_run": "dry_run",
    }

    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token == "--":
            remainder.extend(tokens[i + 1 :])
            break

        if token in {"-h", "--help"}:
            set_meta("help")
            i += 1
            continue
        if token in {"-V", "--version"}:
            set_meta("version")
            i += 1
            continue
        if token in {"--commands", "--list-commands"}:
            set_meta("commands")
            i += 1
            continue
        if token == "--examples":
            set_meta("examples")
            i += 1
            continue
        if token in {"-n", "--dry-run"}:
            set_value("dry_run", True)
            i += 1
            continue
        if token == "--no-write":
            set_value("write_policy", "deny")
            i += 1
            continue
        if token == "--confirm-write":
            set_value("write_policy", "confirm")
            i += 1
            continue

        shortcut = token[2:] if token.startswith("--") else None
        if shortcut in operations - {"auto"}:
            set_operation(str(shortcut))
            i += 1
            continue

        key: str | None = None
        value: str | None = None
        if "=" in token:
            left, value = token.split("=", 1)
            if left in options_with_values:
                key = options_with_values[left]
            elif left in relaxed_keys:
                key = relaxed_keys[left]
            elif left in {"-n", "--dry-run"}:
                key = "dry_run"
            elif left.startswith("-"):
                raise SkillArgumentError(
                    "ARGUMENT_UNKNOWN", f"unknown option: {left}"
                )
        elif token in options_with_values:
            key = options_with_values[token]
            if i + 1 >= len(tokens):
                raise SkillArgumentError(
                    "ARGUMENT_VALUE_REQUIRED", f"{token} requires a value"
                )
            i += 1
            value = tokens[i]
        elif token in relaxed_keys:
            key = relaxed_keys[token]
            if i + 1 >= len(tokens):
                raise SkillArgumentError(
                    "ARGUMENT_VALUE_REQUIRED", f"{token} requires a value"
                )
            i += 1
            value = tokens[i]

        if key is not None:
            assert value is not None
            if key == "operation":
                set_operation(value)
            elif key == "decision_policy":
                if value not in DECISION_POLICIES:
                    raise SkillArgumentError(
                        "ARGUMENT_VALUE_INVALID",
                        "decision_policy must be one of "
                        + ", ".join(DECISION_POLICIES),
                    )
                set_value(key, value)
            elif key == "write_policy":
                if value not in WRITE_POLICIES:
                    raise SkillArgumentError(
                        "ARGUMENT_VALUE_INVALID",
                        "write_policy must be one of "
                        + ", ".join(WRITE_POLICIES),
                    )
                set_value(key, value)
            elif key == "output":
                if value not in OUTPUT_MODES:
                    raise SkillArgumentError(
                        "ARGUMENT_VALUE_INVALID",
                        "output must be one of " + ", ".join(OUTPUT_MODES),
                    )
                set_value(key, value)
            elif key == "dry_run":
                set_value(key, _parse_bool(value, "dry_run"))
            else:
                if value == "":
                    raise SkillArgumentError(
                        "ARGUMENT_VALUE_INVALID", f"{key} must not be empty"
                    )
                set_value(key, value)
            i += 1
            continue

        if token in supported:
            if token in META_COMMANDS:
                set_meta(token)
            else:
                set_operation(token)
            i += 1
            continue
        if token.startswith("-"):
            raise SkillArgumentError(
                "ARGUMENT_UNKNOWN", f"unknown option: {token}"
            )
        remainder.append(token)
        i += 1

    distinct_operations = list(dict.fromkeys(operation_values))
    distinct_meta = list(dict.fromkeys(meta_values))
    if len(distinct_operations) > 1:
        raise SkillArgumentError(
            "ARGUMENT_CONFLICT",
            "multiple operations were requested",
            details={"operations": distinct_operations},
        )
    if len(distinct_meta) > 1:
        raise SkillArgumentError(
            "ARGUMENT_CONFLICT",
            "multiple meta commands were requested",
            details={"commands": distinct_meta},
        )

    operation = (
        distinct_operations[0] if distinct_operations else spec.default_command
    )
    command = operation
    if distinct_meta:
        meta = distinct_meta[0]
        if meta == "help" and distinct_operations:
            command = "help"
            help_topic = operation
        elif distinct_operations:
            raise SkillArgumentError(
                "ARGUMENT_CONFLICT",
                f"{meta} cannot be combined with operation {operation}",
            )
        else:
            command = meta
        execution_options = {
            name: value for name, value in explicit.items() if name != "output"
        }
        if execution_options:
            raise SkillArgumentError(
                "ARGUMENT_CONFLICT",
                f"{meta} cannot be combined with execution options",
            )
        if remainder:
            raise SkillArgumentError(
                "ARGUMENT_CONFLICT",
                f"{meta} cannot be combined with request text",
            )

    return SkillCommand(
        contract=INTERFACE_CONTRACT,
        skill=spec.skill,
        skill_version=spec.skill_version,
        command=command,
        project_root=values["project_root"],
        artifact_reference=values["artifact_reference"],
        decision_policy=values["decision_policy"],
        write_policy=values["write_policy"],
        dry_run=values["dry_run"],
        output=values["output"],
        request_text=" ".join(remainder).strip(),
        help_topic=help_topic,
        warnings=tuple(warnings),
    )


def render_commands(spec: SkillInterfaceSpec) -> str:
    lines = [f"{spec.skill} commands:"]
    for item in spec.commands:
        lines.append(f"  {item['name']:<10} {item['description']}")
    return "\n".join(lines)


def render_help(spec: SkillInterfaceSpec, topic: str | None = None) -> str:
    if topic:
        for item in spec.commands:
            if item["name"] == topic:
                return (
                    f"{spec.skill} {topic}\n\n"
                    f"{item['description']}\n\n"
                    f"Usage: /{spec.skill} {topic} [options] [-- request text]\n"
                    "Use --help without a topic for common options."
                )
        raise SkillArgumentError(
            "COMMAND_UNKNOWN", f"unknown help topic: {topic}"
        )
    return (
        f"{spec.skill} {spec.skill_version}\n\n"
        f"Usage: /{spec.skill} [command] [options] [-- request text]\n\n"
        "Commands:\n"
        + "\n".join(
            f"  {item['name']:<10} {item['description']}"
            for item in spec.commands
        )
        + "\n\nCommon options:\n"
        "  -h, --help\n"
        "  -V, --version\n"
        "      --commands\n"
        "      --examples\n"
        "  -o, --operation VALUE\n"
        "  -p, --project-root PATH\n"
        "  -r, --reference REF\n"
        "  -d, --decision-policy user|model|experiment\n"
        "  -w, --write-policy auto|confirm|deny\n"
        "  -n, --dry-run\n"
        "  -f, --output summary|json|debug"
    )


def render_version(spec: SkillInterfaceSpec) -> str:
    return f"{spec.skill} {spec.skill_version}\ninterface {INTERFACE_CONTRACT}"


def render_examples(spec: SkillInterfaceSpec) -> str:
    return "\n".join(spec.examples)

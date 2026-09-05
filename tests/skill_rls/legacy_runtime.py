#!/usr/bin/env python3
"""Historical provisional CLI fixture (never installed): shared parsing and private domain dispatch only."""
from __future__ import annotations

import json
from pathlib import Path
import shlex
import sys

sys.dont_write_bytecode = True
PLUGIN_ROOT = Path(__file__).resolve().parents[2]
for entry in (PLUGIN_ROOT, PLUGIN_ROOT / "skills/sdlc-600-rls/scripts"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

INTERFACE_PATH = PLUGIN_ROOT / "skills/sdlc-600-rls/references/interface.json"
EXTENSIONS = {
    "target": ("--target",),
    "release_reference": ("--release-reference",),
}
META_COMMANDS = ("help", "version", "commands", "examples")


def _shared_parser():
    from packages.sdlc_runtime import (
        META_COMMANDS as SHARED_META_COMMANDS,
        SkillArgumentError,
        load_skill_interface,
        parse_skill_command_with_extensions,
        render_commands,
        render_examples,
        render_help,
        render_version,
    )

    return {
        "meta": SHARED_META_COMMANDS,
        "error": SkillArgumentError,
        "load": load_skill_interface,
        "parse": parse_skill_command_with_extensions,
        "commands": render_commands,
        "examples": render_examples,
        "help": render_help,
        "version": render_version,
    }


def _extract_repeatable_items(arguments, error_type):
    if isinstance(arguments, str):
        try:
            tokens = shlex.split(arguments, posix=True)
        except ValueError as exc:
            raise error_type("ARGUMENT_QUOTE_ERROR", str(exc)) from exc
    else:
        try:
            tokens = list(arguments)
        except TypeError as exc:
            raise error_type(
                "ARGUMENT_TYPE_INVALID", "arguments must be text or a token sequence"
            ) from exc
        if any(not isinstance(token, str) for token in tokens):
            raise error_type(
                "ARGUMENT_TYPE_INVALID", "every argument token must be a string"
            )

    filtered: list[str] = []
    items: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            filtered.extend(tokens[index:])
            break
        value = None
        if token == "--item":
            if index + 1 >= len(tokens) or tokens[index + 1].startswith("-"):
                raise error_type("ARGUMENT_VALUE_REQUIRED", "--item requires a value")
            index += 1
            value = tokens[index]
        elif token.startswith("--item="):
            value = token.partition("=")[2]
        if value is None:
            filtered.append(token)
        else:
            value = value.strip()
            if not value:
                raise error_type("ARGUMENT_VALUE_INVALID", "--item must not be empty")
            # Preserve occurrence order and duplicates. Domain normalization emits
            # the stable duplicate warning and performs exact RLI/RCF validation.
            items.append(value)
        index += 1
    return filtered, items


def parse_command(arguments):
    shared = _shared_parser()
    filtered, items = _extract_repeatable_items(arguments, shared["error"])
    spec = shared["load"](INTERFACE_PATH)
    command, values = shared["parse"](filtered, spec, EXTENSIONS)
    if command.command in shared["meta"] and items:
        raise shared["error"](
            "ARGUMENT_CONFLICT", "meta commands cannot take execution parameters"
        )
    values["items"] = items
    if len(items) == 1:
        values["item"] = items[0]
    return shared, spec, command, values


def meta_result(command_name: str, display: str) -> dict:
    return {
        "contract": "sdlc-ai-spec/skill-command-result/v1",
        "ok": True,
        "state": "meta",
        "command": command_name,
        "display": display,
        "effects": [],
        "real_target_effects": 0,
    }


def run_cli(arguments, payload=None):
    shared, spec, command, values = parse_command(arguments)
    if command.command in shared["meta"]:
        displays = {
            "help": lambda: shared["help"](spec, command.help_topic),
            "version": lambda: shared["version"](spec),
            "commands": lambda: shared["commands"](spec),
            "examples": lambda: shared["examples"](spec),
        }
        return meta_result(command.command, displays[command.command]()), command.output

    from rls_common import exact_reference, require
    from rls_handler import (
        auto_operation,
        cancel,
        check,
        confirm,
        create,
        execute,
        finalize,
        revise,
    )
    from tests.skill_rls.support import HistoricalSandboxTarget as SandboxReleaseTarget
    from rls_vfy_adapter import adapt_vfy_payload

    payload = {} if payload is None else payload
    if not isinstance(payload, dict):
        raise TypeError("stdin payload must be an object")
    artifact = payload.get("artifact")
    if artifact is not None and not isinstance(artifact, dict):
        raise TypeError("artifact must be an object")

    candidate = None
    vfy_payload = payload.get("vfy")
    candidate_required = command.command in {"create", "revise"} or (
        command.command == "auto" and artifact is None
    )
    if vfy_payload is not None:
        candidate = adapt_vfy_payload(vfy_payload)
    elif candidate_required:
        candidate = adapt_vfy_payload(payload)

    if command.input_references:
        expected_vfy_reference = (
            candidate.vfy_reference
            if candidate is not None
            else (
                artifact.get("release_contract", {}).get("vfy_reference")
                if isinstance(artifact, dict)
                else None
            )
        )
        require(
            isinstance(expected_vfy_reference, str)
            and expected_vfy_reference in command.input_references,
            "RLS_VFY_NOT_READY",
            "--input does not identify the current VFY Revision",
            expected=expected_vfy_reference,
            supplied=list(command.input_references),
        )

    if artifact is not None and command.artifact_reference:
        supplied_reference = exact_reference(command.artifact_reference, "RLS")
        require(
            supplied_reference == artifact["artifact"]["reference"],
            "RLS_REFERENCE_NOT_EXACT",
            "--reference does not match the supplied RLS Artifact",
            expected=artifact["artifact"]["reference"],
            supplied=supplied_reference,
        )

    operation = command.command
    if operation == "auto":
        operation = auto_operation(candidate, artifact)
    if operation == "complete":
        return {
            "ok": True,
            "status": "completed",
            "artifact": None,
            "real_target_effects": 0,
        }, command.output
    if operation == "action_required":
        return {
            "ok": False,
            "status": "action_required",
            "errors": [{"code": "RLS_APPLICABILITY_PENDING", "message": "RLS applicability is pending"}],
            "real_target_effects": 0,
        }, command.output
    if operation == "create":
        result = create(
            candidate,
            release_reference=values.get("release_reference") or payload.get("release_reference"),
            release_target=values.get("target") or payload.get("target"),
            target_baseline=payload.get("target_baseline"),
        )
        return {
            "ok": True,
            "status": "PROVISIONAL",
            "artifact": None if result.get("artifact") is None else result,
            "disposition": result.get("rls_applicability"),
            "real_target_effects": 0,
            "sandbox_target_effects": 0,
        }, command.output

    if not isinstance(artifact, dict):
        raise TypeError("artifact object is required")
    release_contract = artifact["release_contract"]
    contract_target = release_contract["release_target"]
    requested_target = values.get("target")
    requested_release_reference = values.get("release_reference")
    require(
        requested_release_reference is None
        or requested_release_reference == release_contract["release_reference"],
        "RLS_EFFECT_AUTHORIZATION_STALE"
        if operation == "execute"
        else "RLS_CONTRACT_INVALID",
        "requested Release Reference does not match the current RLS Artifact",
        expected=release_contract["release_reference"],
        supplied=requested_release_reference,
    )
    if operation == "revise":
        target_id = requested_target or contract_target
    else:
        require(
            requested_target is None or requested_target == contract_target,
            "RLS_EFFECT_AUTHORIZATION_STALE"
            if operation == "execute"
            else "RLS_TARGET_STATE_UNVERIFIED",
            "requested target does not match the Release Contract",
            expected=contract_target,
            supplied=requested_target,
        )
        target_id = contract_target

    sandbox_root = payload.get("sandbox_root")
    require(
        isinstance(sandbox_root, (str, Path)),
        "RLS_TARGET_REQUIRED",
        "sandbox_root is required for target operations",
    )
    target = SandboxReleaseTarget(sandbox_root, target_id)
    selected = values.get("items") or payload.get("items") or []
    if isinstance(selected, str):
        selected = [selected]
    if command.command == "auto" and not selected:
        if operation == "execute":
            selected = [
                row["id"]
                for row in artifact["release_items"]
                if row["result"] == "pending"
            ]
        elif operation == "confirm":
            selected = [
                row["id"]
                for row in artifact["confirmations"]
                if row["result"] == "pending"
            ]

    if operation == "execute":
        artifact = execute(
            artifact,
            target,
            selected,
            payload.get("effect_authorization"),
            behaviors=payload.get("behaviors"),
            now=payload.get("now"),
        )
    elif operation == "confirm":
        artifact = confirm(
            artifact,
            target,
            selected,
            force_fail=bool(payload.get("force_fail")),
            pipeline_only=bool(payload.get("pipeline_only")),
            human_evidence=payload.get("human_evidence"),
        )
    elif operation == "check":
        return {
            "ok": True,
            "status": "PROVISIONAL",
            "check": check(artifact, target),
            "real_target_effects": 0,
            "sandbox_target_effects": 0,
        }, command.output
    elif operation == "cancel":
        artifact = cancel(artifact, target)
    elif operation == "revise":
        require(candidate is not None, "RLS_VFY_NOT_READY", "VFY candidate is required for revise")
        artifact = revise(
            artifact,
            candidate,
            target=target_id,
            target_baseline=target.baseline(),
            retry=bool(payload.get("retry")),
        )
    elif operation == "finalize":
        # Auto-finalization binds the final record to the still-current target.
        check(artifact, target)
        artifact = finalize(artifact)
    else:
        raise ValueError(f"unsupported operation: {operation}")
    return {
        "ok": True,
        "status": "PROVISIONAL",
        "artifact": artifact,
        "real_target_effects": 0,
        "sandbox_target_effects": 1 if artifact.get("target_effect") else 0,
    }, command.output


def render_summary(result: dict) -> str:
    if result.get("state") == "meta":
        return result["display"]
    lines = [f"状态：{result.get('status', 'unknown')}"]
    artifact = result.get("artifact")
    if isinstance(artifact, dict):
        lines.append(f"RLS：{artifact['artifact']['reference']}")
        lines.append(
            f"Conclusion：{artifact['release_conclusion']}；Gate：{artifact['artifact_gate']}"
        )
    lines.append(f"真实目标效果：{result.get('real_target_effects', 0)}")
    return "\n".join(lines)


def main(argv=None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        shared, _spec, command, _values = parse_command(arguments)
        payload = None
        if command.command not in shared["meta"] and not sys.stdin.isatty():
            raw = sys.stdin.read().strip()
            payload = json.loads(raw) if raw else None
        result, output = run_cli(arguments, payload)
        print(
            render_summary(result)
            if output == "summary"
            else json.dumps(result, ensure_ascii=False, sort_keys=True)
        )
        return 0 if result.get("ok") else 2
    except Exception as exc:
        error = (
            exc.to_dict()
            if hasattr(exc, "to_dict")
            else {
                "code": getattr(exc, "code", "RLS_RUNTIME_FAILED"),
                "message": str(exc),
            }
        )
        print(json.dumps({"ok": False, "errors": [error]}, ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Stable VFY CLI: shared parsing, exact authority inputs and structured result."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

sys.dont_write_bytecode = True
PLUGIN_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_ROOT = Path(__file__).resolve().parent
for entry in (PLUGIN_ROOT, SCRIPT_ROOT):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from packages.sdlc_runtime import (  # noqa: E402
    META_COMMANDS,
    SkillArgumentError,
    load_skill_interface,
    parse_skill_command_with_extensions,
    render_commands,
    render_examples,
    render_help,
    render_version,
)
from vfy_authority import compile_candidate  # noqa: E402
from vfy_common import VfyError, load_json_object, require  # noqa: E402

INTERFACE_PATH = Path(__file__).resolve().parents[1] / "references/interface.json"


def _extract_methods(arguments: list[str]) -> tuple[list[str], list[str]]:
    remaining: list[str] = []
    methods: list[str] = []
    index = 0
    while index < len(arguments):
        token = arguments[index]
        if token in {"--method", "-m"}:
            if index + 1 >= len(arguments):
                raise VfyError("VFY_METHOD_NOT_READY", f"{token} requires VFM-NNN")
            value = arguments[index + 1]
            if value not in methods:
                methods.append(value)
            index += 2
            continue
        if token.startswith("--method="):
            value = token.split("=", 1)[1]
            if not value:
                raise VfyError("VFY_METHOD_NOT_READY", "--method requires VFM-NNN")
            if value not in methods:
                methods.append(value)
            index += 1
            continue
        remaining.append(token)
        index += 1
    return remaining, methods


def parse_command(arguments: list[str]):
    normalized, methods = _extract_methods(arguments)
    spec = load_skill_interface(INTERFACE_PATH)
    command, values = parse_skill_command_with_extensions(normalized, spec, {})
    return spec, command, values, methods


def _meta_result(spec: Any, command: Any) -> dict[str, Any]:
    displays = {
        "help": lambda: render_help(spec, command.help_topic)
        + "\n\nVFY options:\n"
        + "  -i, --input REF    repeatable exact Scope/Subject/Control/Exception input\n"
        + "  -r, --reference REF exact persisted VFY Revision for run/revise/check\n"
        + "  -m, --method VFM-NNN repeatable selected Method for run\n"
        + "      persistent create/revise compiles Authority from --input\n",
        "version": lambda: render_version(spec),
        "commands": lambda: render_commands(spec),
        "examples": lambda: render_examples(spec),
    }
    return {
        "contract": "sdlc-ai-spec/skill-command-result/v1",
        "ok": True,
        "state": "meta",
        "command": command.command,
        "display": displays[command.command](),
        "effects": [],
    }


def _persistent(command: Any, body: dict[str, Any]) -> bool:
    if command.dry_run:
        return False
    write_policy = str(getattr(command, "write_policy", "auto"))
    requested = bool(body.get("persist", False))
    if write_policy == "deny":
        return False
    if write_policy in {"allow", "required"}:
        return True
    return requested


def _compile(
    project_root: Path,
    command: Any,
    body: dict[str, Any],
) -> dict[str, Any]:
    hint = body.get("candidate") or body.get("replacement") or body
    require(isinstance(hint, dict), "VFY_CONTRACT_INVALID", "Candidate hint must be an object")
    return compile_candidate(project_root, command.input_references, hint)


def run_cli(arguments: list[str], payload: dict[str, Any] | None = None):
    spec, command, _values, methods = parse_command(arguments)
    if command.command in META_COMMANDS:
        return _meta_result(spec, command), command.output

    from vfy_handler import VfyHandler

    body = {} if payload is None else load_json_object(payload)
    project_root = Path(command.project_root or body.get("project_root") or Path.cwd())
    project_root = project_root.expanduser().resolve()
    require(project_root.is_dir(), "VFY_SCOPE_REQUIRED", "Project root must be an existing directory")
    handler = VfyHandler(project_root)
    operation = "auto" if command.command == "auto" else command.command
    persist = _persistent(command, body)
    selected_methods = methods or body.get("method_ids")
    if selected_methods:
        selected_methods = list(dict.fromkeys(str(item) for item in selected_methods))

    if operation == "auto":
        auto_body = dict(body)
        auto_body["persist"] = persist
        auto_body["method_ids"] = selected_methods
        auto_body["reference"] = command.artifact_reference or body.get("reference")
        if auto_body.get("state") is None and persist:
            auto_body["candidate"] = _compile(project_root, command, body)
        result = handler.auto(auto_body)
    elif operation == "create":
        candidate = _compile(project_root, command, body) if persist else (body.get("candidate") or body)
        result = handler.create(
            candidate,
            persist=persist,
            run_automated=bool(body.get("run_automated", True)),
            allow_commands=bool(body.get("allow_commands", False)),
            finalize=bool(body.get("finalize", False)),
            confirmation=body.get("confirmation"),
        )
    elif operation == "run":
        reference = command.artifact_reference or body.get("reference")
        require(reference is not None, "VFY_REFERENCE_REQUIRED", "run requires exact persisted VFY Revision")
        result = handler.run(
            reference=reference,
            state=None,
            store_generation=None,
            persist=persist,
            method_ids=selected_methods,
            allow_commands=bool(body.get("allow_commands", False)),
            automated_only=False,
            manual_observations=body.get("manual_observations"),
            failure_returns=body.get("failure_returns"),
            early_stop_basis=body.get("early_stop_basis"),
            finalize=bool(body.get("finalize", False)),
            confirmation=body.get("confirmation"),
        )
    elif operation == "revise":
        reference = command.artifact_reference or body.get("reference")
        require(reference is not None, "VFY_REFERENCE_REQUIRED", "revise requires exact prior VFY Revision")
        old_state = handler.check(reference=reference)["state"]
        replacement = _compile(project_root, command, body) if persist else (body.get("candidate") or body.get("replacement"))
        require(isinstance(replacement, dict), "VFY_CONTRACT_INVALID", "revise requires replacement Candidate")
        result = handler.revise(old_state, replacement, persist=persist)
    elif operation == "check":
        reference = command.artifact_reference or body.get("reference")
        require(
            reference is not None and body.get("state") is None,
            "VFY_REFERENCE_REQUIRED",
            "check requires exact persisted VFY Revision and rejects in-memory state",
        )
        result = handler.check(reference=reference)
    else:
        raise VfyError("VFY_CONTRACT_INVALID", f"Unsupported operation: {operation}")

    state = result.get("state")
    return {
        "contract": "sdlc-ai-spec/vfy-runtime-result/v1",
        "ok": True,
        "operation": operation,
        "status": result.get("status"),
        "artifact": state.get("artifact") if isinstance(state, dict) else None,
        "product_result": state.get("product_result") if isinstance(state, dict) else None,
        "artifact_gate": state.get("artifact_gate") if isinstance(state, dict) else None,
        "rls_ready": state.get("rls_ready") if isinstance(state, dict) else False,
        "next_action": state.get("next_action") if isinstance(state, dict) else None,
        "result": result,
        "effective_decision_policy": str(getattr(command, "decision_policy", "auto")),
        "effective_write_policy": str(getattr(command, "write_policy", "auto")),
        "effects": ["artifact_store_write"] if persist else [],
    }, command.output


def render_summary(result: dict[str, Any]) -> str:
    if result.get("state") == "meta":
        return str(result["display"])
    artifact = result.get("artifact") or {}
    return "\n".join(
        (
            f"状态：{result.get('status')}",
            f"VFY：{artifact.get('reference', 'not allocated')}",
            f"Product Result：{result.get('product_result')}",
            f"Artifact Gate：{result.get('artifact_gate')}",
            f"RLS ready：{'yes' if result.get('rls_ready') else 'no'}",
            f"下一步：{result.get('next_action')}",
        )
    )


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        _, command, _, _ = parse_command(arguments)
        payload = None
        if command.command not in META_COMMANDS and not sys.stdin.isatty():
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
        if isinstance(exc, (VfyError, SkillArgumentError)) and hasattr(exc, "to_dict"):
            error = exc.to_dict()
        else:
            error = {"code": getattr(exc, "code", "VFY_RUNTIME_FAILED"), "message": str(exc)}
        print(json.dumps({"ok": False, "errors": [error]}, ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Final RLS CLI: shared parsing and private domain dispatch only."""
from __future__ import annotations

import json
from pathlib import Path
import shlex
import sys

sys.dont_write_bytecode = True
PLUGIN_ROOT = Path(__file__).resolve().parents[3]
for entry in (PLUGIN_ROOT, Path(__file__).resolve().parent):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

INTERFACE_PATH = Path(__file__).resolve().parents[1] / "references/interface.json"
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

    from rls_common import exact_reference, require, assert_no_secret
    from rls_service import RlsService
    from rls_target import SandboxReleaseTarget
    from rls_handler import auto_operation
    from rls_vfy_adapter import read_vfy_candidate

    payload = {} if payload is None else payload
    require(isinstance(payload, dict), "INVALID_ENVELOPE", "business input must be an object")
    assert_no_secret(payload)
    require("artifact" not in payload and "vfy" not in payload,
            "RLS_REFERENCE_NOT_EXACT", "Artifact and VFY authority must be read by exact Store reference")
    allowed = {"sandbox_root", "release_reference", "target", "items", "effect_authorization", "behaviors",
               "force_fail", "pipeline_only", "human_evidence", "exception_authorization", "retry", "final_confirmation", "write_confirmed"}
    require(not (set(payload) - allowed), "INVALID_ENVELOPE", "business envelope contains unsupported fields")
    root = Path(command.project_root or Path.cwd()).expanduser().resolve(strict=True)
    service = RlsService(root)
    operation = command.command
    reference = command.artifact_reference
    inputs = list(command.input_references)
    state = None
    candidate = None
    if reference:
        exact_reference(reference, "RLS")
        state, _ = service.read(reference)
    if inputs:
        require(len(inputs) == 1, "RLS_VFY_NOT_READY", "select exactly one VFY input")
        candidate = read_vfy_candidate(root, exact_reference(inputs[0], "VFY"))
    if state is not None and candidate is not None and operation != "revise":
        require(candidate.vfy_reference == state["release_contract"]["vfy_reference"],
                "RLS_VFY_NOT_READY", "selected input differs from exact persisted RLS binding")
    if operation == "auto" and state is None and candidate is None:
        from packages.sdlc_lifecycle import LifecycleQueryService
        query = LifecycleQueryService(root)
        references = []
        existing = []
        for requirement in query.list_requirements():
            if not requirement.lineage_head:
                continue
            projection = query.inspect_requirement(requirement.reference)
            view = projection.vfy_projection
            if not projection.blockers and view and view.get("revision_state") == "frozen":
                references.append(view["artifact_reference"])
                rls = projection.rls_projection
                if rls and rls.get("next_action") == "SELECT_RLS_TARGET":
                    require(False, "RLS_SCOPE_AMBIGUOUS", "select one exact RLS Target Artifact")
                if rls and rls.get("artifact_reference"):
                    existing.append(rls["artifact_reference"])
        require(len(references) == 1, "RLS_SCOPE_AMBIGUOUS", "auto requires one exact current frozen VFY Scope")
        candidate = read_vfy_candidate(root, references[0])
        if existing:
            require(len(existing) == 1, "RLS_SCOPE_AMBIGUOUS", "select one exact RLS Artifact")
            reference = existing[0]
            state, _ = service.read(reference)
    if operation == "auto":
        operation = auto_operation(candidate, state)
    if operation == "complete":
        return {"ok": True, "status": "completed", "artifact": None, "disposition": candidate.rls_applicability,
                "real_target_effects": 0, "sandbox_target_effects": 0}, command.output
    if operation == "action_required":
        return {"ok": False, "status": "action_required", "errors": [{"code": "RLS_APPLICABILITY_PENDING", "message": "RLS applicability is pending"}],
                "real_target_effects": 0}, command.output
    if operation != "check":
        require(not command.dry_run and command.write_policy != "deny", "RLS_WRITE_DENIED", "Store mutation is forbidden by write policy")
        require(command.write_policy != "confirm" or payload.get("write_confirmed") is True,
                "RLS_WRITE_CONFIRMATION_REQUIRED", "Store write confirmation is required; it does not authorize target effects")
    target_id = values.get("target") or payload.get("target") or (state or {}).get("release_contract", {}).get("release_target")
    target = SandboxReleaseTarget(payload.get("sandbox_root"), target_id)
    if state is not None and operation != "revise":
        require(target_id == state["release_contract"]["release_target"], "RLS_EFFECT_AUTHORIZATION_STALE", "target differs from bound Release Contract")
        requested_release = values.get("release_reference") or payload.get("release_reference")
        require(requested_release is None or requested_release == state["release_contract"]["release_reference"],
                "RLS_EFFECT_AUTHORIZATION_STALE", "release differs from bound Release Contract")
    selected = values.get("items") or payload.get("items") or []
    if isinstance(selected, str):
        selected = [selected]
    if command.command == "auto" and state is not None and not selected:
        key = "release_items" if operation == "execute" else "confirmations"
        selected = [x["id"] for x in state[key] if x["result"] == "pending"]
    generation = None
    if operation == "create":
        require(candidate is not None, "RLS_VFY_NOT_READY", "create requires exact VFY --input")
        state, generation = service.create(candidate.vfy_reference, target,
            release_reference=values.get("release_reference") or payload.get("release_reference"))
        if state.get("artifact") is None:
            return {"ok": True, "status": "completed", "artifact": None, "disposition": state["rls_applicability"],
                    "real_target_effects": 0, "sandbox_target_effects": 0}, command.output
    else:
        require(state is not None, "RLS_REFERENCE_REQUIRED", "operation requires an exact persisted RLS --reference")
        if operation == "check":
            return {"ok": True, "status": "completed", "check": service.check(reference, target),
                    "real_target_effects": 0, "sandbox_target_effects": 0}, command.output
        if operation in {"execute", "confirm"} and payload.get("exception_authorization"):
            require(selected == payload["exception_authorization"].get("scope"), "RLS_EXCEPTION_INVALID", "selected items differ from the host risk grant")
            state, generation = service.waive(reference, target, payload["exception_authorization"])
        elif operation == "execute":
            state, generation = service.execute(reference, target, selected, payload.get("effect_authorization"), behaviors=payload.get("behaviors"))
        elif operation == "confirm":
            state, generation = service.confirm(reference, target, selected, force_fail=bool(payload.get("force_fail")),
                pipeline_only=bool(payload.get("pipeline_only")), human_evidence=payload.get("human_evidence"))
        elif operation == "cancel":
            state, generation = service.cancel(reference, target)
        elif operation == "revise":
            state, generation = service.revise(reference, candidate.vfy_reference if candidate else state["release_contract"]["vfy_reference"], target, retry=bool(payload.get("retry")))
        elif operation == "finalize":
            state, generation = service.finalize(reference, target, payload.get("final_confirmation"))
        else:
            require(False, "INVALID_ENVELOPE", "unsupported RLS operation")
    return {"ok": True, "status": "completed", "artifact": state, "generation": generation,
            "real_target_effects": 0, "sandbox_target_effects": int(bool(state.get("target_effect")))}, command.output


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
        # Unknown exceptions never echo exception text, paths or credential-bearing input.
        from rls_common import sanitize
        error = sanitize({"code": getattr(exc, "code", "RLS_RUNTIME_FAILED"),
                          "message": "RLS request failed; inspect exact local state and recovery records"})
        print(json.dumps({"ok": False, "errors": [error]}, ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

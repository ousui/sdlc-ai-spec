#!/usr/bin/env python3
"""Stable IMP CLI: shared argument normalization and single-operation dispatch."""
from __future__ import annotations

import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
PLUGIN_ROOT = Path(__file__).resolve().parents[3]
for entry in (PLUGIN_ROOT, Path(__file__).resolve().parent):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from packages.sdlc_runtime import (
    META_COMMANDS, SkillArgumentError, execute_phase, load_skill_interface,
    parse_skill_command_with_extensions, render_commands, render_examples,
    render_help, render_version, validate_invocation,
)

INTERFACE_PATH = Path(__file__).resolve().parents[1] / "references/interface.json"
EXTENSIONS = {"binding": ("--binding", "-b"), "owner": ("--owner",)}


def parse_command(arguments):
    spec = load_skill_interface(INTERFACE_PATH)
    command, values = parse_skill_command_with_extensions(arguments, spec, EXTENSIONS)
    return spec, command, values


def run_cli(arguments, payload=None):
    spec, command, values = parse_command(arguments)
    if command.command in META_COMMANDS:
        displays = {
            "help": lambda: render_help(spec, command.help_topic) +
                "\n\nIMP options:\n  -b, --binding REF   exact PLN@Revision#WI or REQ/DSN@Revision\n"
                "  -i, --input REF     repeatable, stable order\n"
                "      --owner TOKEN   stable identity; fallback SDLC_EXECUTOR_TOKEN\n"
                "  -r, --reference REF exact IMP Revision for revise/check/abandon",
            "version": lambda: render_version(spec),
            "commands": lambda: render_commands(spec),
            "examples": lambda: render_examples(spec),
        }
        return {
            "contract": "sdlc-ai-spec/skill-command-result/v1", "ok": True,
            "state": "meta", "command": command.command, "display": displays[command.command](),
            "resolved": command.to_dict(), "effects": [],
        }, command.output
    # No project discovery, Owner resolution, Claim or Store code runs for meta.
    from imp_handler import ImpHandler
    from imp_common import require
    payload = {} if payload is None else payload
    require(isinstance(payload, dict), "IMP_READINESS_FAILED", "stdin payload must be an object")
    root = Path(command.project_root or Path.cwd()).expanduser().resolve()
    require(root.is_dir(), "IMP_READINESS_FAILED", "Project Root must be an existing directory")
    inputs = dict(payload.get("inputs") or {})
    inputs.update(values)
    if command.input_references:
        inputs["input_references"] = list(command.input_references)
    if command.command == "abandon" and command.request_text:
        inputs.setdefault("abandon_reason", command.request_text)
    invocation = {
        "contract": "sdlc-ai-spec/runtime-invocation/v1",
        "operation": "create" if command.command == "auto" else command.command,
        "project_root": str(root), "artifact_reference": command.artifact_reference,
        "inputs": inputs, "confirmations": list(payload.get("confirmations") or []),
        "options": {"dry_run": command.dry_run, "write_policy": command.write_policy},
    }
    handler = ImpHandler(root)
    result = (handler.auto(validate_invocation(invocation)) if command.command == "auto"
              else execute_phase(handler, invocation))
    return result, command.output


def render_summary(result):
    if result.get("state") == "meta":
        return result["display"]
    lines = [f"状态：{result['status']}"]
    info = next((item for item in result["warnings"] if item.get("code") == "IMP_EXECUTION_STATE"), {})
    if info.get("binding"):
        lines.extend([f"Binding：{info['binding']}",
                      f"Owner：{info['owner']}；Attempt：{info['attempt']}；Claim：{info['claim_state']}"])
    if result.get("artifact"):
        lines.append(f"IMP：{result['artifact']['reference']} ({result['artifact']['revision_state']})")
    if info.get("baseline"):
        lines.append("Baseline：" + ", ".join(info["baseline"]))
    if info.get("scope"):
        lines.append("Execution Scope：" + ", ".join(info["scope"]))
    if info.get("approach"):
        lines.append("Approach：" + " → ".join(info["approach"]))
    if info.get("results"):
        lines.extend(["Changed Scope：" + (", ".join(info["changed_scope"]) or "None"),
                      "Result：" + ", ".join(info["results"])])
    for preview in result["warnings"]:
        if preview.get("code") in {"IMP_PRODUCT_CONFIRMATION", "IMP_PREVIEW"}:
            lines.extend([f"Binding：{preview['binding']}",
                          "Execution Scope：" + ", ".join(preview["scope"]),
                          "Baseline：" + json.dumps(preview["baseline"], ensure_ascii=False, sort_keys=True)])
            if preview.get("subject_digest"):
                lines.append("Product Confirmation：" + preview["subject_digest"])
    lines.append(f"Gate：{result['gate']['result']}；VFY ready：{'yes' if info.get('vfy_ready') else 'no'}")
    lines.extend(f"{item['code']}：{item['message']}" for item in result["errors"])
    if result.get("next_action"):
        lines.append("下一步：" + result["next_action"]["message"])
    return "\n".join(lines)


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        _, command, _ = parse_command(arguments)
        payload = None
        if command.command not in META_COMMANDS and not sys.stdin.isatty():
            raw = sys.stdin.read().strip()
            payload = json.loads(raw) if raw else None
        result, output = run_cli(arguments, payload)
        print(render_summary(result) if output == "summary" else json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result.get("ok") else 2
    except Exception as exc:
        error = exc.to_dict() if isinstance(exc, SkillArgumentError) else {
            "code": getattr(exc, "code", "IMP_READINESS_FAILED"), "message": str(exc),
        }
        print(json.dumps({"ok": False, "errors": [error]}, ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

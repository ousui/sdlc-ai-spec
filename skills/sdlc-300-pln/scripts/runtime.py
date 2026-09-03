#!/usr/bin/env python3
"""User-facing CLI for sdlc-300-pln."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
for candidate in (PLUGIN_ROOT, PLUGIN_ROOT / "packages", Path(__file__).resolve().parent):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from packages.sdlc_runtime import (
    RESULT_CONTRACT,
    SkillArgumentError,
    execute_phase,
    load_skill_interface,
    parse_skill_command_with_inputs,
    render_commands,
    render_examples,
    render_help,
    render_version,
)
from pln_runtime import PlnError, PlnHandler

INTERFACE_PATH = Path(__file__).resolve().parents[1] / "references/interface.json"


def _meta(command, display):
    return {"contract":"sdlc-ai-spec/skill-command-result/v1","ok":True,"state":"meta","command":command.command,"display":display,"resolved":command.to_dict(),"effects":[]}


def run_cli(arguments: Sequence[str], payload: Mapping[str, Any] | None = None):
    spec = load_skill_interface(INTERFACE_PATH)
    command = parse_skill_command_with_inputs(arguments, spec)
    if command.command == "help":
        return _meta(command, render_help(spec, command.help_topic) + "\n\nPLN input options:\n  -i, --input REF   repeatable complete REQ/DSN Scope or VFY/RLS Control Input"), command.output
    if command.command == "version": return _meta(command, render_version(spec)), command.output
    if command.command == "commands": return _meta(command, render_commands(spec)), command.output
    if command.command == "examples": return _meta(command, render_examples(spec)), command.output
    root = Path(command.project_root or Path.cwd()).expanduser().resolve()
    if not root.is_dir(): raise PlnError(f"project_root is not an existing directory: {root}")
    operation = command.command
    if operation == "auto": operation = "check" if command.artifact_reference else "create"
    inputs = dict((payload or {}).get("inputs") or {})
    if command.input_references:
        scope=[]; controls=[]
        for item in command.input_references:
            if "#RET-" in item or "#RLI-" in item or "#RCF-" in item: controls.append(item)
            else: scope.append(item)
        inputs.setdefault("scope_inputs", scope); inputs.setdefault("control_inputs", controls)
    invocation={
        "contract":"sdlc-ai-spec/runtime-invocation/v1","operation":operation,
        "project_root":str(root),"artifact_reference":command.artifact_reference,
        "inputs":inputs,"confirmations":list((payload or {}).get("confirmations") or []),
        "options":{"dry_run":command.dry_run,"write_policy":command.write_policy},
    }
    result=execute_phase(PlnHandler(root),invocation)
    return result, command.output


def render_summary(result):
    if result.get("state") == "meta": return str(result.get("display", ""))
    lines=[f"状态：{result.get('status')}"]
    artifact=result.get("artifact")
    if artifact: lines.append("PLN："+(artifact.get("reference") or f"{artifact.get('id')}@{artifact.get('revision')} ({artifact.get('revision_state')})"))
    lines.append(f"Gate：{(result.get('gate') or {}).get('result','pending')}")
    for error in result.get("errors",[]): lines.append(f"错误 {error.get('code')}：{error.get('message')}")
    action=result.get("next_action")
    if action: lines.append(f"下一步：{action.get('message')}")
    return "\n".join(lines)


def main(argv=None):
    try:
        payload={}
        if not sys.stdin.isatty():
            raw=sys.stdin.read().strip()
            if raw:
                payload=json.loads(raw)
                if not isinstance(payload,Mapping): raise PlnError("stdin payload must be a JSON object")
        result,output=run_cli(list(sys.argv[1:] if argv is None else argv),payload)
        print(render_summary(result) if output=="summary" else json.dumps(result,ensure_ascii=False,sort_keys=True))
        return 0 if result.get("ok") else 2
    except (OSError,json.JSONDecodeError,SkillArgumentError,PlnError) as exc:
        error=exc.to_dict() if isinstance(exc,SkillArgumentError) else {"code":getattr(exc,"code","PLN_RUNTIME_ERROR"),"message":str(exc)}
        print(json.dumps({"contract":RESULT_CONTRACT,"ok":False,"errors":[error]},ensure_ascii=False,sort_keys=True)); return 2

if __name__=="__main__": raise SystemExit(main())

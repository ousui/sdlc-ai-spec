#!/usr/bin/env python3
"""User-facing CLI entry for sdlc-200-dsn."""

from dsn_common import *
from dsn_analyzer import DsnAnalyzer
from dsn_builder import DsnBuilder
from dsn_verifier import DsnVerifier
from dsn_handler import DsnHandler, INTERFACE_PATH


def _meta_result(command: SkillCommandWithInputs, display: str) -> dict[str, Any]:
    return {
        "contract": "sdlc-ai-spec/skill-command-result/v1",
        "ok": True,
        "state": "meta",
        "command": command.command,
        "display": display,
        "resolved": command.to_dict(),
        "effects": [],
    }


def _resolve_project(command: SkillCommandWithInputs) -> Path:
    candidate = command.project_root or str(Path.cwd())
    root = Path(candidate).expanduser().resolve()
    if not root.is_dir():
        raise DsnRuntimeError(
            f"project_root is not an existing directory: {root}"
        )
    return root


def _build_invocation(
    command: SkillCommandWithInputs,
    payload: Mapping[str, Any],
    project_root: Path,
) -> dict[str, Any]:
    operation = command.command
    if operation == "auto":
        operation = "check" if command.artifact_reference else "create"
    if operation not in {"create", "revise", "check"}:
        raise DsnRuntimeError(f"unsupported runtime operation: {operation}")
    inputs = dict(payload.get("inputs") or {})
    if command.input_references:
        scope = [
            item
            for item in command.input_references
            if "#RET-" not in item
            and "#RLI-" not in item
            and "#RCF-" not in item
        ]
        controls = [
            item for item in command.input_references if item not in scope
        ]
        inputs.setdefault("scope_inputs", scope)
        inputs.setdefault("control_inputs", controls)
    return {
        "contract": "sdlc-ai-spec/runtime-invocation/v1",
        "operation": operation,
        "project_root": str(project_root),
        "artifact_reference": command.artifact_reference,
        "inputs": inputs,
        "confirmations": list(payload.get("confirmations") or []),
        "options": {
            "dry_run": command.dry_run,
            "write_policy": command.write_policy,
        },
    }


def run_cli(
    arguments: Sequence[str],
    payload: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], str]:
    spec = load_skill_interface(INTERFACE_PATH)
    command = parse_skill_command_with_inputs(arguments, spec)
    if command.command == "help":
        display = render_help(spec, command.help_topic)
        display += (
            "\n\nDSN input options:\n"
            "  -i, --input REF   repeatable REQ Scope Input or VFY/RLS Control Input"
        )
        return _meta_result(command, display), command.output
    if command.command == "version":
        return _meta_result(command, render_version(spec)), command.output
    if command.command == "commands":
        return _meta_result(command, render_commands(spec)), command.output
    if command.command == "examples":
        return _meta_result(command, render_examples(spec)), command.output
    root = _resolve_project(command)
    invocation = _build_invocation(command, payload or {}, root)
    result = execute_phase(DsnHandler(root), invocation)
    if command.output == "debug":
        result = {
            **result,
            "resolved": command.to_dict(),
            "effects": (
                []
                if invocation["operation"] == "check" or command.dry_run
                else [{"type": "write", "target": ".sdlc/store.sqlite3"}]
            ),
        }
    return result, command.output


def render_summary(result: Mapping[str, Any]) -> str:
    if result.get("state") == "meta":
        return str(result.get("display", ""))
    lines = [f"状态：{result.get('status')}"]
    artifact = result.get("artifact")
    if artifact:
        lines.append(
            "DSN："
            + (
                artifact.get("reference")
                or (
                    f"{artifact.get('id')}@{artifact.get('revision')} "
                    f"({artifact.get('revision_state')})"
                )
            )
        )
    gate = result.get("gate") or {}
    lines.append(f"Gate：{gate.get('result', 'pending')}")
    if result.get("open_items"):
        lines.append(f"待确认项：{len(result['open_items'])}")
    for error in result.get("errors", []):
        lines.append(f"错误 {error.get('code')}：{error.get('message')}")
    action = result.get("next_action")
    if action:
        lines.append(f"下一步：{action.get('message')}")
        if action.get("command"):
            lines.append(f"命令：{action['command']}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        payload: Mapping[str, Any] = {}
        if not sys.stdin.isatty():
            text = sys.stdin.read().strip()
            if text:
                value = json.loads(text)
                if not isinstance(value, Mapping):
                    raise DsnRuntimeError(
                        "stdin payload must be a JSON object"
                    )
                payload = value
        result, output = run_cli(arguments, payload)
        if output == "summary":
            print(render_summary(result))
        else:
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result.get("ok") else 2
    except (
        OSError,
        json.JSONDecodeError,
        SkillArgumentError,
        DsnRuntimeError,
    ) as exc:
        error = (
            exc.to_dict()
            if isinstance(exc, SkillArgumentError)
            else {
                "code": getattr(exc, "code", "DSN_RUNTIME_ERROR"),
                "message": str(exc),
            }
        )
        print(
            json.dumps(
                {"contract": RESULT_CONTRACT, "ok": False, "errors": [error]},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

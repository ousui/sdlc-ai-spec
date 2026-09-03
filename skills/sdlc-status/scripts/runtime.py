#!/usr/bin/env python3
"""Strictly read-only user interface for lifecycle status projections."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Callable, Mapping, Sequence

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
for candidate in (PLUGIN_ROOT, PLUGIN_ROOT / "packages"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from packages.sdlc_lifecycle import (  # noqa: E402
    LifecycleQueryError,
    LifecycleQueryService,
    LifecycleStoreUnavailable,
)
from packages.sdlc_runtime import (  # noqa: E402
    SkillArgumentError,
    SkillCommand,
    load_skill_interface,
    parse_skill_command,
    render_commands,
    render_examples,
    render_help,
    render_version,
)

RESULT_CONTRACT = "sdlc-ai-spec/status-result/v1"
INTERFACE_PATH = Path(__file__).resolve().parents[1] / "references/interface.json"
META = {"help", "version", "commands", "examples"}


def _error(code: str, message: str, details: Mapping[str, Any] | None = None):
    result: dict[str, Any] = {"code": code, "message": message}
    if details:
        result["details"] = dict(details)
    return result


def _base_result(command: str, project_root: str | None) -> dict[str, Any]:
    return {
        "contract": RESULT_CONTRACT,
        "ok": True,
        "command": command,
        "status": "completed",
        "project_root": project_root,
        "effective_write_policy": "deny",
        "state": "completed",
        "overview": None,
        "projection": None,
        "warnings": [],
        "errors": [],
        "next_action": None,
    }


def _finish(result: dict[str, Any], command: SkillCommand) -> dict[str, Any]:
    if command.output == "debug":
        result["resolved"] = command.to_dict()
    return result


def _next_action(value):
    if value is None:
        return None
    return value.to_dict() if hasattr(value, "to_dict") else dict(value)


def _projection_action(projection):
    if len(projection.next_actions) > 1:
        return {
            "code": "SELECT_NEXT_ACTION",
            "reason": "存在多个下一动作，请从准确 Binding 对应的候选中选择",
            "requires_user": True,
            "command": None,
        }
    return _next_action(projection.next_actions[0] if projection.next_actions else None)


def _resolve_root(value: str | None, cwd: Path | None) -> Path:
    if value:
        path = Path(value).expanduser()
        if not path.is_absolute():
            raise LifecycleQueryError(
                "project_root must be an absolute directory",
                code="PROJECT_ROOT_INVALID",
                details={"project_root": value},
            )
    else:
        path = Path.cwd() if cwd is None else cwd
    path = path.resolve()
    if not path.exists() or not path.is_dir():
        raise LifecycleQueryError(
            "project_root must be one existing directory",
            code="PROJECT_ROOT_INVALID",
            details={"project_root": str(path)},
        )
    return path


def _not_started(
    root: Path,
    command: str,
    *,
    inspect: bool = False,
    warnings: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    result = _base_result(command, str(root))
    result["warnings"] = [dict(item) for item in warnings]
    if inspect:
        result.update(
            ok=False,
            status="failed",
            state="store_unavailable",
            errors=[
                _error(
                    "LIFECYCLE_STORE_UNAVAILABLE",
                    "项目尚无可读取的 .sdlc/store.sqlite3",
                )
            ],
        )
        return result
    skill_path = PLUGIN_ROOT / "skills/sdlc-000-ctx/SKILL.md"
    action = {
        "code": "START_PROJECT_CONTEXT",
        "phase": "CTX",
        "skill": "sdlc-000-ctx",
        "skill_available": skill_path.is_file(),
        "reason": "项目尚无 CTX 或 REQ Artifact",
        "command": "/sdlc-000-ctx" if skill_path.is_file() else None,
        "requires_user": not skill_path.is_file(),
    }
    result.update(
        status="action_required",
        state="not_started",
        overview={
            "contract": "sdlc-ai-spec/lifecycle-status/v1",
            "state": "not_started",
            "context_candidates": [],
            "requirement_candidates": [],
            "selected_requirement": None,
            "next_actions": [action],
        },
        next_action=action,
    )
    return result


def run_status(
    arguments: str | Sequence[str],
    *,
    cwd: Path | None = None,
    service_factory: Callable[..., LifecycleQueryService] = LifecycleQueryService,
) -> dict[str, Any]:
    spec = load_skill_interface(INTERFACE_PATH)
    command = parse_skill_command(arguments, spec)
    result = _base_result(command.command, None)
    result["warnings"] = [
        {"code": item.code, "message": item.message} for item in command.warnings
    ]
    if command.write_policy != "deny":
        result["warnings"].append(
            {
                "code": "WRITE_POLICY_FORCED_DENY",
                "message": "sdlc-status is strictly read-only; effective write policy is deny",
            }
        )

    if command.command in META:
        result.update(
            state="meta",
            display={
                "help": lambda: render_help(spec, command.help_topic),
                "version": lambda: render_version(spec),
                "commands": lambda: render_commands(spec),
                "examples": lambda: render_examples(spec),
            }[command.command](),
        )
        return _finish(result, command)

    try:
        root = _resolve_root(command.project_root, cwd)
    except LifecycleQueryError as exc:
        result.update(
            ok=False,
            status="failed",
            state="invalid_target",
            errors=[exc.to_dict()],
        )
        return _finish(result, command)
    result["project_root"] = str(root)

    reference = command.artifact_reference
    if command.command == "inspect" and not reference:
        result.update(
            ok=False,
            status="action_required",
            state="reference_required",
            errors=[
                _error(
                    "LIFECYCLE_REFERENCE_INVALID",
                    "inspect 需要准确 REQ-...@数字Revision",
                )
            ],
            next_action={
                "code": "PROVIDE_EXACT_REQUIREMENT",
                "message": "提供准确 REQ Revision，或先执行 /sdlc-status list",
                "requires_user": True,
                "command": "/sdlc-status list",
            },
        )
        return _finish(result, command)

    try:
        service = service_factory(root, plugin_root=PLUGIN_ROOT)
    except LifecycleStoreUnavailable:
        return _finish(
            _not_started(
                root,
                command.command,
                inspect=command.command == "inspect",
                warnings=result["warnings"],
            ),
            command,
        )
    except LifecycleQueryError as exc:
        result.update(
            ok=False,
            status="failed",
            state="query_failed",
            errors=[exc.to_dict()],
        )
        return _finish(result, command)
    except Exception as exc:
        result.update(
            ok=False,
            status="failed",
            state="query_failed",
            errors=[
                _error(
                    getattr(exc, "code", "STATUS_RUNTIME_ERROR"),
                    str(exc),
                )
            ],
        )
        return _finish(result, command)

    try:
        if command.command == "inspect" or (command.command == "auto" and reference):
            projection = service.inspect_requirement(str(reference))
            result.update(
                state=projection.overall_state,
                projection=projection.to_dict(),
                status=(
                    "blocked"
                    if projection.overall_state == "blocked"
                    else "action_required"
                    if projection.overall_state in {"action_required", "selection_required"}
                    else "completed"
                ),
                next_action=_projection_action(projection),
            )
        elif command.command == "list":
            overview = service.project_overview()
            candidates = [item.to_dict() for item in service.list_requirements()]
            overview_data = overview.to_dict()
            overview_data["requirement_candidates"] = candidates
            active_count = len(
                [
                    item
                    for item in candidates
                    if item["lineage_head"] and item["revision_state"] != "abandoned"
                ]
            )
            list_state = "selection_required" if active_count > 1 else overview.state
            result.update(
                state=list_state,
                overview=overview_data,
                status="action_required" if list_state == "selection_required" else "completed",
                next_action=_next_action(
                    overview.next_actions[0] if overview.next_actions else None
                ),
            )
        else:
            overview = service.project_overview()
            if overview.selected_requirement:
                projection = service.inspect_requirement(overview.selected_requirement)
                result.update(
                    state=projection.overall_state,
                    overview=overview.to_dict(),
                    projection=projection.to_dict(),
                    status=(
                        "blocked"
                        if projection.overall_state == "blocked"
                        else "action_required"
                        if projection.overall_state == "action_required"
                        else "completed"
                    ),
                    next_action=_projection_action(projection),
                )
            else:
                result.update(
                    state=overview.state,
                    overview=overview.to_dict(),
                    status=(
                        "action_required"
                        if overview.state in {
                            "not_started",
                            "context_only",
                            "context_action_required",
                            "selection_required",
                        }
                        else "completed"
                    ),
                    next_action=_next_action(
                        overview.next_actions[0] if overview.next_actions else None
                    ),
                )
    except LifecycleQueryError as exc:
        result.update(
            ok=False,
            status="blocked" if exc.code != "LIFECYCLE_REFERENCE_INVALID" else "failed",
            state="query_failed",
            errors=[exc.to_dict()],
        )
    except Exception as exc:  # fail closed at the CLI boundary
        result.update(
            ok=False,
            status="failed",
            state="internal_error",
            errors=[_error("STATUS_RUNTIME_ERROR", str(exc))],
        )
    return _finish(result, command)


def _candidate_line(candidate: Mapping[str, Any], selected: str | None) -> str:
    marker = "*" if candidate.get("reference") == selected else "-"
    head = "head" if candidate.get("lineage_head") else "history"
    return (
        f"{marker} {candidate.get('reference')} | "
        f"{candidate.get('revision_state')}/{candidate.get('artifact_status')} | "
        f"gate={candidate.get('gate_result')} | "
        f"authority={candidate.get('authority_state')} | "
        f"open={candidate.get('open_item_count', 0)} | {head}"
    )


def render_summary(result: Mapping[str, Any]) -> str:
    lines = [f"状态：{result['state']}"]
    if result.get("project_root"):
        lines.append(f"项目：{result['project_root']}")
    projection = result.get("projection")
    overview = result.get("overview")
    if projection:
        lines.append(f"需求：{projection['root_reference']}")
        lines.append("当前前沿：" + (", ".join(projection["frontier"]) or "无"))
        for claim in projection.get("current_claims", []):
            lines.append(
                f"IMP：{claim['binding_reference']} | Owner={claim['owner']} | "
                f"Attempt={claim['attempt']} | Claim={claim['claim_state']}"
            )
            if claim.get("outcome"):
                lines.append(f"结果目标：{claim['outcome']}")
            if claim.get("materialized"):
                lines.append(f"Artifact：{claim['artifact_reference']} ({claim['revision_state']})")
            else:
                lines.append("Artifact：尚未物化，Current Claim 不代表 Artifact 已完成")
            for row in claim.get("results", []):
                lines.append(f"Resource {row['resource']}：{row['baseline_reference']} → {row['result_reference']}")
                lines.append("Changed Scope：" + (", ".join(row.get("changed_scope", [])) or "无"))
            lines.append("当前实施完成：" + ("是" if claim.get("completed") else "否"))
            lines.append("VFY 就绪：" + ("是" if claim.get("vfy_ready") else "否"))
        if projection.get("vfy_inputs"):
            lines.append("VFY 输入：" + ", ".join(projection["vfy_inputs"]))
        for row in projection.get("vfy_results", []):
            lines.append(f"VFY Resource {row['resource']}：{row['result_reference']}")
        blockers = projection.get("blockers", [])
        if blockers:
            lines.append(f"阻塞项：{len(blockers)}")
            for item in blockers:
                reference = f" [{item.get('reference')}]" if item.get("reference") else ""
                lines.append(
                    f"- {item.get('code', 'BLOCKER')}{reference}：{item.get('message', '')}"
                )
        else:
            lines.append("阻塞项：无")
    elif overview:
        contexts = overview.get("context_candidates", [])
        candidates = overview.get("requirement_candidates", [])
        lines.append(f"CTX 候选：{len(contexts)}")
        for context in contexts:
            lines.append(
                f"- {context.get('reference')} | "
                f"{context.get('revision_state')}/{context.get('artifact_status')} | "
                f"authority={context.get('authority_state')}"
            )
        lines.append(f"REQ 候选：{len(candidates)}")
        for candidate in candidates:
            lines.append(_candidate_line(candidate, overview.get("selected_requirement")))
        if overview.get("selected_requirement"):
            lines.append(f"已选择：{overview['selected_requirement']}")
    for error in result.get("errors", []):
        lines.append(f"错误 {error['code']}：{error['message']}")
    actions = (projection or {}).get("next_actions", [])
    if not actions:
        actions = [result["next_action"]] if result.get("next_action") else []
    for action in actions:
        lines.append(
            f"下一步：{action.get('reason') or action.get('message') or action.get('code')}"
        )
        if action.get("command"):
            lines.append(f"命令：{action['command']}")
        if action.get("skill") and not action.get("skill_available", False):
            lines.append(f"对应 Skill 尚未安装：{action['skill']}")
    return "\n".join(lines)


def emit(result: Mapping[str, Any], output: str) -> None:
    if result.get("state") == "meta" and output != "debug":
        print(result.get("display", ""))
    elif output == "summary":
        print(render_summary(result))
    else:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        spec = load_skill_interface(INTERFACE_PATH)
        parsed = parse_skill_command(arguments, spec)
        result = run_status(arguments)
        emit(result, parsed.output)
        return 0 if result["ok"] else 2
    except (OSError, json.JSONDecodeError, SkillArgumentError) as exc:
        error = (
            exc.to_dict()
            if isinstance(exc, SkillArgumentError)
            else _error("INTERFACE_SPEC_INVALID", str(exc))
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

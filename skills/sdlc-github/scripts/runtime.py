#!/usr/bin/env python3
"""Offline invocation compiler. Calls no MCP or network; the host calls tools."""
from __future__ import annotations
import json
import os
from pathlib import Path
import shlex
import stat
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from packages.sdlc_runtime.skill_args import (load_skill_interface, SkillArgumentError, META_COMMANDS,
    render_help, render_commands, render_version, render_examples)
from packages.sdlc_runtime.skill_command import parse_skill_command
from packages.sdlc_runtime.local_paths import directory
from packages.sdlc_github.operations import validate_request, READS
from packages.sdlc_github.models import GithubError, ensure_no_secret, redact
from packages.sdlc_github.targets import parse_url, merge_target, repository_from_remotes

SPEC_PATH = Path(__file__).resolve().parents[1] / "references/interface.json"
BUSINESS = {"repo": "repository", "url": "url", "kind": "operation", "number": "number", "title": "title", "body": "body", "body-file": "body_file",
            "head": "head", "base": "base", "state": "state", "page": "page", "per-page": "per_page", "after": "after", "request-id": "request_id",
            "path": "path", "ref": "ref", "sha": "sha", "workflow-id": "workflow_id", "run-id": "run_id", "job-id": "job_id", "tag": "tag",
            "subject-type": "subject_type", "expected-actor-id": "expected_actor_id", "reconcile": "reconcile"}
NUMBERS = {"number", "page", "per_page", "run_id", "job_id", "expected_actor_id"}
COMMANDS = {"status": "sdlc_github_status", "read": "sdlc_github_read", "issue-create": "sdlc_github_issue_create",
            "issue-update": "sdlc_github_issue_update", "comment": "sdlc_github_comment_create", "pr-create": "sdlc_github_pr_create",
            "pr-update": "sdlc_github_pr_update", "receipt": "sdlc_github_operation_status"}


def compile_invocation(arguments, *, remotes=None):
    try:
        tokens = shlex.split(arguments) if isinstance(arguments, str) else list(arguments)
    except ValueError:
        raise SkillArgumentError("ARGUMENT_QUOTE_ERROR", "Unclosed argument quote") from None
    common, business = [], {}
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token == "--":
            common.extend(tokens[i:]); break
        name, equal, val = token.partition("=")
        key = BUSINESS.get(name[2:]) if name.startswith("--") else None
        if key:
            if not equal:
                if i + 1 >= len(tokens) or tokens[i + 1].startswith("--"):
                    raise SkillArgumentError("ARGUMENT_VALUE_REQUIRED", "Business option requires a value")
                i += 1; val = tokens[i]
            if key in NUMBERS:
                if not val.isdigit():
                    raise SkillArgumentError("ARGUMENT_VALUE_INVALID", "An integer is required")
                val = int(val)
            if key == "reconcile":
                if val not in {"true", "false"}:
                    raise SkillArgumentError("ARGUMENT_VALUE_INVALID", "reconcile must be true or false")
                val = val == "true"
            if key in business and business[key] != val:
                raise SkillArgumentError("ARGUMENT_CONFLICT", "Conflicting business values")
            business[key] = val
        else:
            common.append(token)
        i += 1
    spec = load_skill_interface(SPEC_PATH)
    try:
        command = parse_skill_command(common, spec)
    except ValueError as error:
        if isinstance(error, SkillArgumentError):
            raise
        raise SkillArgumentError("ARGUMENT_QUOTE_ERROR", "Invalid argument quoting") from None
    if command.command in META_COMMANDS:
        if business:
            raise SkillArgumentError("ARGUMENT_CONFLICT", "Meta commands cannot include business options")
        text = {"help": lambda: render_help(spec, command.help_topic) + "\n\nGitHub options: " + " ".join("--" + k for k in BUSINESS) + "\nRead kinds: " + ", ".join(READS),
                "commands": lambda: render_commands(spec), "version": lambda: render_version(spec), "examples": lambda: render_examples(spec)}[command.command]()
        return {"ok": True, "status": "completed", "effects": [], "text": text, "output": command.output}
    name = command.command
    if name == "auto":
        if command.request_text or business:
            return {"ok": False, "status": "action_required", "effects": [], "next_action": "Resolve the user's exact intent and rerun with one declared command; no write authorization was inferred.", "output": command.output}
        name = "status"
    if command.request_text:
        return {"ok": False, "status": "action_required", "effects": [], "next_action": "Normalize free-form intent to exact command fields before invoking MCP.", "output": command.output}
    if name not in COMMANDS:
        raise GithubError("ARGUMENT_INVALID")
    if "body_file" in business and "body" in business:
        raise SkillArgumentError("ARGUMENT_CONFLICT", "body and body-file are mutually exclusive")
    if "url" in business:
        url = business.pop("url")
        business = merge_target(business, parse_url(url, ref=business.get("ref"), path=business.get("path")))
        if "subject_type" in business and name != "comment":
            expected = "issue" if name.startswith("issue-") or str(business.get("operation", "")).startswith("issue.") else "pr" if name.startswith("pr-") or str(business.get("operation", "")).startswith("pr.") else None
            if expected and expected != business["subject_type"]:
                raise GithubError("TARGET_MISMATCH")
            if expected:
                business.pop("subject_type")
    if name != "status" and "repository" not in business:
        business["repository"] = repository_from_remotes(remotes or [])
    if "body_file" in business:
        file = Path(business.pop("body_file"))
        if not file.is_absolute():
            if not command.project_root or not Path(command.project_root).is_absolute():
                raise GithubError("ARGUMENT_INVALID")
            file = Path(command.project_root) / file
        if ".." in file.parts or file.is_symlink():
            raise GithubError("STORAGE_UNSAFE")
        try:
            with directory(file.parent, ()) as parent_fd:
                fd = os.open(file.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
            try:
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or info.st_size > 65536:
                    raise GithubError("ARGUMENT_INVALID")
                body = os.read(fd, 65537)
                if len(body) > 65536:
                    raise GithubError("ARGUMENT_INVALID")
                business["body"] = body.decode("utf-8")
            finally:
                os.close(fd)
        except (OSError, UnicodeDecodeError):
            raise GithubError("ARGUMENT_INVALID") from None
    tool = COMMANDS[name]
    writing = name in {"issue-create", "issue-update", "comment", "pr-create", "pr-update"}
    if writing:
        business.setdefault("request_id", str(uuid4()))
        business["write_policy"] = command.write_policy
        business["dry_run"] = command.dry_run
    if (writing or name == "receipt") and "expected_actor_id" not in business:
        return {"ok": False, "status": "action_required", "effects": [], "request_id": business.get("request_id"),
                "next_action": "Call sdlc_github_status; reuse this request_id and supply the returned id via --expected-actor-id. Do not ask the user to invent IDs.", "output": command.output}
    ensure_no_secret(business)
    operation, normalized = validate_request(tool, business)
    if tool == "sdlc_github_read":
        normalized["operation"] = operation
    return {"ok": True, "status": "action_required", "effects": [], "tool": tool, "arguments": normalized,
            "source_reference": command.artifact_reference, "decision_policy": command.decision_policy,
            "next_action": "Host calls the declared MCP tool only within the current explicit user authorization. Reuse request_id for retries.", "output": command.output}


def main(argv=None):
    try:
        response = compile_invocation(sys.argv[1:] if argv is None else argv)
        response = redact(response)
    except (SkillArgumentError, GithubError) as error:
        response = {"ok": False, "status": "blocked", "errors": [{"code": error.code, "message": "Invalid invocation; use help. No network or remote effect."}], "effects": [], "output": "json"}
    if response.get("output") == "json" or response.get("output") == "debug":
        print(json.dumps(response, ensure_ascii=False, sort_keys=True))
    else:
        print(response.get("text") or ("状态：" + response["status"] + "\n" + response.get("next_action", "参数无效；使用 help。")))
    return 0 if response.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())

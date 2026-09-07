"""Closed 27-read / 5-write catalog. No caller-supplied upstream methods."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass
import re
from uuid import UUID

from .models import GithubError


def string(maximum=1024, minimum=1):
    return {"type": "string", "minLength": minimum, "maxLength": maximum}


def integer(maximum=2**53 - 1):
    return {"type": "integer", "minimum": 1, "maximum": maximum}


REPOSITORY = {**string(201), "pattern": r"^[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+$"}
FIELDS = {
    "repository": REPOSITORY, "path": string(4096, 0), "ref": string(1024), "sha": string(1024),
    "tag": string(1024), "number": integer(), "workflow_id": string(1024), "run_id": integer(), "job_id": integer(),
    "page": integer(1000000), "per_page": integer(100), "after": string(4096),
    "state": {"enum": ["open", "closed", "all"]}, "head": string(1024), "base": string(1024),
    "title": {**string(256), "pattern": r"\S"}, "body": string(65000, 0),
    "subject_type": {"enum": ["issue", "pr"]},
    "expected_actor_id": integer(),
    "request_id": {"type": "string", "pattern": r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"},
    "write_policy": {"enum": ["auto", "confirm", "deny"], "default": "auto"},
    "dry_run": {"type": "boolean", "default": False}, "reconcile": {"type": "boolean", "default": False},
}
PAGE = ("page", "per_page")
CURSOR = ("after", "per_page")
WRITE_CONTROL = ("expected_actor_id", "request_id", "write_policy", "dry_run")


@dataclass(frozen=True)
class Operation:
    tool: str
    method: str | None = None
    fields: tuple[str, ...] = ()
    required: tuple[str, ...] = ()
    pagination: str = "none"
    shape: str = "object"
    write: bool = False


OPERATIONS = {
    "repo.files": Operation("get_file_contents", fields=("path", "ref", "sha"), shape="files"),
    "repo.branches": Operation("list_branches", fields=PAGE, pagination="page", shape="list"),
    "repo.commits": Operation("list_commits", fields=("sha", "path", *PAGE), pagination="page", shape="list"),
    "repo.commit": Operation("get_commit", fields=("sha", *PAGE), required=("sha",), pagination="page", shape="commit"),
    "repo.tags": Operation("list_tags", fields=PAGE, pagination="page", shape="list"),
    "repo.tag": Operation("get_tag", fields=("tag",), required=("tag",), shape="tag"),
    "issue.list": Operation("list_issues", fields=("state", *CURSOR), pagination="cursor", shape="list"),
    "issue.get": Operation("issue_read", "get", ("number",), ("number",), shape="issue"),
    "issue.comments": Operation("issue_read", "get_comments", ("number", *PAGE), ("number",), "page", "list"),
    "pr.list": Operation("list_pull_requests", fields=("state", "head", "base", *PAGE), pagination="page", shape="list"),
    "pr.get": Operation("pull_request_read", "get", ("number",), ("number",), shape="pr"),
    "pr.diff": Operation("pull_request_read", "get_diff", ("number",), ("number",), shape="text"),
    "pr.files": Operation("pull_request_read", "get_files", ("number", *PAGE), ("number",), "page", "list"),
    "pr.reviews": Operation("pull_request_read", "get_reviews", ("number", *PAGE), ("number",), "page", "list"),
    "pr.review-comments": Operation("pull_request_read", "get_review_comments", ("number", *CURSOR), ("number",), "cursor", "list"),
    "pr.comments": Operation("pull_request_read", "get_comments", ("number", *PAGE), ("number",), "page", "list"),
    "pr.checks": Operation("pull_request_read", "get_check_runs", ("number", *PAGE), ("number",), "page", "checks"),
    "pr.status": Operation("pull_request_read", "get_status", ("number",), ("number",), shape="status"),
    "actions.workflows": Operation("actions_list", "list_workflows", PAGE, pagination="page", shape="list"),
    "actions.runs": Operation("actions_list", "list_workflow_runs", ("workflow_id", *PAGE), pagination="page", shape="list"),
    "actions.jobs": Operation("actions_list", "list_workflow_jobs", ("run_id", *PAGE), ("run_id",), "page", "list"),
    "actions.artifacts": Operation("actions_list", "list_workflow_run_artifacts", ("run_id", *PAGE), ("run_id",), "page", "list"),
    "actions.run": Operation("actions_get", "get_workflow_run", ("run_id",), ("run_id",), shape="run"),
    "actions.logs": Operation("get_job_logs", fields=("job_id",), required=("job_id",), shape="text"),
    "release.list": Operation("list_releases", fields=PAGE, pagination="page", shape="list"),
    "release.get": Operation("get_release_by_tag", fields=("tag",), required=("tag",), shape="release"),
    "release.latest": Operation("get_latest_release", shape="release"),
    "issue.create": Operation("issue_write", "create", ("title", "body"), ("title",), shape="issue", write=True),
    "issue.update": Operation("issue_write", "update", ("number", "title", "body", "state"), ("number",), shape="issue", write=True),
    "comment.create": Operation("add_issue_comment", fields=("number", "subject_type", "body"), required=("number", "subject_type", "body"), shape="comment", write=True),
    "pr.create": Operation("create_pull_request", fields=("head", "base", "title", "body"), required=("head", "base", "title"), shape="pr", write=True),
    "pr.update": Operation("update_pull_request", fields=("number", "title", "body", "state"), required=("number",), shape="pr", write=True),
}
READS = tuple(k for k, v in OPERATIONS.items() if not v.write)
WRITES = tuple(k for k, v in OPERATIONS.items() if v.write)
WRITE_TOOLS = {"sdlc_github_" + k.replace(".", "_"): k for k in WRITES}
TOOLS = ("sdlc_github_status", "sdlc_github_read", *WRITE_TOOLS, "sdlc_github_operation_status")


def operation_schema(name: str, *, discriminator=False) -> dict:
    op = OPERATIONS[name]
    fields = ("repository", *op.fields, *(WRITE_CONTROL if op.write else ()))
    properties = {k: deepcopy(FIELDS[k]) for k in fields}
    required = ["repository", *op.required]
    if name == "comment.create":
        properties["body"] = {**properties["body"], "minLength": 1, "pattern": r"\S"}
    if op.write:
        required += ["expected_actor_id", "request_id"]
        if "state" in properties:
            properties["state"] = {"enum": ["open", "closed"]}
    if discriminator:
        properties["operation"] = {"const": name}
        required += ["operation"]
    schema = {"type": "object", "properties": properties, "required": required, "additionalProperties": False}
    if name.endswith(".update"):
        schema["anyOf"] = [{"required": [f]} for f in ("title", "body", "state")]
    return schema


def tool_schema(tool: str) -> dict:
    if tool == "sdlc_github_status":
        return {"type": "object", "properties": {}, "additionalProperties": False}
    if tool == "sdlc_github_read":
        # Top-level type/properties aid hosts; oneOf still enforces per-operation fields.
        properties = {"operation": {"enum": list(READS)}}
        for name in READS:
            properties.update(operation_schema(name)["properties"])
        return {"type": "object", "properties": properties, "required": ["operation", "repository"],
                "oneOf": [operation_schema(k, discriminator=True) for k in READS]}
    if tool in WRITE_TOOLS:
        return operation_schema(WRITE_TOOLS[tool])
    if tool == "sdlc_github_operation_status":
        return {"type": "object", "properties": {k: deepcopy(FIELDS[k]) for k in ("repository", "expected_actor_id", "request_id", "reconcile")},
                "required": ["repository", "expected_actor_id", "request_id"], "additionalProperties": False}
    raise GithubError("ARGUMENT_INVALID")


def validate_request(tool: str, payload: dict) -> tuple[str, dict]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        raise GithubError("DEPENDENCY_UNAVAILABLE") from None
    schema = tool_schema(tool)
    if not isinstance(payload, dict) or not Draft202012Validator(schema).is_valid(payload):
        raise GithubError("ARGUMENT_INVALID")
    data = deepcopy(payload)
    if "repository" in data:
        repo = data["repository"]
        if any(p in {".", ".."} for p in repo.split("/")) or len(repo.split("/")[0]) > 39:
            raise GithubError("ARGUMENT_INVALID")
        data["repository"] = repo.lower()
    for field in ("path", "ref", "sha", "head", "base", "tag", "workflow_id"):
        if field in data:
            text = data[field]
            if "\\" in text or any(ord(c) < 32 for c in text) or text.startswith("/") or any(p in {".", ".."} for p in text.split("/")):
                raise GithubError("ARGUMENT_INVALID")
    if "ref" in data and "sha" in data:
        raise GithubError("ARGUMENT_INVALID")
    if data.get("head") is not None and data.get("head") == data.get("base"):
        raise GithubError("ARGUMENT_INVALID")
    operation = (data.pop("operation") if tool == "sdlc_github_read" else WRITE_TOOLS.get(tool, tool.removeprefix("sdlc_github_")))
    if operation in OPERATIONS:
        op = OPERATIONS[operation]
        if op.pagination != "none":
            data.setdefault("per_page", 30)
            if op.pagination == "page":
                data.setdefault("page", 1)
        if op.write:
            data.setdefault("write_policy", "auto")
            data.setdefault("dry_run", False)
            if operation.endswith(".create"):
                data.setdefault("body", "")
        if operation == "repo.files":
            data.setdefault("path", "")
    return operation, data


def map_upstream(name: str, data: dict) -> tuple[str, dict]:
    op = OPERATIONS[name]
    owner, repo = data["repository"].split("/")
    mapped = {"owner": owner, "repo": repo}
    if op.method:
        mapped["method"] = op.method
    for field in op.fields:
        if field not in data or field == "subject_type":
            continue
        dest = {"per_page": "perPage", "workflow_id": "resource_id", "run_id": "resource_id"}.get(field, field)
        if field == "number":
            dest = "pullNumber" if op.tool in {"pull_request_read", "update_pull_request"} else "issue_number"
        mapped[dest] = str(data[field]) if dest == "resource_id" else data[field]
    if name == "issue.list" and "state" in mapped:
        if mapped["state"] == "all":
            mapped.pop("state")
        else:
            mapped["state"] = mapped["state"].upper()
    if name == "pr.create":
        mapped["draft"] = True
    if name == "actions.logs":
        mapped["return_content"] = True
    return op.tool, mapped


def marker(request_id: str) -> str:
    if str(UUID(request_id)) != request_id:
        raise GithubError("ARGUMENT_INVALID")
    return f"<!-- sdlc-github:{request_id} -->"

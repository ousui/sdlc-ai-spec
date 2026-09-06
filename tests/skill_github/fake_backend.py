"""Stateful synthetic GitHub MCP. Independent wire schemas, no network calls."""
from __future__ import annotations
from contextlib import asynccontextmanager
from copy import deepcopy
import json
from pathlib import Path
from mcp import types
from packages.sdlc_github.transport import Upstream, unpack
from packages.sdlc_github.models import GithubError, redact

S = {"type": "string"}
N = {"type": "number"}
B = {"type": "boolean"}
OWNER = {"owner": S, "repo": S}
PAGE = {"page": N, "perPage": N}
# These are reviewed fixture schemas, not generated from runtime.operation_schema.
SCHEMAS = {
    "get_me": ({}, []),
    "get_file_contents": ({**OWNER, "path": S, "ref": S, "sha": S}, ["owner", "repo"]),
    "list_branches": ({**OWNER, **PAGE}, ["owner", "repo"]),
    "list_commits": ({**OWNER, **PAGE, "sha": S, "path": S}, ["owner", "repo"]),
    "get_commit": ({**OWNER, **PAGE, "sha": S}, ["owner", "repo", "sha"]),
    "list_tags": ({**OWNER, **PAGE}, ["owner", "repo"]),
    "get_tag": ({**OWNER, "tag": S}, ["owner", "repo", "tag"]),
    "list_issues": ({**OWNER, "after": S, "perPage": N, "state": S}, ["owner", "repo"]),
    "issue_read": ({**OWNER, **PAGE, "issue_number": N, "method": {"type": "string", "enum": ["get", "get_comments"]}}, ["owner", "repo", "issue_number", "method"]),
    "pull_request_read": ({**OWNER, **PAGE, "after": S, "pullNumber": N, "method": {"type": "string", "enum": ["get", "get_diff", "get_files", "get_reviews", "get_review_comments", "get_comments", "get_check_runs", "get_status"]}}, ["owner", "repo", "pullNumber", "method"]),
    "list_pull_requests": ({**OWNER, **PAGE, "state": S, "head": S, "base": S}, ["owner", "repo"]),
    "actions_list": ({**OWNER, **PAGE, "resource_id": S, "method": {"type": "string", "enum": ["list_workflows", "list_workflow_runs", "list_workflow_jobs", "list_workflow_run_artifacts"]}}, ["owner", "repo", "method"]),
    "actions_get": ({**OWNER, "resource_id": S, "method": {"type": "string", "enum": ["get_workflow_run"]}}, ["owner", "repo", "method", "resource_id"]),
    "get_job_logs": ({**OWNER, "job_id": N, "return_content": B}, ["owner", "repo"]),
    "list_releases": ({**OWNER, **PAGE}, ["owner", "repo"]),
    "get_release_by_tag": ({**OWNER, "tag": S}, ["owner", "repo", "tag"]),
    "get_latest_release": (OWNER, ["owner", "repo"]),
    "issue_write": ({**OWNER, "method": {"type": "string", "enum": ["create", "update"]}, "issue_number": N, "title": S, "body": S, "state": S}, ["owner", "repo", "method"]),
    "add_issue_comment": ({**OWNER, "issue_number": N, "body": S}, ["owner", "repo", "issue_number"]),
    "create_pull_request": ({**OWNER, "title": S, "body": S, "head": S, "base": S, "draft": B}, ["owner", "repo", "title", "head", "base"]),
    "update_pull_request": ({**OWNER, "pullNumber": N, "title": S, "body": S, "state": S}, ["owner", "repo", "pullNumber"]),
}
WRITE_NAMES = {"issue_write", "add_issue_comment", "create_pull_request", "update_pull_request"}


def definitions():
    tools = {k: types.Tool(name=k, inputSchema={"type": "object", "properties": deepcopy(props), "required": list(required), "additionalProperties": False}) for k, (props, required) in SCHEMAS.items()}
    fixture = json.loads((Path(__file__).parent / "fixtures/hosted-contracts.json").read_text())
    for op, name in (("issue.list", "list_issues"), ("comment.create", "add_issue_comment")):
        tools[name] = types.Tool(name=name, inputSchema=fixture["schemas"][op])
    return tools


def envelope(value):
    return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps(value))])


class Backend:
    def __init__(self, actor=101, state_file=None):
        self.actor = actor
        self.calls = []
        self.tools = definitions()
        self.failures = {}
        self.replacements = {}
        self.after_write_error = None
        self.state_file = Path(state_file) if state_file else None
        self.page_metadata = True
        self.return_invalid_json = False
        self.issue = self.object(1, "issue", title="Original issue")
        self.pr = self.object(2, "pr", title="Original draft")
        self.objects = {1: self.issue, 2: self.pr}
        self.comments = {1: [], 2: []}
        self.next_number = 3
        self.next_comment = 1000
        self.branches = ["main", "fixture/topic"]

    def object(self, number, kind, **fields):
        item = {"id": 10000 + number, "number": number, "title": "Synthetic", "body": "", "state": "open",
                "html_url": f"https://github.com/example/project/{'issues' if kind == 'issue' else 'pull'}/{number}",
                "user": {"id": self.actor, "login": f"fixture-{self.actor}"}}
        if kind == "pr":
            item.update({"draft": True, "head": {"ref": "fixture/topic"}, "base": {"ref": "main"}, "merged": False})
        item.update(fields)
        return item

    @property
    def writes(self):
        return [row for row in self.calls if row[0] in WRITE_NAMES]

    def save(self):
        if self.state_file:
            state = {"calls": self.calls, "writes": len(self.writes), "objects": self.objects, "comments": self.comments}
            self.state_file.write_text(json.dumps(redact(state)))

    def page(self, values, args, key="items", cursor=False):
        page = int(args.get("page", 1))
        if cursor:
            page = int(args.get("after", "1"))
        size = int(args.get("perPage", 30))
        selected = deepcopy(values[(page - 1) * size:page * size])
        if not self.page_metadata:
            return selected
        if cursor:
            return {key: selected, "pageInfo": {"hasNextPage": page * size < len(values), "endCursor": str(page + 1) if page * size < len(values) else None}}
        return {key: selected, "total_count": len(values)}

    async def call(self, tool, args):
        self.calls.append((tool, deepcopy(args)))
        self.save()
        key = tool + ":" + args.get("method", "")
        if key in self.failures or tool in self.failures:
            code = self.failures.get(key, self.failures.get(tool))
            return types.CallToolResult(isError=True, content=[types.TextContent(type="text", text=f"upstream status {code}")])
        if key in self.replacements or tool in self.replacements:
            replacement = self.replacements.get(key, self.replacements.get(tool))
            return replacement if isinstance(replacement, types.CallToolResult) else envelope(deepcopy(replacement))
        value = self.execute(tool, args)
        self.save()
        if tool in WRITE_NAMES and self.after_write_error:
            raise GithubError(self.after_write_error)
        if self.return_invalid_json and tool != "get_me":
            return types.CallToolResult(content=[types.TextContent(type="text", text="not-json")])
        return value if isinstance(value, types.CallToolResult) else envelope(value)

    def execute(self, tool, a):
        method = a.get("method")
        if tool == "get_me":
            return {"id": self.actor, "login": f"fixture-{self.actor}"}
        if tool == "get_file_contents":
            path = a.get("path", "")
            if not path:
                return [{"path": "README.md", "name": "README.md", "sha": "a" * 40, "type": "file"}]
            return types.CallToolResult(content=[types.TextContent(type="text", text="successfully downloaded text file (SHA: " + "a" * 40 + ")"),
                types.EmbeddedResource(type="resource", resource=types.TextResourceContents(uri=f"repo://example/project/sha/{a.get('sha', 'a' * 40)}/contents/{path}", text="Synthetic README\n", mimeType="text/plain"))])
        if tool == "list_branches":
            return self.page([{"name": x, "commit": {"sha": "a" * 40}} for x in self.branches], a)
        if tool in {"get_commit", "list_commits"}:
            value = {"sha": "a" * 40, "commit": {"message": "fixture"}, "files": []}
            return value if tool == "get_commit" else self.page([value], a)
        if tool in {"get_tag", "list_tags"}:
            value = {"name": "v1.0.0", "tag": "v1.0.0", "sha": "a" * 40, "commit": {"sha": "a" * 40}}
            return {"ref": "refs/tags/" + a["tag"], "object": {"type": "commit", "sha": "a" * 40}} if tool == "get_tag" else self.page([value], a)
        if tool == "list_issues":
            return self.page([x for x in self.objects.values() if "draft" not in x and (not a.get("state") or x["state"].upper() == a["state"])], a, "issues", cursor=True)
        if tool == "list_pull_requests":
            return self.page([x for x in self.objects.values() if "draft" in x], a, "pull_requests")
        if tool in {"issue_read", "pull_request_read"}:
            n = int(a.get("issue_number", a.get("pullNumber")))
            if n not in self.objects:
                return types.CallToolResult(isError=True, content=[types.TextContent(type="text", text="404 not found")])
            if method == "get":
                return deepcopy(self.objects[n])
            if method == "get_comments":
                return self.page(self.comments.get(n, []), a, "comments")
            if method == "get_diff":
                return types.CallToolResult(content=[types.TextContent(type="text", text="diff --git a/README.md b/README.md\n+synthetic\n")])
            if method == "get_files":
                return self.page([{"filename": "README.md", "status": "modified"}], a)
            if method == "get_reviews":
                return self.page([{"id": 300, "state": "COMMENTED"}], a)
            if method == "get_review_comments":
                return self.page([{"id": "PRRT_fixture", "comments": []}], a, "threads", cursor=True)
            if method == "get_check_runs":
                return self.page([{"id": 500, "status": "completed", "conclusion": "success"}], a, "check_runs")
            if method == "get_status":
                return {"state": "success", "sha": "a" * 40, "statuses": [], "total_count": 0}
        if tool == "actions_list":
            key, records = {"list_workflows": ("workflows", [{"id": 99, "path": ".github/workflows/ci.yml"}]),
                            "list_workflow_runs": ("workflow_runs", [{"id": 100, "status": "completed"}]),
                            "list_workflow_jobs": ("jobs", [{"id": 101, "run_id": 100, "status": "completed"}]),
                            "list_workflow_run_artifacts": ("artifacts", [{"id": 102, "name": "synthetic"}])}[method]
            if method == "list_workflow_jobs":
                records[0]["run_id"] = int(a["resource_id"])
            paged = self.page(records, a, key)
            return {"jobs": paged} if method == "list_workflow_jobs" and isinstance(paged, dict) else paged
        if tool == "actions_get":
            return {"id": int(a["resource_id"]), "status": "completed", "conclusion": "success"}
        if tool == "get_job_logs":
            return {"job_id": int(a["job_id"]), "logs_content": "synthetic log\n", "original_length": 14}
        if tool in {"list_releases", "get_release_by_tag", "get_latest_release"}:
            value = {"id": 200, "tag_name": "v1.0.0", "html_url": "https://github.com/example/project/releases/tag/v1.0.0"}
            return self.page([value], a) if tool == "list_releases" else value
        if tool in {"issue_write", "create_pull_request", "update_pull_request"}:
            if tool == "create_pull_request" or (tool == "issue_write" and method == "create"):
                n = self.next_number; self.next_number += 1
                kind = "pr" if tool == "create_pull_request" else "issue"
                item = self.object(n, kind)
                self.objects[n] = item
                self.comments[n] = []
            else:
                n = int(a.get("issue_number", a.get("pullNumber")))
                item = self.objects[n]
            for key in ("title", "body", "state", "draft"):
                if key in a:
                    item[key] = a[key]
            for key in ("head", "base"):
                if key in a:
                    item[key] = {"ref": a[key]}
            return {"id": str(item["id"]), "url": item["html_url"]}
        if tool == "add_issue_comment":
            n = int(a["issue_number"]); cid = self.next_comment; self.next_comment += 1
            item = {"id": cid, "body": a["body"], "html_url": self.objects[n]["html_url"] + f"#issuecomment-{cid}", "user": {"id": self.actor, "login": f"fixture-{self.actor}"}}
            self.comments[n].append(item)
            return item
        raise AssertionError("Unknown synthetic operation")


class FakeUpstream(Upstream):
    def __init__(self, backend):
        super().__init__(None, backend.tools)
        self.backend = backend

    async def call(self, name, args, operation):
        self.check(name, args)
        return unpack(await self.backend.call(name, args), operation)


class FakeTransport:
    def __init__(self, backend=None):
        self.backend = backend or Backend()
        self._token = "synthetic-credential"
        self.connections = 0

    @asynccontextmanager
    async def connect(self):
        self.connections += 1
        yield FakeUpstream(self.backend)

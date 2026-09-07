"""Independent v1.12.0 mapping oracle. Not imported from production operations.

Source: github/github-mcp-server v1.12.0 README + pkg/github tool definitions.
Fixture values are synthetic; real credentials must never be recorded here.
"""
from copy import deepcopy

REPO = "example/project"
SHA = "a" * 40
# operation -> (upstream tool, method, input extras, exact upstream extras)
CASES = {
    "repo.files": ("get_file_contents", None, {"path": "README.md", "sha": SHA}, {"path": "README.md", "sha": SHA}),
    "repo.branches": ("list_branches", None, {}, {"page": 1, "perPage": 30}),
    "repo.commits": ("list_commits", None, {"sha": SHA}, {"sha": SHA, "page": 1, "perPage": 30}),
    "repo.commit": ("get_commit", None, {"sha": SHA}, {"sha": SHA, "page": 1, "perPage": 30}),
    "repo.tags": ("list_tags", None, {}, {"page": 1, "perPage": 30}),
    "repo.tag": ("get_tag", None, {"tag": "v1.0.0"}, {"tag": "v1.0.0"}),
    "issue.list": ("list_issues", None, {}, {"perPage": 30}),
    "issue.get": ("issue_read", "get", {"number": 1}, {"issue_number": 1}),
    "issue.comments": ("issue_read", "get_comments", {"number": 1}, {"issue_number": 1, "page": 1, "perPage": 30}),
    "pr.list": ("list_pull_requests", None, {}, {"page": 1, "perPage": 30}),
    "pr.get": ("pull_request_read", "get", {"number": 2}, {"pullNumber": 2}),
    "pr.diff": ("pull_request_read", "get_diff", {"number": 2}, {"pullNumber": 2}),
    "pr.files": ("pull_request_read", "get_files", {"number": 2}, {"pullNumber": 2, "page": 1, "perPage": 30}),
    "pr.reviews": ("pull_request_read", "get_reviews", {"number": 2}, {"pullNumber": 2, "page": 1, "perPage": 30}),
    "pr.review-comments": ("pull_request_read", "get_review_comments", {"number": 2}, {"pullNumber": 2, "perPage": 30}),
    "pr.comments": ("pull_request_read", "get_comments", {"number": 2}, {"pullNumber": 2, "page": 1, "perPage": 30}),
    "pr.checks": ("pull_request_read", "get_check_runs", {"number": 2}, {"pullNumber": 2, "page": 1, "perPage": 30}),
    "pr.status": ("pull_request_read", "get_status", {"number": 2}, {"pullNumber": 2}),
    "actions.workflows": ("actions_list", "list_workflows", {}, {"page": 1, "perPage": 30}),
    "actions.runs": ("actions_list", "list_workflow_runs", {"workflow_id": "ci.yml"}, {"resource_id": "ci.yml", "page": 1, "perPage": 30}),
    "actions.jobs": ("actions_list", "list_workflow_jobs", {"run_id": 100}, {"resource_id": "100", "page": 1, "perPage": 30}),
    "actions.artifacts": ("actions_list", "list_workflow_run_artifacts", {"run_id": 100}, {"resource_id": "100", "page": 1, "perPage": 30}),
    "actions.run": ("actions_get", "get_workflow_run", {"run_id": 100}, {"resource_id": "100"}),
    "actions.logs": ("get_job_logs", None, {"job_id": 101}, {"job_id": 101, "return_content": True}),
    "release.list": ("list_releases", None, {}, {"page": 1, "perPage": 30}),
    "release.get": ("get_release_by_tag", None, {"tag": "v1.0.0"}, {"tag": "v1.0.0"}),
    "release.latest": ("get_latest_release", None, {}, {}),
    "issue.create": ("issue_write", "create", {"title": "Fixture issue", "body": "Synthetic issue body"}, {"title": "Fixture issue", "body": "Synthetic issue body"}),
    "issue.update": ("issue_write", "update", {"number": 1, "title": "Updated", "body": "", "state": "closed"}, {"issue_number": 1, "title": "Updated", "body": "", "state": "closed"}),
    "comment.create": ("add_issue_comment", None, {"subject_type": "issue", "number": 1, "body": "Synthetic comment"}, {"issue_number": 1, "body": "Synthetic comment"}),
    "pr.create": ("create_pull_request", None, {"head": "fixture/topic", "base": "main", "title": "Fixture draft", "body": "Synthetic PR body"}, {"head": "fixture/topic", "base": "main", "title": "Fixture draft", "body": "Synthetic PR body", "draft": True}),
    "pr.update": ("update_pull_request", None, {"number": 2, "body": "", "state": "closed"}, {"pullNumber": 2, "body": "", "state": "closed"}),
}
WRITES = {"issue.create", "issue.update", "comment.create", "pr.create", "pr.update"}


def request(name, request_id="11111111-1111-4111-8111-111111111111", actor=101):
    payload = {"repository": REPO, **deepcopy(CASES[name][2])}
    if name in WRITES:
        return "sdlc_github_" + name.replace(".", "_"), {**payload, "request_id": request_id, "expected_actor_id": actor}
    return "sdlc_github_read", {"operation": name, **payload}


def expected_mapping(name, request_id="11111111-1111-4111-8111-111111111111"):
    tool, method, _, fields = CASES[name]
    args = {"owner": "example", "repo": "project", **deepcopy(fields)}
    if method:
        args["method"] = method
    if name in {"issue.create", "comment.create", "pr.create"}:
        args["body"] += "\n\n<!-- sdlc-github:" + request_id + " -->"
    return tool, args

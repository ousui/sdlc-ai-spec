"""Shared business entry point; hosts and tests exercise the same service.

Writes claim durable local intent before sending exactly one upstream mutation.
Unknown outcomes are never automatically replayed. Reconciliation is read-only.
"""
from __future__ import annotations
from copy import deepcopy
import re
from typing import Any, Callable
from urllib.parse import urlsplit, unquote

from .models import (GithubError, result, failure, digest, canonical, now, redact,
                     ensure_no_secret, MAX_RESULT, MAX_TEXT)
from .operations import OPERATIONS, READS, WRITES, WRITE_TOOLS, validate_request, map_upstream, marker
from .records import Records
from .transport import OfficialTransport

LIST_KEYS = ("items", "issues", "pull_requests", "workflows", "workflow_runs", "jobs", "artifacts", "comments", "reviews", "threads", "reviewThreads", "review_threads", "nodes", "check_runs", "tags", "branches", "releases")


def items(value) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in LIST_KEYS:
            if isinstance(value.get(key), list):
                return value[key]
    raise GithubError("UPSTREAM_INVALID")


def normalize_response(operation: str, data: Any) -> Any:
    """Unwrap only the observed jobs envelope; never recursively find an array."""
    if operation == "actions.jobs" and isinstance(data, dict) and isinstance(data.get("jobs"), dict):
        if set(data) != {"jobs"}:
            raise GithubError("UPSTREAM_INVALID")  # conflicting outer metadata
        inner = data["jobs"]
        if not isinstance(inner.get("jobs"), list):
            raise GithubError("UPSTREAM_INVALID")
        return inner
    return data


def pagination(operation: str, data: Any, request: dict) -> dict:
    mode = OPERATIONS[operation].pagination
    if mode == "none":
        return {"mode": mode, "has_more": False, "next_page": None, "next_cursor": None}
    more, cursor, page = "unknown", None, None
    if isinstance(data, dict):
        info = data.get("pageInfo", data.get("page_info", data.get("PageInfo", {})))
        if isinstance(info, dict):
            flag = info.get("hasNextPage", info.get("has_next_page", info.get("HasNextPage")))
            if isinstance(flag, bool):
                more = flag
                cursor = info.get("endCursor", info.get("end_cursor", info.get("EndCursor"))) if flag else None
        if mode == "page":
            total = data.get("total_count", data.get("totalCount"))
            if isinstance(total, int) and not isinstance(total, bool) and total >= 0:
                consumed = request.get("page", 1) * request.get("per_page", 30)
                if operation == "actions.jobs":
                    consumed = (request.get("page", 1) - 1) * request.get("per_page", 30) + len(items(data))
                more = consumed < total
            info = data.get("pagination", {})
            if isinstance(info, dict) and isinstance(info.get("has_more"), bool):
                more = info["has_more"]
    if mode == "cursor" and more is True and (not isinstance(cursor, str) or not cursor):
        more, cursor = "unknown", None
    if mode == "page" and more is not False:
        page = request.get("page", 1) + 1
    return {"mode": mode, "has_more": more, "next_page": page, "next_cursor": cursor}


def object_url(data: dict) -> str:
    value = data.get("html_url") or data.get("url")
    if not isinstance(value, str):
        raise GithubError("UPSTREAM_INVALID")
    return value


def object_meta(data: Any, repository: str, kind: str, expected_number=None) -> dict:
    if not isinstance(data, dict):
        raise GithubError("UPSTREAM_INVALID")
    url = object_url(data)
    try:
        parsed = urlsplit(url)
    except ValueError:
        raise GithubError("UPSTREAM_INVALID") from None
    if parsed.scheme != "https" or parsed.netloc != "github.com" or parsed.query:
        raise GithubError("TARGET_MISMATCH")
    prefix = "/" + repository.lower() + "/"
    if not parsed.path.lower().startswith(prefix):
        raise GithubError("TARGET_MISMATCH")
    tail = parsed.path[len(prefix):].split("/")
    if len(tail) != 2 or tail[0] not in {"issues", "pull"} or not tail[1].isdigit() or int(tail[1]) <= 0:
        raise GithubError("UPSTREAM_INVALID")
    actual_type = "issue" if tail[0] == "issues" else "pr"
    if kind != "comment" and actual_type != kind:
        raise GithubError("TARGET_MISMATCH")
    number = int(tail[1])
    if expected_number is not None and number != expected_number:
        raise GithubError("TARGET_MISMATCH")
    if "number" in data and data["number"] != number:
        raise GithubError("TARGET_MISMATCH")
    remote_id = data.get("id")
    if remote_id is not None and (isinstance(remote_id, bool) or not str(remote_id).isdigit() or int(remote_id) <= 0):
        raise GithubError("UPSTREAM_INVALID")
    if kind == "comment":
        if remote_id is None or parsed.fragment != "issuecomment-" + str(remote_id):
            raise GithubError("TARGET_MISMATCH")
    elif parsed.fragment:
        raise GithubError("TARGET_MISMATCH")
    # MinimalIssue/MinimalPullRequest intentionally omit database ID on reads.
    return {"number": number, "id": str(remote_id) if remote_id is not None else None, "url": url, "subject_type": actual_type}


def field_value(data: dict, key: str):
    if key in {"head", "base"}:
        value = data.get(key)
        return value.get("ref") if isinstance(value, dict) else value
    if key == "state":
        state = data.get("state")
        return state.lower() if isinstance(state, str) else state
    if key == "body":
        # The pinned upstream Minimal types omit body when it is empty.
        return data.get("body") or ""
    return data.get(key)


def expected_fields(operation: str, payload: dict) -> dict:
    fields = {k: payload[k] for k in ("title", "body", "state", "head", "base") if k in payload}
    if operation == "pr.create":
        fields["draft"] = True
    return {k: digest(v) for k, v in fields.items()}


def attributes_match(data: dict, hashes: dict) -> bool:
    return all(digest(field_value(data, k)) == v for k, v in hashes.items())


def validate_data(operation: str, data: Any, request: dict) -> None:
    op = OPERATIONS[operation]
    shape = op.shape
    if shape in {"issue", "pr"}:
        object_meta(data, request["repository"], shape, request.get("number"))
        if not isinstance(data.get("title"), str) or str(data.get("state", "")).lower() not in {"open", "closed"}:
            raise GithubError("UPSTREAM_INVALID")
        if shape == "issue" and data.get("pull_request"):
            raise GithubError("TARGET_MISMATCH")
        if shape == "pr" and not isinstance(data.get("draft"), bool):
            raise GithubError("UPSTREAM_INVALID")
    elif shape in {"list", "checks"}:
        entries = items(data)
        if any(not isinstance(x, dict) for x in entries):
            raise GithubError("UPSTREAM_INVALID")
        # Validate identifiers for non-empty records; empty arrays remain valid.
        keys = {
            "repo.branches": ("name",), "repo.tags": ("name",), "repo.commits": ("sha",),
            "issue.list": ("number",), "pr.list": ("number",), "issue.comments": ("id",),
            "pr.comments": ("id",), "pr.files": ("filename",), "pr.reviews": ("id",),
            "pr.review-comments": ("id",), "pr.checks": ("id",),
            "actions.workflows": ("id",), "actions.runs": ("id",), "actions.jobs": ("id",),
            "actions.artifacts": ("id",), "release.list": ("id",),
        }.get(operation, ())
        for entry in entries:
            for key in keys:
                value = entry.get(key)
                if key in {"number", "id"} and operation != "pr.review-comments":
                    if isinstance(value, bool) or not isinstance(value, (int, str)) or not str(value).isdigit() or int(value) < 1:
                        raise GithubError("UPSTREAM_INVALID")
                elif not isinstance(value, str) or not value:
                    raise GithubError("UPSTREAM_INVALID")
                if key == "sha" and not re.fullmatch(r"[0-9a-f]{40}", value):
                    raise GithubError("UPSTREAM_INVALID")
        if operation == "actions.jobs":
            if isinstance(data, dict) and "total_count" in data:
                total = data["total_count"]
                if type(total) is not int or total < len(entries):
                    raise GithubError("UPSTREAM_INVALID")
            for entry in entries:
                if type(entry.get("id")) is not int or entry["id"] < 1:
                    raise GithubError("UPSTREAM_INVALID")
                if "run_id" in entry and (type(entry["run_id"]) is not int or entry["run_id"] != request["run_id"]):
                    raise GithubError("TARGET_MISMATCH")
    elif shape == "commit":
        if not isinstance(data, dict) or not re.fullmatch(r"[0-9a-f]{40}", str(data.get("sha", ""))):
            raise GithubError("UPSTREAM_INVALID")
        if re.fullmatch(r"[0-9a-f]{40}", request["sha"]) and data["sha"] != request["sha"]:
            raise GithubError("TARGET_MISMATCH")
    elif shape == "tag":
        if not isinstance(data, dict) or ("ref" in data) == ("tag" in data):
            raise GithubError("UPSTREAM_INVALID")
        reference = "ref" in data
        expected = "refs/tags/" + request["tag"] if reference else request["tag"]
        if data.get("ref" if reference else "tag") != expected:
            raise GithubError("TARGET_MISMATCH")
        obj = data.get("object")
        if (not isinstance(obj, dict) or obj.get("type") not in ({"commit"} if reference else {"commit", "tag"})
                or not isinstance(obj.get("sha"), str) or not re.fullmatch(r"[0-9a-f]{40}", obj["sha"])):
            raise GithubError("UPSTREAM_INVALID")
        if not reference and (not isinstance(data.get("sha"), str) or not re.fullmatch(r"[0-9a-f]{40}", data["sha"])):
            raise GithubError("UPSTREAM_INVALID")
    elif shape == "release":
        if not isinstance(data, dict) or type(data.get("id")) is not int or data["id"] < 1 or not isinstance(data.get("tag_name"), str) or not data["tag_name"]:
            raise GithubError("UPSTREAM_INVALID")
        if "tag" in request and data["tag_name"] != request["tag"]:
            raise GithubError("TARGET_MISMATCH")
    elif shape == "run":
        if not isinstance(data, dict) or data.get("id") != request["run_id"]:
            raise GithubError("UPSTREAM_INVALID")
    elif shape == "status":
        if not isinstance(data, dict) or data.get("state") not in {"error", "failure", "pending", "success"} or not isinstance(data.get("sha"), str):
            raise GithubError("UPSTREAM_INVALID")
    elif shape == "files":
        if isinstance(data, list):
            if any(not isinstance(x, dict) or not isinstance(x.get("path"), str) for x in data):
                raise GithubError("UPSTREAM_INVALID")
            prefix = request.get("path", "").rstrip("/")
            if prefix and any(not x["path"].startswith(prefix + "/") for x in data):
                raise GithubError("TARGET_MISMATCH")
        elif isinstance(data, dict):
            if "resource" not in data and not (isinstance(data.get("path"), str) and "sha" in data):
                raise GithubError("UPSTREAM_INVALID")
            if "path" in data and data["path"] != request.get("path", ""):
                raise GithubError("TARGET_MISMATCH")
            if "resource" in data:
                resource = data["resource"]
                if not isinstance(resource, dict) or not isinstance(resource.get("uri"), str):
                    raise GithubError("UPSTREAM_INVALID")
                uri = unquote(resource["uri"])
                repository_prefix = "repo://" + request["repository"] + "/"
                if not uri.lower().startswith(repository_prefix.lower()):
                    raise GithubError("TARGET_MISMATCH")
                expected = "contents/" + request.get("path", "")
                if request.get("sha"):
                    expected = "sha/" + request["sha"] + "/" + expected
                elif request.get("ref"):
                    ref = request["ref"]
                    if not ref.startswith("refs/"):
                        ref = "sha/" + ref if re.fullmatch(r"[0-9a-f]{40}", ref) else "refs/heads/" + ref
                    expected = ref + "/" + expected
                if uri[len(repository_prefix):].rstrip("/") != expected.rstrip("/"):
                    raise GithubError("TARGET_MISMATCH")
        else:
            raise GithubError("UPSTREAM_INVALID")
    elif shape == "text":
        if operation == "pr.diff":
            if not isinstance(data, str) or (data and not data.startswith("diff --git ")):
                raise GithubError("UPSTREAM_INVALID")
        elif not isinstance(data, dict) or data.get("job_id") != request["job_id"] or not isinstance(data.get("logs_content"), str):
            raise GithubError("UPSTREAM_INVALID")


def bounded_data(operation: str, value: Any) -> tuple[Any, bool]:
    """Cap serialized JSON, not raw text (escaping can expand sixfold)."""
    budget = (MAX_TEXT if operation in {"pr.diff", "actions.logs"} else MAX_RESULT) - 8192
    partial = False
    if operation == "actions.logs":
        data = deepcopy(value)
        text = data["logs_content"]
        original = data.get("original_length", len(text))
        partial = type(original) is int and original > len(text)
        if len(canonical(data)) <= budget:
            return data, partial
        # Non-log metadata must itself be bounded. Preserve the exact job binding.
        data = {"job_id": value["job_id"], "original_length": original if type(original) is int else len(text),
                "logs_content": "", "tail_truncated": True}
        low, high = 0, len(text)
        while low < high:
            mid = (low + high + 1) // 2
            data["logs_content"] = text[-mid:] if mid else ""
            if len(canonical(data)) <= budget:
                low = mid
            else:
                high = mid - 1
        data["logs_content"] = text[-low:] if low else ""
        return data, True
    raw = canonical(value)
    if len(raw) <= budget:
        return value, isinstance(value, dict) and value.get("content_available") is False
    if operation == "pr.diff":
        low, high = 0, len(value)
        while low < high:
            mid = (low + high + 1) // 2
            if len(canonical(value[:mid])) <= budget:
                low = mid
            else:
                high = mid - 1
        return value[:low], True
    # Six bytes per character bounds JSON control escapes; reserve envelope bytes.
    preview = raw[:(budget - 256) // 6].decode("utf-8", "ignore")
    return {"truncated": True, "preview": preview, "preview_encoding": "json-prefix"}, True


class GithubService:
    def __init__(self, data_root, *, transport=None, fault: Callable[[str], None] | None = None):
        self.records = Records(data_root)
        self.transport = transport if transport is not None else OfficialTransport()
        self.actor = None
        self.fault = fault or (lambda point: None)

    async def _identity(self, upstream) -> dict:
        me = await upstream.call("get_me", {}, "status")
        if not isinstance(me, dict) or isinstance(me.get("id"), bool) or not isinstance(me.get("id"), int) or me["id"] <= 0 or not isinstance(me.get("login"), str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", me["login"]):
            raise GithubError("UPSTREAM_INVALID")
        actor = {"id": me["id"], "login": me["login"]}
        self.actor = actor
        return actor

    async def handle(self, tool: str, payload: dict) -> dict:
        op = WRITE_TOOLS.get(tool, tool.removeprefix("sdlc_github_") if isinstance(tool, str) else "invalid")
        repository, actor, response = None, None, None
        progress = {"intent": False, "observed": None}
        try:
            op, data = validate_request(tool, payload)
            repository = data.get("repository")
            ensure_no_secret(data, getattr(self.transport, "_token", ""))
            if op in WRITES and data["write_policy"] == "deny":
                raise GithubError("WRITE_DENIED")
            if op == "operation_status" and not data.get("reconcile"):
                if self.actor is None:
                    raise GithubError("IDENTITY_REQUIRED")
                actor = self.actor
                self._check_actor(data, actor)
                response = self._local_status(data, actor)
            else:
                async with self.transport.connect() as upstream:
                    actor = await self._identity(upstream)
                    if op == "status":
                        capabilities = {k: upstream.capability(k) for k in OPERATIONS}
                        unavailable = [k for k, v in capabilities.items() if not v]
                        response = result(op, actor=actor, data={"capabilities": capabilities},
                                          status="partial" if unavailable else "completed", completeness="partial" if unavailable else "complete",
                                          warnings=[{"code": "CAPABILITY_UNAVAILABLE", "message": ", ".join(unavailable)}] if unavailable else [])
                    elif op == "operation_status":
                        self._check_actor(data, actor)
                        response = await self._reconcile(data, actor, upstream)
                    elif op in READS:
                        response = await self._read(op, data, actor, upstream)
                    else:
                        self._check_actor(data, actor)
                        response = await self._write(op, data, actor, upstream, progress)
            return redact(response, getattr(self.transport, "_token", ""))
        except GithubError as error:
            if response is None and progress["observed"] is not None:
                response = progress["observed"]
            if response is not None:
                # Closing an SDK context must not erase an already observed effect.
                response["warnings"].append({"code": error.code, "message": "Upstream session closed after an observed result; no write was replayed."})
                return redact(response, getattr(self.transport, "_token", ""))
            if progress["intent"] or (op == "operation_status" and error.code in {"RECORD_CORRUPT", "STORAGE_FAILED", "STORAGE_UNSAFE"}):
                error = GithubError(error.code, effect="unknown")
            return redact(failure(op, error, actor=actor, repository=repository), getattr(self.transport, "_token", ""))
        except Exception:
            # Unexpected programming/SDK failures must not imply an unsent write.
            if progress["observed"] is not None:
                return redact(progress["observed"], getattr(self.transport, "_token", ""))
            return failure(op, GithubError("UPSTREAM_INVALID", effect="unknown" if progress["intent"] else "none"), actor=actor, repository=repository)

    @staticmethod
    def _check_actor(data, actor):
        if data["expected_actor_id"] != actor["id"]:
            raise GithubError("ACTOR_MISMATCH")

    async def _raw_read(self, operation, data, upstream):
        if not upstream.capability(operation):
            raise GithubError("CAPABILITY_UNAVAILABLE")
        tool, args = map_upstream(operation, data)
        value = await upstream.call(tool, args, operation)
        value = normalize_response(operation, value)
        validate_data(operation, value, data)
        return value

    async def _read(self, operation, data, actor, upstream):
        value = await self._raw_read(operation, data, upstream)
        paging = pagination(operation, value, data)
        value, partial = bounded_data(operation, value)
        return result(operation, actor=actor, repository=data["repository"], target=self._target(data), data=value,
                      pagination=paging, status="partial" if partial else "completed",
                      completeness="partial" if partial else "unknown" if paging["has_more"] == "unknown" else "partial" if paging["has_more"] or data.get("page", 1) > 1 or data.get("after") else "complete",
                      warnings=[{"code": "RESULT_LIMIT", "message": "Truncated/linked content is not a complete result."}] if partial else [],
                      next_action="Read an explicitly selected next page; do not infer complete coverage." if paging["has_more"] is not False else None)

    @staticmethod
    def _target(data):
        return {k: data[k] for k in ("number", "subject_type", "head", "base", "path", "ref", "sha", "tag", "workflow_id", "run_id", "job_id") if k in data} or None

    async def _preflight(self, operation, data, upstream):
        if not upstream.capability(operation):
            raise GithubError("CAPABILITY_UNAVAILABLE")
        before = None
        if operation in {"issue.update", "pr.update", "comment.create"}:
            kind = data["subject_type"] if operation == "comment.create" else operation.split(".")[0]
            before = await self._raw_read(kind + ".get", {"repository": data["repository"], "number": data["number"]}, upstream)
        if operation == "pr.create":
            if ":" in data["head"] or ":" in data["base"]:
                raise GithubError("ARGUMENT_INVALID")  # first version: same repository branches only
            found = set()
            for page in range(1, 21):
                branches = await self._raw_read("repo.branches", {"repository": data["repository"], "page": page, "per_page": 100}, upstream)
                entries = items(branches)
                found.update(x.get("name") for x in entries)
                if {data["head"], data["base"]} <= found:
                    break
                if not entries:
                    raise GithubError("TARGET_REQUIRED")
            else:
                raise GithubError("TARGET_REQUIRED")
        readback = (data["subject_type"] + ".comments") if operation == "comment.create" else operation.split(".")[0] + ".get"
        if not upstream.capability(readback):
            raise GithubError("CAPABILITY_UNAVAILABLE")
        return before

    async def _write(self, operation, data, actor, upstream, progress):
        rid, repo = data["request_id"], data["repository"]
        params = {k: v for k, v in data.items() if k not in {"write_policy", "dry_run"}}
        # Check existing claims before preflight reads; never silently re-execute.
        try:
            old, receipt = self.records.load(actor["id"], repo, rid)
        except GithubError as e:
            if e.code != "RECEIPT_NOT_FOUND":
                raise GithubError(e.code, effect="unknown") from None
        else:
            return self._existing(operation, data, actor, old, receipt, digest(params))
        before = await self._preflight(operation, data, upstream)
        if data["dry_run"]:
            return result(operation, actor=actor, repository=repo, target=self._target(data), data={"dry_run": True, "preflight": "passed"})
        send = dict(data)
        if operation.endswith(".create"):
            send["body"] = send["body"] + "\n\n" + marker(rid)
        intent = {"version": 1, "actor": actor, "repository": repo, "request_id": rid, "operation": operation,
                  "params_digest": digest(params), "expected_hashes": expected_fields(operation, send),
                  "target": self._target(data), "created_at": now(),
                  "before_hashes": {k: digest(field_value(before, k)) for k in ("title", "body", "state")} if before else {}}
        self.fault("before_intent")
        if not self.records.claim(intent):
            old, receipt = self.records.load(actor["id"], repo, rid)
            return self._existing(operation, data, actor, old, receipt, digest(params))
        progress["intent"] = True
        self.fault("after_intent_before_send")
        tool, arguments = map_upstream(operation, send)
        confirmed = False
        meta = None
        try:
            response = await upstream.call(tool, arguments, operation)
            self.fault("after_send")
            kind = "comment" if operation == "comment.create" else operation.split(".")[0]
            meta = object_meta(response, repo, kind, data.get("number"))
            if meta["id"] is None:
                raise GithubError("UPSTREAM_INVALID")
            if operation == "comment.create" and meta["subject_type"] != data["subject_type"]:
                raise GithubError("TARGET_MISMATCH")
            confirmed = True
            progress["observed"] = self._write_result(intent, meta, None)
            self.fault("after_success_before_readback")
            readback = await self._readback(intent, meta, upstream)
            response = self._write_result(intent, meta, readback)
        except Exception as caught:
            error = caught if isinstance(caught, GithubError) else GithubError("UPSTREAM_INVALID")
            if confirmed:
                response = self._write_result(intent, meta, None)
            else:
                effect = "none" if error.code in {"AUTH_FAILED", "PERMISSION_DENIED", "NOT_FOUND_OR_INACCESSIBLE", "RATE_LIMITED", "CAPABILITY_UNAVAILABLE"} else "unknown"
                response = failure(operation, GithubError(error.code, effect=effect), actor=actor, repository=repo, target=intent["target"])
                response["receipt"] = self._receipt(intent, None, "unknown" if effect == "unknown" else "rejected", False)
        progress["observed"] = response
        self.fault("before_receipt")
        response = redact(response, getattr(self.transport, "_token", ""))
        try:
            self.records.save_receipt(intent, response)
        except GithubError:
            # Do not erase a confirmed GitHub write merely because receipt fsync failed.
            response["ok"] = False
            response["status"] = "partial" if response["effect"] == "confirmed" else "unknown"
            response["warnings"].append({"code": "STORAGE_FAILED", "message": "Receipt persistence failed; preserve intent and reconcile without replay."})
        self.fault("after_receipt")
        return response

    @staticmethod
    def _existing(operation, data, actor, intent, receipt, params_digest):
        if intent is None:
            return failure(operation, GithubError("EFFECT_UNKNOWN", effect="unknown"), actor=actor, repository=data["repository"])
        if intent["params_digest"] != params_digest or intent["operation"] != operation:
            return failure(operation, GithubError("REQUEST_CONFLICT", effect="unknown"), actor=actor, repository=data["repository"])
        if receipt:
            return deepcopy(receipt["result"])
        return failure(operation, GithubError("EFFECT_UNKNOWN", effect="unknown"), actor=actor, repository=data["repository"], target=intent["target"])

    @staticmethod
    def _receipt(intent, meta, state, verified):
        return {"request_id": intent["request_id"], "operation": intent["operation"], "remote_id": meta.get("id") if meta else None,
                "url": meta.get("url") if meta else None, "record_state": state,
                "time": now(), "readback_verified": verified}

    def _write_result(self, intent, meta, readback, *, reconciled=False):
        verified = readback is not None
        data = {**meta, "verified_fields": list(intent["expected_hashes"]), "readback_verified": verified}
        if readback:
            data.update({k: field_value(readback, k) for k in ("state", "draft") if k in readback})
        warnings = [] if verified else [{"code": "READBACK_FAILED", "message": "Write confirmed; readback did not match or was inaccessible."}]
        if reconciled and intent["operation"].endswith(".update"):
            warnings.append({"code": "STATE_OBSERVATION_ONLY", "message": "Matching current fields do not prove exclusive causal attribution to this update."})
        return result(intent["operation"], actor=intent["actor"], repository=intent["repository"], target=intent["target"],
                      data=data, status="completed" if verified else "partial", effect="confirmed", completeness="complete" if verified else "partial",
                      receipt=self._receipt(intent, meta, "reconciled" if reconciled else "completed" if verified else "confirmed_partial", verified), warnings=warnings,
                      next_action=None if verified else "Use operation_status with reconcile=true; never resend this write.")

    async def _readback(self, intent, meta, upstream):
        operation, repo = intent["operation"], intent["repository"]
        if operation == "comment.create":
            kind = intent["target"]["subject_type"]
            read = None
            for page in range(1, 21):
                response = await self._raw_read(kind + ".comments", {"repository": repo, "number": meta["number"], "page": page, "per_page": 100}, upstream)
                entries = items(response)
                candidates = [x for x in entries if str(x.get("id")) == meta["id"]]
                if len(candidates) > 1:
                    return None
                if candidates:
                    read = candidates[0]
                    object_meta(read, repo, "comment", meta["number"])
                    break
                if not entries:
                    return None
            if read is None:
                return None
        else:
            kind = operation.split(".")[0]
            read = await self._raw_read(kind + ".get", {"repository": repo, "number": meta["number"]}, upstream)
        if not attributes_match(read, intent["expected_hashes"]):
            return None
        if operation.endswith(".create"):
            if marker(intent["request_id"]) not in field_value(read, "body"):
                return None
            if read.get("user", {}).get("id") != intent["actor"]["id"]:
                return None
        return read

    def _local_status(self, data, actor):
        intent, receipt = self.records.load(actor["id"], data["repository"], data["request_id"])
        if receipt:
            answer = deepcopy(receipt["result"])
        else:
            answer = failure("operation_status", GithubError("EFFECT_UNKNOWN", effect="unknown"), actor=actor, repository=data["repository"], target=intent["target"] if intent else None)
        answer["operation"] = "operation_status"
        return answer

    async def _collect(self, operation, params, upstream):
        mode = OPERATIONS[operation].pagination
        query = {**params, "per_page": 100}
        if mode == "page":
            query["page"] = 1
        values = []
        seen = set()
        for _ in range(20):
            value = await self._raw_read(operation, query, upstream)
            values.extend(items(value))
            p = pagination(operation, value, query)
            if isinstance(value, dict) and any(value.get(k) for k in ("truncated", "filtered", "incomplete_results")):
                return values, False
            if p["has_more"] is False:
                return values, True
            if p["has_more"] == "unknown":
                return values, False
            if mode == "cursor":
                cursor = p["next_cursor"]
                if not cursor or cursor in seen:
                    return values, False
                seen.add(cursor)
                query["after"] = cursor
            else:
                query["page"] = p["next_page"]
        return values, False

    def _inconclusive(self, intent, stored, error=None):
        """Append a failed observation without downgrading an observed effect."""
        previous = stored["result"] if stored else None
        if previous and previous.get("effect") == "confirmed":
            answer = deepcopy(previous)
            answer.update(ok=False, status="partial", completeness="partial")
            answer["warnings"].append({"code": "READBACK_FAILED", "message": "Prior write remains confirmed; current read-only verification is inconclusive."})
            answer["next_action"] = "Preserve the original receipt; reconcile read-only, never replay."
        else:
            answer = failure(intent["operation"], GithubError("EFFECT_UNKNOWN", effect="unknown"),
                             actor=intent["actor"], repository=intent["repository"], target=intent["target"],
                             receipt=deepcopy(previous.get("receipt")) if previous else None)
        if error:
            answer["warnings"].append({"code": error.code, "message": str(error)})
        try:
            self.records.save_receipt(intent, answer, observation=True)
        except GithubError:
            answer["warnings"].append({"code": "STORAGE_FAILED", "message": "Observation not persisted; original intent/receipt retained."})
        answer["operation"] = "operation_status"
        return answer

    async def _reconcile(self, data, actor, upstream):
        intent, receipt = self.records.load(actor["id"], data["repository"], data["request_id"])
        if intent is None:
            return failure("operation_status", GithubError("EFFECT_UNKNOWN", effect="unknown"), actor=actor, repository=data["repository"])
        if receipt and receipt["result"]["status"] == "completed":
            answer = deepcopy(receipt["result"])
            answer["operation"] = "operation_status"
            return answer
        operation = intent["operation"]
        try:
            known = receipt["result"].get("data") if receipt else None
            if isinstance(known, dict) and known.get("url"):
                meta = known
                readback = await self._readback(intent, meta, upstream)
            elif operation.endswith(".update"):
                kind = operation.split(".")[0]
                query = {"repository": intent["repository"], "number": intent["target"]["number"]}
                readback = await self._raw_read(kind + ".get", query, upstream)
                meta = object_meta(readback, intent["repository"], kind, query["number"])
                if not attributes_match(readback, intent["expected_hashes"]):
                    readback = None
            else:
                if operation == "comment.create":
                    kind = intent["target"]["subject_type"]
                    readop, query = kind + ".comments", {"repository": intent["repository"], "number": intent["target"]["number"]}
                else:
                    kind = operation.split(".")[0]
                    readop, query = kind + ".list", {"repository": intent["repository"], "state": "all"}
                entries, complete = await self._collect(readop, query, upstream)
                # Count ALL marker-bearing candidates before filtering attributes or actor.
                matches = [x for x in entries if isinstance(field_value(x, "body"), str)
                           and marker(intent["request_id"]) in field_value(x, "body")]
                if not complete or len(matches) != 1:
                    return self._inconclusive(intent, receipt)
                readback = matches[0]
                meta = object_meta(readback, intent["repository"], "comment" if operation == "comment.create" else kind, query.get("number"))
                if (not attributes_match(readback, intent["expected_hashes"])
                        or not isinstance(readback.get("user"), dict) or readback["user"].get("id") != actor["id"]
                        or meta["subject_type"] != kind):
                    return self._inconclusive(intent, receipt)
            if readback is None:
                return self._inconclusive(intent, receipt)
            answer = self._write_result(intent, meta, readback, reconciled=True)
            try:
                self.records.save_receipt(intent, answer, observation=True)
            except GithubError:
                answer.update(ok=False, status="partial")
                answer["warnings"].append({"code": "STORAGE_FAILED", "message": "Readback confirmed, observation not persisted; do not replay."})
            answer["operation"] = "operation_status"
            return answer
        except GithubError as error:
            return self._inconclusive(intent, receipt, error)

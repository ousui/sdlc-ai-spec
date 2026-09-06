"""The sole production network path: official SDK -> GitHub Remote MCP.

No REST fallback, caller URLs, caller headers, OAuth flow or automatic write
retry. Every invocation owns its SDK context in one task (cancel-scope safe).
"""
from __future__ import annotations
from contextlib import asynccontextmanager
from datetime import timedelta
import asyncio
import json
import logging
import os
import re
from typing import Any

from .models import GithubError, TIMEOUT, MAX_TEXT
from .operations import OPERATIONS, map_upstream

REMOTE_URL = "https://api.githubcopilot.com/mcp/"
MAX_WIRE_BYTES = 8 * 1024 * 1024
TOOLSETS = "context,repos,issues,pull_requests,actions"


def classify(error: BaseException | str) -> str:
    if isinstance(error, BaseExceptionGroup):
        codes = [classify(e) for e in error.exceptions]
        return next((c for c in codes if c != "DISCONNECTED"), "DISCONNECTED")
    if isinstance(error, GithubError):
        return error.code
    text = str(error).lower()
    if isinstance(error, (TimeoutError, asyncio.TimeoutError)) or "timed out" in text or "timeout" in type(error).__name__.lower():
        return "TIMEOUT"
    for number, code in ((401, "AUTH_FAILED"), (403, "PERMISSION_DENIED"), (404, "NOT_FOUND_OR_INACCESSIBLE"), (429, "RATE_LIMITED")):
        if re.search(rf"\b{number}\b", text):
            return code
    if re.search(r"\b5[0-9]{2}\b", text):
        return "UPSTREAM_FAILED"
    if "rate limit" in text:
        return "RATE_LIMITED"
    if "bad credentials" in text or "unauthorized" in text:
        return "AUTH_FAILED"
    if "forbidden" in text or "resource not accessible" in text:
        return "PERMISSION_DENIED"
    return "UPSTREAM_FAILED" if isinstance(error, str) else "DISCONNECTED"


def _json(text: str):
    def unique(pairs):
        value = {}
        for k, v in pairs:
            if k in value:
                raise ValueError("duplicate JSON key")
            value[k] = v
        return value
    return json.loads(text, object_pairs_hook=unique, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def unpack(response, operation: str) -> Any:
    """Decode supported SDK content shapes; messages alone never prove a write."""
    raw = response.model_dump(mode="json", exclude_none=True) if hasattr(response, "model_dump") else response
    if not isinstance(raw, dict):
        raise GithubError("UPSTREAM_INVALID")
    if raw.get("isError"):
        raise GithubError(classify(json.dumps(raw, ensure_ascii=False)))
    if raw.get("structuredContent") is not None:
        return raw["structuredContent"]
    content = raw.get("content")
    if not isinstance(content, list):
        raise GithubError("UPSTREAM_INVALID")
    texts = [x.get("text", "") for x in content if x.get("type") == "text"]
    resources = [x for x in content if x.get("type") in {"resource", "resource_link"}]
    if operation == "repo.files" and resources:
        if len(resources) != 1:
            raise GithubError("UPSTREAM_INVALID")
        note = "\n".join(texts)
        if "default branch" in note.lower() and ("was used" in note.lower() or "does not exist" in note.lower()):
            raise GithubError("TARGET_MISMATCH")
        item = resources[0]
        if item["type"] == "resource_link":
            return {"resource": item, "content_available": False}
        resource = item.get("resource", {})
        if not isinstance(resource, dict) or not isinstance(resource.get("uri"), str) or not any(k in resource for k in ("text", "blob")):
            raise GithubError("UPSTREAM_INVALID")
        sha = re.search(r"SHA:\s*([0-9a-f]{40})", note, re.I)
        return {"resource": resource, "sha": sha.group(1) if sha else None, "content_available": True}
    if len(texts) != 1:
        raise GithubError("UPSTREAM_INVALID")
    if operation == "pr.diff":
        return texts[0]
    try:
        return _json(texts[0])
    except (ValueError, TypeError, RecursionError):
        raise GithubError("UPSTREAM_INVALID") from None


def _contains_ref(value) -> bool:
    if isinstance(value, dict):
        return any(k in {"$ref", "$dynamicRef", "$recursiveRef"} or _contains_ref(v) for k, v in value.items())
    return isinstance(value, list) and any(_contains_ref(v) for v in value)


class Upstream:
    def __init__(self, session, tools: dict):
        self.session = session
        self.tools = tools
        self.calls: list[str] = []  # names only; never bodies, args or credentials

    def check(self, name: str, args: dict) -> None:
        from jsonschema import Draft202012Validator
        from jsonschema.exceptions import SchemaError
        tool = self.tools.get(name)
        schema = tool.inputSchema if tool is not None else None
        if not isinstance(schema, dict) or _contains_ref(schema) or schema.get("type") != "object":
            raise GithubError("CAPABILITY_UNAVAILABLE")
        props = schema.get("properties", {})
        if not isinstance(props, dict) or any(k not in props for k in args):
            raise GithubError("CAPABILITY_UNAVAILABLE")
        try:
            Draft202012Validator.check_schema(schema)
            if not Draft202012Validator(schema).is_valid(args):
                raise GithubError("CAPABILITY_UNAVAILABLE")
        except (ValueError, RecursionError, TypeError, SchemaError):
            raise GithubError("CAPABILITY_UNAVAILABLE") from None

    def capability(self, operation: str) -> bool:
        op = OPERATIONS[operation]
        sample = {"repository": "example/project", "path": "README.md", "ref": "refs/heads/main",
                  "sha": "a" * 40, "number": 1, "tag": "v1.0.0", "head": "topic", "base": "main",
                  "title": "Probe", "body": "", "state": "open", "page": 1, "per_page": 100,
                  "after": "cursor", "workflow_id": "ci.yml", "run_id": 1, "job_id": 1, "subject_type": "issue"}
        # Map every allowed field, not only fields in one successful invocation.
        try:
            name, args = map_upstream(operation, sample)
            self.check(name, args)
            for key, value in args.items():
                schema = self.tools[name].inputSchema["properties"][key]
                typ = schema.get("type")
                expected = "boolean" if isinstance(value, bool) else "integer" if isinstance(value, int) else "string"
                accepted = typ if isinstance(typ, list) else [typ]
                if expected not in accepted and not (expected == "integer" and "number" in accepted) and "enum" not in schema:
                    return False
            if "state" in args:
                self.check(name, {**args, "state": "closed"})
            return True
        except GithubError:
            return False

    async def call(self, name: str, args: dict, operation: str):
        self.check(name, args)
        self.calls.append(name)
        try:
            async with asyncio.timeout(TIMEOUT):
                response = await self.session.call_tool(name, args, read_timeout_seconds=timedelta(seconds=TIMEOUT))
            return unpack(response, operation)
        except GithubError:
            raise
        except Exception as error:
            raise GithubError(classify(error)) from None


class OfficialTransport:
    """One credential snapshot per instance. Test adapters override _endpoint only."""
    def __init__(self):
        self._token = os.environ.get("SDLC_GITHUB_TOKEN", "")

    def _endpoint(self) -> str:
        return REMOTE_URL

    @asynccontextmanager
    async def connect(self):
        if not self._token:
            raise GithubError("AUTH_REQUIRED")
        import httpx
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        class LimitedStream(httpx.AsyncByteStream):
            def __init__(self, stream):
                self.stream = stream

            async def __aiter__(self):
                total = 0
                async for chunk in self.stream:
                    total += len(chunk)
                    if total > MAX_WIRE_BYTES:
                        raise GithubError("RESULT_LIMIT")
                    yield chunk

            async def aclose(self):
                await self.stream.aclose()

        class LimitedTransport(httpx.AsyncHTTPTransport):
            async def handle_async_request(self, request):
                response = await super().handle_async_request(request)
                if response.headers.get("content-encoding", "identity").lower() not in {"", "identity"}:
                    await response.aclose()
                    raise GithubError("RESULT_LIMIT")
                response.stream = LimitedStream(response.stream)
                return response

        headers = {"Authorization": "Bearer " + self._token, "X-MCP-Toolsets": TOOLSETS, "Accept-Encoding": "identity"}
        try:
            # No SDK exception/HTTP headers are allowed into diagnostics.
            logging.getLogger("httpx").setLevel(logging.CRITICAL + 1)
            logging.getLogger("mcp").setLevel(logging.CRITICAL + 1)
            async with httpx.AsyncClient(headers=headers, timeout=httpx.Timeout(TIMEOUT), follow_redirects=False,
                                         transport=LimitedTransport(retries=0), trust_env=False) as client:
                async with streamable_http_client(self._endpoint(), http_client=client) as (read, write, _):
                    async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=TIMEOUT)) as session:
                        async with asyncio.timeout(TIMEOUT):
                            await session.initialize()
                            tools = {}
                            cursor = None
                            seen = set()
                            for _ in range(32):
                                page = await session.list_tools(cursor=cursor)
                                for tool in page.tools:
                                    if tool.name in tools:
                                        raise GithubError("CAPABILITY_UNAVAILABLE")
                                    tools[tool.name] = tool
                                cursor = page.nextCursor
                                if not cursor:
                                    break
                                if cursor in seen:
                                    raise GithubError("CAPABILITY_UNAVAILABLE")
                                seen.add(cursor)
                            else:
                                raise GithubError("CAPABILITY_UNAVAILABLE")
                        yield Upstream(session, tools)
        except GithubError:
            raise
        except Exception as error:
            raise GithubError(classify(error)) from None

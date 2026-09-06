#!/usr/bin/env python3
"""Production stdio entry. Dependency and configuration errors fail offline."""
from __future__ import annotations
import argparse
import asyncio
import importlib.metadata
import json
import logging
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def dependency_check() -> dict:
    lock = ROOT / "packages/sdlc_github/requirements.lock"
    missing = []
    for name, version in re.findall(r"(?m)^([A-Za-z0-9_.-]+)==([^\s;\\]+)", lock.read_text(encoding="utf-8")):
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            actual = None
        if actual != version:
            missing.append(name)
    return {"ok": not missing, "code": "READY" if not missing else "DEPENDENCY_UNAVAILABLE", "mismatched_packages": missing}


def output_schema():
    return json.loads((ROOT / "skills/_shared/schemas/github-result.schema.json").read_text(encoding="utf-8"))


def build_server(service):
    from mcp.server.lowlevel import Server
    from mcp import types
    from jsonschema import Draft202012Validator
    from packages.sdlc_github.models import canonical, failure, result, GithubError, redact
    from packages.sdlc_github.operations import TOOLS, WRITE_TOOLS, tool_schema
    server = Server("sdlc-github", version="0.1.0", instructions="Explicit GitHub foundation operations only. Tool approval remains the host's responsibility.")
    output = output_schema()
    validator = Draft202012Validator(output)

    @server.list_tools()
    async def list_tools():
        return [types.Tool(name=name, description=("明确授权后执行固定 GitHub 写操作；相同 request_id 不重放。" if name in WRITE_TOOLS else "读取准确 GitHub 或本地回执信息；不授予后续写入授权。"),
                           inputSchema=tool_schema(name), outputSchema=output,
                           annotations=types.ToolAnnotations(readOnlyHint=name not in WRITE_TOOLS,
                               destructiveHint=name in WRITE_TOOLS, idempotentHint=name not in WRITE_TOOLS,
                               openWorldHint=True)) for name in TOOLS]

    @server.call_tool(validate_input=False)
    async def call_tool(name, arguments):
        # Own validation avoids the SDK echoing invalid input/credentials in errors.
        try:
            response = await service.handle(name, arguments)
            response = redact(response, getattr(service.transport, "_token", ""))
            if not validator.is_valid(response):
                observed = response.get("effect") if isinstance(response, dict) else None
                if observed == "confirmed":
                    response = result("invalid", status="partial", effect="confirmed", completeness="unknown",
                                      errors=[{"code":"UPSTREAM_INVALID","message":"Write observed; malformed result requires read-only reconciliation."}],
                                      next_action="Reconcile the original request_id without replay.")
                else:
                    response = failure("invalid", GithubError("UPSTREAM_INVALID", effect="unknown" if name in WRITE_TOOLS or name == "sdlc_github_operation_status" else "none"))
        except Exception:
            response = failure("invalid", GithubError("UPSTREAM_FAILED", effect="unknown" if name in WRITE_TOOLS or name == "sdlc_github_operation_status" else "none"))
        return types.CallToolResult(content=[types.TextContent(type="text", text=canonical(response).decode("utf-8"))],
                                    structuredContent=response, isError=response["status"] in {"failed", "blocked", "unknown"})
    return server


async def serve(service):
    from mcp.server.stdio import stdio_server
    server = build_server(service)
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "ARGUMENT_INVALID: use --help for the fixed startup interface.\n")


def main(argv=None):
    parser = SafeParser(description="SDLC GitHub stdio MCP; no automatic authentication or installation.")
    parser.add_argument("--data-root", help="Absolute stable data root, created by the installer.")
    parser.add_argument("--check-install", action="store_true", help="Offline dependency check; no PAT needed.")
    args = parser.parse_args(argv)
    check = dependency_check()
    if args.check_install:
        print(json.dumps(check, sort_keys=True))
        return 0 if check["ok"] else 2
    if not check["ok"]:
        print("DEPENDENCY_UNAVAILABLE: install packages/sdlc_github/requirements.lock explicitly.", file=sys.stderr)
        return 2
    if not args.data_root:
        parser.error("data root required")
    # Suppress dependency diagnostics rather than risk emitting headers or bodies.
    logging.disable(logging.CRITICAL)
    from packages.sdlc_github.service import GithubService
    from packages.sdlc_github.models import GithubError
    try:
        service = GithubService(args.data_root)
        asyncio.run(serve(service))
        return 0
    except GithubError as error:
        print(error.code, file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
    except Exception:
        print("MCP_SESSION_FAILED", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

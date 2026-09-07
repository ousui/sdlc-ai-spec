#!/usr/bin/env python3
"""Loopback-only real HTTP MCP fixture; never shipped as a production entry."""
import argparse
import json
import logging
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from mcp.server.fastmcp import FastMCP
from tests.skill_github.fake_backend import Backend
from mcp import types
import uvicorn


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--state-file", required=True)
    args = parser.parse_args()
    backend = Backend(state_file=args.state_file)
    server = FastMCP("fixed-fake-github", host="127.0.0.1", port=args.port, json_response=True, stateless_http=True, log_level="ERROR")

    @server._mcp_server.list_tools()
    async def tools():
        return list(backend.tools.values())

    @server._mcp_server.call_tool(validate_input=False)
    async def call(name, arguments):
        # Synthetic identities derived from the test-only request context header.
        context = server._mcp_server.request_context
        request = context.request
        token = request.headers.get("authorization", "") if request else ""
        if token.endswith("fixture-beta"):
            backend.actor = 202
        elif token.endswith("fixture-alpha"):
            backend.actor = 101
        else:
            return types.CallToolResult(isError=True, content=[types.TextContent(type="text", text="401 fixture credential required")])
        return await backend.call(name, arguments)

    logging.disable(logging.CRITICAL)
    app = server.streamable_http_app()
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="critical", access_log=False)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Dependency injection for protocol tests; production accepts no endpoint flag."""
import argparse
import asyncio
import importlib.util
import logging
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

p = argparse.ArgumentParser()
p.add_argument("--plugin", required=True)
p.add_argument("--data-root", required=True)
p.add_argument("--endpoint", required=True)
p.add_argument("--crash-point", choices=["before_intent", "after_intent_before_send", "after_send", "after_success_before_readback", "before_receipt", "after_receipt"])
a = p.parse_args()
u = urlsplit(a.endpoint)
if u.scheme != "http" or u.hostname != "127.0.0.1" or not u.port or u.path != "/mcp":
    raise SystemExit("Test injection must be loopback MCP")
root = Path(a.plugin)
sys.path.insert(0, str(root))
from packages.sdlc_github.transport import OfficialTransport
from packages.sdlc_github.service import GithubService


class Loopback(OfficialTransport):
    def _endpoint(self):
        return a.endpoint


spec = importlib.util.spec_from_file_location("production_mcp_entry", root / "scripts/sdlc_github_mcp.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
logging.disable(logging.CRITICAL)
def fault(point):
    if point == a.crash_point:
        os._exit(77)  # deterministic real process death, no Python cleanup

asyncio.run(module.serve(GithubService(a.data_root, transport=Loopback(), fault=fault)))

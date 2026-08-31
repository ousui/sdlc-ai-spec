from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_PATH = ROOT / "skills/sdlc-000-ctx/scripts/runtime.py"
SPEC = importlib.util.spec_from_file_location("ctx_digest_producer", RUNTIME_PATH)
assert SPEC is not None and SPEC.loader is not None
CTX = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CTX
SPEC.loader.exec_module(CTX)

from packages.sdlc_runtime import (  # noqa: E402
    compute_ctx_check_set_result_digest,
    compute_ctx_control_input_digest,
    parse_canonical_artifact,
)


class CtxAuthorityCompatibilityTests(unittest.TestCase):
    def blob(self, checks):
        lines = [
            "---",
            "contract: sdlc-ai-spec/project-context/v1",
            "id: CTX-20260831190000-01",
            "revision: 1",
            "status: ready",
            "---",
            "",
            "# CTX Fixture",
            "",
            "## 摘要 Summary",
            "",
            "Digest compatibility fixture.",
            "",
            "## 门禁 Gate",
            "",
            "### Core Checks",
            "",
            "| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |",
            "|---|---|---|---|",
        ]
        for check_id in CTX.CORE_CHECKS:
            result, notes = checks[check_id]
            lines.append(
                f"| {check_id} | Core Contract Integrity | {result} | {notes} |"
            )
        lines += [
            "",
            "### CTX Checks",
            "",
            "| Check ID | Check | Result | Basis References |",
            "|---|---|---|---|",
        ]
        for check_id in CTX.CTX_CHECKS:
            result, notes = checks[check_id]
            lines.append(
                f"| {check_id} | Project Context Contract | {result} | {notes} |"
            )
        return ("\n".join(lines) + "\n").encode("utf-8")

    def test_ctx_control_and_check_digest_match_producer(self):
        checks = {
            check_id: ("pass", f"evidence-{check_id}")
            for check_id in (*CTX.CORE_CHECKS, *CTX.CTX_CHECKS)
        }
        raw = self.blob(checks)
        self.assertEqual(
            compute_ctx_control_input_digest(raw),
            CTX._control_input_digest(raw),
        )
        self.assertEqual(
            compute_ctx_check_set_result_digest(parse_canonical_artifact(raw)),
            CTX._check_digest(checks),
        )


if __name__ == "__main__":
    unittest.main()

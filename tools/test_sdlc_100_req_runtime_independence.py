#!/usr/bin/env python3
"""Execute sdlc-100-req from an installed-runtime copy with no docs tree."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def _request(project_root: Path) -> dict[str, object]:
    return {
        "contract": "sdlc-ai-spec/runtime-invocation/v1",
        "operation": "create",
        "project_root": str(project_root),
        "artifact_reference": None,
        "inputs": {
            "context_reference": "CTX-20260831030000-01@1",
            "requirement": {
                "title": "运行时独立性检查",
                "summary": "验证删除开发文档后 REQ Runtime 仍可执行。",
                "sources": [
                    {
                        "type": "text",
                        "content": "REQ Runtime must be self-contained",
                        "evidence_reference": "N/A",
                    }
                ],
                "goals": [
                    {
                        "problem": "运行时不能依赖设计文档",
                        "outcome": "安装包在没有 docs 的环境中运行",
                        "success_condition": "dry-run 返回合法 completed Result",
                    }
                ],
                "in_scope": ["REQ Runtime import and deterministic analysis"],
                "out_of_scope": ["Artifact Store write and host discovery"],
                "affected_parties": [],
                "requirements": [
                    {
                        "type": "constraint",
                        "source_references": ["SRC-001", "GOAL-001"],
                        "statement": "REQ Runtime 不得在执行时读取 docs。",
                    }
                ],
                "acceptance_criteria": [
                    {
                        "requirement_references": ["R-001"],
                        "condition": "复制安装后 Runtime 且不复制 docs",
                        "expected_result": "dry-run 输出合法 completed Result",
                    }
                ],
                "dependencies": [],
                "profile": "lite",
                "profile_basis": "只验证 Runtime 自包含边界",
                "lifecycle_applicability": [
                    {
                        "phase": "DSN",
                        "disposition": "n/a",
                        "host": "N/A",
                        "basis": "隔离测试不进入产品设计",
                    },
                    {
                        "phase": "PLN",
                        "disposition": "n/a",
                        "host": "N/A",
                        "basis": "隔离测试不进入实施计划",
                    },
                    {
                        "phase": "IMP",
                        "disposition": "n/a",
                        "host": "N/A",
                        "basis": "隔离测试不修改产品",
                    },
                    {
                        "phase": "VFY",
                        "disposition": "required",
                        "host": "N/A",
                        "basis": "VFY 为固定控制点",
                    },
                    {
                        "phase": "RLS",
                        "disposition": "n/a",
                        "host": "N/A",
                        "basis": "隔离测试不发版",
                    },
                ],
                "open_items": [],
                "evidence": [],
                "supporting_members": [],
                "exceptions": [],
            },
            "control_inputs": [],
            "final_confirmation": None,
        },
        "confirmations": [],
        "options": {"dry_run": True},
    }


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        workspace = Path(temporary)
        plugin = workspace / "plugin"
        project = workspace / "target-project"
        outside = workspace / "unrelated-cwd"
        project.mkdir()
        outside.mkdir()
        (plugin / "skills").mkdir(parents=True)

        shutil.copytree(ROOT / "packages", plugin / "packages")
        shutil.copytree(ROOT / "skills/_shared", plugin / "skills/_shared")
        shutil.copytree(
            ROOT / "skills/sdlc-100-req",
            plugin / "skills/sdlc-100-req",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        if (plugin / "docs").exists():
            print("runtime independence: FAIL: docs tree was copied", file=sys.stderr)
            return 1

        command = [
            sys.executable,
            str(plugin / "skills/sdlc-100-req/scripts/runtime_final.py"),
        ]
        completed = subprocess.run(
            command,
            input=json.dumps(_request(project), ensure_ascii=False),
            text=True,
            cwd=outside,
            capture_output=True,
            check=False,
        )
        try:
            result = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            print(
                "runtime independence: FAIL: stdout is not one JSON result: "
                + completed.stdout,
                file=sys.stderr,
            )
            return 1
        if completed.returncode != 0:
            print(
                f"runtime independence: FAIL: exit={completed.returncode} "
                f"result={result} stderr={completed.stderr}",
                file=sys.stderr,
            )
            return 1
        if not result.get("ok") or result.get("status") != "completed":
            print(
                "runtime independence: FAIL: dry-run did not complete: "
                + json.dumps(result, ensure_ascii=False),
                file=sys.stderr,
            )
            return 1
        warnings = result.get("warnings") or []
        if not any(item.get("code") == "DRY_RUN" for item in warnings):
            print("runtime independence: FAIL: DRY_RUN evidence missing", file=sys.stderr)
            return 1
        if (project / ".sdlc").exists():
            print("runtime independence: FAIL: dry-run created runtime state", file=sys.stderr)
            return 1

    print("sdlc-100-req runtime independence: PASS")
    print("docs copied: 0")
    print("external dependencies installed: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

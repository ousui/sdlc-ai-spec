#!/usr/bin/env python3
"""Static RLS schema/source review; real execution is recorded by the delivery runner."""
from __future__ import annotations

import argparse
import ast
import base64
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
import sys
import zlib

DEFAULT_ROOT = Path(__file__).resolve().parents[2]
SHADOW_SNAPSHOT_SHA = "1d2af1ad8d20c3935a72b632b47a14b62910b6ff"
FINAL_CANDIDATE_FIELDS = {
    "contract", "provisional", "vfy_reference", "revision_state",
    "artifact_status", "artifact_gate", "early_stop", "pending_fields",
    "scope_reference", "subject_references", "result_references",
    "subject_current_valid", "imp_chain_current_valid", "con_ver",
    "con_val", "product_result", "unresolved_returns", "rls_applicability",
    "release_target_obligations", "evidence_references", "exception",
    "exception_references", "source_digest", "rls_ready",
}
AUTHORIZATION_FIELDS = {
    "rls_artifact_reference",
    "release_contract_digest",
    "selected_rli_contract_digest",
    "release_item_set_digest",
    "confirmation_set_digest",
    "vfy_source_digest",
    "vfy_candidate_digest",
    "pre_execution_checklist_digest",
    "effect_digest",
}
BANNED_IMPORTS = {
    "requests", "httpx", "boto3", "paramiko", "socket", "subprocess",
}
BANNED_CALLS = {
    ("os", "system"), ("os", "popen"),
    ("subprocess", "run"), ("subprocess", "call"),
    ("subprocess", "Popen"), ("subprocess", "check_call"),
    ("subprocess", "check_output"),
}
BANNED_TEXT = (
    "git push", "git tag", "gh release", "github release",
    "kubectl ", "terraform apply", "aws deploy",
)


def _check(checks: list[dict], identity: str, condition: bool, detail: str) -> None:
    checks.append(
        {
            "id": identity,
            "status": "PASS" if condition else "FAIL",
            "detail": detail,
        }
    )


def _dotted_name(node: ast.AST) -> tuple[str, ...]:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return tuple(reversed(parts))


def scan_runtime_source(relative: str, text: str) -> list[str]:
    failures: list[str] = []
    try:
        tree = ast.parse(text, filename=relative)
    except SyntaxError as exc:
        return [f"syntax error: {exc}"]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".", 1)[0] in BANNED_IMPORTS:
                    failures.append(f"banned import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.split(".", 1)[0] in BANNED_IMPORTS:
                failures.append(f"banned import {module}")
        elif isinstance(node, ast.Call):
            name = _dotted_name(node.func)
            if name in BANNED_CALLS:
                failures.append(f"banned call {'.'.join(name)}")
    lowered = text.lower()
    for token in BANNED_TEXT:
        if token in lowered:
            failures.append(f"banned capability literal {token!r}")
    if "docs/" in text or "docs\\" in text:
        failures.append("runtime names development docs")
    return sorted(set(failures))


def _schema_checks(root: Path, checks: list[dict]) -> dict:
    path = root / "skills/sdlc-600-rls/references/vfy-release-candidate-v1.schema.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        _check(checks, "RLS-PW-001", False, f"candidate schema unreadable: {exc}")
        return {}
    _check(
        checks,
        "RLS-PW-001",
        data.get("$id") == "sdlc-ai-spec/vfy-release-candidate/v1"
        and data.get("additionalProperties") is False
        and set(data.get("required", [])) == FINAL_CANDIDATE_FIELDS
        and data.get("properties", {}).get("provisional", {}).get("const") is False,
        "bundled final-shaped VFY schema is exact and closed",
    )
    return data


def _runtime_scan(root: Path, checks: list[dict]) -> None:
    scripts = root / "skills/sdlc-600-rls/scripts"
    failures: list[str] = []
    for path in sorted(scripts.glob("*.py")):
        for failure in scan_runtime_source(
            path.relative_to(root).as_posix(),
            path.read_text(encoding="utf-8"),
        ):
            failures.append(f"{path.name}: {failure}")
    target_text = (scripts / "rls_target.py").read_text(encoding="utf-8")
    target_boundary = (
        "SandboxReleaseTarget" in target_text
        and "GitHubReleaseTarget" not in target_text
        and "ProductionReleaseTarget" not in target_text
    )
    _check(
        checks,
        "RLS-PW-008",
        not failures and target_boundary,
        "runtime has no network/process/release capability and exposes sandbox target only"
        if not failures
        else "; ".join(failures),
    )


def review(root: Path, profile: str = "final") -> dict:
    root = root.resolve()
    checks = []
    _schema_checks(root, checks)
    _runtime_scan(root, checks)
    from tools.validate_sdlc_600_rls_source_lock import validate
    try:
        validate(root)
        _check(checks, "RLS-PW-FINAL-LOCK", True, "final bundled bytes match accepted upstream")
    except Exception:
        _check(checks, "RLS-PW-FINAL-LOCK", False, "final Source Lock failed")
    _check(checks, "RLS-PW-AUTHORITY", profile == "final", "historical provisional profile cannot verify final delivery")
    return {"contract": "sdlc-ai-spec/rls-preweb-review/v1", "profile": profile,
            "provisional": False, "review_level": "STATIC_ONLY",
            "success": all(x["status"] == "PASS" for x in checks), "checks": checks,
            "final_requirements": [], "real_target_effects": 0,
            "fixed_eval": "NOT CLAIMED", "closed_loop": "NOT CLAIMED"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("provisional", "final"), required=True)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    try:
        result = review(args.root, args.profile)
    except Exception as exc:
        print(f"RLS_PREWEB_REVIEW = HARD_BLOCKED: {exc}", file=sys.stderr)
        return 1
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if result["success"]:
        print(f"RLS_PREWEB_REVIEW = PASS ({args.profile})")
        print("RLS_CLOSED_LOOP = NOT CLAIMED")
        print("REAL_TARGET_EFFECTS = 0")
        return 0
    failed = [row["id"] for row in result["checks"] if row["status"] != "PASS"]
    if args.profile == "final":
        failed.extend(
            row["id"]
            for row in result["final_requirements"]
            if row["status"] != "PASS"
        )
    print("RLS_PREWEB_REVIEW = HARD_BLOCKED", file=sys.stderr)
    print("FAILED_OR_DEFERRED = " + ",".join(failed), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

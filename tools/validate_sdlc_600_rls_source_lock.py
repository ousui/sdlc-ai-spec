#!/usr/bin/env python3
"""Validate the final RLS bundled Source Lock and exact accepted VFY schema."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = Path("skills/sdlc-600-rls/references/source-lock.json")
EXPECTED_PATHS = sorted(['packages/sdlc_artifact_store/__init__.py', 'packages/sdlc_artifact_store/models.py', 'packages/sdlc_lifecycle/query_rls.py', 'packages/sdlc_lifecycle/query_vfy.py', 'packages/sdlc_phasekit/models.py', 'packages/sdlc_runtime/authority.py', 'packages/sdlc_runtime/canonical.py', 'packages/sdlc_runtime/control_inputs.py', 'skills/_shared/contracts/skill-interface.md', 'skills/sdlc-status/references/rls-projection.schema.json', 'skills/sdlc-600-rls/references/600-rls-spec.md', 'skills/sdlc-600-rls/references/contract.md', 'skills/sdlc-600-rls/references/interface.json', 'skills/sdlc-600-rls/references/vfy-release-candidate-v1.schema.json'])


def validate(root: Path) -> dict:
    root = root.resolve()
    lock_path = root / LOCK_PATH
    if not lock_path.is_file():
        raise AssertionError(f"missing source lock: {LOCK_PATH}")
    data = json.loads(lock_path.read_text(encoding="utf-8"))
    if data.get("contract") != "sdlc-ai-spec/source-lock/v1":
        raise AssertionError("invalid source-lock contract")
    if (
        data.get("provisional") is not False
        or data.get("status") != "FINAL"
    ):
        raise AssertionError("Source Lock must bind final bundled contracts")
    upstream = data.get("vfy_upstream_sha")
    if upstream != "46509eb6688df30e71ed094132b2d10e81ceb2ac":
        raise AssertionError("Source Lock must bind accepted VFY")
    schema = root / "skills/sdlc-600-rls/references/vfy-release-candidate-v1.schema.json"
    if hashlib.sha256(schema.read_bytes()).hexdigest() != "15aff25625c2d43c29e62129ea3aaff9ee5ab45dd146eecff2b417e135d98027":
        raise AssertionError("bundled schema differs from accepted exact bytes")
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise AssertionError("source-lock entries must be an array")
    paths = [row.get("path") for row in entries]
    if paths != sorted(paths) or paths != EXPECTED_PATHS:
        raise AssertionError(
            f"source-lock paths are missing, extra or unsorted: {paths}"
        )
    if len(paths) != len(set(paths)):
        raise AssertionError("duplicate source-lock path")
    for row in entries:
        relative = row["path"]
        if relative.startswith("docs/") or Path(relative).is_absolute():
            raise AssertionError(
                f"development/absolute path in runtime source lock: {relative}"
            )
        path = root / relative
        if not path.is_file():
            raise AssertionError(f"missing bundled source: {relative}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != row.get("sha256"):
            raise AssertionError(f"digest mismatch: {relative}")
    return {
        "contract": "sdlc-ai-spec/rls-final-source-lock-validation/v1",
        "provisional": False,
        "vfy_upstream_sha": upstream,
        "entries": len(entries),
        "result": "PASS",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    try:
        result = validate(args.root)
    except Exception as exc:
        print(f"RLS_FINAL_SOURCE_LOCK = FAIL: {exc}", file=sys.stderr)
        return 1
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
    print(
        f"RLS_FINAL_SOURCE_LOCK = PASS "
        f"({result['entries']} bundled sources)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

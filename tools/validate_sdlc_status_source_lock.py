#!/usr/bin/env python3
"""Build/review-only status contract lock. Never imported by installed Runtime."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from packages.sdlc_runtime import ContractSource, SourceLockError, build_source_lock, verify_source_lock

LOCK = "skills/sdlc-status/references/source-lock.json"
# Status projects every phase through these shared modules, not sibling Skill code.
DEPENDENCIES = ("sdlc_artifact_store", "sdlc_lifecycle", "sdlc_runtime", "sdlc_claim_provider", "sdlc_resource", "sdlc_execution", "sdlc_phasekit")
RESOURCES = {
    "sdlc-ai-spec/status/conformance/v1": "skills/sdlc-status/references/conformance.md",
    "sdlc-ai-spec/status/contract/v1": "skills/sdlc-status/references/contract.md",
    "sdlc-ai-spec/status/interface/v1": "skills/sdlc-status/references/interface.json",
    "sdlc-ai-spec/status/result-schema/v1": "skills/sdlc-status/references/status-result.schema.json",
    "sdlc-ai-spec/status/rls-projection-schema/v1": "skills/sdlc-status/references/rls-projection.schema.json",
    "sdlc-ai-spec/status/entry/v1": "skills/sdlc-status/SKILL.md",
    "sdlc-ai-spec/runtime/skill-interface/v1": "skills/_shared/contracts/skill-interface.md",
    "sdlc-ai-spec/runtime/skill-execution/v1": "skills/_shared/contracts/skill-execution.md",
    "sdlc-ai-spec/runtime/lifecycle/v1": "packages/sdlc_lifecycle/CONTRACT.md",
    "sdlc-ai-spec/runtime/artifact-store/v1": "packages/sdlc_artifact_store/CONTRACT.md",
}


def sources(root: Path):
    rows = [ContractSource(key, "1", value) for key, value in RESOURCES.items()]
    directories = [root / "packages" / name for name in DEPENDENCIES] + [root / "skills/sdlc-status/scripts"]
    for directory in directories:
        if directory.is_symlink() or not directory.is_dir():
            raise SourceLockError("missing or linked status dependency: " + str(directory))
        files = sorted(directory.rglob("*.py"))
        if not files: raise SourceLockError("empty status dependency: " + str(directory))
        for path in files:
            if path.is_symlink(): raise SourceLockError("linked source is not allowed")
            relative = path.relative_to(root).as_posix()
            rows.append(ContractSource("sdlc-ai-spec/status/source/" + relative + "/v1", "1", relative))
    for row in rows:
        path = root / row.resource
        if any(p.is_symlink() for p in (path, *path.parents) if p != root.parent):
            raise SourceLockError("linked status source is not allowed")
    return tuple(rows)


def validate(root: Path = ROOT):
    expected = sources(root)
    lock_path = root / LOCK
    if lock_path.is_symlink(): raise SourceLockError("linked lock is not allowed")
    actual = json.loads(lock_path.read_text(encoding="utf-8"))
    verify_source_lock(root, actual, expected)
    return {"success": True, "skill": "sdlc-status", "contracts": len(expected)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Explicit build-time lock regeneration; never validation")
    args = parser.parse_args()
    try:
        if args.write:
            value = build_source_lock(ROOT, sources(ROOT))
            (ROOT / LOCK).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print("STATUS_SOURCE_LOCK = GENERATED; validation is separate")
        else: print(json.dumps(validate(), sort_keys=True))
        return 0
    except (OSError, ValueError, SourceLockError) as exc:
        print("STATUS_SOURCE_LOCK = FAIL: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__": raise SystemExit(main())

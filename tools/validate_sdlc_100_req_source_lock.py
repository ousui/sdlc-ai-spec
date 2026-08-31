#!/usr/bin/env python3
"""Verify the built sdlc-100-req source-lock against exact source bytes."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages"))

from packages.sdlc_runtime import (  # noqa: E402
    ContractSource,
    SourceLockError,
    build_source_lock,
    registry_sources,
    validate_source_lock_shape,
)

LOCK_PATH = ROOT / "skills/sdlc-100-req/references/source-lock.json"
REGISTRY_PATH = ROOT / "skills/_shared/contracts/registry.json"
SPEC_SOURCES = (
    ContractSource(
        "sdlc-ai-spec/spec/artifact-store/v1.1",
        "1.1",
        "docs/v1.1/artifact-store-spec.md",
    ),
    ContractSource(
        "sdlc-ai-spec/spec/core/v1.1",
        "1.1",
        "docs/v1.1/core-spec.md",
    ),
    ContractSource(
        "sdlc-ai-spec/spec/requirement/v1.1",
        "1.1",
        "docs/v1.1/100-req-spec.md",
    ),
)


def main() -> int:
    try:
        sources = (*registry_sources(ROOT, REGISTRY_PATH), *SPEC_SOURCES)
        expected = build_source_lock(ROOT, sources)
        actual = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        if validate_source_lock_shape(actual) != validate_source_lock_shape(expected):
            print("sdlc-100-req source lock: FAIL", file=sys.stderr)
            print(
                "EXPECTED_SOURCE_LOCK="
                + json.dumps(expected, ensure_ascii=False, sort_keys=True),
                file=sys.stderr,
            )
            return 1
    except (OSError, json.JSONDecodeError, SourceLockError) as exc:
        print(f"sdlc-100-req source lock: FAIL: {exc}", file=sys.stderr)
        return 1
    print("sdlc-100-req source lock: PASS")
    print("contracts:", len(expected["contracts"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Verify the built sdlc-200-dsn source lock and bundled contract bytes."""

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

LOCK_PATH = ROOT / "skills/sdlc-200-dsn/references/source-lock.json"
REGISTRY_PATH = ROOT / "skills/_shared/contracts/registry.json"
BUNDLED_ROOT = ROOT / "skills/sdlc-200-dsn/references"

DOMAIN_FILES = (
    "110-workflow-state.md",
    "120-ux-interaction.md",
    "130-ui-content.md",
    "140-accessibility-i18n.md",
    "210-system-architecture.md",
    "220-components-modules.md",
    "230-interfaces-integration.md",
    "240-data-design.md",
    "310-security-privacy-compliance.md",
    "320-performance-capacity.md",
    "330-reliability-recovery.md",
    "340-compatibility-migration.md",
    "350-maintainability-extensibility.md",
    "410-deployment-configuration.md",
    "420-observability-operability.md",
    "510-verifiability-vfy-strategy.md",
)

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
    *(
        ContractSource(
            f"sdlc-ai-spec/spec/design-domain/{name.split('-', 1)[0]}/v1.1",
            "1.1",
            f"docs/v1.1/200-dsn-domains/{name}",
        )
        for name in DOMAIN_FILES
    ),
    ContractSource(
        "sdlc-ai-spec/spec/design/v1.1",
        "1.1",
        "docs/v1.1/200-dsn-spec.md",
    ),
    ContractSource(
        "sdlc-ai-spec/spec/project-context/v1.1",
        "1.1",
        "docs/v1.1/000-ctx-spec.md",
    ),
    ContractSource(
        "sdlc-ai-spec/spec/requirement/v1.1",
        "1.1",
        "docs/v1.1/100-req-spec.md",
    ),
)


def _verify_bundled_bytes() -> None:
    pairs = [
        (
            ROOT / "docs/v1.1/200-dsn-spec.md",
            BUNDLED_ROOT / "200-dsn-spec.md",
        )
    ]
    pairs.extend(
        (
            ROOT / "docs/v1.1/200-dsn-domains" / name,
            BUNDLED_ROOT / "200-dsn-domains" / name,
        )
        for name in DOMAIN_FILES
    )
    for source, bundled in pairs:
        if not source.is_file() or not bundled.is_file():
            raise SourceLockError(
                f"bundled DSN contract is missing: {bundled.relative_to(ROOT)}"
            )
        if source.read_bytes() != bundled.read_bytes():
            raise SourceLockError(
                f"bundled DSN contract drift: {bundled.relative_to(ROOT)}"
            )


def main() -> int:
    try:
        sources = (*registry_sources(ROOT, REGISTRY_PATH), *SPEC_SOURCES)
        expected = build_source_lock(ROOT, sources)
        actual = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        if validate_source_lock_shape(actual) != validate_source_lock_shape(expected):
            print("sdlc-200-dsn source lock: FAIL", file=sys.stderr)
            print(
                "EXPECTED_SOURCE_LOCK="
                + json.dumps(expected, ensure_ascii=False, sort_keys=True),
                file=sys.stderr,
            )
            return 1
        _verify_bundled_bytes()
    except (OSError, json.JSONDecodeError, SourceLockError) as exc:
        print(f"sdlc-200-dsn source lock: FAIL: {exc}", file=sys.stderr)
        return 1
    print("sdlc-200-dsn source lock: PASS")
    print("contracts:", len(expected["contracts"]))
    print("bundled contracts:", 1 + len(DOMAIN_FILES))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

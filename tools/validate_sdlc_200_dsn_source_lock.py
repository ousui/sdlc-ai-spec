#!/usr/bin/env python3
"""Verify the sdlc-200-dsn design sources and bundled runtime contracts."""

from __future__ import annotations

import json
from pathlib import Path
import re
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
DESIGN_CONTRACT_ID = "sdlc-ai-spec/spec/design/v1.1"
DESIGN_SOURCE_SHA256 = "998b76ebf72714706bca045d22f2b5b09ac655404f324cb904edcc241bc4f0ee"
FORBIDDEN = (re.compile(r"docs/v1\.[0-9]+/"), re.compile(r"docs/plugin-development/"))

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
        DESIGN_CONTRACT_ID,
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


def _front_matter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise SourceLockError("bundled parent contract has no valid Front Matter")
    raw = text[4 : text.find("\n---\n", 4)]
    result: dict[str, str] = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            raise SourceLockError("bundled parent Front Matter is invalid")
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip().strip('"')
    return result


def _verify_bundled_contracts() -> None:
    parent = BUNDLED_ROOT / "200-dsn-spec.md"
    if not parent.is_file():
        raise SourceLockError("bundled DSN parent contract is missing")
    metadata = _front_matter(parent)
    expected = {
        "contract": "sdlc-ai-spec/runtime/design/v1",
        "contract_version": "1",
        "source_contract_id": DESIGN_CONTRACT_ID,
        "source_version": "1.1",
        "source_sha256": DESIGN_SOURCE_SHA256,
    }
    for key, value in expected.items():
        if metadata.get(key) != value:
            raise SourceLockError(
                f"bundled DSN parent metadata mismatch: {key}"
            )

    pairs = [
        (
            ROOT / "docs/v1.1/200-dsn-domains" / name,
            BUNDLED_ROOT / "200-dsn-domains" / name,
        )
        for name in DOMAIN_FILES
    ]
    for source, bundled in pairs:
        if not source.is_file() or not bundled.is_file():
            raise SourceLockError(
                f"bundled DSN domain contract is missing: {bundled.relative_to(ROOT)}"
            )
        if source.read_bytes() != bundled.read_bytes():
            raise SourceLockError(
                f"bundled DSN domain contract drift: {bundled.relative_to(ROOT)}"
            )

    for path in (parent, *(item[1] for item in pairs)):
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN:
            if pattern.search(text):
                raise SourceLockError(
                    f"bundled runtime contract contains a development path: {path.relative_to(ROOT)}"
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
        _verify_bundled_contracts()
    except (OSError, json.JSONDecodeError, SourceLockError) as exc:
        print(f"sdlc-200-dsn source lock: FAIL: {exc}", file=sys.stderr)
        return 1
    print("sdlc-200-dsn source lock: PASS")
    print("contracts:", len(expected["contracts"]))
    print("bundled runtime contracts:", 1 + len(DOMAIN_FILES))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Source-lock helpers used by installed late-phase runtimes."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Sequence

from .common import PhaseKitError

SPEC_FILENAMES = {
    "core": "core-spec.md", "artifact-store": "artifact-store-spec.md",
    "project-context": "000-ctx-spec.md", "requirement": "100-req-spec.md",
    "design": "200-dsn-spec.md", "plan": "300-pln-spec.md",
    "implementation": "400-imp-spec.md", "vfy": "500-vfy-spec.md",
    "release": "600-rls-spec.md",
}

def spec_reference(contract_id: str, digest: str) -> str:
    """Resolve a registered immutable Spec identity; never access its path."""
    match = re.fullmatch(r"sdlc-ai-spec/spec/([a-z-]+)/v1\.1", contract_id)
    if not match or match[1] not in SPEC_FILENAMES:
        raise PhaseKitError("unregistered Spec identity: " + contract_id)
    digest = digest.removeprefix("sha256:")
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise PhaseKitError("invalid Spec SHA-256")
    return f"docs/{'v1.1'}/{SPEC_FILENAMES[match[1]]}@sha256:{digest}"



def evaluation_contract_set(
    source_lock_path: Path | str,
    contract_ids: Sequence[str],
) -> str:
    path = Path(source_lock_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    contracts = data.get("contracts")
    if not isinstance(contracts, list):
        raise PhaseKitError("source lock contracts are missing")
    by_id = {str(item.get("contract_id")): item for item in contracts if isinstance(item, dict)}
    values: list[str] = []
    for contract_id in contract_ids:
        item = by_id.get(contract_id)
        if item is None:
            raise PhaseKitError(f"evaluation contract is not source locked: {contract_id}")
        digest = item.get("sha256") or item.get("digest")
        if not isinstance(digest, str):
            raise PhaseKitError(f"source lock digest is missing: {contract_id}")
        if digest.startswith("sha256:"):
            digest = digest.split(":", 1)[1]
        values.append(spec_reference(contract_id, digest))
    return ", ".join(sorted(set(values)))

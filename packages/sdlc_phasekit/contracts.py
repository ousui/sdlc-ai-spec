"""Source-lock helpers used by installed late-phase runtimes."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from .common import PhaseKitError


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
        values.append(f"{contract_id}@sha256:{digest}")
    return ", ".join(values)

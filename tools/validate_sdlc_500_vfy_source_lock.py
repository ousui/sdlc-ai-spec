#!/usr/bin/env python3
"""Strictly validate the complete VFY Runtime and design Source Lock."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LOCK_RELATIVE = Path("skills/sdlc-500-vfy/references/source-lock.json")
EXPECTED_CONTRACTS = (
    ("sdlc-ai-spec/runtime/artifact-store/v1", "1", "packages/sdlc_artifact_store/CONTRACT.md"),
    ("sdlc-ai-spec/runtime/artifact/v1", "1", "skills/_shared/contracts/artifact-runtime.md"),
    ("sdlc-ai-spec/runtime/imp-claim/v1", "1", "packages/sdlc_claim_provider/CONTRACT.md"),
    ("sdlc-ai-spec/runtime/kernel/v1", "1", "packages/sdlc_runtime/CONTRACT.md"),
    ("sdlc-ai-spec/runtime/lifecycle/v1", "1", "packages/sdlc_lifecycle/CONTRACT.md"),
    ("sdlc-ai-spec/runtime/phase/v1", "1", "skills/_shared/contracts/phase-runtime.md"),
    ("sdlc-ai-spec/runtime/resource-result/v1", "1", "packages/sdlc_resource/CONTRACT.md"),
    ("sdlc-ai-spec/runtime/skill-execution/v1", "1", "skills/_shared/contracts/skill-execution.md"),
    ("sdlc-ai-spec/runtime/skill-inputs/v1", "1", "skills/_shared/contracts/skill-inputs.md"),
    ("sdlc-ai-spec/runtime/skill-interface/v1", "1", "skills/_shared/contracts/skill-interface.md"),
    ("sdlc-ai-spec/runtime/status/v1", "1", "skills/sdlc-status/references/contract.md"),
    ("sdlc-ai-spec/runtime/vfy-interface/v1", "1", "skills/sdlc-500-vfy/references/interface.json"),
    ("sdlc-ai-spec/runtime/vfy/v1", "1", "skills/sdlc-500-vfy/references/contract.md"),
    ("sdlc-ai-spec/schema/status-result/v1", "1", "skills/sdlc-status/references/status-result.schema.json"),
    ("sdlc-ai-spec/schema/vfy-release-candidate/v1", "1", "skills/sdlc-500-vfy/references/vfy-release-candidate-v1.schema.json"),
    ("sdlc-ai-spec/spec/artifact-store/v1.1", "1.1", "docs/v1.1/artifact-store-spec.md"),
    ("sdlc-ai-spec/spec/core/v1.1", "1.1", "docs/v1.1/core-spec.md"),
    ("sdlc-ai-spec/spec/vfy/v1.1", "1.1", "skills/sdlc-500-vfy/references/500-vfy-spec.md"),
)
EXPECTED_DESIGN_SOURCES = (
    ("sdlc-ai-spec/spec/artifact-store/v1.1", "docs/v1.1/artifact-store-spec.md"),
    ("sdlc-ai-spec/spec/core/v1.1", "docs/v1.1/core-spec.md"),
    ("sdlc-ai-spec/spec/vfy/v1.1", "docs/v1.1/500-vfy-spec.md"),
)


def _git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _digest(root: Path, relative: str, expected: str) -> dict[str, str]:
    path = root / relative
    if not path.is_file():
        raise ValueError(f"Source Lock path does not exist: {relative}")
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if expected != actual:
        raise ValueError(
            f"Source Lock digest mismatch for {relative}: expected {expected}, got {actual}"
        )
    return {"path": relative, "sha256": actual}


def validate(*, require_final: bool, root: Path = ROOT) -> dict[str, Any]:
    root = Path(root).resolve()
    lock_path = root / LOCK_RELATIVE
    payload = json.loads(lock_path.read_text(encoding="utf-8"))
    if set(payload) != {"contract", "phase", "contracts", "design_sources"}:
        raise ValueError("Source Lock top-level fields are incomplete or contain extras")
    if payload["contract"] != "sdlc-ai-spec/vfy-source-lock/v1" or payload["phase"] != "VFY":
        raise ValueError("wrong final VFY Source Lock contract or phase")
    contracts = payload["contracts"]
    if not isinstance(contracts, list) or any(not isinstance(item, dict) for item in contracts):
        raise ValueError("Source Lock contracts must be an array of objects")
    actual_contracts = tuple(
        (item.get("contract_id"), item.get("contract_version")) for item in contracts
    )
    if actual_contracts != tuple((item[0], item[1]) for item in EXPECTED_CONTRACTS):
        raise ValueError("Source Lock Contract Set is missing, extra, duplicated, unsorted or remapped")
    if any(set(item) != {"contract_id", "contract_version", "sha256"} for item in contracts):
        raise ValueError("Source Lock Contract entry fields are incomplete or contain extras")
    verified = []
    contract_digests: dict[str, str] = {}
    for entry, (contract_id, _version, resource) in zip(contracts, EXPECTED_CONTRACTS):
        row = _digest(root, resource, str(entry["sha256"]))
        row["contract_id"] = contract_id
        verified.append(row)
        contract_digests[contract_id] = str(entry["sha256"])

    sources = payload["design_sources"]
    if not isinstance(sources, list) or any(not isinstance(item, dict) for item in sources):
        raise ValueError("design_sources must be an array of objects")
    if tuple(item.get("contract_id") for item in sources) != tuple(
        item[0] for item in EXPECTED_DESIGN_SOURCES
    ):
        raise ValueError("Design Source identities are missing, extra, duplicated or unsorted")
    if any(set(item) != {"contract_id", "git_blob", "sha256"} for item in sources):
        raise ValueError("Design Source fields are incomplete or contain extras")
    source_rows: list[dict[str, str]] = []
    for entry, (contract_id, resource) in zip(sources, EXPECTED_DESIGN_SOURCES):
        path = root / resource
        if not path.is_file():
            raise ValueError(f"Design Source path does not exist: {resource}")
        raw = path.read_bytes()
        row = _digest(root, resource, str(entry["sha256"]))
        actual_blob = _git_blob(raw)
        if entry["git_blob"] != actual_blob:
            raise ValueError(
                f"Design Source Git blob mismatch for {resource}: expected {entry['git_blob']}, got {actual_blob}"
            )
        if entry["sha256"] != contract_digests[contract_id]:
            raise ValueError(f"Design Source digest does not match locked contract: {contract_id}")
        row["contract_id"] = contract_id
        row["git_blob"] = actual_blob
        source_rows.append(row)
    return {
        "contract": "sdlc-ai-spec/vfy-source-lock-validation/v1",
        "status": "PASS",
        "provisional": False,
        "require_final": require_final,
        "contract_count": len(verified),
        "design_source_count": len(source_rows),
        "contracts": verified,
        "design_sources": source_rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-final", action="store_true")
    parser.add_argument("--json-out", type=Path)
    arguments = parser.parse_args(argv)
    try:
        report = validate(require_final=arguments.require_final)
        code = 0
    except Exception as exc:
        report = {
            "contract": "sdlc-ai-spec/vfy-source-lock-validation/v1",
            "status": "FAIL",
            "provisional": False,
            "require_final": arguments.require_final,
            "error": {"type": exc.__class__.__name__, "message": str(exc)},
        }
        code = 2
    text = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if arguments.json_out:
        arguments.json_out.parent.mkdir(parents=True, exist_ok=True)
        arguments.json_out.write_text(text, encoding="utf-8")
    print(text, end="")
    return code


if __name__ == "__main__":
    raise SystemExit(main())

"""Build-time source-lock registry and verification helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

REGISTRY_CONTRACT = "sdlc-ai-spec/runtime-contract-registry/v1"
SOURCE_LOCK_CONTRACT = "sdlc-ai-spec/runtime-source-lock/v1"


class SourceLockError(ValueError):
    """Raised when a runtime contract registry or source lock is invalid."""


@dataclass(frozen=True)
class ContractSource:
    contract_id: str
    contract_version: str
    resource: str


def _safe_relative_path(value: str) -> Path:
    path = Path(value)
    if not value or path.is_absolute() or value.startswith("./") or ".." in path.parts:
        raise SourceLockError(
            f"resource must be a safe repository-relative path: {value}"
        )
    return path


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_registry(path: Path) -> tuple[ContractSource, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("contract") != REGISTRY_CONTRACT:
        raise SourceLockError(f"registry contract must be {REGISTRY_CONTRACT}")
    if payload.get("contract_version") != "1":
        raise SourceLockError("registry contract_version must be 1")
    if set(payload) != {"contract", "contract_version", "contracts"}:
        raise SourceLockError("registry contains unsupported fields")
    contracts = payload["contracts"]
    if not isinstance(contracts, list) or not contracts:
        raise SourceLockError("registry contracts must be a non-empty array")
    result: list[ContractSource] = []
    seen: set[str] = set()
    for item in contracts:
        if not isinstance(item, Mapping):
            raise SourceLockError("registry contract entry must be an object")
        if set(item) != {"contract_id", "contract_version", "resource"}:
            raise SourceLockError("registry contract entry contains unsupported fields")
        contract_id = item["contract_id"]
        contract_version = item["contract_version"]
        resource = item["resource"]
        if not all(
            isinstance(value, str) and value
            for value in (contract_id, contract_version, resource)
        ):
            raise SourceLockError("registry fields must be non-empty strings")
        _safe_relative_path(resource)
        if contract_id in seen:
            raise SourceLockError(f"duplicate contract_id: {contract_id}")
        seen.add(contract_id)
        result.append(ContractSource(contract_id, contract_version, resource))
    if [item.contract_id for item in result] != sorted(seen):
        raise SourceLockError("registry contracts must be sorted by contract_id")
    return tuple(result)


def build_source_lock(
    repository_root: Path,
    sources: Sequence[ContractSource],
) -> dict[str, object]:
    contracts = []
    seen: set[str] = set()
    for source in sorted(sources, key=lambda item: item.contract_id):
        if source.contract_id in seen:
            raise SourceLockError(f"duplicate contract_id: {source.contract_id}")
        seen.add(source.contract_id)
        resource_path = repository_root / _safe_relative_path(source.resource)
        if not resource_path.is_file():
            raise SourceLockError(
                f"contract resource does not exist: {source.resource}"
            )
        contracts.append(
            {
                "contract_id": source.contract_id,
                "contract_version": source.contract_version,
                "sha256": sha256_file(resource_path),
            }
        )
    return {"contract": SOURCE_LOCK_CONTRACT, "contracts": contracts}


def validate_source_lock_shape(
    value: Mapping[str, object],
) -> tuple[dict[str, str], ...]:
    if set(value) != {"contract", "contracts"}:
        raise SourceLockError("source lock contains unsupported fields")
    if value.get("contract") != SOURCE_LOCK_CONTRACT:
        raise SourceLockError(
            f"source lock contract must be {SOURCE_LOCK_CONTRACT}"
        )
    contracts = value.get("contracts")
    if not isinstance(contracts, list):
        raise SourceLockError("source lock contracts must be an array")
    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in contracts:
        if not isinstance(item, Mapping):
            raise SourceLockError("source lock entry must be an object")
        if set(item) != {"contract_id", "contract_version", "sha256"}:
            raise SourceLockError("source lock entry contains unsupported fields")
        contract_id = item.get("contract_id")
        version = item.get("contract_version")
        digest = item.get("sha256")
        if not isinstance(contract_id, str) or not contract_id:
            raise SourceLockError("contract_id must be a non-empty string")
        if not isinstance(version, str) or not version:
            raise SourceLockError("contract_version must be a non-empty string")
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(char not in "0123456789abcdef" for char in digest)
        ):
            raise SourceLockError(
                "sha256 must be 64 lowercase hexadecimal characters"
            )
        if contract_id in seen:
            raise SourceLockError(f"duplicate contract_id: {contract_id}")
        seen.add(contract_id)
        normalized.append(
            {
                "contract_id": contract_id,
                "contract_version": version,
                "sha256": digest,
            }
        )
    if [item["contract_id"] for item in normalized] != sorted(seen):
        raise SourceLockError("source lock contracts must be sorted by contract_id")
    return tuple(normalized)


def verify_source_lock(
    repository_root: Path,
    lock: Mapping[str, object],
    sources: Sequence[ContractSource],
) -> None:
    actual = validate_source_lock_shape(lock)
    expected = validate_source_lock_shape(build_source_lock(repository_root, sources))
    if actual != expected:
        raise SourceLockError("source lock does not match the required contract set")


def registry_sources(
    repository_root: Path, registry_path: Path
) -> tuple[ContractSource, ...]:
    sources = load_registry(registry_path)
    for source in sources:
        path = repository_root / _safe_relative_path(source.resource)
        if not path.is_file():
            raise SourceLockError(
                f"registry resource does not exist: {source.resource}"
            )
    return sources

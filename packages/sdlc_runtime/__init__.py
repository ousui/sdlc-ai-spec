"""Shared runtime kernel for all sdlc-ai-spec Phase Skills."""

from .envelopes import (
    EnvelopeValidationError,
    INVOCATION_CONTRACT,
    OPERATIONS,
    RESULT_CONTRACT,
    error_result,
    validate_invocation,
    validate_result,
)
from .phase import PhaseHandler, execute_phase
from .source_lock import (
    ContractSource,
    REGISTRY_CONTRACT,
    SOURCE_LOCK_CONTRACT,
    SourceLockError,
    build_source_lock,
    load_registry,
    registry_sources,
    sha256_file,
    validate_source_lock_shape,
    verify_source_lock,
)

__all__ = [
    "ContractSource",
    "EnvelopeValidationError",
    "INVOCATION_CONTRACT",
    "OPERATIONS",
    "PhaseHandler",
    "REGISTRY_CONTRACT",
    "RESULT_CONTRACT",
    "SOURCE_LOCK_CONTRACT",
    "SourceLockError",
    "build_source_lock",
    "error_result",
    "execute_phase",
    "load_registry",
    "registry_sources",
    "sha256_file",
    "validate_invocation",
    "validate_result",
    "validate_source_lock_shape",
    "verify_source_lock",
]

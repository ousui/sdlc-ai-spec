"""Stable ArtifactStore exception hierarchy."""


class ArtifactStoreError(Exception):
    """Base class for all public ArtifactStore failures."""

    code = "ARTIFACT_STORE_ERROR"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class InvalidInputError(ArtifactStoreError):
    code = "INVALID_INPUT"


class ReadOnlyError(ArtifactStoreError):
    code = "READ_ONLY"


class StoreNotFoundError(ArtifactStoreError):
    code = "STORE_NOT_FOUND"


class SchemaError(ArtifactStoreError):
    code = "SCHEMA_ERROR"


class SchemaVersionMismatchError(SchemaError):
    code = "SCHEMA_VERSION_MISMATCH"


class DatabaseError(ArtifactStoreError):
    code = "DATABASE_ERROR"


class TrackedRuntimeContentError(ArtifactStoreError):
    code = "TRACKED_RUNTIME_CONTENT"


class ConflictError(ArtifactStoreError):
    code = "CONFLICT"


class NotFoundError(ArtifactStoreError):
    code = "NOT_FOUND"


class ControlReservationError(ArtifactStoreError):
    code = "CONTROL_RESERVATION"


class InvalidStateError(ArtifactStoreError):
    code = "INVALID_STATE"


class IntegrityError(ArtifactStoreError):
    code = "INTEGRITY_ERROR"


class VerifierRequiredError(ArtifactStoreError):
    code = "VERIFIER_REQUIRED"


class VerificationFailedError(ArtifactStoreError):
    code = "VERIFICATION_FAILED"


class StaleVerificationError(ArtifactStoreError):
    code = "STALE_VERIFICATION"


class ReferenceError(ArtifactStoreError):
    code = "REFERENCE_ERROR"

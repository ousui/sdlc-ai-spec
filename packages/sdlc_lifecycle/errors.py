"""Errors returned by the strictly read-only lifecycle query layer."""

from __future__ import annotations

from typing import Any, Mapping


class LifecycleQueryError(ValueError):
    """Base error with a stable code and structured details."""

    code = "LIFECYCLE_QUERY_ERROR"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.code
        self.details = dict(details or {})

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details:
            result["details"] = dict(self.details)
        return result


class LifecycleStoreUnavailable(LifecycleQueryError):
    code = "LIFECYCLE_STORE_UNAVAILABLE"


class LifecycleReferenceError(LifecycleQueryError):
    code = "LIFECYCLE_REFERENCE_INVALID"


class LifecycleArtifactError(LifecycleQueryError):
    code = "LIFECYCLE_ARTIFACT_INVALID"


class LifecycleSelectionRequired(LifecycleQueryError):
    code = "LIFECYCLE_SELECTION_REQUIRED"

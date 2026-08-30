"""Minimal routing protocol shared by SDLC Phase runtimes."""

from __future__ import annotations

from typing import Any, Mapping, Protocol

from .envelopes import validate_invocation, validate_result


class PhaseHandler(Protocol):
    """A Phase-specific handler for the three shared operation modes."""

    def create(self, invocation: Mapping[str, Any]) -> Mapping[str, Any]:
        ...

    def revise(self, invocation: Mapping[str, Any]) -> Mapping[str, Any]:
        ...

    def check(self, invocation: Mapping[str, Any]) -> Mapping[str, Any]:
        ...


def execute_phase(
    handler: PhaseHandler, invocation: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate, dispatch exactly one operation, then validate the result."""

    normalized = validate_invocation(invocation)
    operation = normalized["operation"]
    method = getattr(handler, operation, None)
    if method is None or not callable(method):
        raise TypeError(f"Phase handler does not implement operation: {operation}")
    return validate_result(method(normalized))

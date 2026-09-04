"""Authoritative VFY Exception normalization and scope validation."""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from vfy_common import exact_item_reference, require, stable_unique

EXCEPTION_ID_RE = re.compile(r"^EX-[0-9]{3}$")
ACTIVE_STATES = frozenset({"active", "carried"})


def normalize_exceptions(rows: Any) -> list[dict[str, Any]]:
    require(isinstance(rows, list), "VFY_EXCEPTION_INVALID", "Exceptions must be an array")
    output: list[dict[str, Any]] = []
    ids: set[str] = set()
    origins: set[str] = set()
    for position, raw in enumerate(rows, 1):
        require(isinstance(raw, Mapping), "VFY_EXCEPTION_INVALID", "Exception entries must be objects")
        identity = str(raw.get("id", "")).strip()
        require(
            EXCEPTION_ID_RE.fullmatch(identity) is not None and identity not in ids,
            "VFY_EXCEPTION_INVALID",
            "Exception ID must be unique EX-NNN",
            details={"position": position, "id": identity},
        )
        ids.add(identity)
        state = str(raw.get("state", "")).strip()
        require(
            state in ACTIVE_STATES,
            "VFY_EXCEPTION_INVALID",
            "Only active/carried Exceptions can affect VFY",
            details={"id": identity, "state": state},
        )
        origin = exact_item_reference(
            str(raw.get("origin_reference") or raw.get("reference") or "")
        )
        require(
            "#EX-" in origin and origin not in origins,
            "VFY_EXCEPTION_INVALID",
            "Exception must bind one unique exact owner item",
            details={"reference": origin},
        )
        origins.add(origin)
        scope = list(stable_unique(raw.get("scope", []), field="exception scope"))
        require(bool(scope), "VFY_EXCEPTION_INVALID", "Exception scope cannot be empty")
        fields: dict[str, str] = {}
        for key in (
            "reason",
            "known_risk",
            "compensating_control",
            "approval",
            "revisit_condition",
            "downstream_obligation",
        ):
            value = str(raw.get(key, "")).strip()
            require(
                bool(value) and value not in {"N/A", "None", "pending"},
                "VFY_EXCEPTION_INVALID",
                f"Exception {key} is required",
                details={"id": identity},
            )
            fields[key] = value
        require(
            raw.get("authority_verified") is True,
            "VFY_EXCEPTION_INVALID",
            "Exception was not read from one frozen owner Artifact",
            details={"reference": origin},
        )
        output.append(
            {
                "id": identity,
                "state": state,
                "origin_reference": origin,
                "scope": scope,
                **fields,
                "resolution_references": list(
                    stable_unique(
                        raw.get("resolution_references", []),
                        field="exception resolution",
                    )
                ),
                "accepts_product_failure": bool(raw.get("accepts_product_failure")),
                "authority_verified": True,
            }
        )
    return output


def exception_index(
    exceptions: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    return {str(item["origin_reference"]): item for item in exceptions}


def validate_exception_bindings(
    methods: Sequence[Mapping[str, Any]],
    exceptions: Sequence[Mapping[str, Any]],
    *,
    rls_applicability: str,
    scope_tokens: Sequence[str],
) -> None:
    indexed = exception_index(exceptions)
    boundary = {
        *(str(item) for item in scope_tokens),
        "product_result:fail",
        *(
            str(value)
            for method in methods
            for value in (
                method.get("id"),
                *method.get("target_references", []),
                *method.get("obligation_references", []),
                *method.get("subject_references", []),
            )
            if value
        ),
    }
    if rls_applicability == "waived":
        boundary.update({"phase:RLS", "RLS"})
    for exception in exceptions:
        require(
            bool(set(exception["scope"]) & boundary),
            "VFY_EXCEPTION_INVALID",
            "Exception scope does not intersect the current VFY boundary",
            details={"reference": exception.get("origin_reference")},
        )
    for method in methods:
        if method.get("disposition") != "waived":
            continue
        reference = str(method.get("exception_reference") or "")
        exception = indexed.get(reference)
        require(
            exception is not None,
            "VFY_EXCEPTION_INVALID",
            "Waived Method references no current verified Exception",
            details={"method_id": method.get("id"), "reference": reference},
        )
        covered = {
            str(method.get("id")),
            *(str(item) for item in method.get("target_references", [])),
            *(str(item) for item in method.get("obligation_references", [])),
            *(str(item) for item in method.get("subject_references", [])),
        }
        require(
            bool(set(exception["scope"]) & covered),
            "VFY_EXCEPTION_INVALID",
            "Exception scope does not cover the waived Method",
            details={"method_id": method.get("id"), "reference": reference},
        )
    if rls_applicability == "waived":
        require(
            any(
                "phase:RLS" in item["scope"]
                or "RLS" in item["scope"]
                or "RLS" in item["downstream_obligation"]
                for item in exceptions
            ),
            "VFY_EXCEPTION_INVALID",
            "RLS applicability=waived requires a current scoped Exception",
        )


def active_failure_exception(
    exceptions: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    for item in exceptions:
        if (
            item.get("accepts_product_failure") is True
            and "product_result:fail" in item.get("scope", [])
        ):
            return item
    return None

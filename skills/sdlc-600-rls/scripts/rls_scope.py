"""Exact RLS Scope and Result Set normalization."""
from rls_common import require, stable_unique


def bind_scope(candidate, requested_scope=None, requested_results=None):
    scope = requested_scope or candidate.scope_reference
    results = stable_unique(requested_results or candidate.result_references)
    require(scope == candidate.scope_reference, "RLS_SCOPE_MISMATCH", "RLS cannot change VFY Scope")
    require(
        set(results) == set(candidate.result_references)
        and len(results) == len(candidate.result_references),
        "RLS_RESULT_MISMATCH",
        "RLS cannot shrink, replace or merge the Result Set",
    )
    return {
        "scope_reference": scope,
        "result_references": list(candidate.result_references),
    }

"""Current RLS risk grants and deterministic carried Exception closure."""
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from rls_common import assert_no_secret, canonical_json, parse_time, require, utc_now
from rls_contract import effect_digest
from rls_safe_files import SafeDirectory


class TrustedRlsExceptions:
    """Explicit host risk approval; business JSON is never its own authority."""
    def __init__(self, root):
        self.files = SafeDirectory(Path(root).resolve(), (".sdlc", "authority", "rls-exceptions"))

    def _raw(self, value):
        assert_no_secret(value)
        return (canonical_json(value) + "\n").encode()

    def grant(self, state, ids, *, approved, authorizer, reason, known_risk,
              compensating_control, revisit_condition, downstream_obligation, valid_until=None):
        require(approved is True and state["artifact"]["revision_state"] == "open",
                "RLS_EXCEPTION_INVALID", "explicit host risk approval of an open Revision is required")
        rows = {row["id"]: row for row in state["release_items"] + state["confirmations"]}
        require(ids and len(ids) == len(set(ids)) and set(ids) <= set(rows)
                and all(rows[identity]["result"] == "pending" for identity in ids),
                "RLS_EXCEPTION_INVALID", "risk grant requires exact pending items")
        now = utc_now()
        fields = dict(authorizer=authorizer, reason=reason, known_risk=known_risk,
                      compensating_control=compensating_control, revisit_condition=revisit_condition,
                      downstream_obligation=downstream_obligation)
        require(all(isinstance(value, str) and value.strip() for value in fields.values()),
                "RLS_EXCEPTION_INVALID", "risk approval fields are incomplete")
        value = dict(contract="sdlc-ai-spec/rls-risk-grant/v1", id="EX-900", state="active",
                     artifact_reference=state["artifact"]["reference"], effect_digest=effect_digest(state),
                     scope=list(ids), approved_at=now,
                     valid_until=valid_until or (parse_time(now) + timedelta(hours=1)).isoformat(), **fields)
        require(parse_time(value["valid_until"]) > parse_time(now), "RLS_EXCEPTION_INVALID", "risk approval is expired")
        self.files.write(value["artifact_reference"] + "#EX-900.json", self._raw(value), exclusive=True)
        return value

    def verify(self, state, value):
        require(value.get("id") == "EX-900" and value.get("state") == "active"
                and value.get("artifact_reference") == state["artifact"]["reference"]
                and value.get("effect_digest") == effect_digest(state),
                "RLS_EXCEPTION_INVALID", "current risk grant binding differs")
        try:
            raw = self.files.read(state["artifact"]["reference"] + "#EX-900.json")
        except FileNotFoundError:
            require(False, "RLS_EXCEPTION_INVALID", "risk grant has no trusted host record")
        require(raw == self._raw(value), "RLS_EXCEPTION_INVALID", "risk grant differs from immutable host record")
        observed = (state.get("final_confirmation") or {}).get("confirmed_at") if state["artifact"]["revision_state"] == "frozen" else utc_now()
        require(parse_time(value["approved_at"]) <= parse_time(observed) <= parse_time(value["valid_until"]),
                "RLS_EXCEPTION_INVALID", "risk grant does not cover the current acceptance time")


def derive_exceptions(state):
    if state.get("provisional", True): return []
    active = state.get("active_exceptions", [])
    require(len(active) <= 1 and all(row.get("id") == "EX-900" for row in active),
            "RLS_EXCEPTION_INVALID", "one explicit current risk grant is supported per Revision")
    grant = active[0] if active else None
    reference = state["artifact"]["reference"]
    for item in state["release_items"] + state["confirmations"]:
        if item["result"] == "waived":
            require(grant is not None and item["id"] in grant["scope"]
                    and item.get("exception_reference") == reference + "#EX-900",
                    "RLS_EXCEPTION_INVALID", "waived item lacks a current scoped RLS risk grant")
    rows = []
    for index, original in enumerate(state.get("upstream_exceptions", []), 1):
        row = deepcopy(original); row.update(id=f"EX-{index:03d}", state="carried", resolution_references=[])
        source = original["origin_reference"]
        mapped = [item for item in state["confirmations"] if source in item["source_references"]]
        if mapped:
            results = {item["result"] for item in mapped}
            if not results & {"pending", "not_run"}:
                if "waived" in results:
                    waived = {item["id"] for item in mapped if item["result"] == "waived"}
                    require(grant is not None and waived <= set(grant["scope"]),
                            "RLS_EXCEPTION_INVALID", "one current RLS Exception must cover every re-waived obligation")
                    row.update(state="superseded", resolution_references=[reference + "#EX-900"])
                else:
                    require(results <= {"pass", "fail"}, "RLS_EXCEPTION_INVALID", "carried obligation needs actual target results")
                    row.update(state="resolved", resolution_references=sorted({
                        *(reference + "#" + item["id"] for item in mapped),
                        *(ref for item in mapped for ref in item["evidence_references"])}))
        rows.append(row)
    for value in active:
        rows.append(dict(value, origin_reference=reference + "#EX-900", approval=value["authorizer"] + " at " + value["approved_at"],
                         resolution_references=[]))
    return rows


def unresolved_exception_references(state):
    return [state["artifact"]["reference"] + "#" + row["id"] for row in state.get("exceptions", [])
            if row["state"] in {"active", "carried"}]


def verify_current_exceptions(root, state, candidate):
    require(state.get("upstream_exceptions", []) == list(candidate.authority_exceptions)
            and state.get("exceptions", []) == derive_exceptions(state),
            "RLS_EXCEPTION_INVALID", "RLS Exception ledger differs from current upstream and RCF outcomes")
    for row in state.get("active_exceptions", []): TrustedRlsExceptions(root).verify(state, row)

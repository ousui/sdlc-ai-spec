"""Host-recorded human RCF observations. Not an effect or final-approval grant."""
from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
import re

from rls_common import assert_no_secret, canonical_json, parse_time, require, sha256_bytes, sha256_value, utc_now
from rls_confirmation_policy import compile_confirmation, observation_binding
from rls_safe_files import SafeDirectory

CONTRACT = "sdlc-ai-spec/rls-human-observation/v1"
ERROR = "RLS_HUMAN_EVIDENCE_INVALID"
MAX_SOURCE_BYTES = 65536
_FIELDS = {"contract", "observation_id", "binding", "evaluator", "observed_at", "recorded_at", "valid_until",
           "source_digest", "source_reference", "result", "observation"}
_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")


def _time(value):
    require(isinstance(value, str) and _TIME.fullmatch(value) is not None, ERROR, "observation time must be RFC3339")
    try:
        return parse_time(value)
    except Exception:
        require(False, ERROR, "invalid observation time")


def _id(record):
    return "HRCF-" + sha256_value({key: value for key, value in record.items() if key != "observation_id"})


def validate_record(record, binding, *, max_age_seconds, at):
    require(isinstance(record, dict) and set(record) == _FIELDS and record.get("contract") == CONTRACT,
            ERROR, "one exact structured human observation is required")
    assert_no_secret(record)
    require(record["binding"] == binding, ERROR, "human observation has the wrong Revision/RCF/Scope/Result/Target/scenario")
    require(record["evaluator"] == binding["executor"]
            and isinstance(record["evaluator"], str)
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}", record["evaluator"]) is not None,
            ERROR, "human evaluator differs from the contracted stable identity")
    require(isinstance(record["result"], str) and record["result"] in {"pass", "fail"} and isinstance(record["observation"], str)
            and 0 < len(record["observation"]) <= 8192, ERROR, "explicit human pass/fail and observation are required")
    observed, recorded, expires, consumed = map(_time, (record["observed_at"], record["recorded_at"], record["valid_until"], at))
    require(observed <= recorded <= consumed <= expires and 0 < (expires - observed).total_seconds() <= max_age_seconds,
            ERROR, "human observation is future-dated, expired or outside its contracted age")
    require(re.fullmatch(r"sha256:[0-9a-f]{64}", str(record["source_digest"])) is not None
            and record["source_reference"] == "HRCF-SOURCE-" + record["source_digest"][7:]
            and record["observation_id"] == _id(record), ERROR, "human source or record digest differs")
    return record


class TrustedHumanObservations:
    """Trusted host records an actual human observation; business CLI only reads.

    This is the existing local host/filesystem trust boundary, not a signature or
    a claim that a malicious same-user process cannot forge host records.
    """
    def __init__(self, project_root):
        self.root = Path(project_root).resolve(strict=True)
        self.records = SafeDirectory(self.root, (".sdlc", "authority", "rls-human-observations"))
        self.sources = SafeDirectory(self.root, (".sdlc", "authority", "rls-human-observation-sources"))

    def _raw(self, value):
        assert_no_secret(value)
        return (canonical_json(value) + "\n").encode("utf-8")

    def record(self, artifact, rcf_id, target, *, evaluator, observed_at, result,
               observation, source_bytes, attested, valid_until=None):
        require(attested is True and artifact["artifact"]["revision_state"] == "open",
                ERROR, "explicit host attestation of an open exact RCF is required")
        rows = [row for row in artifact["confirmations"] if row["id"] == rcf_id]
        require(len(rows) == 1 and rows[0]["result"] == "pending", ERROR, "human RCF must be uniquely pending")
        row = rows[0]
        plan = compile_confirmation(row, artifact["release_contract"]["release_reference"])
        require(plan["kind"] == "human", ERROR, "human mode must be contracted before effects")
        require(target.target_id == artifact["release_contract"]["release_target"]
                and str(target.root) == artifact["release_contract"]["target_locator"], ERROR, "human target differs")
        require(isinstance(source_bytes, bytes) and 0 < len(source_bytes) <= MAX_SOURCE_BYTES,
                ERROR, "human source must be bounded immutable UTF-8 bytes")
        try:
            source_text = source_bytes.decode("utf-8")
        except UnicodeDecodeError:
            require(False, ERROR, "this observation source format is not supported")
        assert_no_secret(source_text)
        snapshot = target.assert_expected_state(artifact["release_contract"]["target_baseline"], artifact.get("target_snapshot_after"))
        recorded_at = utc_now()
        expires = valid_until or (_time(observed_at) + timedelta(seconds=plan["max_age_seconds"])).isoformat()
        digest = sha256_bytes(source_bytes)
        value = {"contract": CONTRACT, "binding": observation_binding(artifact, row, snapshot),
                 "evaluator": evaluator, "observed_at": observed_at, "recorded_at": recorded_at,
                 "valid_until": expires, "source_digest": "sha256:" + digest,
                 "source_reference": "HRCF-SOURCE-" + digest, "result": result, "observation": observation}
        value["observation_id"] = _id(value)
        validate_record(value, value["binding"], max_age_seconds=plan["max_age_seconds"], at=recorded_at)
        require(len(self._raw(value)) <= MAX_SOURCE_BYTES, ERROR, "human record exceeds its byte bound")
        # Validation and secret rejection precede all writes. The original source
        # is stored verbatim, addressed by its digest, never accepted as a path.
        try:
            self.sources.write(digest + ".txt", source_bytes, exclusive=True)
        except FileExistsError:
            require(self.sources.read(digest + ".txt", max_bytes=MAX_SOURCE_BYTES) == source_bytes, ERROR, "human source changed")
        try:
            self.records.write(value["observation_id"] + ".json", self._raw(value), exclusive=True)
        except FileExistsError:
            require(self.records.read(value["observation_id"] + ".json", max_bytes=MAX_SOURCE_BYTES) == self._raw(value), ERROR, "human record changed")
        return deepcopy(value)

    def verify(self, artifact, row, snapshot, record, *, at=None):
        plan = compile_confirmation(row, artifact["release_contract"]["release_reference"])
        require(plan["kind"] == "human", ERROR, "observation supplied to an automated RCF")
        validate_record(record, observation_binding(artifact, row, snapshot),
                        max_age_seconds=plan["max_age_seconds"], at=at or utc_now())
        try:
            saved = self.records.read(record["observation_id"] + ".json", max_bytes=MAX_SOURCE_BYTES)
            source = self.sources.read(record["source_digest"][7:] + ".txt", max_bytes=MAX_SOURCE_BYTES)
        except (FileNotFoundError, OSError):
            require(False, ERROR, "trusted human record or immutable source is unavailable")
        require(saved == self._raw(record) and "sha256:" + sha256_bytes(source) == record["source_digest"],
                ERROR, "human record/source bytes do not match trusted host history")
        return deepcopy(record)

    def verify_history(self, artifact):
        rows = {row["id"]: row for row in artifact["confirmations"]}
        for evidence in artifact.get("evidence", []):
            event = evidence["event"]
            row = rows.get(event.get("item"))
            if row is not None and row.get("subjective") and event.get("result") in {"pass", "fail"}:
                # Expiry limits observation consumption, not later historical reads.
                self.verify(artifact, row, event["observed"], event.get("human_evidence"), at=event["observed_at"])

"""Host-only effect approval and append-only consumption records.

The trusted host invokes grant after an explicit approval decision. The business
CLI can only consume an already-issued record, never manufacture a grant from
stdin. Trust is the project-local host/filesystem boundary, not a JSON signature
or protection against a malicious same-user process.
"""
import json
from pathlib import Path
from rls_authorization import issue_authorization, validate_authorization
from rls_common import assert_no_secret, canonical_json, parse_time, require, sha256_value, utc_now
from rls_safe_files import SafeDirectory


class TrustedEffectRecords:
    def __init__(self, root):
        self.files = SafeDirectory(Path(root).resolve(), (".sdlc", "authority", "rls-effects"))

    def grant(self, artifact, ids, *, authorizer_identity, approved, valid_until=None):
        require(approved is True, "RLS_EFFECT_AUTHORIZATION_REQUIRED", "host approval decision is required")
        authorization = issue_authorization(artifact, ids, authorizer_identity, valid_until=valid_until)
        self.files.write(authorization["authorization_id"] + ".grant.json", self._raw(authorization), exclusive=True)
        return authorization

    def _raw(self, value):
        assert_no_secret(value)
        return (canonical_json(value) + "\n").encode()

    def verify(self, artifact, authorization, *, consumed=False):
        require(isinstance(authorization, dict), "RLS_EFFECT_AUTHORIZATION_REQUIRED", "host grant is required")
        identifier = authorization.get("authorization_id", "")
        import re
        require(bool(re.fullmatch(r"EA-[0-9a-f]{16}", identifier)), "RLS_EFFECT_AUTHORIZATION_REQUIRED", "invalid host grant identity")
        try:
            stored = self.files.read(identifier + ".grant.json")
        except FileNotFoundError:
            require(False, "RLS_EFFECT_AUTHORIZATION_REQUIRED", "authorization has no trusted host grant")
        require(stored == self._raw(authorization), "RLS_EFFECT_AUTHORIZATION_STALE", "trusted grant differs from supplied authorization")
        if consumed:
            record = json.loads(self.files.read(identifier + ".used.json"))
            require(record["grant_digest"] == sha256_value(authorization)
                    and record["artifact_reference"] == artifact["artifact"]["reference"]
                    and parse_time(authorization["authorized_at"]) <= parse_time(record["consumed_at"]) <= parse_time(authorization["valid_until"]),
                    "RLS_EFFECT_AUTHORIZATION_STALE", "consumption is not bound to grant time and Revision")
            return record

    def consume(self, artifact, authorization, ids):
        self.verify(artifact, authorization)
        validate_authorization(artifact, authorization, ids)
        record = {"grant_digest": sha256_value(authorization), "artifact_reference": artifact["artifact"]["reference"], "consumed_at": utc_now()}
        try:
            self.files.write(authorization["authorization_id"] + ".used.json", self._raw(record), exclusive=True)
        except FileExistsError:
            require(False, "RLS_EFFECT_AUTHORIZATION_STALE", "host grant has already been consumed")
        return record

    def verify_history(self, artifact):
        for record in artifact.get("effect_authorization_history", []):
            consumption = self.verify(artifact, record, consumed=True)
            for evidence in artifact.get("evidence", []):
                event = evidence["event"]
                if event.get("item") in record["rli_ids"]:
                    require(parse_time(consumption["consumed_at"]) <= parse_time(event["observed_at"]) <= parse_time(record["valid_until"]),
                            "RLS_EFFECT_AUTHORIZATION_STALE", "execution timestamp falls outside consumed grant")

"""Append-only effect recovery journal, outside the ArtifactStore payload."""
import json
from pathlib import Path
import uuid
from rls_common import assert_no_secret, canonical_json, require, sha256_value, utc_now
from rls_safe_files import SafeDirectory


class ExecutionJournal:
    def __init__(self, root, reference):
        self.reference = reference
        self.files = SafeDirectory(Path(root).resolve(), (".sdlc", "rls-execution", reference))

    def append(self, stage, state, *, item=None, attempt=None):
        value = {"contract": "sdlc-ai-spec/rls-execution-journal/v1", "artifact_reference": self.reference,
                 "stage": stage, "item": item, "attempt": attempt, "recorded_at": utc_now(), "state": state}
        assert_no_secret(value)
        raw = (canonical_json(value) + "\n").encode()
        name = uuid.uuid4().hex + ".json"
        self.files.write(name, raw, exclusive=True)
        return name

    def unresolved(self):
        records = [json.loads(self.files.read(name)) for name in self.files.names() if name.endswith(".json")]
        attempts = {x["attempt"] for x in records if x["stage"] == "intent"}
        committed = {x["attempt"] for x in records if x["stage"] == "persisted"}
        return sorted(attempts - committed)

    def require_resolved(self):
        require(not self.unresolved(), "RLS_EXECUTION_UNCERTAIN", "effect recovery journal requires explicit reconciliation; automatic replay and cancel are forbidden")

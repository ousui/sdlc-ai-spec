from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills/sdlc-600-rls/scripts"
for entry in (ROOT, SCRIPTS):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from rls_authorization import issue_authorization
from rls_builder import build_provisional
from rls_common import canonical_json, sha256_bytes, sha256_value
from rls_handler import cancel, confirm, create, execute, finalize, mark_not_run_before_effect
from rls_target import SandboxReleaseTarget
from rls_confirmation_policy import STATE_CONFIRMATION, STATE_EVIDENCE, STATE_EXPECTATION
from rls_vfy_adapter import adapt_vfy_payload

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures/vfy-release-candidate-v1.json"


def fixture_payload(name: str = "pass") -> dict:
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return deepcopy(data["cases"][name])


def candidate(name: str = "pass", **changes):
    # TEST_FIX_REASON: historical transition tests require an executable target
    # observation. Preserve the raw prose fixture for adapter/negative tests;
    # this explicit scenario retains BOTH version and basic health obligations.
    payload = fixture_payload(name)
    if name == "pass":
        payload["release_target_obligations"][0].update(
            confirmation=STATE_CONFIRMATION,
            expected=json.dumps({"contract": STATE_EXPECTATION,
                                 "equals": {"version": "1.0.0", "health": "healthy"}}),
            evidence_requirement=STATE_EVIDENCE,
        )
    payload.update(changes)
    return adapt_vfy_payload(payload)


class HistoricalSandboxTarget(SandboxReleaseTarget):
    """Synthetic healthy local target for the explicit legacy test scenario."""

    def _default_state(self):
        return {**super()._default_state(), "health": "healthy"}


def artifact(name: str = "pass", **kwargs) -> dict:
    values = {
        "release_reference": "1.0.0",
        "release_target": "sandbox-a",
        "target_baseline": "N/A — Initial Release",
        "artifact_id": "RLS-20260904110000-01",
    }
    values.update(kwargs)
    value = build_provisional(candidate(name), **values)
    value.update(context_reference="CTX-20260904070000-01@1", profile="default",
                 input_references=[value["release_contract"]["scope_reference"], value["release_contract"]["vfy_reference"]])
    return value


def two_item_artifact() -> dict:
    rows = [
        {
            "id": "RLI-001",
            "action": "apply application artifact",
            "source_references": ["IMP-20260904080000-01@1/RES-001"],
            "prerequisite_satisfied": True,
            "executor": "sandbox-executor",
            "result": "pending",
            "follow_up": "none",
            "evidence_references": [],
        },
        {
            "id": "RLI-002",
            "action": "apply configuration artifact",
            "source_references": ["IMP-20260904080000-01@1/RES-001"],
            "prerequisite_satisfied": True,
            "executor": "sandbox-executor",
            "result": "pending",
            "follow_up": "none",
            "evidence_references": [],
        },
    ]
    return artifact(release_items=rows)


@contextmanager
def sandbox(target_id: str = "sandbox-a"):
    with tempfile.TemporaryDirectory(prefix="rls-provisional-") as root:
        target = HistoricalSandboxTarget(root, target_id)
        yield target


def authorize(value: dict, ids=("RLI-001",), at="2026-09-04T04:00:00Z") -> dict:
    return issue_authorization(
        value,
        list(ids),
        "test-authorizer",
        authorized_at=at,
        valid_until="2026-09-04T04:15:00Z",
    )


def run_authorized(value: dict, target: SandboxReleaseTarget, ids=("RLI-001",), behaviors=None) -> dict:
    auth = authorize(value, ids)
    return execute(value, target, list(ids), auth, behaviors=behaviors, now="2026-09-04T04:05:00Z")


def complete_success(value: dict, target: SandboxReleaseTarget) -> dict:
    pending = [row["id"] for row in value["release_items"] if row["result"] == "pending"]
    if pending:
        run_authorized(value, target, pending)
    confirmations = [row["id"] for row in value["confirmations"] if row["result"] == "pending"]
    if confirmations:
        confirm(value, target, confirmations)
    return finalize(value)


def complete_failure_before_effect(value: dict, target: SandboxReleaseTarget) -> dict:
    run_authorized(value, target, ["RLI-001"], {"RLI-001": "failure"})
    evidence_ref = value["release_items"][0]["evidence_references"][0]
    mark_not_run_before_effect(value, evidence_ref)
    return finalize(value)


def rewrite_evidence_event(value: dict, reference: str, **changes) -> str:
    row = next(item for item in value["evidence"] if item["reference"] == reference)
    row["event"].update(changes)
    payload = (canonical_json(row["event"]) + "\n").encode("utf-8")
    digest = sha256_bytes(payload)
    old = row["reference"]
    row.update(reference=f"SANDBOX-EVD-{digest}", sha256=digest, locator=f"evidence/{digest}.json")
    for item in value["release_items"] + value["confirmations"]:
        item["evidence_references"] = [row["reference"] if x == old else x for x in item["evidence_references"]]
    return row["reference"]


def dataclass_replace(value, **changes):
    return replace(value, **changes)

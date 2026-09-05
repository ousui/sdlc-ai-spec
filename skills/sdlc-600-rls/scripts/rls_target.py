"""Target protocol and the only provisional implementation: an OS-temp sandbox."""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import tempfile
import re
from rls_safe_files import SafeDirectory

from rls_common import (
    assert_no_secret,
    canonical_json,
    require,
    sha256_bytes,
    sha256_value,
    utc_now,
)


class SandboxReleaseTarget:
    """Content-addressed local target with no network, Git or production capability."""

    def __init__(self, root, target_id: str = "sandbox") -> None:
        require(
            isinstance(root, (str, os.PathLike)),
            "RLS_TARGET_REQUIRED",
            "Sandbox Target root is required",
        )
        supplied = Path(root).expanduser()
        require(".." not in supplied.parts, "RLS_PATH_UNSAFE", "Sandbox path traversal is forbidden")
        supplied = Path(os.path.abspath(supplied))
        raw_temp = Path(tempfile.gettempdir())
        temp_root = raw_temp.resolve()
        try:
            parts = supplied.relative_to(raw_temp).parts
        except ValueError:
            try:
                parts = supplied.relative_to(temp_root).parts
            except ValueError:
                parts = ()
        require(bool(parts), "RLS_TARGET_REQUIRED", "Sandbox must be beneath OS temp")
        self.files = SafeDirectory(temp_root, parts)
        self.evidence_files = SafeDirectory(temp_root, (*parts, "evidence"))
        self.root = self.files.path
        try:
            with self.files.open():
                pass
        except FileNotFoundError:
            pass
        require(
            self.root != temp_root and temp_root in self.root.parents,
            "RLS_TARGET_REQUIRED",
            "Sandbox Target must be a dedicated directory under the OS temp directory",
        )
        require(
            isinstance(target_id, str) and target_id.strip() and "," not in target_id,
            "RLS_TARGET_REQUIRED",
            "one unique Sandbox Target ID is required",
        )
        self.target_id = target_id.strip()
        self.state_path = self.root / "target-state.json"
        self.evidence_dir = self.root / "evidence"

    def _default_state(self) -> dict:
        return {
            "target": self.target_id,
            "version": None,
            "applied": [],
            "partial": [],
        }

    def snapshot(self) -> dict:
        try:
            state = json.loads(self.files.read("target-state.json"))
        except FileNotFoundError:
            return self._default_state()
        assert_no_secret(state)
        require(
            isinstance(state, dict) and state.get("target") == self.target_id,
            "RLS_TARGET_STATE_UNVERIFIED",
            "Sandbox Target state is malformed or belongs to another target",
        )
        return state

    def baseline(self):
        state = self.snapshot()
        return "N/A — Initial Release" if state == self._default_state() else state

    def assert_expected_state(self, target_baseline, expected_snapshot=None) -> dict:
        """Fail closed if the target drifted since contract capture or last RLS effect."""
        observed_snapshot = self.snapshot()
        if expected_snapshot is None:
            expected = target_baseline
            observed = (
                "N/A — Initial Release"
                if observed_snapshot == self._default_state()
                else observed_snapshot
            )
            dimension = "target_baseline"
        else:
            expected = expected_snapshot
            observed = observed_snapshot
            dimension = "target_snapshot_after"
        require(
            sha256_value(observed) == sha256_value(expected),
            "RLS_EFFECT_AUTHORIZATION_STALE",
            "Sandbox Target changed after the Release Contract or prior RLS effect",
            dimension=dimension,
            expected_digest=sha256_value(expected),
            observed_digest=sha256_value(observed),
        )
        return observed_snapshot

    def _write_state(self, state: dict) -> None:
        assert_no_secret(state)
        self.files.write("target-state.json", (canonical_json(state) + "\n").encode())

    def _evidence(self, event: dict) -> dict:
        assert_no_secret(event)
        payload = (canonical_json(event) + "\n").encode("utf-8")
        digest = sha256_bytes(payload)
        try:
            self.evidence_files.write(f"{digest}.json", payload, exclusive=True)
        except FileExistsError:
            require(self.evidence_files.read(f"{digest}.json") == payload,
                    "RLS_EVIDENCE_TAMPERED", "immutable evidence changed")
        return {"reference": f"SANDBOX-EVD-{digest}", "sha256": digest,
                "locator": f"evidence/{digest}.json", "event": event}

    def execute(self, item: dict, release_reference: str, behavior: str = "success"):
        require(
            behavior in {"no-op", "success", "partial", "failure"},
            "RLS_EXECUTION_FAILED",
            "unsupported sandbox behavior",
        )
        require(
            item.get("prerequisite_satisfied") is True,
            "RLS_EXECUTION_FAILED",
            "Release Item prerequisite is not satisfied",
            item=item.get("id"),
        )
        assert_no_secret({"item": item, "release_reference": release_reference})
        before = self.snapshot()
        after = deepcopy(before)
        target_effect = False
        if behavior == "success":
            if after.get("version") != release_reference or item["id"] not in after["applied"]:
                after["version"] = release_reference
                if item["id"] not in after["applied"]:
                    after["applied"].append(item["id"])
                target_effect = after != before
        elif behavior == "partial":
            if item["id"] not in after["partial"]:
                after["partial"].append(item["id"])
            target_effect = after != before
        if target_effect:
            self._write_state(after)
        result = {
            "no-op": "success",
            "success": "success",
            "partial": "partial",
            "failure": "fail",
        }[behavior]
        event = {
            "target": self.target_id,
            "artifact_reference": item.get("artifact_reference"),
            "release_reference": release_reference,
            "item": item["id"],
            "behavior": behavior,
            "result": result,
            "before": before,
            "after": after,
            "target_effect": target_effect,
            "observed_at": utc_now(),
            "executor": item.get("executor"),
        }
        return result, target_effect, self._evidence(event), before, after

    def _confirmation_event(
        self, confirmation: dict, release_reference: str, *, force_fail: bool = False,
        human_evidence: dict | None = None, artifact: dict | None = None,
        trusted_observations=None,
    ) -> dict:
        from rls_confirmation_policy import (
            compile_confirmation, evaluate_automatic, human_evaluation, observation_binding,
        )
        assert_no_secret(confirmation)
        if human_evidence is not None:
            assert_no_secret(human_evidence)
        plan = compile_confirmation(confirmation, release_reference)
        if artifact is not None:
            contract = artifact["release_contract"]
            require(contract["release_reference"] == release_reference
                    and contract["release_target"] == self.target_id
                    and (artifact.get("provisional", True) or contract.get("target_locator") == str(self.root)),
                    "RLS_TARGET_STATE_UNVERIFIED", "confirmation target/Release Contract mismatch")
        # A human result is accepted only through the service's trusted reader.
        # Bare stdin evidence and automated version checks cannot impersonate it.
        if plan["kind"] == "human":
            require(artifact is not None and trusted_observations is not None,
                    "RLS_HUMAN_EVIDENCE_INVALID", "trusted host human observation is required")
            require(force_fail is False, "RLS_HUMAN_EVIDENCE_INVALID", "cannot override a human judgment")
        else:
            require(human_evidence is None, "RLS_HUMAN_EVIDENCE_INVALID", "human Evidence supplied to automated RCF")
        state = self.snapshot()
        observed_at = utc_now()
        binding = observation_binding(artifact, confirmation, state) if artifact is not None else None
        if plan["kind"] == "human":
            record = trusted_observations.verify(artifact, confirmation, state, human_evidence, at=observed_at)
            evaluation = human_evaluation(confirmation, record)
        else:
            record = None
            evaluation = evaluate_automatic(confirmation, release_reference, state, force_fail=force_fail)
        return {
            "target": self.target_id,
            "artifact_reference": artifact["artifact"]["reference"] if artifact is not None else confirmation.get("artifact_reference"),
            "release_reference": release_reference, "item": confirmation["id"],
            "result": evaluation["result"], "expected_release_reference": release_reference,
            "observed": state, "observed_at": observed_at, "executor": confirmation["executor"],
            "human_evidence": record, "confirmation_binding": binding,
            "confirmation_evaluation": evaluation,
        }

    def preflight_confirmation(self, confirmation: dict, release_reference: str, **options) -> None:
        """Validate an entire batch without writing any Target/Evidence files."""
        self._confirmation_event(confirmation, release_reference, **options)

    def confirm(
        self, confirmation: dict, release_reference: str, *, force_fail: bool = False,
        human_evidence: dict | None = None, artifact: dict | None = None,
        trusted_observations=None,
    ):
        event = self._confirmation_event(confirmation, release_reference, force_fail=force_fail,
                    human_evidence=human_evidence, artifact=artifact, trusted_observations=trusted_observations)
        return event["result"], self._evidence(event), event["observed"]

    def evidence_bytes(self, reference: str) -> bytes:
        digest = reference.removeprefix("SANDBOX-EVD-")
        require(bool(re.fullmatch(r"[0-9a-f]{64}", digest)), "RLS_EVIDENCE_TAMPERED", "invalid Evidence reference")
        try:
            data = self.evidence_files.read(f"{digest}.json")
        except FileNotFoundError:
            require(False, "RLS_EVIDENCE_TAMPERED", "evidence file is missing")
        require(sha256_bytes(data) == digest, "RLS_EVIDENCE_TAMPERED", "evidence digest mismatch")
        return data

    def cleanup(self) -> None:
        temp_root = Path(tempfile.gettempdir()).resolve()
        require(
            self.root != temp_root and temp_root in self.root.parents,
            "RLS_TARGET_REQUIRED",
            "unsafe Sandbox cleanup root",
        )
        try:
            with self.files.open():
                pass
        except FileNotFoundError:
            return
        shutil.rmtree(self.root)

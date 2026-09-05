"""Final RLS operations: exact Store authority, CAS writes and host effects."""
from copy import deepcopy
from pathlib import Path
from packages.sdlc_runtime import compute_control_input_digest, compute_check_set_result_digest, parse_canonical_artifact
from rls_common import require, utc_now
from rls_exceptions import unresolved_exception_references
from rls_canonical import render_markdown, evaluation_contract_set
from rls_contract import final_confirmation_digest
from rls_conclusion import apply_conclusion
from rls_domain_verifier import validate_current_upstream
from rls_execution_journal import ExecutionJournal
from rls_trusted_effect import TrustedEffectRecords
from rls_human_evidence import TrustedHumanObservations
from rls_persistence import create_revision, read_revision, write_open_revision, freeze_revision
from rls_vfy_adapter import read_vfy_candidate
from rls_verifier import verify
import rls_handler as domain


class RlsService:
    def __init__(self, root):
        self.root = Path(root).expanduser().resolve(strict=True)

    def create(self, vfy_reference, target, *, release_reference, **contracts):
        candidate = read_vfy_candidate(self.root, vfy_reference)
        value = domain.create(candidate, release_reference=release_reference, release_target=target.target_id,
                              target_baseline=target.baseline(), **contracts)
        if value.get("artifact") is None:
            return value, None
        value["release_contract"]["target_locator"] = str(target.root)
        from rls_contract import pre_execution_checklist
        from rls_common import sha256_value
        value["pre_execution_checklist"] = pre_execution_checklist(value["release_contract"], value["release_items"], value["confirmations"])
        value["pre_execution_checklist_digest"] = sha256_value(value["pre_execution_checklist"])
        return create_revision(self.root, value)

    def read(self, reference, *, recovery=False):
        state, generation = read_revision(self.root, reference)
        require(not state.get("provisional", True), "RLS_VFY_NOT_READY", "final operations reject provisional Artifact authority")
        if not recovery:
            ExecutionJournal(self.root, reference).require_resolved()
            require(not state.get("effect_uncertain"), "RLS_EXECUTION_UNCERTAIN", "unresolved target effect requires reconciliation")
        validate_current_upstream(self.root, state)
        TrustedEffectRecords(self.root).verify_history(state)
        TrustedHumanObservations(self.root).verify_history(state)
        return state, generation

    def _target(self, state, target):
        require(target.target_id == state["release_contract"]["release_target"]
                and str(target.root) == state["release_contract"]["target_locator"],
                "RLS_EFFECT_AUTHORIZATION_STALE", "Sandbox identity or location differs from the authorized contract")

    def check(self, reference, target):
        state, generation = self.read(reference)
        self._target(state, target)
        if state["artifact"]["revision_state"] == "abandoned":
            return {"ok": True, "revision_state": "abandoned", "artifact_gate": "pending", "release_conclusion": "pending"}
        before_gate = state["artifact_gate"]
        projection = domain.check(state, target)
        require(before_gate == projection["artifact_gate"], "RLS_CONTRACT_INVALID", "stored Gate differs from read-only recomputation")
        if state["artifact"]["revision_state"] == "frozen":
            verify(deepcopy(state), finalizing=True)
        return dict(projection, artifact_reference=reference, generation=generation)

    def execute(self, reference, target, ids, authorization, *, behaviors=None):
        state, generation = self.read(reference)
        self._target(state, target)
        if "no-op" in (behaviors or {}).values():
            require(target.snapshot().get("version") == state["release_contract"]["release_reference"],
                    "RLS_EXECUTION_FAILED", "no-op requires the target already at the exact Release Reference")
        def persist(current):
            nonlocal generation
            _, generation = write_open_revision(self.root, current, expected_generation=generation)
        domain.execute(state, target, ids, authorization, behaviors=behaviors,
                       trusted_records=TrustedEffectRecords(self.root),
                       journal=ExecutionJournal(self.root, reference), persist=persist)
        verify(state)
        persist(state)
        return state, generation

    def confirm(self, reference, target, ids, **observations):
        state, generation = self.read(reference)
        self._target(state, target)
        def persist(current):
            nonlocal generation
            verify(current)
            _, generation = write_open_revision(self.root, current, expected_generation=generation)
        domain.confirm(state, target, ids, trusted_observations=TrustedHumanObservations(self.root),
                       persist=persist, **observations)
        verify(state)
        return write_open_revision(self.root, state, expected_generation=generation)

    def waive(self, reference, target, risk_grant):
        state, generation = self.read(reference)
        self._target(state, target)
        from rls_exceptions import TrustedRlsExceptions
        TrustedRlsExceptions(self.root).verify(state, risk_grant)
        rows = {row["id"]: row for row in state["release_items"] + state["confirmations"]}
        require(all(identity in rows and rows[identity]["result"] == "pending" for identity in risk_grant["scope"]),
                "RLS_EXCEPTION_INVALID", "risk grant can only waive pending exact items")
        state["active_exceptions"] = [deepcopy(risk_grant)]
        for identity in risk_grant["scope"]:
            rows[identity].update(result="waived", follow_up="none", exception_reference=reference + "#EX-900")
        verify(state)
        return write_open_revision(self.root, state, expected_generation=generation)

    def mark_not_run(self, reference, target):
        state, generation = self.read(reference)
        self._target(state, target)
        domain.check(state, target)
        require(not state.get("target_effect") and all(row["result"] in {"fail", "cancelled"} for row in state["release_items"]),
                "RLS_TARGET_STATE_UNVERIFIED", "not_run requires a causative terminal failure with zero effect")
        domain.mark_not_run_before_effect(state, state["release_items"][0]["evidence_references"][0])
        verify(state)
        return write_open_revision(self.root, state, expected_generation=generation)

    def cancel(self, reference, target):
        state, generation = self.read(reference)
        self._target(state, target)
        domain.cancel(state, target)
        return write_open_revision(self.root, state, expected_generation=generation)

    def revise(self, reference, vfy_reference, target, *, retry=False):
        state, _ = self.read(reference)
        candidate = read_vfy_candidate(self.root, vfy_reference)
        if target.target_id == state["release_contract"]["release_target"]:
            self._target(state, target)
        new = domain.revise(state, candidate, target=target.target_id, target_baseline=target.baseline(), retry=retry)
        if new["artifact"]["reference"] == reference:
            return new, None
        new["release_contract"]["target_locator"] = str(target.root)
        from rls_contract import pre_execution_checklist
        from rls_common import sha256_value
        new["pre_execution_checklist"] = pre_execution_checklist(new["release_contract"], new["release_items"], new["confirmations"])
        new["pre_execution_checklist_digest"] = sha256_value(new["pre_execution_checklist"])
        same_artifact = new["artifact"]["id"] == state["artifact"]["id"]
        if same_artifact:
            new["artifact"]["allocated"] = True
        return create_revision(self.root, new, base_revision=state["artifact"]["revision"] if same_artifact else None)

    def confirmation_requirements(self, reference, target):
        state, _ = self.read(reference)
        self._target(state, target)
        domain.check(state, target)
        return self._confirmation_requirements(state)

    def _confirmation_requirements(self, state):
        terminal = deepcopy(state)
        apply_conclusion(terminal)
        projection = verify(terminal)
        require(projection["artifact_gate"] in {"pass", "pass_with_exception"}, "RLS_CONCLUSION_INCONSISTENT", "terminal items are required for final confirmation")
        terminal["status"] = "ready_with_exception" if terminal["artifact_gate"] == "pass_with_exception" else "ready"
        terminal["final_confirmation"] = None
        primary = render_markdown(terminal)
        return {"control_input_digest": compute_control_input_digest(primary),
                "check_set_result_digest": compute_check_set_result_digest(parse_canonical_artifact(primary)),
                "evaluation_contract_set": evaluation_contract_set(),
                "accepted_exception_references": unresolved_exception_references(terminal)}

    def finalize(self, reference, target, confirmation):
        state, generation = self.read(reference)
        self._target(state, target)
        require(state["artifact"]["revision_state"] == "open", "RLS_CONTRACT_INVALID", "finalize requires open Revision")
        domain.check(state, target)
        requirements = self._confirmation_requirements(state)
        require(isinstance(confirmation, dict) and all(confirmation.get(k) == v for k, v in requirements.items()),
                "RLS_FINAL_CONFIRMATION_STALE", "confirmation must explicitly bind current computed requirements")
        require(confirmation.get("mode") in {"human", "delegated"} and confirmation.get("authority_reference"),
                "RLS_FINAL_CONFIRMATION_STALE", "separate final authority record is required")
        apply_conclusion(state)
        state["status"] = "ready_with_exception" if state["artifact_gate"] == "pass_with_exception" else "ready"
        state["final_confirmation"] = {**confirmation, "confirmer_identity": confirmation["confirmer"],
                                       "digest": final_confirmation_digest(state)}
        verify(state, finalizing=True)
        _, generation = write_open_revision(self.root, state, expected_generation=generation, allow_terminal_staging=True)
        return freeze_revision(self.root, reference, expected_generation=generation)

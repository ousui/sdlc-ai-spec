"""Negative boundary faults originate in real persisted accepted producer state."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import tempfile
from unittest.mock import patch
from tests.skill_rls.final_support import FinalRlsCase, snapshot, run_cli, read_vfy_candidate
from tools.rls_fixture_chain import build_chain
from packages.sdlc_artifact_store import ArtifactStore
from packages.sdlc_lifecycle.query_vfy import LifecycleQueryService as VfyQuery
from rls_vfy_adapter import _verify_current_subjects, _verify_exceptions, _verify_supporting, _verify_applicability, _verify_controls


class FinalVfyBoundaryTests(FinalRlsCase):
    def test_producer_full_state_digest_and_24_wire_fields_differential(self):
        self.assertEqual(24, len(self.chain["candidate"]))
        value = read_vfy_candidate(self.root,self.chain["vfy"],expected_candidate=self.chain["candidate"])
        self.assertEqual(self.chain["candidate"]["source_digest"], value.source_digest)
        self.assertNotEqual(value.source_digest, value.candidate_digest)
        changed=deepcopy(self.chain["candidate"]);changed["source_digest"]="sha256:"+"0"*64
        self.code("RLS_VFY_NOT_READY",read_vfy_candidate,self.root,self.chain["vfy"],expected_candidate=changed)

    def test_real_frozen_early_stop_and_return_are_rejected(self):
        for variant in ("early_stop", "unresolved_return"):
            with tempfile.TemporaryDirectory(prefix="rls-real-stop-") as directory:
                root=Path(directory).resolve();chain=build_chain(root,**{variant:True})
                self.assertEqual("frozen",chain["state"]["artifact"]["revision_state"])
                self.assertTrue(chain["state"]["returns"])
                before=snapshot(root)
                self.code("RLS_VFY_NOT_READY",read_vfy_candidate,root,chain["vfy"])
                self.assertEqual(before,snapshot(root))

    def test_real_open_pending_vfy_cannot_be_release_authority(self):
        with tempfile.TemporaryDirectory(prefix="rls-real-open-vfy-") as directory:
            root=Path(directory).resolve();chain=build_chain(root,finalize_vfy=False)
            self.assertEqual("open",chain["state"]["artifact"]["revision_state"])
            with self.assertRaises(Exception): read_vfy_candidate(root,chain["vfy"])

    def test_current_imp_claim_result_digest_and_scope_are_recomputed(self):
        projection=VfyQuery(self.root).inspect_requirement(self.chain["requirement"])
        for key in ("result_digest","binding_lineage","attempt"):
            state=deepcopy(self.chain["state"]);state["subjects"][0][key]="stale"
            self.code("RLS_VFY_NOT_READY",_verify_current_subjects,state,projection)
        state=deepcopy(self.chain["state"]);state["scope"]["delivery_scope"]=[]
        self.code("RLS_SCOPE_MISMATCH",_verify_current_subjects,state,projection)
        state=deepcopy(self.chain["state"]);state["subjects"]=[]
        self.code("RLS_RESULT_MISMATCH",_verify_current_subjects,state,projection)

    def test_expired_or_wrong_scope_exception_is_not_current_authority(self):
        root,chain,_=self.variant(product_failure=True)
        store=ArtifactStore.open_read_only(root)
        _verify_exceptions(store,root,chain["state"])
        for field,value in (("state","expired"),("scope",["unrelated:scope"]),("accepts_product_failure",False)):
            state=deepcopy(chain["state"]);state["exceptions"][0][field]=value
            self.code("RLS_VFY_NOT_READY",_verify_exceptions,store,root,state)

    def test_missing_actual_vfy_evidence_member_is_rejected(self):
        state=self.chain["state"];identity=state["artifact"]
        stored=ArtifactStore.open_read_only(self.root).read_revision(identity["id"],identity["revision"])
        changed=replace(stored,payload=replace(stored.payload,members=stored.payload.members[:1]))
        self.code("RLS_VFY_NOT_READY",_verify_supporting,changed,state)

    def test_applicability_cannot_self_report_n_a_or_pending(self):
        projection=VfyQuery(self.root).inspect_requirement(self.chain["requirement"])
        for value in ("n/a","pending","waived"):
            state=deepcopy(self.chain["state"]);state["rls_applicability"]=value
            self.code("RLS_VFY_NOT_READY",_verify_applicability,ArtifactStore.open_read_only(self.root),self.root,state,projection)

    def test_control_input_cannot_omit_authority_or_self_report_resolution(self):
        state=deepcopy(self.chain["state"]);state["control_inputs"]=[self.chain["vfy"]+"#RET-001"]
        self.code("RLS_VFY_NOT_READY",_verify_controls,state)
        state=deepcopy(self.chain["state"]);state["control_resolutions"]=[dict(control_reference=self.chain["vfy"]+"#RET-001",status="resolved")]
        self.code("RLS_VFY_NOT_READY",_verify_controls,state)

    def test_existing_auto_reads_current_rls_without_allocating_another_artifact(self):
        self.create();before=snapshot(self.root)
        self.code("RLS_EFFECT_AUTHORIZATION_REQUIRED",run_cli,["auto","-p",str(self.root)],{"sandbox_root":str(self.target.root)})
        self.assertEqual(before,snapshot(self.root))

    def test_new_target_location_with_same_id_cannot_silently_reuse(self):
        self.finish()
        from rls_target import SandboxReleaseTarget
        with tempfile.TemporaryDirectory(prefix="rls-drift-target-") as directory:
            target=SandboxReleaseTarget(directory,"sandbox-a")
            self.code("RLS_EFFECT_AUTHORIZATION_STALE",self.service.revise,self.reference,self.chain["vfy"],target)

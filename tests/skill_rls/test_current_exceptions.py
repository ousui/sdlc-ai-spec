"""Current host risk authority and carried exception closure through real Store."""
from copy import deepcopy
from tests.skill_rls.final_support import FinalRlsCase, default_items, RlsService, read_vfy_candidate, snapshot
from rls_exceptions import TrustedRlsExceptions
from rls_common import utc_now
from rls_verifier import verify


class CurrentRlsExceptionTests(FinalRlsCase):
    def carried(self,two=False):
        self.root,self.chain,self.candidate=self.variant(waived_method=True)
        self.service=RlsService(self.root)
        _,rows=default_items(self.candidate)
        required = {self.chain["vfy"]+"#VFM-002", self.chain["design"]+"#VFO-001", self.candidate.exception_references[0]}
        self.assertTrue(required <= set(rows[0]["source_references"]))
        if two:
            second=deepcopy(rows[0]);second["id"]="RCF-002";rows.append(second)
        self.create(confirmations=rows)
        self.assertEqual("carried",self.state["exceptions"][0]["state"])

    def test_carried_method_target_or_exception_source_cannot_be_removed(self):
        self.carried()
        for ref in self.state["confirmations"][0]["source_references"]:
            changed=deepcopy(self.state);changed["confirmations"][0]["source_references"].remove(ref)
            self.code("RLS_CONFIRMATION_CONTRACT_INCOMPLETE",verify,changed)
        self.assertEqual(self.state,self.service.read(self.reference)[0])

    def test_carried_exception_resolves_only_with_all_target_results_and_evidence(self):
        self.carried();self.execute();self.confirm();self.freeze()
        row=self.state["exceptions"][0]
        self.assertEqual("resolved",row["state"])
        self.assertIn(self.reference+"#RCF-001",row["resolution_references"])
        self.assertTrue(set(self.state["confirmations"][0]["evidence_references"]) <= set(row["resolution_references"]))
        candidate=read_vfy_candidate(self.root,self.chain["vfy"])
        self.assertEqual("active",candidate.authority_exceptions[0]["state"])

    def test_rewaived_obligation_requires_current_host_risk_grant_and_human_confirmation(self):
        self.carried(two=True);self.execute();self.confirm()
        forged=deepcopy(self.state);forged["confirmations"][1].update(result="waived",exception_reference=self.candidate.exception_references[0])
        self.code("RLS_EXCEPTION_INVALID",verify,forged)
        risk=TrustedRlsExceptions(self.root).grant(self.state,["RCF-002"],approved=True,authorizer="fixture-risk-owner",
             reason="Explicit current fixture re-waiver",known_risk="Second observation is unavailable",
             compensating_control="Keep local Sandbox only",revisit_condition="next Revision",downstream_obligation="Repeat target confirmation")
        self.state,self.generation=self.service.waive(self.reference,self.target,risk)
        self.assertEqual("superseded",self.state["exceptions"][0]["state"])
        self.freeze()
        self.assertEqual("pass_with_exception",self.state["artifact_gate"])
        self.assertEqual("success",self.state["release_conclusion"])
        self.assertEqual("human",self.state["final_confirmation"]["mode"])
        self.assertEqual(self.state,self.service.read(self.reference)[0])

    def test_failure_before_effect_keeps_carried_exception_with_accurate_failed_gate(self):
        self.carried();self.finish(failure=True)
        self.assertEqual("failed",self.state["release_conclusion"])
        self.assertEqual("carried",self.state["exceptions"][0]["state"])
        self.assertEqual("pass_with_exception",self.state["artifact_gate"])
        self.assertFalse(self.state["target_effect"])

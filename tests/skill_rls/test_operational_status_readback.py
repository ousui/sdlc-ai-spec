"""The public RLS view survives persistence without changing signed members."""
from tests.skill_rls.final_support import FinalRlsCase


class RlsOperationalStatusReadbackTests(FinalRlsCase):
    def test_created_contract_stays_ready_for_execution(self):
        self.create()
        self.assertEqual("contract_ready", self.service.read(self.reference)[0]["status"])

    def test_successful_execution_returns_the_same_waiting_state_on_readback(self):
        self.create(); self.execute()
        self.assertEqual("waiting_confirmation", self.state["status"])
        self.assertEqual(self.state, self.service.read(self.reference)[0])
        self.confirm()
        self.assertEqual("waiting_confirmation", self.service.read(self.reference)[0]["status"])

    def test_failed_execution_does_not_regress_to_unexecuted_contract(self):
        self.create(); self.execute(behaviors={"RLI-001": "failure"})
        self.assertEqual("waiting_confirmation", self.state["status"])
        self.assertEqual(self.state, self.service.read(self.reference)[0])

    def test_frozen_state_restores_final_status_without_claiming_pending_is_ready(self):
        self.finish()
        state, _ = self.service.read(self.reference)
        self.assertEqual("ready", state["status"])
        self.assertEqual("frozen", state["artifact"]["revision_state"])
        self.assertEqual("success", state["release_conclusion"])

"""Real Store RLS lifecycle/status projection and precise return routes."""
from dataclasses import replace
from tests.skill_rls.final_support import FinalRlsCase, snapshot, ROOT
from packages.sdlc_artifact_store import ArtifactStore
from packages.sdlc_lifecycle import LifecycleQueryService
from packages.sdlc_runtime.control_inputs import ControlInputResolver
from rls_persistence import abandon_revision


class FinalRlsLifecycleTests(FinalRlsCase):
    def test_open_waits_and_status_interface_preserve_vfy_and_do_not_write(self):
        self.create();self.assertEqual("AUTHORIZE_RLS_EFFECT",self.projection()["next_action"])
        self.execute();self.assertEqual("CONFIRM_RLS_TARGET",self.projection()["next_action"])
        self.confirm();self.assertEqual("FINALIZE_RLS",self.projection()["next_action"])
        import importlib.util
        spec=importlib.util.spec_from_file_location("rls_status_boundary",ROOT/"skills/sdlc-status/scripts/runtime.py")
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        before=snapshot(self.root)
        result=module.run_status(["inspect","-p",str(self.root),"-r",self.chain["requirement"],"--output","json"])
        self.assertTrue(result["ok"]);self.assertIsNotNone(result["projection"]["vfy_projection"])
        self.assertEqual("FINALIZE_RLS",result["projection"]["rls_projection"]["next_action"])
        self.assertEqual(before,snapshot(self.root))

    def test_frozen_return_dsn_reads_real_control_owner(self):
        self.finish(failure=True,follow_up="return_dsn")
        self.assertEqual("RETURN_TO_DSN",self.projection()["next_action"])
        for ref in self.projection()["issue_references"]:
            self.assertEqual("return_dsn",ControlInputResolver(self.root).resolve_rls_issue(ArtifactStore.open_read_only(self.root),ref,"return_dsn").follow_up_disposition)

    def test_frozen_return_pln_reads_real_control_owner(self):
        self.finish(failure=True,follow_up="return_pln")
        self.assertEqual("RETURN_TO_PLN",self.projection()["next_action"])
        for ref in self.projection()["issue_references"]:
            ControlInputResolver(self.root).resolve_rls_issue(ArtifactStore.open_read_only(self.root),ref,"return_pln")

    def test_abandoned_materialized_and_failed_first_write_reservation(self):
        self.create();abandon_revision(self.root,self.reference,expected_generation=self.generation)
        query=LifecycleQueryService(self.root)
        self.assertEqual("CREATE_RLS_REVISION",query.inspect_rls(self.reference)["next_action"])
        store=ArtifactStore.open_read_write(self.root);allocation=store.allocate_artifact("RLS");control=store.allocate_revision(allocation.artifact_id)
        store.abandon_revision(allocation.artifact_id,control.revision,reason="injected first-write failure")
        before=snapshot(self.root)
        view=LifecycleQueryService(self.root).inspect_rls(allocation.artifact_id+"@1")
        self.assertEqual("abandoned",view["revision_state"]);self.assertEqual(before,snapshot(self.root))

    def test_frozen_projection_requires_valid_core_authority(self):
        self.finish();query=LifecycleQueryService(self.root);node=query.read_node(self.reference)
        with self.assertRaises(Exception): query._rls_state(replace(node,authority_state="invalid"))

    def test_retry_replaces_one_revision_and_new_target_requires_selection(self):
        self.finish();self.service.revise(self.reference,self.chain["vfy"],self.target,retry=True)
        self.assertEqual(2,int(self.projection()["artifact_reference"].split("@")[1]))
        from rls_target import SandboxReleaseTarget
        from pathlib import Path
        target=SandboxReleaseTarget(Path(self.target_temp.name)/"second","sandbox-b")
        self.service.create(self.chain["vfy"],target,release_reference="2.0.0")
        view=self.projection();self.assertEqual("SELECT_RLS_TARGET",view["next_action"]);self.assertEqual(2,len(view["targets"]))

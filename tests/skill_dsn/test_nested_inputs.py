"""Regression for nested DSN input shapes and invocation-owned write recovery.

The small domain fixture isolates failures; installed CLI tests separately use
real CTX/REQ producers and the shipped Authority verifier, without PassingVerifier.
"""
from copy import deepcopy
from dataclasses import asdict
from unittest.mock import patch

from . import support_patch  # noqa: F401
from .support import DsnRuntimeFixture
from dsn_common import DsnRuntimeError
from packages.sdlc_artifact_store import ArtifactStore, InvalidStateError, ConflictError
from packages.sdlc_artifact_store.catalog import ArtifactCatalog


class DsnNestedInputTests(DsnRuntimeFixture):
    def state(self):
        catalog = self.catalog()
        return {item.artifact_id: [asdict(row) for row in catalog.list_revisions(item.artifact_id)]
                for item in catalog.list_artifacts()}

    def evidence(self):
        return {"reference": self.req_item, "supports": ["CHG-001"],
                "purpose": "说明边界依据；Compare the observed behaviour, without a fixed phrase."}

    def test_nested_domain_inputs_fail_before_allocation_and_revise(self):
        frozen = self.execute(self.invocation())["artifact"]["reference"]
        cases = []
        for field in ("constraints_impacts", "vfy_points", "evidence_references"):
            for value in ("wrong", {}, True, 7):
                cases.append((field, value, field))
            cases.append((field, ["wrong"], field + "[0]"))
        for name in ("reference", "supports", "purpose"):
            row = self.evidence(); del row[name]
            cases.append(("evidence_references", [row], "evidence_references[0]." + name))
        for name, value in (("reference", ""), ("reference", None), ("reference", {}),
                            ("supports", []), ("supports", {}), ("supports", [""]),
                            ("supports", ["CHG-001", 1]), ("purpose", []), ("purpose", " ")):
            row = self.evidence(); row[name] = value
            suffix = ".supports[0]" if name == "supports" and value == [""] else (
                ".supports[1]" if name == "supports" and value == ["CHG-001", 1] else "." + name)
            cases.append(("evidence_references", [row], "evidence_references[0]" + suffix))
        cases.append(("evidence_references", [self.evidence(), "wrong"], "evidence_references[1]"))
        point = self.complete_design(require_workflow=True)["domains"]["DOM-110"]["vfy_points"][0]
        for name, value in (("references", []), ("references", [1]),
                            ("verification_object", {}), ("observable_result", None),
                            ("expected_evidence", "")):
            row = deepcopy(point); row[name] = value
            suffix = name + "[0]" if name == "references" and value == [1] else name
            cases.append(("vfy_points", [row], "vfy_points[0]." + suffix))
        cases.extend((field, value, field) for field, value in (("disposition", []), ("completion", {})))
        for field, value, suffix in cases:
            for operation, dry_run in (("create", True), ("create", False), ("revise", False)):
                with self.subTest(field=field, value=value, operation=operation, dry_run=dry_run):
                    design = self.complete_design(require_workflow=True); design["domains"]["DOM-110"][field] = value
                    invocation = self.invocation(design=design, final=False, operation=operation,
                                                 reference=frozen if operation == "revise" else None)
                    invocation["options"]["dry_run"] = dry_run
                    before = self.state()
                    with patch.object(ArtifactStore, "allocate_artifact", side_effect=AssertionError("late validation")), \
                         patch.object(ArtifactStore, "allocate_revision", side_effect=AssertionError("late validation")):
                        result = self.execute(invocation)
                    self.assertFalse(result["ok"], result)
                    self.assertIsNone(result["artifact"], result)
                    details = result["errors"][0]["details"]
                    self.assertEqual("inputs.design.domains.DOM-110." + suffix, details["path"])
                    self.assertTrue(details["expected"] and details["actual"] and details["hint"])
                    self.assertFalse(result["next_action"]["requires_user"])
                    self.assertEqual(before, self.state())

    def test_optional_empty_values_and_free_text_still_build(self):
        for empty in (None, []):
            with self.subTest(empty=empty):
                design = self.complete_design(require_workflow=True)
                domain = design["domains"]["DOM-110"]
                domain.update(completion="in_progress", constraints_impacts=empty,
                              evidence_references=empty, vfy_points=empty)
                result = self.execute(self.invocation(design=design, final=False))
                self.assertEqual([], result["errors"], result)
                self.assertEqual("waiting_input", result["artifact"]["artifact_status"])
        design = self.complete_design(require_workflow=True); domain = design["domains"]["DOM-110"]
        domain.pop("constraints_impacts", None); domain.pop("evidence_references", None)
        self.assertTrue(self.execute(self.invocation(design=design))["ok"])
        for purpose in ("用于比较当前筛选结果与导出边界", "Check behaviour; a typo is not an enum: desgin", "自由説明 ABC abc"):
            design = self.complete_design(require_workflow=True); domain = design["domains"]["DOM-110"]
            domain["evidence_references"] = [dict(self.evidence(), purpose=purpose, extension={"custom": True})]
            domain["constraints_impacts"] = [{"content": "自然语言描述，不强制关键词", "extension": True}]
            result = self.execute(self.invocation(design=design))
            self.assertTrue(result["ok"], result)
            member = next(item for item in self.store.read_revision(result["artifact"]["id"], 1).payload.members
                          if item.member_id == "DOM-110")
            self.assertIn(purpose, member.raw_bytes.decode())

    def test_related_analyzer_renderer_structures_reject_before_write(self):
        mutations = (
            ("changes", "affected_domains", ["DOM-110", {}], "inputs.design.changes[0].affected_domains[1]"),
            ("changes", "affected_domains", "DOM-110", "inputs.design.changes[0].affected_domains"),
            ("changes", "baseline_references", [123], "inputs.design.changes[0].baseline_references[0]"),
            ("traceability", "decision_references", True, "inputs.design.traceability[0].decision_references"),
            ("evidence", "supports_references", [None], "inputs.design.evidence[0].supports_references[0]"),
            ("lifecycle_applicability", "disposition", [], "inputs.design.lifecycle_applicability[0].disposition"),
        )
        for collection, field, value, path in mutations:
            with self.subTest(path=path):
                design = self.complete_design(require_workflow=True); design[collection][0][field] = value
                before = self.state()
                result = self.execute(self.invocation(design=design, final=False))
                self.assertEqual(path, result["errors"][0]["details"]["path"])
                self.assertEqual(before, self.state())
        for confirmation, path in ((["approved"], "inputs.final_confirmation"),
                                   ({"mode": []}, "inputs.final_confirmation.mode"),
                                   ({"mode": "human", "subject_digest": {}}, "inputs.final_confirmation.subject_digest")):
            request = self.invocation(final=False); request["inputs"]["final_confirmation"] = confirmation
            before = self.state(); result = self.execute(request)
            self.assertEqual(path, result["errors"][0]["details"]["path"])
            self.assertEqual(before, self.state())

    def test_existing_gate_still_rejects_invented_domain_and_empty_required_vfy(self):
        design = self.complete_design(require_workflow=True); design["changes"][0]["affected_domains"] = ["DOM-999"]
        result = self.execute(self.invocation(design=design, final=False))
        self.assertEqual("fail", result["gate"]["result"])
        self.assertIn("DSN-G-002", result["gate"]["failed_checks"])
        design = self.complete_design(require_workflow=True); design["domains"]["DOM-110"]["vfy_points"] = []
        before = self.state(); result = self.execute(self.invocation(design=design, final=False))
        self.assertFalse(result["ok"]); self.assertEqual(before, self.state())

    def test_expected_build_failure_cleans_only_owned_revision(self):
        other = []
        def fail(invocation, store, control, upstream):
            allocation = store.allocate_artifact("DSN")
            other.append(store.allocate_revision(allocation.artifact_id))
            raise DsnRuntimeError("controlled builder rejection")
        with patch.object(self.handler, "_write", side_effect=fail):
            result = self.execute(self.invocation())
        self.assertEqual("abandoned", result["artifact"]["revision_state"], result)
        self.assertTrue(result["errors"][0]["details"]["cleanup"]["confirmed_abandoned"])
        self.assertEqual("open", self.catalog().list_revisions(other[0].artifact_id)[0].state)
        self.assertTrue(self.execute(self.invocation())["ok"])

    def test_unknown_builder_defect_is_not_relabelled_as_input_error(self):
        before = self.state()
        with patch.object(self.handler.builder, "build", side_effect=RuntimeError("injected builder defect")):
            result = self.execute(self.invocation())
        self.assertEqual("DSN_INTERNAL_ERROR", result["errors"][0]["code"])
        self.assertEqual("RuntimeError", result["errors"][0]["details"]["exception_type"])
        self.assertEqual("abandoned", result["artifact"]["revision_state"])
        self.assertFalse(result["errors"][0]["details"]["cleanup"]["materialized"])
        self.assertEqual(before, {key: value for key, value in self.state().items() if key in before})

    def test_write_or_freeze_failure_state_is_read_back(self):
        original_write = ArtifactStore.write_open_revision
        original_freeze = ArtifactStore.freeze_revision
        for where in ("before_write", "after_write", "before_freeze", "after_freeze"):
            with self.subTest(where=where):
                def write(store, *args, **kwargs):
                    if where == "before_write": raise RuntimeError(where)
                    value = original_write(store, *args, **kwargs)
                    if where == "after_write": raise RuntimeError(where)
                    return value
                def freeze(store, *args, **kwargs):
                    if where == "before_freeze": raise RuntimeError(where)
                    value = original_freeze(store, *args, **kwargs)
                    if where == "after_freeze": raise RuntimeError(where)
                    return value
                invocation = self.invocation()
                with patch.object(ArtifactStore, "write_open_revision", write), \
                     patch.object(ArtifactStore, "freeze_revision", freeze):
                    result = self.execute(invocation)
                state = "frozen" if where == "after_freeze" else "abandoned"
                self.assertFalse(result["ok"])
                self.assertEqual(state, result["artifact"]["revision_state"])
                actual = self.catalog().list_revisions(result["artifact"]["id"])[0]
                self.assertEqual(state, actual.state)
                self.assertEqual(where != "before_write", actual.materialized)
                self.assertEqual(state == "abandoned", result["errors"][0]["details"]["cleanup"]["confirmed_abandoned"])

    def test_cleanup_failure_and_unknown_readback_never_claim_success(self):
        for read_failure in (False, True):
            with self.subTest(read_failure=read_failure):
                invocation = self.invocation()
                with patch.object(self.handler, "_write", side_effect=RuntimeError("original defect")), \
                     patch.object(ArtifactStore, "abandon_revision", side_effect=InvalidStateError("cleanup unavailable")):
                    if read_failure:
                        with patch.object(ArtifactCatalog, "list_revisions", side_effect=InvalidStateError("read unavailable")):
                            result = self.execute(invocation)
                    else:
                        result = self.execute(invocation)
                self.assertEqual("original defect", result["errors"][0]["message"])
                self.assertEqual("DSN_INTERNAL_ERROR", result["errors"][0]["code"])
                self.assertIn("DSN_CLEANUP_FAILED", [item["code"] for item in result["errors"]])
                self.assertEqual("unknown" if read_failure else "open", result["artifact"]["revision_state"])
                self.assertFalse(result["errors"][0]["details"]["cleanup"]["confirmed_abandoned"])
                self.assertEqual("open", self.catalog().list_revisions(result["artifact"]["id"])[0].state)
                self.assertTrue(self.execute(self.invocation())["ok"])

    def test_frozen_revise_failure_preserves_formal_record_and_retry(self):
        original = self.execute(self.invocation())["artifact"]
        before = self.store.read_revision(original["id"], 1)
        design = self.complete_design(require_workflow=True); design["summary"] += " 第二次候选设计"
        invocation = self.invocation(design=design, operation="revise", reference=original["reference"])
        with patch.object(self.handler, "_write", side_effect=RuntimeError("post allocation failure")):
            result = self.execute(invocation)
        self.assertEqual(2, result["artifact"]["revision"])
        self.assertEqual("abandoned", result["artifact"]["revision_state"])
        self.assertEqual(before, self.store.read_revision(original["id"], 1))
        retry = self.execute(invocation)
        self.assertTrue(retry["ok"], retry)
        self.assertEqual(3, retry["artifact"]["revision"])

    def test_open_revise_failure_does_not_abandon_preexisting_revision(self):
        original = self.execute(self.invocation(final=False))["artifact"]
        before = self.store.read_revision(original["id"], 1)
        invocation = self.invocation(operation="revise", reference=f"{original['id']}@1")
        with patch.object(self.handler, "_write", side_effect=RuntimeError("write not reached")):
            result = self.execute(invocation)
        self.assertEqual("open", result["artifact"]["revision_state"])
        self.assertFalse(result["errors"][0]["details"]["cleanup"]["attempted"])
        self.assertEqual(before, self.store.read_revision(original["id"], 1))
        self.assertTrue(self.execute(invocation)["ok"])

    def test_conflicting_write_preserves_observed_revision(self):
        def conflicting(invocation, store, control, upstream):
            build = self.handler.builder.build(artifact_id=control.artifact_id, revision=control.revision,
                                                upstream=upstream, design=invocation["inputs"]["design"],
                                                final_confirmation=None)
            store.write_open_revision(self.handler._payload(control, build), expected_generation=control.generation)
            raise ConflictError("another writer advanced the revision")
        with patch.object(self.handler, "_write", side_effect=conflicting):
            result = self.execute(self.invocation())
        self.assertEqual("blocked", result["status"])
        self.assertEqual("open", result["artifact"]["revision_state"])
        self.assertFalse(result["errors"][0]["details"]["cleanup"]["attempted"])
        self.assertTrue(self.store.read_revision(result["artifact"]["id"], 1).control.materialized)

    def test_noop_cleanup_is_not_reported_as_confirmed(self):
        with patch.object(self.handler, "_write", side_effect=RuntimeError("original defect")), \
             patch.object(ArtifactStore, "abandon_revision", return_value=None):
            result = self.execute(self.invocation())
        self.assertEqual("open", result["artifact"]["revision_state"])
        self.assertIn("DSN_CLEANUP_NOT_CONFIRMED", [item["code"] for item in result["errors"]])
        self.assertEqual("original defect", result["errors"][0]["message"])

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_PATH = ROOT / "skills/sdlc-000-ctx/scripts/runtime.py"
SPEC = importlib.util.spec_from_file_location("sdlc_000_ctx_runtime", RUNTIME_PATH)
assert SPEC is not None and SPEC.loader is not None
runtime = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runtime
SPEC.loader.exec_module(runtime)

from packages.sdlc_runtime import ContractSource, build_source_lock, registry_sources
from sdlc_artifact_store.catalog import ArtifactCatalog

FIXED_TIME = datetime(2026, 8, 30, 10, 11, 12, tzinfo=timezone.utc)


def fact(value, basis, *references):
    return {
        "value": value,
        "basis": basis,
        "basis_references": list(references),
    }


def none_section():
    return {"none": {"basis": "confirmed", "basis_references": ["EVD-001"]}}


class CtxRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temporary.name) / "project"
        self.project_root.mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def context(self):
        return {
            "summary": "A deterministic project context fixture.",
            "project_identity": {
                "project_name": fact("Example", "confirmed", "EVD-001"),
                "purpose": fact("Validate CTX Runtime", "confirmed", "EVD-001"),
                "boundary": fact("Example Project Boundary", "confirmed", "EVD-001"),
                "primary_resource_reference": fact("RSC-001", "observed", "EVD-002"),
                "authoritative_references": fact("None", "confirmed", "EVD-001"),
            },
            "resources": [
                {
                    "id": "RSC-001",
                    "type": "repository",
                    "name": "example",
                    "role": "primary",
                    "locator": "vcs:example@0123456789abcdef",
                    "baseline_reference": "vcs:example@0123456789abcdef",
                    "basis": "observed",
                    "basis_references": ["EVD-002"],
                }
            ],
            "technologies": none_section(),
            "engineering_entries": none_section(),
            "components": none_section(),
            "rules": none_section(),
            "environments": none_section(),
            "constraints": none_section(),
            "exceptions": [],
        }

    def evidence(self):
        return [
                {
                    "id": "EVD-001",
                    "type": "confirmation",
                    "supports_references": ["CTX-G-002", "CTX-G-004"],
                    "source_or_producer": "project-owner",
                    "reference": "authority/project-context.txt@sha256:" + "a" * 64,
                    "integrity_or_digest": "sha256:" + "a" * 64,
                    "produced_at": "2026-08-30T10:00:00+00:00",
                    "sensitivity_or_access": "project-authorized",
                },
                {
                    "id": "EVD-002",
                    "type": "observation",
                    "supports_references": ["CTX-G-003"],
                    "source_or_producer": "fixture",
                    "reference": "vcs:example@0123456789abcdef",
                    "integrity_or_digest": "sha256:" + "b" * 64,
                    "produced_at": "2026-08-30T10:00:00+00:00",
                    "sensitivity_or_access": "project-authorized",
                },
            ]

    def invocation(self, operation="create", *, context=None, reference=None, dry_run=False):
        value = {
            "contract": "sdlc-ai-spec/runtime-invocation/v1",
            "operation": operation,
            "project_root": str(self.project_root),
            "artifact_reference": reference,
            "inputs": {
                "context": context if context is not None else self.context(),
                "evidence": self.evidence(),
                "supporting_members": [],
            },
            "confirmations": [],
            "options": {"dry_run": dry_run},
        }
        if operation == "create":
            value["confirmations"] = [
                {"type": "write", "approved": True},
                {
                    "type": "project_boundary",
                    "value": "Example Project Boundary",
                    "authority_reference": "EVD-001",
                },
            ]
        return value

    def invoke(self, value):
        return runtime.invoke(value, clock=lambda: FIXED_TIME)

    def refresh(self, base_revision, *, reason="confirmed context change", changes="None"):
        return {
            "base_revision": base_revision,
            "observed_at": "2026-08-30T10:11:12+00:00",
            "observation_baseline": "vcs:example@0123456789abcdef",
            "refresh_reason": reason,
            "effective_change_references": changes,
            "evidence_references": ["EVD-001", "EVD-002"],
        }

    def write_authority(self, reference, bindings, *, name="final-confirmation.txt"):
        authority_dir = self.project_root / "authority"
        authority_dir.mkdir(exist_ok=True)
        authority_text = "\n".join(
            [
                f"artifact: {reference}",
                f"control: {bindings['control_input_digest']}",
                f"contracts: {bindings['evaluation_contract_set']}",
                f"checks: {bindings['check_set_result_digest']}",
                "decision: approved",
            ]
        ) + "\n"
        authority_path = authority_dir / name
        authority_path.write_text(authority_text, encoding="utf-8")
        return f"authority/{name}@sha256:" + hashlib.sha256(authority_text.encode()).hexdigest()

    def finalize_open(self, reference, context, refresh):
        dry = self.invocation("revise", context=context, reference=reference, dry_run=True)
        dry["inputs"]["refresh"] = refresh
        preview = self.invoke(dry)
        bindings = next(
            item for item in preview["warnings"] if item["code"] == "FINAL_CONFIRMATION_BINDINGS"
        )["details"]
        revise = self.invocation("revise", context=context, reference=reference)
        revise["inputs"]["refresh"] = refresh
        revise["confirmations"] = [
            {"type": "write", "approved": True},
            {
                "type": "final_confirmation",
                "result": "approved",
                "mode": "human",
                "confirmer": "project-owner",
                "role": "Project Maintainer",
                "authority_reference": self.write_authority(
                    reference, bindings, name=f"final-confirmation-{reference.rsplit('@', 1)[1]}.txt"
                ),
                "accepted_exception_references": [],
                "confirmed_at": "2026-08-30T10:11:12+00:00",
                **bindings,
            },
        ]
        return self.invoke(revise)

    def create_and_freeze(self):
        created = self.invoke(self.invocation())
        artifact_id = created["artifact"]["id"]
        reference = f"{artifact_id}@1"
        refresh = {
            "base_revision": None,
            "observed_at": "2026-08-30T10:11:12+00:00",
            "observation_baseline": "vcs:example@0123456789abcdef",
            "refresh_reason": "complete final confirmation",
            "effective_change_references": "None",
            "evidence_references": ["EVD-001", "EVD-002"],
        }
        dry = self.invocation("revise", reference=reference, dry_run=True)
        dry["inputs"]["refresh"] = refresh
        preview = self.invoke(dry)
        binding_warning = next(item for item in preview["warnings"] if item["code"] == "FINAL_CONFIRMATION_BINDINGS")
        bindings = binding_warning["details"]
        authority_dir = self.project_root / "authority"
        authority_dir.mkdir(exist_ok=True)
        authority_text = "\n".join(
            [
                f"artifact: {reference}",
                f"control: {bindings['control_input_digest']}",
                f"contracts: {bindings['evaluation_contract_set']}",
                f"checks: {bindings['check_set_result_digest']}",
                "decision: approved",
            ]
        ) + "\n"
        authority_path = authority_dir / "final-confirmation.txt"
        authority_path.write_text(authority_text, encoding="utf-8")
        authority_reference = "authority/final-confirmation.txt@sha256:" + hashlib.sha256(authority_text.encode()).hexdigest()
        revise = self.invocation("revise", reference=reference)
        revise["inputs"]["refresh"] = refresh
        revise["confirmations"] = [
            {"type": "write", "approved": True},
            {
                "type": "final_confirmation",
                "result": "approved",
                "mode": "human",
                "confirmer": "project-owner",
                "role": "Project Maintainer",
                "authority_reference": authority_reference,
                "accepted_exception_references": [],
                "confirmed_at": "2026-08-30T10:11:12+00:00",
                **bindings,
            },
        ]
        completed = self.invoke(revise)
        self.assertTrue(completed["ok"], completed)
        return reference, completed

    def test_boundary_key_normalizes_nfc_line_endings_and_outer_whitespace(self):
        first = runtime.boundary_key("  Cafe\u0301\r\nBoundary  ")
        second = runtime.boundary_key("Café\nBoundary")
        self.assertEqual(first, second)
        self.assertRegex(first, r"^sha256:[0-9a-f]{64}$")

    def test_unconfirmed_boundary_does_not_create_store(self):
        value = self.invocation()
        value["confirmations"] = [{"type": "write", "approved": True}]
        result = self.invoke(value)
        self.assertEqual(result["errors"][0]["code"], "PROJECT_BOUNDARY_CONFIRMATION_REQUIRED")
        self.assertFalse((self.project_root / ".sdlc").exists())

    def test_create_materializes_waiting_input_and_duplicate_is_blocked(self):
        first = self.invoke(self.invocation())
        self.assertEqual(first["status"], "action_required")
        self.assertEqual(first["artifact"]["revision_state"], "open")
        self.assertEqual(first["artifact"]["artifact_status"], "waiting_input")
        self.assertIsNone(first["artifact"]["reference"])
        self.assertEqual(first["open_items"][-1]["blocked_references"], "CORE-G-009")

        second = self.invoke(self.invocation())
        self.assertEqual(second["status"], "blocked")
        self.assertEqual(second["errors"][0]["code"], "CTX_LINEAGE_EXISTS")
        self.assertEqual(second["artifact"]["id"], first["artifact"]["id"])

    def test_concurrent_first_create_converges_on_one_ctx_id(self):
        for attempt in range(200):
            with self.subTest(attempt=attempt):
                project_root = Path(self.temporary.name) / f"race-{attempt}"
                project_root.mkdir()
                invocation = self.invocation()
                invocation["project_root"] = str(project_root)
                barrier = threading.Barrier(2)

                def create():
                    barrier.wait()
                    return self.invoke(deepcopy(invocation))

                with ThreadPoolExecutor(max_workers=2) as executor:
                    results = list(executor.map(lambda _: create(), range(2)))

                artifact_ids = {
                    (result.get("artifact") or {}).get("id") for result in results
                }
                self.assertEqual(len(artifact_ids), 1, results)
                self.assertNotIn(None, artifact_ids, results)
                self.assertEqual(
                    sorted(result["status"] for result in results),
                    ["action_required", "blocked"],
                    results,
                )
                reader = runtime.ArtifactStore.open_read_only(project_root)
                artifacts = ArtifactCatalog(reader).list_artifacts("CTX")
                binding = runtime.ContextLineageRegistry(reader).find(
                    runtime.boundary_key("Example Project Boundary")
                )
                self.assertEqual(len(artifacts), 1)
                self.assertIsNotNone(binding)
                self.assertEqual(binding.artifact_id, next(iter(artifact_ids)))

    def test_corrupt_schema_is_not_hidden_by_initialize_recovery(self):
        runtime_dir = self.project_root / ".sdlc"
        runtime_dir.mkdir()
        (runtime_dir / ".gitignore").write_bytes(b"*\n")
        (runtime_dir / "store.sqlite3").write_bytes(b"")

        result = self.invoke(self.invocation())

        self.assertFalse(result["ok"])
        self.assertEqual(result["errors"][0]["code"], "SCHEMA_ERROR")
        self.assertIsNone(result["artifact"])

    def test_concurrent_cli_first_create_converges_across_processes(self):
        for attempt in range(10):
            with self.subTest(attempt=attempt):
                project_root = Path(self.temporary.name) / f"process-race-{attempt}"
                project_root.mkdir()
                invocation = self.invocation()
                invocation["project_root"] = str(project_root)
                raw_invocation = json.dumps(invocation)

                def create():
                    process = subprocess.run(
                        [sys.executable, str(RUNTIME_PATH)],
                        input=raw_invocation,
                        text=True,
                        cwd=ROOT,
                        capture_output=True,
                        check=False,
                        env={"PYTHONDONTWRITEBYTECODE": "1"},
                    )
                    self.assertNotIn("Traceback", process.stderr)
                    return json.loads(process.stdout)

                with ThreadPoolExecutor(max_workers=2) as executor:
                    results = list(executor.map(lambda _: create(), range(2)))

                artifact_ids = {
                    (result.get("artifact") or {}).get("id") for result in results
                }
                self.assertEqual(len(artifact_ids), 1, results)
                self.assertNotIn(None, artifact_ids, results)
                self.assertEqual(
                    sorted(result["status"] for result in results),
                    ["action_required", "blocked"],
                    results,
                )
                reader = runtime.ArtifactStore.open_read_only(project_root)
                self.assertEqual(
                    len(ArtifactCatalog(reader).list_artifacts("CTX")), 1
                )
                binding = runtime.ContextLineageRegistry(reader).find(
                    runtime.boundary_key("Example Project Boundary")
                )
                self.assertIsNotNone(binding)
                self.assertEqual(binding.artifact_id, next(iter(artifact_ids)))

    def test_corrupt_store_is_not_hidden_by_lock_recovery(self):
        runtime_dir = self.project_root / ".sdlc"
        runtime_dir.mkdir()
        (runtime_dir / ".gitignore").write_bytes(b"*\n")
        store_path = runtime_dir / "store.sqlite3"
        corrupt_bytes = b"not-a-sqlite-database"
        store_path.write_bytes(corrupt_bytes)

        result = self.invoke(self.invocation())

        self.assertFalse(result["ok"])
        self.assertEqual(result["errors"][0]["code"], "DATABASE_ERROR")
        self.assertIsNone(result["artifact"])
        self.assertEqual(store_path.read_bytes(), corrupt_bytes)

    def test_open_revise_binds_confirmation_freezes_and_checks_read_only(self):
        reference, completed = self.create_and_freeze()
        self.assertEqual(completed["artifact"]["revision_state"], "frozen")
        self.assertEqual(completed["artifact"]["artifact_status"], "ready")
        self.assertEqual(completed["artifact"]["reference"], reference)

        before = self.snapshot()
        checked = self.invoke(self.invocation("check", reference=reference))
        after = self.snapshot()
        self.assertTrue(checked["ok"], checked)
        self.assertEqual(checked["artifact"]["reference"], reference)
        self.assertEqual(before, after)

    def test_frozen_no_change_keeps_revision_and_effective_change_allocates_next(self):
        reference, _ = self.create_and_freeze()
        artifact_id = reference.split("@", 1)[0]
        no_change = self.invocation("revise", reference=reference)
        no_change["inputs"]["refresh"] = {
            "base_revision": 1,
            "observed_at": "2026-08-30T10:11:12+00:00",
            "observation_baseline": "vcs:example@0123456789abcdef",
            "refresh_reason": "periodic review",
            "effective_change_references": "None",
            "evidence_references": ["EVD-001", "EVD-002"],
        }
        no_change["confirmations"] = [{"type": "write", "approved": True}]
        unchanged = self.invoke(no_change)
        self.assertTrue(unchanged["ok"], unchanged)
        self.assertEqual(unchanged["artifact"]["reference"], reference)
        self.assertEqual(unchanged["warnings"][0]["code"], "NO_EFFECTIVE_CHANGE")

        before = runtime.ArtifactStore.open_read_only(self.project_root).read_revision(artifact_id, 1).payload.primary_blob
        changed_context = deepcopy(self.context())
        changed_context["project_identity"]["purpose"] = fact("Validate changed CTX Runtime", "confirmed", "EVD-001")
        changed = self.invocation("revise", context=changed_context, reference=reference)
        changed["inputs"]["refresh"] = {
            **no_change["inputs"]["refresh"],
            "refresh_reason": "confirmed purpose change",
            "effective_change_references": [f"{reference}#EVD-001"],
        }
        changed["confirmations"] = [{"type": "write", "approved": True}]
        revised = self.invoke(changed)
        self.assertEqual(revised["status"], "action_required", revised)
        self.assertEqual(revised["artifact"]["revision"], 2)
        self.assertEqual(revised["artifact"]["revision_state"], "open")
        self.assertIsNone(revised["artifact"]["reference"])
        after = runtime.ArtifactStore.open_read_only(self.project_root).read_revision(artifact_id, 1).payload.primary_blob
        self.assertEqual(before, after)

    def test_check_missing_store_is_strictly_read_only(self):
        before = self.snapshot()
        result = self.invoke(self.invocation("check", reference="CTX-20260830101112-01@1"))
        self.assertEqual(result["errors"][0]["code"], "STORE_NOT_FOUND")
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.project_root / ".sdlc").exists())

    def test_dry_run_creates_no_persistent_state(self):
        result = self.invoke(self.invocation(dry_run=True))
        self.assertTrue(result["ok"])
        self.assertIsNone(result["artifact"])
        self.assertFalse((self.project_root / ".sdlc").exists())

    def test_runtime_source_lock_is_exact_and_runtime_has_no_design_source_dependency(self):
        runtime._verify_bundled_source_lock()
        lock = json.loads((ROOT / "skills/sdlc-000-ctx/references/source-lock.json").read_text())
        self.assertEqual(len(lock["contracts"]), 8)
        sources = registry_sources(ROOT, ROOT / "skills/_shared/contracts/registry.json") + (
            ContractSource("sdlc-ai-spec/build-source/artifact-store/v1.1", "1.1", "docs/v1.1/artifact-store-spec.md"),
            ContractSource("sdlc-ai-spec/build-source/core/v1.1", "1.1", "docs/v1.1/core-spec.md"),
            ContractSource("sdlc-ai-spec/build-source/ctx/v1.1", "1.1", "docs/v1.1/000-ctx-spec.md"),
        )
        self.assertEqual(lock, build_source_lock(ROOT, sources))
        text = RUNTIME_PATH.read_text(encoding="utf-8")
        self.assertNotIn("docs" + "/v1.1/", text)

    def test_missing_foundation_returns_structured_result_without_traceback(self):
        scenarios = {
            "missing-artifact-store": "sdlc_runtime",
            "missing-runtime": "sdlc_artifact_store",
        }
        for name, available_package in scenarios.items():
            with self.subTest(name=name):
                plugin_root = Path(self.temporary.name) / name
                shutil.copytree(ROOT / "skills", plugin_root / "skills")
                shutil.copytree(
                    ROOT / "packages" / available_package,
                    plugin_root / "packages" / available_package,
                )
                runtime_path = plugin_root / "skills/sdlc-000-ctx/scripts/runtime.py"
                process = subprocess.run(
                    [sys.executable, str(runtime_path)],
                    input=json.dumps(self.invocation("check", reference="CTX-20260830101112-01@1")),
                    text=True,
                    cwd=plugin_root,
                    capture_output=True,
                    check=False,
                    env={"PYTHONDONTWRITEBYTECODE": "1"},
                )
                result = json.loads(process.stdout)
                self.assertEqual(process.returncode, 1)
                self.assertNotIn("Traceback", process.stderr)
                self.assertEqual(result["contract"], "sdlc-ai-spec/runtime-result/v1")
                self.assertEqual(result["errors"][0]["code"], "FOUNDATION_RUNTIME_UNAVAILABLE")
                self.assertEqual(result["next_action"]["code"], "RESTORE_VERIFIED_PLUGIN_RUNTIME")
                self.assertEqual(runtime.validate_result(result), result)

    def test_domain_validator_rejects_tampered_basis_even_with_updated_blob_digest(self):
        created = self.invoke(self.invocation())
        artifact_id = created["artifact"]["id"]
        stored = runtime.ArtifactStore.open_read_only(self.project_root).read_revision(artifact_id, 1)
        tampered_primary = stored.payload.primary_blob.replace(
            b"| observed | EVD-002 |", b"| inferred | EVD-002 |", 1
        )
        tampered_payload = replace(
            stored.payload,
            primary_blob=tampered_primary,
            primary_sha256=runtime.compute_sha256(tampered_primary),
        )
        tampered = replace(stored, payload=tampered_payload)
        failures, gate_result, _ = runtime.validate_stored_revision(tampered)
        self.assertEqual(gate_result, "fail")
        self.assertIn("CTX-G-002", failures)

        text = stored.payload.primary_blob.decode("utf-8")
        evidence_start = text.index("## 证据 Evidence\n")
        refresh_start = text.index("## 刷新摘要 Refresh Summary\n")
        none_evidence = "\n".join(
            [
                "## 证据 Evidence",
                "",
                "| ID | Type | Supports References | Source or Producer | Reference | Integrity or Digest | Produced At | Sensitivity or Access | Empty Reason |",
                "|---|---|---|---|---|---|---|---|---|",
                "| None | none | N/A | N/A | N/A | N/A | N/A | N/A | No independent Evidence |",
                "",
                "",
            ]
        )
        no_evidence_primary = (
            text[:evidence_start] + none_evidence + text[refresh_start:]
        ).encode("utf-8")
        no_evidence = replace(
            stored,
            payload=replace(
                stored.payload,
                primary_blob=no_evidence_primary,
                primary_sha256=runtime.compute_sha256(no_evidence_primary),
            ),
        )
        failures, gate_result, _ = runtime.validate_stored_revision(no_evidence)
        self.assertEqual(gate_result, "fail")
        self.assertIn("CTX-G-005", failures)

    def test_domain_validator_rejects_missing_primary_invalid_enums_and_exception_contract(self):
        cases = []

        no_primary = self.context()
        no_primary["resources"] = none_section()
        cases.append(("no-primary-resource", no_primary))

        invalid_enum = self.context()
        invalid_enum["resources"][0]["role"] = "leader"
        cases.append(("invalid-resource-role", invalid_enum))

        invalid_exception = self.context()
        invalid_exception["exceptions"] = [
            {
                "id": "EX-001",
                "state": "active",
                "origin_exception_reference": "CTX-example@1#EX-000",
                "scope_or_skipped_obligation": "Known constraint",
                "reason": "Fixture risk",
                "known_risk": "Known impact",
                "compensating_control": "Review before use",
                "approver_role_time": "Maintainer at 2026-08-30T10:00:00+00:00",
                "revisit_condition": "Next revision",
                "downstream_obligation": "Carry the risk",
                "resolution_or_superseding_references": "N/A",
            }
        ]
        cases.append(("invalid-active-exception-origin", invalid_exception))

        for name, context in cases:
            with self.subTest(name=name):
                result = self.invoke(self.invocation(context=context))
                self.assertFalse(result["ok"], result)
                self.assertEqual(result["errors"][0]["code"], "CTX_CONTENT_INVALID")
                self.assertFalse((self.project_root / ".sdlc").exists())

    def test_approved_peer_input_shape_consumes_evidence_and_supporting_members(self):
        value = self.invocation()
        value["inputs"]["supporting_members"] = [
            {
                "member_id": "SUP-001",
                "canonical_name": "evidence/context.txt",
                "media_type": "text/plain",
                "purpose": "Stable supporting evidence",
                "content": "fixture\n",
            }
        ]
        created = self.invoke(value)
        self.assertEqual(created["status"], "action_required", created)
        stored = runtime.ArtifactStore.open_read_only(self.project_root).read_revision(
            created["artifact"]["id"], 1
        )
        self.assertEqual([member.member_id for member in stored.payload.members], ["SUP-001"])

        nested = self.invocation("revise", reference=f"{created['artifact']['id']}@1")
        nested["inputs"]["refresh"] = self.refresh(None)
        nested["inputs"]["context"]["supporting_members"] = nested["inputs"].pop("supporting_members")
        nested["confirmations"] = [{"type": "write", "approved": True}]
        rejected = self.invoke(nested)
        self.assertEqual(rejected["errors"][0]["code"], "CTX_CONTENT_INVALID")

        nested_evidence = self.invocation("revise", reference=f"{created['artifact']['id']}@1")
        nested_evidence["inputs"]["refresh"] = self.refresh(None)
        nested_evidence["inputs"]["context"]["evidence"] = nested_evidence["inputs"].pop("evidence")
        nested_evidence["confirmations"] = [{"type": "write", "approved": True}]
        rejected = self.invoke(nested_evidence)
        self.assertEqual(rejected["errors"][0]["code"], "CTX_CONTENT_INVALID")

    def test_domain_validator_rejects_manifest_member_closure_tampering(self):
        created = self.invoke(self.invocation())
        stored = runtime.ArtifactStore.open_read_only(self.project_root).read_revision(
            created["artifact"]["id"], 1
        )
        tampered_manifest = replace(stored.payload.manifest, raw_bytes=b"{}")
        tampered = replace(
            stored,
            payload=replace(stored.payload, manifest=tampered_manifest),
        )
        failures, gate_result, _ = runtime.validate_stored_revision(tampered)
        self.assertEqual(gate_result, "fail")
        self.assertIn("CORE-G-003", failures)

    def test_delegated_confirmation_requires_and_accepts_fixed_authority_contract(self):
        created = self.invoke(self.invocation())
        artifact_id = created["artifact"]["id"]
        reference = f"{artifact_id}@1"
        refresh = self.refresh(None, reason="delegated final confirmation")
        dry = self.invocation("revise", reference=reference, dry_run=True)
        dry["inputs"]["refresh"] = refresh
        preview = self.invoke(dry)
        bindings = next(
            item for item in preview["warnings"] if item["code"] == "FINAL_CONFIRMATION_BINDINGS"
        )["details"]

        authority_dir = self.project_root / "authority"
        authority_dir.mkdir(exist_ok=True)
        malformed = "\n".join(
            [
                reference,
                bindings["control_input_digest"],
                bindings["evaluation_contract_set"],
                bindings["check_set_result_digest"],
                "reviewer-run-02",
                "builder-run-01",
            ]
        ) + "\n"
        malformed_path = authority_dir / "delegated-malformed.md"
        malformed_path.write_text(malformed, encoding="utf-8")
        malformed_reference = "authority/delegated-malformed.md@sha256:" + hashlib.sha256(malformed.encode()).hexdigest()
        confirmation = {
            "type": "final_confirmation",
            "result": "approved",
            "mode": "delegated",
            "confirmer": "reviewer-run-02",
            "role": "Delegated Independent Reviewer",
            "reviewed_executor": "builder-run-01",
            "authority_reference": malformed_reference,
            "accepted_exception_references": [],
            "confirmed_at": "2026-08-30T10:11:12+00:00",
            **bindings,
        }
        revise = self.invocation("revise", reference=reference)
        revise["inputs"]["refresh"] = refresh
        revise["confirmations"] = [{"type": "write", "approved": True}, confirmation]
        rejected = self.invoke(revise)
        self.assertEqual(rejected["status"], "action_required", rejected)
        self.assertEqual(rejected["artifact"]["revision_state"], "open")

        delegation_basis_text = "delegation: reviewer-run-02 may confirm CTX contract compliance\n"
        delegation_basis_path = authority_dir / "delegation.txt"
        delegation_basis_path.write_text(delegation_basis_text, encoding="utf-8")
        delegation_basis = "authority/delegation.txt@sha256:" + hashlib.sha256(delegation_basis_text.encode()).hexdigest()
        authority_text = "\n".join(
            [
                "---",
                "contract: sdlc-ai-spec/final-confirmation-authority/v1",
                f"artifact: {reference}",
                "decision: approved",
                "decided_at: 2026-08-30T10:11:12+00:00",
                "---",
                "",
                "| " + " | ".join(runtime.DELEGATED_AUTHORITY_HEADER) + " |",
                "| " + " | ".join("---" for _ in runtime.DELEGATED_AUTHORITY_HEADER) + " |",
                "| " + " | ".join(
                    [
                        delegation_basis,
                        "reviewer-run-02",
                        "Delegated Independent Reviewer",
                        "builder-run-01",
                        runtime.DELEGATED_INDEPENDENCE,
                        bindings["control_input_digest"],
                        bindings["evaluation_contract_set"],
                        bindings["check_set_result_digest"],
                        runtime.DELEGATED_EXCLUDED_AUTHORITY,
                    ]
                ) + " |",
            ]
        ) + "\n"
        authority_path = authority_dir / "delegated.md"
        authority_path.write_text(authority_text, encoding="utf-8")
        confirmation["authority_reference"] = "authority/delegated.md@sha256:" + hashlib.sha256(authority_text.encode()).hexdigest()
        accepted = self.invoke(revise)
        self.assertTrue(accepted["ok"], accepted)
        self.assertEqual(accepted["artifact"]["revision_state"], "frozen")
        self.assertEqual(accepted["artifact"]["reference"], reference)

    def test_old_frozen_base_uses_lineage_max_revision_and_invalid_input_allocates_nothing(self):
        reference_one, _ = self.create_and_freeze()
        artifact_id = reference_one.split("@", 1)[0]
        context_two = self.context()
        context_two["project_identity"]["purpose"] = fact(
            "Validate CTX Runtime revision two", "confirmed", "EVD-001"
        )
        revise_two = self.invocation("revise", context=context_two, reference=reference_one)
        revise_two["inputs"]["refresh"] = self.refresh(
            1, changes=[f"{reference_one}#EVD-001"]
        )
        revise_two["confirmations"] = [{"type": "write", "approved": True}]
        open_two = self.invoke(revise_two)
        reference_two = f"{artifact_id}@2"
        self.assertEqual(open_two["artifact"]["revision"], 2)
        frozen_two = self.finalize_open(reference_two, context_two, revise_two["inputs"]["refresh"])
        self.assertTrue(frozen_two["ok"], frozen_two)

        invalid = self.invocation("revise", context=self.context(), reference=reference_one)
        invalid["inputs"]["context"]["resources"][0]["type"] = "workspace"
        invalid["inputs"]["refresh"] = self.refresh(
            1, changes=[f"{reference_one}#RSC-001"]
        )
        invalid["confirmations"] = [{"type": "write", "approved": True}]
        rejected = self.invoke(invalid)
        self.assertEqual(rejected["errors"][0]["code"], "CTX_CONTENT_INVALID")
        catalog = ArtifactCatalog(runtime.ArtifactStore.open_read_only(self.project_root))
        self.assertEqual([item.revision for item in catalog.list_revisions(artifact_id)], [1, 2])

        context_three = self.context()
        context_three["project_identity"]["purpose"] = fact(
            "Validate CTX Runtime revision three from revision one", "confirmed", "EVD-001"
        )
        revise_three = self.invocation("revise", context=context_three, reference=reference_one)
        revise_three["inputs"]["refresh"] = self.refresh(
            1, changes=[f"{reference_one}#EVD-001"]
        )
        revise_three["confirmations"] = [{"type": "write", "approved": True}]
        open_three = self.invoke(revise_three)
        self.assertEqual(open_three["artifact"]["revision"], 3, open_three)
        stored_three = runtime.ArtifactStore.open_read_only(self.project_root).read_revision(artifact_id, 3)
        self.assertEqual(stored_three.control.base_revision, 1)
        self.assertTrue(stored_three.control.materialized)
        self.assertIn(b"revision: 3\n", stored_three.payload.primary_blob)

    def test_post_allocation_failure_abandons_unmaterialized_control_reservation(self):
        reference, _ = self.create_and_freeze()
        artifact_id = reference.split("@", 1)[0]
        changed = self.context()
        changed["project_identity"]["purpose"] = fact(
            "Trigger post-allocation failure", "confirmed", "EVD-001"
        )
        invocation = self.invocation("revise", context=changed, reference=reference)
        invocation["inputs"]["refresh"] = self.refresh(
            1, changes=[f"{reference}#EVD-001"]
        )
        invocation["confirmations"] = [{"type": "write", "approved": True}]

        original = runtime.build_payload
        calls = 0

        def fail_after_allocation(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("fixture post-allocation failure")
            return original(*args, **kwargs)

        runtime.build_payload = fail_after_allocation
        try:
            failed = self.invoke(invocation)
        finally:
            runtime.build_payload = original
        self.assertFalse(failed["ok"], failed)
        controls = ArtifactCatalog(
            runtime.ArtifactStore.open_read_only(self.project_root)
        ).list_revisions(artifact_id)
        self.assertEqual(controls[-1].revision, 2)
        self.assertEqual(controls[-1].state, "abandoned")
        self.assertFalse(controls[-1].materialized)

        retry = self.invoke(invocation)
        self.assertEqual(retry["artifact"]["revision"], 3, retry)
        self.assertEqual(retry["artifact"]["revision_state"], "open")

    def snapshot(self):
        return {
            str(path.relative_to(self.project_root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(self.project_root.rglob("*"))
            if path.is_file()
        }


if __name__ == "__main__":
    unittest.main()

"""Real local Stores, Claims, Resource files and PLN producer for IMP tests."""
from __future__ import annotations

from contextlib import closing
from dataclasses import replace
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "tests", ROOT / "skills/sdlc-400-imp/scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from tests.skill_pln.support import PlnFixture, FIXED
from packages.sdlc_artifact_store import ArtifactStore, CanonicalMember, CanonicalRevisionPayload, compute_sha256
from packages.sdlc_artifact_store.catalog import ArtifactCatalog
from packages.sdlc_phasekit import CheckOutcome, PhaseInputs, manifest, render_phase_artifact, table
from packages.sdlc_runtime import (
    FrozenArtifactAuthorityVerifier, compute_ctx_check_set_result_digest,
    compute_ctx_control_input_digest, parse_canonical_artifact,
)
from packages.sdlc_runtime.canonical import CHECK_HEADERS, FINAL_CONFIRMATION_HEADERS, GATE_SUMMARY_HEADERS
from imp_common import CONSIDERATIONS
from imp_result import read_state
from packages.sdlc_runtime.control_inputs import VFY_RETURN_HEADERS

ENTRY = ROOT / "skills/sdlc-400-imp/scripts/runtime.py"
spec = importlib.util.spec_from_file_location("focused_imp_cli", ENTRY)
cli = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = cli
spec.loader.exec_module(cli)

OWNER = "executor-fixture"


class FixtureAuthority:
    """Bootstrap synthetic upstream facts, but verify their real canonical binding."""
    def __init__(self, root):
        self.verifier = FrozenArtifactAuthorityVerifier(root)

    def verify(self, reference, revision):
        return self.verifier.verify(reference, replace(revision, control=replace(revision.control, state="frozen")))


def tree_bytes(root):
    return {path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*") if path.is_file()}


class ImpFixture(PlnFixture):
    def complete_design(self, **kwargs):
        design = super().complete_design(**kwargs)
        design["changes"][0]["object_or_boundary"] = "resource:repo"
        return design

    def plan(self, **kwargs):
        plan = super().plan(**kwargs)
        if kwargs.get("second_imp"):
            plan["work_items"][1]["expected_evidence"] = "Second immutable snapshot and local check evidence"
        return plan

    def _authority(self, name):
        target = self.root / ".sdlc/authority" / (name + ".txt")
        target.parent.mkdir(exist_ok=True)
        target.write_text(f"Fixture authority approved {name}\n")
        return target.relative_to(self.root).as_posix() + "@" + compute_sha256(target.read_bytes())

    def _source(self, phase, producer):
        allocation = self.store.allocate_artifact(phase, now=FIXED)
        control = self.store.allocate_revision(allocation.artifact_id, now=FIXED)
        raw = producer(allocation.artifact_id, control.revision)
        self.store.write_open_revision(CanonicalRevisionPayload(
            allocation.artifact_id, phase, control.revision, "ready", raw, "text/markdown",
            compute_sha256(raw), (), manifest(()),
        ), expected_generation=control.generation)
        self.store.freeze_revision(allocation.artifact_id, control.revision, verifier=FixtureAuthority(self.root))
        return f"{allocation.artifact_id}@{control.revision}"

    def _create_context(self):
        authority = self._authority("context")
        def produce(identity, revision):
            raw = (
                f"---\ncontract: sdlc-ai-spec/project-context/v1\nid: {identity}\n"
                f"revision: {revision}\nstatus: ready\n---\n# Temporary project Context\n\n"
                "## 摘要 Summary\n\nA local fixture project for exact Context binding.\n\n"
                "## 门禁 Gate\n\n" +
                table(CHECK_HEADERS, [(f"CORE-G-{index:03d}", "Fixture source", "pass", "Local fixture authority")
                                      for index in range(1, 10)]) +
                "\n\n" + table(("Check ID", "Check", "Result", "Basis References"),
                               [("CTX-G-001", "Project boundary", "pass", "Fixture project")]) + "\n\n"
            ).encode()
            control_digest = compute_ctx_control_input_digest(raw)
            check_digest = compute_ctx_check_set_result_digest(parse_canonical_artifact(raw))
            evaluation = "fixture-context@sha256:" + "a" * 64
            confirmation = (revision, control_digest, evaluation, check_digest, "approved", "human",
                            "fixture-owner", "Context Authority", authority, "None", "2026-09-01T13:00:00Z")
            summary = (revision, control_digest, evaluation, check_digest, "pass", "None",
                       "Fixture producer", "2026-09-01T13:00:00Z")
            return raw + ("### Final Confirmation\n\n" + table(FINAL_CONFIRMATION_HEADERS, [confirmation]) +
                          "\n\n### Artifact Gate Summary\n\n" + table(GATE_SUMMARY_HEADERS, [summary]) + "\n").encode()
        return self._source("CTX", produce)

    def create_requirement(self, context_reference, dsn_disposition="required", pln_disposition="required", *, dependencies=()):
        authority = self._authority("requirement")
        def produce(identity, revision):
            sections = (
                ("## 摘要 Summary", "Authorized fixture behavior"),
                ("## 范围 Scope", "- Direct IMP Scope: resource:repo, path:repo/integration"),
                ("## 目标与成功条件 Goal and Success", table(
                    ("ID", "当前问题 Current Problem", "目标结果与预期用途 Goal, Intended Outcome and Use", "成功条件 Success Condition"),
                    [("GOAL-001", "Before marker", "Write the expected local marker", "Local content matches the target")],
                )),
                ("## 需求项 Requirements", table(
                    ("ID", "类型 Type", "来源或父项引用 Source or Parent References", "需求描述 Requirement Statement"),
                    [("R-001", "behavior", "GOAL-001", "已授权用户可以导出当前筛选结果")],
                )),
                ("## 验收条件 Acceptance Criteria", table(
                    ("ID", "关联需求 Requirement References", "条件 Condition", "预期结果 Expected Result"),
                    [("AC-001", "R-001", "用户具有权限并应用筛选条件", "导出记录与筛选结果一致")],
                )),
                ("## 依赖 Dependencies", table(
                    ("ID", "依赖项 Dependency", "要求状态 Required State", "当前状态 Current State",
                     "状态检查引用 State Check Reference"),
                    dependencies or [("None", "No dependencies", "N/A", "N/A", "N/A")],
                )),
            )
            return render_phase_artifact(
                artifact_id=identity, phase="REQ", revision=revision, status="ready", profile="full",
                phase_inputs=PhaseInputs(context_reference, ()), title="Fixture Requirement", sections=sections,
                checks={f"CORE-G-{index:03d}": CheckOutcome("pass", "Fixture authority") for index in range(1, 10)},
                open_items=(), evidence=(), exceptions=(),
                lifecycle_applicability=[
                    {"phase": phase, "disposition": disposition, "host": "N/A", "basis": "Explicit fixture scope"}
                    for phase, disposition in (("DSN", dsn_disposition), ("PLN", pln_disposition),
                                                ("IMP", "required"), ("VFY", "required"), ("RLS", "n/a"))
                ],
                final_confirmation={"mode": "human", "confirmer": "fixture-owner", "role": "Product Owner",
                                    "authority_reference": authority, "confirmed_at": "2026-09-01T13:00:00Z"},
                gate_result="pass", evaluation_contract_set="fixture-requirement@sha256:" + "b" * 64,
                evaluator="Fixture producer",
            )
        return self._source("REQ", produce)

    def setUp(self):
        super().setUp()
        result = self.execute_pln()
        self.assertTrue(result["ok"], result)
        self.pln_reference = result["artifact"]["reference"]
        self.binding = self.pln_reference + "#WI-001"
        (self.root / "integration").mkdir()
        (self.root / "integration/app.txt").write_text("version=before\n")
        (self.root / "user-note.txt").write_text("user baseline\n")
        self.git("init", "-q")
        self.git("add", "integration/app.txt", "user-note.txt")
        self.git("-c", "user.name=IMP Fixture", "-c", "user.email=imp-fixture@example.invalid",
                 "commit", "-qm", "seed isolated product fixture")
        self.imp_authority = self._authority("implementation")
        self.original_head = self.git("rev-parse", "HEAD")

    def git(self, *args):
        process = subprocess.run(["git", "-C", str(self.root), *args], capture_output=True,
                                 text=True, env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})
        self.assertEqual(process.returncode, 0, process.stderr)
        return process.stdout.strip()

    def claim_count(self):
        path = self.root / ".sdlc/store.sqlite3"
        if not path.is_file():
            return 0
        with closing(sqlite3.connect(path)) as connection:
            exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='imp_claims'"
            ).fetchone()
            if exists is None:
                return 0
            return connection.execute("SELECT COUNT(*) FROM imp_claims").fetchone()[0]

    def implementation(self, *, binding=None, before="before", after="after"):
        binding = binding or self.binding
        basis = self.dsn_reference + "#CHG-001" if binding.startswith(("PLN-", "DSN-")) else binding
        path = self.root / "integration/app.txt"
        return {
            "summary": "Apply the exact local fixture outcome",
            "considerations": [
                {"name": name, "disposition": "required" if name == "Effects & Consistency" else "n/a",
                 "basis": "A conditional local file write" if name == "Effects & Consistency" else
                          "This marker edit introduces no rule, calculation, state machine, mapping or algorithm in this category",
                 "steps": ["STEP-001"] if name == "Effects & Consistency" else [], "exception": None}
                for name in CONSIDERATIONS
            ],
            "steps": [{
                "id": "STEP-001", "order": 1, "purpose": "Publish the expected marker",
                "target": ["resource:repo", "path:repo/integration"],
                "basis_references": [basis], "considerations": ["Effects & Consistency"],
                "logic": ["Replace the exact marker only after verifying its current content"],
                "expected_result": "The local marker reflects the specified outcome",
                "transaction_boundary": "One conditional file write", "failure_boundary": "Stop before a mismatched file",
                "blocks": [{
                    "id": "EFF-001", "consideration": "Effects & Consistency",
                    "resource_or_effect": "The claimed product file",
                    "order_and_condition": "Read Baseline, match content, write once",
                    "consistency_or_atomicity": "One local operation in a serialized Claim",
                    "idempotency": "Reuse the current Attempt and retained operation identity",
                    "failure_handling": "Preserve Baseline and stop on mismatch",
                }],
            }],
            "resources": [{"id": "repo", "root": "."}],
            "operations": [{
                "resource": "repo", "path": "integration/app.txt", "step": "STEP-001",
                "op": "replace_text", "before": before, "after": after,
                "expected_sha256": compute_sha256(path.read_bytes()),
            }],
            "checks": [{"id": "CHK-001", "name": "Marker equals target", "kind": "equals", "resource": "repo",
                        "path": "integration/app.txt", "expected": f"version={after}\n"}],
            "exceptions": [], "open_items": [],
        }

    def invoke(self, command="create", *, binding=None, reference=None, owner=OWNER, implementation=None,
               inputs=None, policy="auto", final=None, confirmations=None):
        arguments = [command, "-p", str(self.root), "-f", "json", "--write-policy", policy]
        if binding is not False:
            arguments.extend(["--binding", binding or self.binding])
        if reference:
            arguments.extend(["-r", reference])
        if owner is not None:
            arguments.extend(["--owner", owner])
        data = dict(inputs or {})
        if implementation is not None:
            data["implementation"] = implementation
        if final is not None:
            data["final_confirmation"] = final
        result, _ = cli.run_cli(arguments, {"inputs": data, "confirmations": confirmations or []})
        return result

    def create_open(self, **kwargs):
        result = self.invoke(implementation=kwargs.pop("implementation", self.implementation()), **kwargs)
        self.assertEqual(result["status"], "action_required", result)
        self.assertEqual(result["artifact"]["revision_state"], "open", result)
        self.assertEqual(read_state(self.stored(result))["stage"], "executed")
        return result

    def info(self, result):
        return next(item for item in result["warnings"] if item["code"] == "IMP_EXECUTION_STATE")

    def stored(self, result):
        artifact = result["artifact"]
        return ArtifactStore.open_read_only(self.root).read_revision(artifact["id"], artifact["revision"])

    def confirmation(self, result):
        return {"mode": "human", "confirmer": "fixture-owner", "role": "Implementation Authority",
                "authority_reference": self.imp_authority, "confirmed_at": "2026-09-03T10:00:00Z",
                "subject_digest": self.info(result)["subject_digest"]}

    def finish(self, result):
        closed = self.invoke("revise", binding=False, reference=result["artifact"]["reference"],
                             final=self.confirmation(result))
        self.assertTrue(closed["ok"], closed)
        self.assertEqual(closed["artifact"]["revision_state"], "frozen", closed)
        return closed

    def revise_plan(self):
        plan = self.plan()
        plan["summary"] = "The same Work Item with a newly approved upstream clarification"
        result = self.execute_pln(operation="revise", reference=self.pln_reference, plan=plan)
        self.assertTrue(result["ok"], result)
        return result["artifact"]["reference"]

    def vfy_return(self, result, *, binding=None, context=None, evidence_item=False):
        """Canonical frozen input only; this fixture implements no VFY runtime."""
        source = result["artifact"]["reference"]
        authority = self._authority("return")
        allocation = self.store.allocate_artifact("VFY")
        control = self.store.allocate_revision(allocation.artifact_id)
        base = f"{allocation.artifact_id}@{control.revision}"
        evidence_raw = b"Observed marker requires a second authorized local replacement."
        evidence = CanonicalMember("EVD-001", "evidence/return.txt", "text/plain",
                                   evidence_raw, compute_sha256(evidence_raw))
        raw = render_phase_artifact(
            artifact_id=allocation.artifact_id, phase="VFY", revision=control.revision,
            status="ready", profile="full", phase_inputs=PhaseInputs(context or self.context_reference, (source,)),
            title="Frozen Return fixture", sections=(("## Return", table(VFY_RETURN_HEADERS, [
                ("RET-001", "IMP", binding or self.binding, source, base + "#MET-001",
                 self.info(result)["results"][0], "Observed marker must change", "Replace the marker with reworked",
                 base + ("#EVD-001" if evidence_item else "/EVD-001")),
            ])),),
            checks={f"CORE-G-{index:03d}": CheckOutcome("pass", "Fixture source authority") for index in range(1, 10)},
            open_items=(), evidence=[{
                "id": "EVD-001", "type": "observation", "supports_references": [source],
                "source": "Fixture producer", "reference": base + "/EVD-001",
                "integrity": evidence.sha256,
            }], exceptions=(), lifecycle_applicability=(),
            final_confirmation={"mode": "human", "confirmer": "fixture-owner", "role": "Return Authority",
                                "authority_reference": authority, "confirmed_at": "2026-09-03T10:00:00Z"},
            gate_result="pass", evaluation_contract_set="fixture-return@sha256:" + "c" * 64,
            evaluator="Fixture producer", members=(evidence,),
        )
        self.store.write_open_revision(CanonicalRevisionPayload(
            allocation.artifact_id, "VFY", control.revision, "ready", raw, "text/markdown",
            compute_sha256(raw), (evidence,), manifest((evidence,)),
        ), expected_generation=control.generation)
        self.store.freeze_revision(allocation.artifact_id, control.revision, verifier=FixtureAuthority(self.root))
        return base + "#RET-001"

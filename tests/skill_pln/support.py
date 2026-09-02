from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
for candidate in (ROOT, ROOT / "packages", ROOT / "skills/sdlc-200-dsn/scripts", ROOT / "skills/sdlc-300-pln/scripts", ROOT / "tests"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from tests.skill_dsn.support import DsnRuntimeFixture
from tests.skill_dsn import support_patch  # noqa: F401
from packages.sdlc_artifact_store import ArtifactStore
from packages.sdlc_phasekit import subject_digest
from packages.sdlc_runtime import execute_phase, sha256_bytes
from pln_runtime import PlnHandler, resolve_inputs

FIXED = datetime(2026, 9, 1, 13, 0, tzinfo=timezone.utc)


class PlnFixture(DsnRuntimeFixture):
    def setUp(self):
        super().setUp()
        self.dsn_reference = self.execute(self.invocation())["artifact"]["reference"]
        authority = self.root / ".sdlc/authority/pln.md"
        authority.write_text("Approved by plan-authority-1\n", encoding="utf-8")
        self.pln_authority = authority.relative_to(self.root).as_posix() + "@" + sha256_bytes(authority.read_bytes())
        self.pln_handler = PlnHandler(self.root, clock=lambda: FIXED)


    def create_scope_with_pln_disposition(self, disposition: str):
        design = self.complete_design()
        for row in design["lifecycle_applicability"]:
            if row["phase"] == "PLN":
                row["disposition"] = disposition
                row["basis"] = (
                    "The scope is one atomic implementation outcome with no planning obligation"
                    if disposition == "n/a"
                    else "An approved exception waives the otherwise required independent Plan"
                )
        if disposition == "waived":
            design["exceptions"] = [{
                "id": "EX-001",
                "state": "active",
                "origin_reference": self.dsn_reference if hasattr(self, "dsn_reference") else self.requirement_reference,
                "scope": "PLN lifecycle obligation",
                "reason": "Authorized waiver for the independent Plan Artifact",
                "known_risk": "Coordination remains implicit",
                "compensating_control": "The direct IMP Binding remains atomic and VFY is required",
                "approval": "plan-authority at 2026-09-01T13:00:00Z",
                "revisit_condition": "If the delivery scope expands",
                "downstream_obligation": "IMP must preserve one atomic outcome",
                "resolution_references": "None",
            }]
        result = self.execute(self.invocation(design=design))
        if not result.get("ok"):
            raise AssertionError(result)
        return result["artifact"]["reference"]

    def plan(self, *, disposition="required", second_imp=False):
        change = self.dsn_reference + "#CHG-001"
        objective = self.dsn_reference + "#OBJ-001"
        work = [
            {
                "id":"WI-001", "target_phase":"IMP", "outcome":"Implement the designed change",
                "execution_scope":["resource:repo", "path:repo/integration"],
                "source_references":[change], "constraint_references":[], "depends_on":[],
                "completion_criteria":"An immutable implementation result exists",
                "expected_evidence":"Result snapshot and local check evidence",
                "responsible_role":"Implementer",
            },
            {
                "id":"WI-002", "target_phase":"VFY", "outcome":"Verify and validate the result",
                "execution_scope":["resource:repo"], "source_references":[objective],
                "constraint_references":[], "depends_on":["WI-001"],
                "completion_criteria":"All required methods have final results",
                "expected_evidence":"Method evidence and conclusions",
                "responsible_role":"Verifier",
            },
        ]
        if second_imp:
            work.insert(1, {
                "id":"WI-002", "target_phase":"IMP", "outcome":"Apply the follow-up change",
                "execution_scope":["resource:repo", "path:repo/integration"],
                "source_references":[change], "constraint_references":[], "depends_on":["WI-001"],
                "completion_criteria":"Second immutable result exists", "expected_evidence":"Snapshot",
                "responsible_role":"Implementer",
            })
            work[2]["id"]="WI-003"; work[2]["depends_on"]=["WI-002"]
        return {
            "title":"Delivery Plan", "summary":"Plan the confirmed design for implementation and verification.",
            "profile":"full", "pln_disposition":disposition,
            "delivery_scope":[{"scope_token":"resource:repo","source_references":[change],"outcome":"Deliver the design change"}],
            "aggregated_applicability":[
                {"phase":"IMP","disposition":"required","host":"N/A","basis":"Design change requires implementation"},
                {"phase":"VFY","disposition":"required","host":"N/A","basis":"VFY is mandatory"},
                {"phase":"RLS","disposition":"n/a","host":"N/A","basis":"Fixture has no formal release"},
            ],
            "obligations":[change, objective], "work_items":work if disposition=="required" else [],
            "lifecycle_applicability":[
                {"phase":"IMP","disposition":"required" if disposition=="required" else "n/a","host":"N/A","basis":"Plan decision"},
                {"phase":"VFY","disposition":"required","host":"N/A","basis":"VFY is mandatory"},
                {"phase":"RLS","disposition":"n/a","host":"N/A","basis":"No release"},
            ],
            "open_items":[], "evidence":[], "supporting_members":[], "exceptions":[],
        }

    def pln_final_confirmation(self, plan, scope=None):
        scope = scope or (self.dsn_reference,)
        store=ArtifactStore.open_read_only(self.root)
        phase_inputs=resolve_inputs(store,{"scope_inputs":list(scope),"control_inputs":[]})
        digest=subject_digest(plan,{"context":phase_inputs.context_reference,"scope":phase_inputs.scope_references,"control":phase_inputs.control_references})
        return {"mode":"human","confirmer":"plan-authority-1","role":"Plan Authority","authority_reference":self.pln_authority,"confirmed_at":"2026-09-01T13:00:00Z","subject_digest":digest}

    def pln_invocation(self, *, operation="create", reference=None, plan=None, final=True, scope=None):
        scope=scope or (self.dsn_reference,)
        value=plan or self.plan()
        return {
            "contract":"sdlc-ai-spec/runtime-invocation/v1", "operation":operation,
            "project_root":str(self.root), "artifact_reference":reference,
            "inputs":{"scope_inputs":list(scope),"control_inputs":[],"plan":value,"final_confirmation":self.pln_final_confirmation(value,scope) if final else None},
            "confirmations":[], "options":{"dry_run":False,"write_policy":"auto"},
        }

    def execute_pln(self, **kwargs):
        return execute_phase(self.pln_handler, self.pln_invocation(**kwargs))

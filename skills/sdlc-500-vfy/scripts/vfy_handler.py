"""VFY create/run/revise/check orchestration with authority re-read."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import os
from pathlib import Path
from typing import Any, Mapping

from packages.sdlc_phasekit import (
    validate_delegated_final_confirmation,
    validate_final_confirmation,
)
from packages.sdlc_lifecycle import LifecycleQueryService

from vfy_authority import assert_candidate_authority, compile_candidate
from vfy_builder import (
    build_state,
    canonical_members,
    confirmation_subject_digest,
    final_confirmation_bindings,
    state_contract_digest,
)
from vfy_common import (
    VfyError,
    canonical_bytes,
    exact_artifact_reference,
    reject_secrets,
    require,
    sha256_value,
)
from vfy_conclusions import (
    aggregate_fixed_conclusions,
    aggregate_target_conclusions,
    product_result,
)
from vfy_executor import execute_method
from vfy_persistence import (
    abandon_revision,
    create_revision,
    freeze_revision,
    read_revision,
    write_open_revision,
)
from vfy_results import method_result_index
from vfy_returns import normalize_returns
from vfy_subject import assert_subjects_still_current
from vfy_verifier import apply_projection, verify_state


def _workspace_digest(root: Path) -> str:
    rows: list[tuple[str, str]] = []
    for directory, names, files in os.walk(root):
        names[:] = sorted(name for name in names if name not in {".git", "__pycache__"})
        base = Path(directory)
        for name in sorted(files):
            path = base / name
            relative = path.relative_to(root).as_posix()
            try:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError as exc:
                digest = f"ERROR:{exc.__class__.__name__}"
            rows.append((relative, digest))
    return sha256_value(rows)


def _candidate_input_references(candidate: Mapping[str, Any]) -> list[str]:
    values = [str(candidate.get("context_reference", ""))]
    scope = candidate.get("scope") or {}
    if isinstance(scope, Mapping) and scope.get("reference"):
        values.append(str(scope["reference"]))
    for subject in candidate.get("subjects", []):
        if isinstance(subject, Mapping):
            values.extend(
                str(item)
                for item in (
                    subject.get("reference"),
                    subject.get("imp_revision_reference"),
                )
                if item
            )
    for target in candidate.get("targets", []):
        if isinstance(target, Mapping) and target.get("reference"):
            values.append(str(target["reference"]))
    values.extend(str(item) for item in candidate.get("control_inputs", []))
    values.extend(
        str(item.get("origin_reference"))
        for item in candidate.get("exceptions", [])
        if isinstance(item, Mapping) and item.get("origin_reference")
    )
    values.extend(str(item) for item in candidate.get("owner_artifact_inputs", []))
    return list(dict.fromkeys(item for item in values if item))


def _refresh_conclusions(state: dict[str, Any]) -> None:
    targets = tuple(state["targets"])
    methods = tuple(state["methods"])
    state["target_conclusions"] = aggregate_target_conclusions(
        targets,
        methods,
        list(state["method_results"]),
    )
    state["fixed_conclusions"] = aggregate_fixed_conclusions(
        targets,
        state["target_conclusions"],
    )
    state["product_result"] = product_result(state["fixed_conclusions"])


def _attach_failure_returns(
    state: dict[str, Any],
    failure_returns: Mapping[str, Any] | None,
) -> None:
    if not failure_returns:
        return
    subject_lineages = {
        str(item["reference"]): str(item["binding_lineage"])
        for item in state["subjects"]
    }
    existing_ids = {str(item["id"]) for item in state["returns"]}
    for result in state["method_results"]:
        method_id = str(result["method_id"])
        if result["result"] != "fail" or method_id not in failure_returns:
            continue
        raw = failure_returns[method_id]
        require(
            isinstance(raw, Mapping),
            "VFY_RETURN_INVALID",
            "Failure Return input must be an object",
            details={"method_id": method_id},
        )
        candidate = dict(raw)
        if not candidate.get("id"):
            candidate["id"] = f"RET-{len(existing_ids) + 1:03d}"
        candidate["status"] = "open"
        candidate["resolution_references"] = []
        candidate.setdefault("method_references", [method_id])
        method = next(item for item in state["methods"] if item["id"] == method_id)
        candidate.setdefault("target_references", method["target_references"])
        candidate.setdefault("subject_references", method["subject_references"])
        candidate["evidence_references"] = list(result["evidence_references"])
        normalized = normalize_returns(
            [candidate],
            subject_lineages=subject_lineages,
        )[0]
        require(
            normalized["id"] not in existing_ids,
            "VFY_RETURN_INVALID",
            "Return ID already exists",
            details={"return_id": normalized["id"]},
        )
        existing_ids.add(normalized["id"])
        state["returns"].append(normalized)
        result["return_references"] = [
            f"{state['artifact']['reference']}#{normalized['id']}"
        ]


def _prospective_confirmation_bindings(state: Mapping[str, Any]) -> dict[str, str]:
    projected = apply_projection(
        state,
        verify_state(state, finalizing=False),
        freeze=False,
    )
    stub = {
        "mode": "human",
        "accepted_exception_references": [
            f"{projected['artifact']['reference']}#{item['id']}"
            for item in projected.get("exceptions", [])
            if item.get("state") in {"active", "carried"}
        ],
        "subject_digest": confirmation_subject_digest(projected),
        "contract_digest": projected["pre_execution_contract_digest"],
        "subject_set_digest": projected["subject_set_digest"],
        "product_result": projected["product_result"],
        "method_result_digest": sha256_value(projected["method_results"]),
        "return_digest": sha256_value(projected["returns"]),
    }
    projected["final_confirmation"] = stub
    final_projection = verify_state(projected, finalizing=True)
    projected = apply_projection(projected, final_projection, freeze=True)
    projected["artifact"]["revision_state"] = "open"
    projected["final_confirmation"] = None
    return final_confirmation_bindings(
        projected,
        members=canonical_members(projected),
    )


def _final_confirmation(
    project_root: Path,
    state: Mapping[str, Any],
    confirmation: Mapping[str, Any] | None,
) -> dict[str, Any]:
    require(
        isinstance(confirmation, Mapping),
        "VFY_FINAL_CONFIRMATION_STALE",
        "Finalization requires a real Final Confirmation object",
        status="action_required",
    )
    expected_subject = confirmation_subject_digest(state)
    require(
        confirmation.get("subject_digest") == expected_subject,
        "VFY_FINAL_CONFIRMATION_STALE",
        "Final Confirmation Subject binding is missing or stale",
        status="action_required",
    )
    try:
        valid = validate_final_confirmation(project_root, confirmation, expected_subject)
    except Exception as exc:
        raise VfyError(
            "VFY_FINAL_CONFIRMATION_STALE",
            f"Final Confirmation authority is invalid: {exc}",
            status="action_required",
        ) from exc
    require(
        valid,
        "VFY_FINAL_CONFIRMATION_STALE",
        "Final Confirmation does not bind the current VFY result boundary",
        status="action_required",
    )
    expected_exceptions = [
        f"{state['artifact']['reference']}#{item['id']}"
        for item in state.get("exceptions", [])
        if item.get("state") in {"active", "carried"}
    ]
    accepted_exceptions = confirmation.get("accepted_exception_references")
    require(
        isinstance(accepted_exceptions, list)
        and all(isinstance(item, str) for item in accepted_exceptions)
        and accepted_exceptions == expected_exceptions,
        "VFY_FINAL_CONFIRMATION_STALE",
        "Final Confirmation must accept the exact current Exception Reference Set",
        status="action_required",
        details={
            "expected": expected_exceptions,
            "actual": accepted_exceptions,
        },
    )
    require(
        confirmation.get("mode") != "delegated" or not expected_exceptions,
        "VFY_FINAL_CONFIRMATION_STALE",
        "Delegated Final Confirmation cannot approve active or carried Exceptions",
        status="action_required",
    )
    bindings = _prospective_confirmation_bindings(state)
    if confirmation.get("mode") == "delegated":
        executors = {
            str(item["executor_identity"])
            for item in state["methods"]
            if item["disposition"] in {"required", "embedded"}
        }
        require(
            len(executors) == 1,
            "VFY_FINAL_CONFIRMATION_STALE",
            "Delegated confirmation requires one exact reviewed Executor identity",
            status="action_required",
        )
        require(
            validate_delegated_final_confirmation(
                project_root,
                confirmation,
                artifact_reference=str(state["artifact"]["reference"]),
                reviewed_executor=next(iter(executors)),
                control_input_digest=bindings["control_input_digest"],
                evaluation_contract_set=bindings["evaluation_contract_set"],
                check_set_result_digest=bindings["check_set_result_digest"],
            ),
            "VFY_FINAL_CONFIRMATION_STALE",
            "Delegated Final Confirmation bindings or independence are invalid",
            status="action_required",
        )
    return {
        "mode": str(confirmation["mode"]),
        "confirmer": str(confirmation["confirmer"]),
        "role": str(confirmation["role"]),
        "authority_reference": str(confirmation["authority_reference"]),
        "confirmed_at": str(confirmation["confirmed_at"]),
        "accepted_exception_references": expected_exceptions,
        "subject_digest": expected_subject,
        **bindings,
        "contract_digest": state["pre_execution_contract_digest"],
        "subject_set_digest": state["subject_set_digest"],
        "product_result": state["product_result"],
        "method_result_digest": sha256_value(state["method_results"]),
        "return_digest": sha256_value(state["returns"]),
    }


class VfyHandler:
    """One-operation facade; persistent paths always re-read Authority."""

    def __init__(self, project_root: Path) -> None:
        root = Path(project_root).expanduser().resolve()
        require(
            root.is_dir(),
            "VFY_SCOPE_REQUIRED",
            "Project root must be an existing directory",
        )
        self.project_root = root

    def confirmation_requirements(self, state: Mapping[str, Any]) -> dict[str, str]:
        return _prospective_confirmation_bindings(state)

    def _current_subject_snapshot(self, state: Mapping[str, Any]) -> dict[str, Any]:
        """Resolve and require the complete exact current terminal IMP Result Set."""

        references = {str(item["reference"]) for item in state["subjects"]}
        matches: list[list[dict[str, Any]]] = []
        service = LifecycleQueryService(self.project_root)
        for requirement in service.list_requirements():
            if not requirement.lineage_head or requirement.revision_state == "abandoned":
                continue
            projection = service.inspect_requirement(requirement.reference)
            if state["scope"]["reference"] not in {node.reference for node in projection.nodes}:
                continue
            current_claims = [
                claim
                for claim in projection.current_claims
                if claim.completed
            ]
            full = {
                str(item["result_reference"])
                for claim in current_claims
                for item in claim.results
            }
            if full != references:
                continue
            rows: list[dict[str, Any]] = []
            for claim in current_claims:
                for result in claim.results:
                    reference = str(result.get("result_reference"))
                    if reference not in full:
                        continue
                    rows.append(
                        {
                            "reference": reference,
                            "result_digest": result["result_digest"],
                            "binding_lineage": claim.binding_lineage,
                            "attempt": str(claim.attempt),
                        }
                    )
            if {row["reference"] for row in rows} == full:
                matches.append(rows)
        require(
            len(matches) == 1,
            "VFY_SUBJECT_NOT_CURRENT",
            "Candidate Subject Set must equal one complete current terminal IMP Result Set",
            details={"candidate_count": len(matches), "candidate_subjects": sorted(references)},
        )
        return {"subjects": sorted(matches[0], key=lambda item: item["reference"])}

    def _compile_for_persistence(self, candidate: Mapping[str, Any]) -> dict[str, Any]:
        if candidate.get("authority_compiled") is True:
            assert_candidate_authority(self.project_root, candidate)
            return deepcopy(dict(candidate))
        return compile_candidate(
            self.project_root,
            _candidate_input_references(candidate),
            candidate,
        )

    def create(
        self,
        candidate: Mapping[str, Any],
        *,
        persist: bool,
        run_automated: bool = True,
        allow_commands: bool = False,
        finalize: bool = False,
        confirmation: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        source = self._compile_for_persistence(candidate) if persist else candidate
        state = build_state(source)
        current_snapshot = self._current_subject_snapshot(state) if persist else None
        verify_state(state, finalizing=False, current_subject_snapshot=current_snapshot)
        generation: int | None = None
        allocated_reference: str | None = None
        try:
            if persist:
                state, generation = create_revision(self.project_root, state)
                allocated_reference = state["artifact"]["reference"]
            if run_automated:
                state = self.run_state(
                    state,
                    method_ids=None,
                    allow_commands=allow_commands,
                    automated_only=True,
                    current_subject_snapshot=current_snapshot,
                    finalize=finalize,
                    confirmation=confirmation,
                )["state"]
            else:
                state = apply_projection(
                    state, verify_state(state, finalizing=False), freeze=False
                )
            if persist:
                require(generation is not None, "VFY_CONTRACT_INVALID", "Store generation missing")
                current_snapshot = self._current_subject_snapshot(state)
                verify_state(
                    state,
                    finalizing=state["artifact"]["revision_state"] == "frozen",
                    current_subject_snapshot=current_snapshot,
                )
                open_state = deepcopy(state)
                should_freeze = open_state["artifact"]["revision_state"] == "frozen"
                if should_freeze:
                    open_state["artifact"]["revision_state"] = "open"
                state, generation = write_open_revision(
                    self.project_root,
                    open_state,
                    expected_generation=generation,
                )
                if should_freeze:
                    state = freeze_revision(self.project_root, state["artifact"]["reference"])
            return {"status": "created", "state": state, "store_generation": generation}
        except Exception:
            if persist and allocated_reference:
                try:
                    abandon_revision(
                        self.project_root,
                        allocated_reference,
                        "VFY create/first-write failed",
                    )
                except Exception:
                    pass
            raise

    def run_state(
        self,
        state: Mapping[str, Any],
        *,
        method_ids: list[str] | tuple[str, ...] | None,
        allow_commands: bool,
        automated_only: bool = False,
        manual_observations: Mapping[str, Mapping[str, Any]] | None = None,
        failure_returns: Mapping[str, Any] | None = None,
        early_stop_basis: Mapping[str, Any] | None = None,
        finalize: bool = False,
        confirmation: Mapping[str, Any] | None = None,
        current_subject_snapshot: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        output = deepcopy(dict(state))
        require(
            output["artifact"]["revision_state"] == "open",
            "VFY_METHOD_NOT_READY",
            "Only an open VFY Revision can run",
        )
        assert_subjects_still_current(tuple(output["subjects"]), current_subject_snapshot)
        method_index = {str(item["id"]): item for item in output["methods"]}
        result_index = method_result_index(output["method_results"])
        selected = list(method_index) if method_ids is None else list(method_ids)
        selected = list(dict.fromkeys(selected))
        require(
            all(item in method_index for item in selected),
            "VFY_METHOD_NOT_READY",
            "Selected Method does not exist",
            details={"selected": selected},
        )
        next_evidence = len(output["evidence"]) + 1
        executed: list[str] = []
        waiting: list[str] = []
        for method_id in selected:
            assert_subjects_still_current(tuple(output["subjects"]), current_subject_snapshot)
            method = method_index[method_id]
            current = result_index[method_id]
            if current["result"] != "pending":
                continue
            if automated_only and method["execution_mode"] != "automated":
                waiting.append(method_id)
                continue
            observation = (manual_observations or {}).get(method_id)
            try:
                result, evidence = execute_method(
                    method,
                    project_root=self.project_root,
                    evidence_sequence=next_evidence,
                    allow_commands=allow_commands,
                    manual_observation=observation,
                )
            except VfyError as exc:
                if exc.status == "action_required":
                    waiting.append(method_id)
                    continue
                raise
            assert_subjects_still_current(tuple(output["subjects"]), current_subject_snapshot)
            next_evidence += 1
            output["evidence"].append(evidence)
            position = next(
                index
                for index, item in enumerate(output["method_results"])
                if item["method_id"] == method_id
            )
            output["method_results"][position] = result
            result_index[method_id] = result
            executed.append(method_id)

        _attach_failure_returns(output, failure_returns)
        _refresh_conclusions(output)
        if early_stop_basis is not None:
            output["early_stop"] = True
            output["early_stop_basis"] = deepcopy(dict(early_stop_basis))
            references = list(early_stop_basis.get("return_references", []))
            for item in output["method_results"]:
                if item["result"] == "pending":
                    item["actual_result"] = (
                        "Not executed because a verified failure checkpoint requires upstream rework"
                    )
                    item["return_references"] = list(references)
            _refresh_conclusions(output)
        if finalize:
            output["final_confirmation"] = _final_confirmation(
                self.project_root, output, confirmation
            )
        projection = verify_state(
            output,
            finalizing=finalize,
            current_subject_snapshot=current_subject_snapshot,
        )
        output = apply_projection(output, projection, freeze=finalize)
        reject_secrets(output)
        return {
            "status": "finalized" if finalize else "updated",
            "state": output,
            "executed_methods": executed,
            "waiting_methods": waiting,
            "projection": projection,
        }

    def run(
        self,
        *,
        reference: str | None,
        state: Mapping[str, Any] | None,
        store_generation: int | None,
        persist: bool,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if persist:
            require(
                reference is not None or state is not None,
                "VFY_REFERENCE_REQUIRED",
                "Persistent run requires exact VFY Reference or state read with generation",
            )
        if state is None:
            require(reference is not None, "VFY_REFERENCE_REQUIRED", "run requires exact VFY Reference")
            state, generation = read_revision(self.project_root, reference)
        else:
            state = deepcopy(dict(state))
            generation = store_generation
        if persist:
            kwargs["current_subject_snapshot"] = self._current_subject_snapshot(state)
        result = self.run_state(state, **kwargs)
        if persist:
            require(
                generation is not None,
                "VFY_CONTRACT_INVALID",
                "Persistent run requires current Store generation",
            )
            current = self._current_subject_snapshot(result["state"])
            verify_state(
                result["state"],
                finalizing=result["state"]["artifact"]["revision_state"] == "frozen",
                current_subject_snapshot=current,
            )
            open_state = deepcopy(result["state"])
            should_freeze = open_state["artifact"]["revision_state"] == "frozen"
            if should_freeze:
                open_state["artifact"]["revision_state"] = "open"
            stored, generation = write_open_revision(
                self.project_root, open_state, expected_generation=generation
            )
            if should_freeze:
                stored = freeze_revision(self.project_root, stored["artifact"]["reference"])
            result["state"] = stored
            result["store_generation"] = generation
        return result

    def revise(
        self,
        old_state: Mapping[str, Any],
        candidate: Mapping[str, Any],
        *,
        persist: bool,
    ) -> dict[str, Any]:
        source = self._compile_for_persistence(candidate) if persist else candidate
        replacement = build_state(
            source,
            artifact_id=str(old_state["artifact"]["id"]),
            revision=int(old_state["artifact"]["revision"]) + 1,
            base_revision=int(old_state["artifact"]["revision"]),
        )
        if (
            state_contract_digest(old_state) == state_contract_digest(replacement)
            and old_state.get("control_inputs") == replacement.get("control_inputs")
        ):
            return {"status": "NO_CHANGE", "state": deepcopy(dict(old_state))}
        if persist:
            verify_state(
                replacement,
                finalizing=False,
                current_subject_snapshot=self._current_subject_snapshot(replacement),
            )
            replacement["artifact"]["allocated"] = True
            replacement, generation = create_revision(
                self.project_root,
                replacement,
                base_revision=int(old_state["artifact"]["revision"]),
            )
            return {"status": "revised", "state": replacement, "store_generation": generation}
        return {"status": "revised", "state": replacement}

    def check(
        self,
        *,
        reference: str | None = None,
        state: Mapping[str, Any] | None = None,
        current_subject_snapshot: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        require(
            state is None,
            "VFY_REFERENCE_REQUIRED",
            "Production check requires exact persisted VFY Reference",
        )
        require(reference is not None, "VFY_REFERENCE_REQUIRED", "check requires exact VFY Reference")
        before = _workspace_digest(self.project_root)
        state, generation = read_revision(
            self.project_root,
            exact_artifact_reference(reference, "VFY"),
        )
        state_before = canonical_bytes(state)
        if current_subject_snapshot is None:
            current_subject_snapshot = self._current_subject_snapshot(state)
        projection = verify_state(
            state,
            finalizing=state["artifact"]["revision_state"] == "frozen",
            current_subject_snapshot=current_subject_snapshot,
        )
        require(
            state_before == canonical_bytes(state),
            "VFY_CHECK_MUTATED",
            "check mutated supplied VFY bytes",
        )
        after = _workspace_digest(self.project_root)
        require(
            before == after,
            "VFY_CHECK_MUTATED",
            "check changed Artifact Store or project bytes",
            details={"before": before, "after": after},
        )
        return {
            "status": "checked",
            "state": state,
            "store_generation": generation,
            "projection": projection,
            "workspace_digest": before,
        }

    def check_state_for_test(
        self,
        state: Mapping[str, Any],
        *,
        current_subject_snapshot: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Pure fixture helper; deliberately not exposed by the production CLI."""

        before = canonical_bytes(state)
        projection = verify_state(
            state,
            finalizing=state["artifact"]["revision_state"] == "frozen",
            current_subject_snapshot=current_subject_snapshot,
        )
        require(before == canonical_bytes(state), "VFY_CHECK_MUTATED", "fixture check mutated state")
        return {"status": "checked", "state": deepcopy(dict(state)), "projection": projection}

    def auto(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        state = payload.get("state")
        if state is None:
            return self.create(
                payload["candidate"],
                persist=bool(payload.get("persist", False)),
                run_automated=bool(payload.get("run_automated", True)),
                allow_commands=bool(payload.get("allow_commands", False)),
                finalize=bool(payload.get("finalize", False)),
                confirmation=payload.get("confirmation"),
            )
        if state["artifact"]["revision_state"] == "open":
            return self.run(
                reference=payload.get("reference"),
                state=state,
                store_generation=payload.get("store_generation"),
                persist=bool(payload.get("persist", False)),
                method_ids=payload.get("method_ids"),
                allow_commands=bool(payload.get("allow_commands", False)),
                automated_only=False,
                manual_observations=payload.get("manual_observations"),
                failure_returns=payload.get("failure_returns"),
                early_stop_basis=payload.get("early_stop_basis"),
                finalize=bool(payload.get("finalize", False)),
                confirmation=payload.get("confirmation"),
            )
        if payload.get("candidate") is not None:
            return self.revise(
                state,
                payload["candidate"],
                persist=bool(payload.get("persist", False)),
            )
        if payload.get("reference"):
            return self.check(reference=str(payload["reference"]))
        return self.check_state_for_test(state)

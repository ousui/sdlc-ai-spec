"""IMP state machine across the separate Claim, product and Artifact authorities."""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
from pathlib import Path

from packages.sdlc_artifact_store import (
    ArtifactStore, ArtifactStoreError, CanonicalRevisionPayload, ClaimReservation,
    ControlReservationError, NotFoundError, compute_sha256,
)
from packages.sdlc_artifact_store.catalog import ArtifactCatalog
from packages.sdlc_claim_provider import AcquireRequest, ClaimConflictError, ClaimProvider
from packages.sdlc_phasekit import refs, subject_digest
from packages.sdlc_runtime import RESULT_CONTRACT, validate_result

from imp_binding import discover_binding, resolve_binding
from imp_builder import ImpBuilder, final_confirmation_from_payload
from imp_candidate import (
    candidate_members, persisted_candidate_records, resolve_candidate_material,
    restore_declared_baselines, verify_replayed_candidates,
)
from imp_common import ImpError, canonical, exact_base, require, resolve_owner
from imp_executor import (
    execute, execute_checks, operation_digest, preflight, readback_evidence,
    validate_execution_history,
)
from imp_method import validate_method, validate_stable_identities
from imp_readiness import (
    claim_identity, current_result, provider_read_only, resolve_request,
    validate_chain, verify_claim_snapshot,
)
from imp_result import (
    capture, changed_paths, changed_scope, member, read_state, registry,
    snapshot_from_member, snapshot_reference,
)
from imp_recovery import recovery_evidence, recovery_method, verify_candidate_resources
from imp_verifier import ImpVerifier


class ImpHandler:
    def __init__(self, project_root, *, clock=None):
        self.root = Path(project_root).resolve()
        self.clock = clock
        self.builder = ImpBuilder(self.root)
        self.verifier = ImpVerifier(self.root)

    def _result(self, invocation, *, stored=None, claim=None, build=None, ok=False,
                status="action_required", errors=(), warnings=(), action=None):
        artifact = None
        info = {"code": "IMP_EXECUTION_STATE", "message": "IMP 当前实施状态", "vfy_ready": False}
        if claim:
            info.update(binding=claim.binding_reference, owner=claim.owner,
                        attempt=claim.attempt, claim_state=claim.state, scope=list(claim.execution_scope))
        if stored:
            control = stored.control
            artifact = {
                "id": control.artifact_id, "type": "IMP", "revision": control.revision,
                "revision_state": control.state, "artifact_status": stored.payload.artifact_status,
                "reference": f"{control.artifact_id}@{control.revision}",
            }
            state = read_state(stored)
            info.update(
                context=state["binding"]["context_reference"],
                baseline=[row["baseline_reference"] for row in state["resources"]],
                approach=[step["purpose"] for step in state["method"]["steps"]],
                changed_scope=[token for row in state["resources"] for token in row["changed_scope"]],
                results=[row["result_reference"] for row in state["resources"]],
            )
            info["vfy_ready"] = bool(ok and claim and claim.state == "completed" and control.state == "frozen")
        if build:
            info["subject_digest"] = build.subject_digest
            info["final_confirmation_bindings"] = dict(
                build.final_confirmation_bindings
            )
        return validate_result({
            "contract": RESULT_CONTRACT, "operation": invocation["operation"], "ok": ok,
            "status": status, "artifact": artifact,
            "gate": {"result": build.gate_result if build else "pending",
                     "failed_checks": list(build.failed_checks) if build else []},
            "open_items": list(build.open_items) if build else [],
            "warnings": [info, *warnings], "errors": list(errors),
            "next_action": action,
        })

    def _error(self, invocation, exc, *, stored=None, claim=None):
        code = "IMP_RESOURCE_CONFLICT" if isinstance(exc, ClaimConflictError) else getattr(exc, "code", "IMP_READINESS_FAILED")
        return self._result(
            invocation, stored=stored, claim=claim, status=getattr(exc, "status", "blocked"),
            errors=[{"code": code, "message": str(exc), "details": getattr(exc, "details", {})}],
            action={"code": getattr(exc, "action", code), "message": str(exc),
                    "requires_user": True, "command": None},
        )

    @contextmanager
    def _lock(self):
        # Serialization protects journal/readback ordering, not Claim Authority.
        # All execution rights are still checked against the public Provider.
        runtime = self.root / ".sdlc"
        require(runtime.is_dir() and not runtime.is_symlink(), "IMP_SCOPE_VIOLATION",
                "Runtime state must remain inside Project Root")
        lock = runtime / "imp-runtime.lock"
        require(not lock.is_symlink(), "IMP_SCOPE_VIOLATION", "Runtime lock cannot be a symlink")
        with lock.open("a+b") as handle:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ImpError("IMP_CLAIM_CONFLICT", "Another IMP operation is materializing this project") from exc
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _selection(self, invocation, store):
        inputs = invocation["inputs"]
        reference = invocation.get("artifact_reference")
        provider = provider_read_only(self.root)
        by_reference = None
        if reference:
            artifact, revision = exact_base(reference, "IMP")
            by_reference = provider.resolve_artifact(artifact) if provider else None
            require(by_reference is not None and by_reference.revision == revision,
                    "IMP_BINDING_MISMATCH", "Reference must match the Current Attempt's exact IMP Revision")
        requested = inputs.get("binding") or (by_reference.binding_reference if by_reference else None)
        binding = resolve_binding(store, requested) if requested else discover_binding(store)
        current = provider.resolve(binding.reference) if provider else None
        if by_reference:
            require(current == by_reference, "IMP_BINDING_MISMATCH", "Binding and IMP Reference belong to different Claims")
        previous = None
        if current:
            try:
                previous = store.read_revision(current.artifact_id, current.revision)
            except (NotFoundError, ControlReservationError):
                require(current.state == "active", "IMP_RESULT_INCOMPLETE", "A terminal Claim has no readable Artifact")
        return binding, current, previous

    def auto(self, invocation):
        try:
            store = ArtifactStore.open_read_only(self.root)
            binding, current, _ = self._selection(invocation, store)
            selected = deepcopy(invocation)
            selected["inputs"]["binding"] = binding.reference
            selected["operation"] = "revise" if current else "create"
            if current:
                selected["artifact_reference"] = f"{current.artifact_id}@{current.revision}"
            return self._mutate(selected)
        except Exception as exc:
            selected = {**invocation, "operation": "check" if invocation.get("artifact_reference") else "create"}
            return self._error(selected, exc)

    def _prepare(self, invocation):
        store = ArtifactStore.open_read_only(self.root)
        binding, current, previous = self._selection(invocation, store)
        if invocation["operation"] == "create":
            require(not invocation.get("artifact_reference"), "IMP_BINDING_MISMATCH", "create does not accept --reference")
        else:
            require(invocation.get("artifact_reference") and current, "IMP_BINDING_MISMATCH",
                    "revise requires the exact Current IMP Reference")
        inputs = invocation["inputs"]
        owner = resolve_owner(inputs.get("owner"))
        recovering = bool(current and current.state in {"completed", "abandoned"} and previous
                          and f"{current.artifact_id}@{current.revision}" in
                          refs(inputs.get("input_references"), "input references"))
        state = ((self.verifier.verify_recovery_candidate(previous) if recovering else
                  self.verifier.verify_payload(previous)) if previous else None)
        if current and current.state == "active" and previous and previous.control.state == "frozen":
            require(current.owner == owner, "IMP_OWNER_MISMATCH", "Only the Current Claim Owner may complete")
            require(binding.reference == current.binding_reference, "IMP_BINDING_MISMATCH",
                    "Frozen recovery requires the same exact Binding")
            require(tuple(refs(inputs.get("input_references", state["request"]["input_references"]),
                               "input references")) == tuple(state["request"]["input_references"]),
                    "IMP_BINDING_MISMATCH", "Frozen recovery cannot change the Input Set")
            if "implementation" in inputs:
                require(canonical(validate_method(inputs["implementation"], binding)) == canonical(state["method"]),
                        "IMP_BINDING_MISMATCH", "Frozen recovery cannot change Implementation")
            verify_claim_snapshot(previous, state, current)
            # Dependency failure belongs to complete recovery. It must reach
            # that handler so the frozen history can be retained and released.
            return {"terminal": True, "binding": binding, "claim": current, "stored": previous}
        current, request, dependencies = resolve_request(store, binding, inputs, owner, previous=state)
        resume = current is not None and current.state == "active"
        done = current is not None and current.state == "completed" and (
            not request["rework"] or tuple(request["rework"]) == current.rework_references)
        if done or (resume and previous and previous.control.state == "frozen"):
            require(current.owner == owner, "IMP_OWNER_MISMATCH",
                    "Only the Current Claim Owner may reuse a completed execution")
            if "implementation" in inputs:
                require(state is not None and canonical(validate_method(inputs["implementation"], binding)) == canonical(state["method"]),
                        "IMP_BINDING_MISMATCH", "Frozen implementation cannot be rewritten without legal Rework")
            return {"terminal": True, "binding": binding, "claim": current, "stored": previous}
        candidate = (recovery_method(store, request["control_recovery"], inputs.get("implementation"))
                     if request.get("control_recovery") else
                     inputs.get("implementation", state["method"] if state and resume else None))
        method = validate_method(candidate, binding)
        if state:
            validate_stable_identities(state["method"], method)
        roots = registry(self.root, method.get("resources"), binding)
        observed_snapshots = {
            resource: capture(self.root / relative, resource)
            for resource, relative in roots.items()
        }
        candidates, snapshots, candidate_owned, candidate_restore = resolve_candidate_material(
            inputs.get("candidate_material"), binding, self.root, roots, observed_snapshots,
            stored=previous, state=state,
        )
        if request.get("control_recovery"):
            require(not candidates, "IMP_CONTROL_RECOVERY_INVALID",
                    "Control Recovery cannot also introduce Candidate Material")
            verify_candidate_resources(
                store, request["control_recovery"], binding, roots, observed_snapshots,
            )
        completed, owned = (), set()
        sources = [(stored, data) for _, stored, data in dependencies]
        if state and state["stage"] == "executed":
            sources.append((previous, state))
        for source_stored, source_state in sources:
            for row in source_state["resources"]:
                resource = row["resource"]
                if resource not in roots:
                    continue
                require(row["root"] == roots[resource], "IMP_BINDING_MISMATCH",
                        "A canonical Resource ID cannot be remapped to another root")
                expected = snapshot_reference(store, row["result_reference"], resource, local=source_stored)
                if observed_snapshots[resource] == expected:
                    owned.update((resource, path) for path in row["changed_paths"])
        owned.update(candidate_owned)
        for resource in roots:
            source = self._baseline_source(store, dependencies, resource)
            if source:
                baseline = snapshots[resource]
                if resume and state:
                    retained = next(row for row in state["resources"] if row["resource"] == resource)
                    require(retained["baseline_reference"] == source, "IMP_DEPENDENCY_INCOMPLETE",
                            "Retained Baseline no longer names the Current predecessor Result")
                    baseline = snapshot_from_member(previous, retained["baseline_member"], resource)
                require(snapshot_reference(store, source, resource) == baseline,
                        "IMP_BASELINE_UNRESOLVED", "Actual Baseline differs from the Current predecessor Result")
        if resume and state:
            require(roots == {row["resource"]: row["root"] for row in state["resources"]},
                    "IMP_BINDING_MISMATCH", "Resource roots cannot change during an active Attempt")
            completed = tuple(state.get("completed_operations", []))
            validate_execution_history(method, completed, state.get("actions"))
            for row in state["resources"]:
                expected = (snapshot_reference(store, row["result_reference"], row["resource"], local=previous)
                            if state["stage"] == "executed" else
                            snapshot_from_member(previous, row["baseline_member"], row["resource"]))
                observed = observed_snapshots[row["resource"]]
                retained_candidate = candidates.get(row["resource"])
                require(observed == expected or (
                            state["stage"] == "prepared" and retained_candidate
                            and observed == retained_candidate["candidate"]
                        ), "IMP_BASELINE_UNRESOLVED",
                        "Workspace differs from this Attempt's last readback; preserve the scene and resolve or abandon",
                        status="action_required")
                owned.update((row["resource"], path) for path in row["changed_paths"])
        planned = preflight(self.root, binding, method, roots, snapshots, completed=completed, owned=owned)
        require(resume or planned or request.get("control_recovery"), "IMP_READINESS_FAILED",
                "A new Attempt requires implementation from its declared Baseline, not a pre-existing candidate Result")
        return dict(terminal=False, store=store, binding=binding, claim=current, stored=previous,
                    previous_state=state, owner=owner, request=request, dependencies=dependencies,
                    method=method, roots=roots, snapshots=snapshots,
                    observed_snapshots=observed_snapshots, candidates=candidates,
                    candidate_restore=candidate_restore, planned=planned)

    def _authorization(self, invocation, prepared):
        policy = invocation["options"].get("write_policy", "auto")
        require(policy in {"auto", "confirm", "deny"}, "IMP_READINESS_FAILED", "Unknown write_policy")
        digest = subject_digest(
            {key: prepared[key] for key in (
                "method", "roots", "snapshots", "candidates", "request", "owner",
            )},
            {"project_root": str(self.root), "binding": prepared["binding"].to_dict(),
             "claim": claim_identity(prepared["claim"]) if prepared["claim"] else None},
        )
        if invocation["options"].get("dry_run") or policy == "deny":
            return self._result(
                invocation, claim=prepared["claim"], warnings=[{
                    "code": "IMP_PREVIEW", "message": "Readiness 与 Method Preview 完成，未执行任何项目写入",
                    "binding": prepared["binding"].reference, "owner": prepared["owner"],
                    "scope": list(prepared["binding"].execution_scope),
                    "baseline": prepared["snapshots"], "approach": prepared["method"]["steps"],
                }],
                action={"code": "IMP_WRITE_DENIED", "message": "当前策略只允许预览和只读检查",
                        "requires_user": True, "command": None},
            )
        if policy == "confirm" and prepared["planned"]:
            valid = any(item.get("kind") == "product_write" and item.get("decision") == "approved"
                        and item.get("subject_digest") == digest for item in invocation["confirmations"])
            if not valid:
                return self._result(
                    invocation, claim=prepared["claim"],
                    warnings=[{"code": "IMP_PRODUCT_CONFIRMATION", "message": "首次产品写入需要确认",
                               "subject_digest": digest, "binding": prepared["binding"].reference,
                               "scope": list(prepared["binding"].execution_scope),
                               "baseline": {key: compute_sha256(canonical(value)) for key, value in prepared["snapshots"].items()},
                               "approach": [step["purpose"] for step in prepared["method"]["steps"]]}],
                    action={"code": "CONFIRM_IMP_PRODUCT_WRITE", "message": "确认准确 Binding、Baseline、Method 和 Scope 内的产品修改",
                            "requires_user": True, "command": None},
                )
        return None

    def create(self, invocation):
        return self._mutate(invocation)

    def revise(self, invocation):
        return self._mutate(invocation)

    def _mutate(self, invocation):
        prepared = None
        try:
            prepared = self._prepare(invocation)
            if prepared["terminal"]:
                if prepared["claim"].state == "completed":
                    return self._check(invocation, prepared["binding"], prepared["claim"], prepared["stored"])
                if invocation["options"].get("write_policy") == "deny" or invocation["options"].get("dry_run"):
                    return self._check(invocation, prepared["binding"], prepared["claim"], prepared["stored"])
                with self._lock():
                    return self._complete(invocation, prepared["binding"], prepared["claim"], prepared["stored"])
            authorization = self._authorization(invocation, prepared)
            if authorization:
                return authorization
            with self._lock():
                # Repeat the same pure preparation after serialization, then
                # recheck the confirmation against that exact current Baseline.
                prepared = self._prepare(invocation)
                if prepared["terminal"]:
                    return self._complete(invocation, prepared["binding"], prepared["claim"], prepared["stored"])
                authorization = self._authorization(invocation, prepared)
                if authorization:
                    return authorization
                return self._implement(invocation, prepared)
        except Exception as exc:
            return self._error(invocation, exc)

    def _provider(self):
        return ClaimProvider.open_read_write(self.root, clock=self.clock)

    def _reserve(self, store, claim, previous=None):
        reservation = ClaimReservation(claim.binding_lineage, str(claim.attempt), claim.owner)
        store.allocate_artifact("IMP", external_artifact_id=claim.artifact_id, claim=reservation)
        base = previous.control.revision if previous and previous.control.state == "frozen" and previous.control.revision < claim.revision else None
        return store.allocate_revision(claim.artifact_id, external_revision=claim.revision,
                                       claim=reservation, base_revision=base)

    def _persist(self, store, control, claim, state, members, final=None):
        build = self.builder.build(artifact_id=control.artifact_id, revision=control.revision,
                                   state=state, members=members, final_confirmation=final)
        payload = CanonicalRevisionPayload(
            control.artifact_id, "IMP", control.revision, build.status, build.raw_bytes,
            "text/markdown", compute_sha256(build.raw_bytes), build.members, build.manifest,
        )
        if control.materialized:
            existing = store.read_revision(control.artifact_id, control.revision)
            if existing.payload == payload:
                return existing, build
        store.write_open_revision(payload, expected_generation=control.generation)
        stored = store.read_revision(control.artifact_id, control.revision)
        state = self.verifier.verify_payload(stored)
        verify_claim_snapshot(stored, state, claim)
        return stored, build

    def _baseline_source(self, store, dependencies, resource):
        references = set()
        provider = provider_read_only(self.root)

        def visit(dep):
            _, _, state = dep
            match = next((row for row in state["resources"] if row["resource"] == resource), None)
            if match:
                references.add(match["result_reference"])
                return
            for reference in state["request"]["dependencies"]:
                stored, parent = current_result(store, provider, reference)
                visit((reference, stored, parent))

        for dependency in dependencies:
            visit(dependency)
        require(len(references) <= 1, "IMP_DEPENDENCY_INCOMPLETE",
                "Resource has multiple unordered predecessor Results", action="RETURN_TO_PLAN")
        return next(iter(references), None)

    def _initial_state(self, prepared, claim):
        reference = f"{claim.artifact_id}@{claim.revision}"
        prior = prepared["previous_state"] or {}
        if not prior and prepared["request"].get("control_recovery"):
            artifact, revision = exact_base(prepared["request"]["control_recovery"], "IMP")
            prior = read_state(prepared["store"].read_revision(artifact, revision))
        old_ids = {row["resource"]: row["id"] for row in prior.get("resources", [])}
        historical_by_resource = {}
        historical_by_id = {}
        for control in ArtifactCatalog(prepared["store"]).list_revisions(
            claim.artifact_id
        ):
            if control.revision >= claim.revision or not control.materialized:
                continue
            history = read_state(
                prepared["store"].read_revision(
                    claim.artifact_id, control.revision
                )
            )
            for row in history.get("resources", []):
                resource, identity = row.get("resource"), row.get("id")
                require(
                    isinstance(resource, str)
                    and isinstance(identity, str)
                    and identity.startswith("RES-")
                    and identity[4:].isdigit(),
                    "IMP_BINDING_MISMATCH",
                    "Historical Result identity is invalid",
                )
                require(
                    historical_by_resource.setdefault(resource, identity)
                    == identity
                    and historical_by_id.setdefault(identity, resource)
                    == resource,
                    "IMP_BINDING_MISMATCH",
                    "Historical Result identity was repurposed",
                )
        require(
            all(historical_by_resource.get(resource, identity) == identity
                for resource, identity in old_ids.items()),
            "IMP_BINDING_MISMATCH",
            "Previous Result identity disagrees with Artifact history",
        )
        sequence = max(
            (int(value[4:]) for value in historical_by_id), default=0
        )
        records, members = [], []
        for resource, relative in prepared["roots"].items():
            identity = old_ids.get(resource)
            if identity is None:
                sequence += 1
                identity = f"RES-{sequence:03d}"
            observed = capture(self.root / relative, resource)
            require(observed == prepared["observed_snapshots"][resource],
                    "IMP_BASELINE_UNRESOLVED",
                    "Workspace changed between Candidate admission and acquisition")
            baseline = prepared["snapshots"][resource]
            baseline_id = "BASE-" + identity
            source = self._baseline_source(prepared["store"], prepared["dependencies"], resource)
            if source:
                require(snapshot_reference(prepared["store"], source, resource) == baseline,
                        "IMP_BASELINE_UNRESOLVED", "Actual Baseline differs from the Current predecessor Result")
            baseline_ref = source or f"{reference}/{baseline_id}" if baseline["existed"] else "N/A"
            records.append({
                "id": identity, "resource": resource, "root": relative,
                "baseline_member": baseline_id, "baseline_reference": baseline_ref,
                "change_member": "CHANGE-" + identity, "change_reference": "N/A",
                "result_member": "RESULT-" + identity, "result_reference": "N/A",
                "changed_paths": [], "changed_scope": [], "steps": [],
            })
            members.append(member(baseline_id, baseline, directory="snapshots"))
        persisted_candidates = persisted_candidate_records(
            prepared["candidates"], records,
        )
        members.extend(candidate_members(
            prepared["candidates"], persisted_candidates, member,
        ))
        state = {
            "contract": "sdlc-ai-spec/imp-state/v1", "stage": "prepared",
            "binding": prepared["binding"].to_dict(), "claim": claim_identity(claim),
            "request": prepared["request"], "method": prepared["method"],
            "resources": records, "completed_operations": [], "actions": [], "checks": [],
            "candidate_material": persisted_candidates,
            "pre_execution": None, "failure": None,
        }
        return state, members

    def _guard(self, claim, generation):
        provider = provider_read_only(self.root)
        current = provider.resolve(claim.binding_reference) if provider else None
        require(current == claim and current.state == "active", "IMP_CLAIM_CONFLICT", "Execution Claim changed")
        store = ArtifactStore.open_read_only(self.root)
        stored = store.read_revision(claim.artifact_id, claim.revision)
        require(stored.control.state == "open" and stored.control.generation == generation,
                "IMP_CLAIM_CONFLICT", "Pre-execution Revision changed")
        verify_claim_snapshot(stored, read_state(stored), claim)

    def _implement(self, invocation, prepared):
        provider = self._provider()
        request = prepared["request"]
        claim = provider.acquire(AcquireRequest(
            prepared["binding"].reference, prepared["owner"], prepared["binding"].execution_scope,
            tuple(request["dependencies"]), tuple(request["rework"]),
            invocation["inputs"].get("retry_abandoned") is True,
        ))
        require(claim.state == "active", "IMP_CLAIM_CONFLICT", "Acquisition did not grant an active Attempt")
        store = ArtifactStore.open_read_write(self.root)
        control = self._reserve(store, claim, prepared["stored"])
        if control.materialized:
            stored = store.read_revision(claim.artifact_id, claim.revision)
            state = self.verifier.verify_payload(stored)
            verify_claim_snapshot(stored, state, claim)
            if control.state == "frozen":
                return self._complete(invocation, prepared["binding"], claim, stored)
            state, members = deepcopy(state), list(stored.payload.members)
        else:
            try:
                state, members = self._initial_state(prepared, claim)
                stored, _ = self._persist(store, control, claim, state, members)
            except ArtifactStoreError:
                # Failed Store registration/materialization retains the exact
                # active Claim and reservation for a same-condition retry.
                raise
            except Exception as exc:
                reason = f"IMP preparation failed: {getattr(exc, 'code', type(exc).__name__)}"
                store.abandon_revision(claim.artifact_id, claim.revision, reason=reason)
                provider.abandon(claim.binding_lineage, attempt=claim.attempt, owner=claim.owner,
                                 artifact_id=claim.artifact_id, revision=claim.revision,
                                 generation=claim.generation, reason=reason)
                raise
        unchanged = canonical(state["method"]) == canonical(prepared["method"]) and state["stage"] == "executed"
        if not unchanged or prepared["planned"]:
            state["method"] = prepared["method"]
            state["stage"], state["checks"], state["failure"] = "prepared", [], None
            # Keep the original Baseline through active revisions.
            for row in state["resources"]:
                row["result_reference"] = row["change_reference"] = "N/A"
                row["changed_paths"], row["changed_scope"], row["steps"] = [], [], []
            state["pre_execution"] = None
            members = [item for item in members if item.member_id != "EVD-PRE"]
            stored, _ = self._persist(store, stored.control, claim, state, members)
            observed_at = (self.clock() if self.clock else datetime.now(timezone.utc))
            observed_at = observed_at.astimezone(timezone.utc).isoformat()
            pre, pre_record = readback_evidence(stored, state, observed_at)
            state["pre_execution"] = pre_record
            members = [item for item in stored.payload.members if item.member_id != "EVD-PRE"] + [pre]
            stored, _ = self._persist(store, stored.control, claim, state, members)
            if prepared["candidate_restore"]:
                # Restoring the declared Candidate to its immutable Baseline is
                # itself a product mutation.  The complete Checklist and its
                # Evidence must therefore be durable and read back first.
                restore_declared_baselines(
                    self.root, prepared["roots"], prepared["candidate_restore"],
                    guard=lambda: self._guard(claim, stored.control.generation),
                )
            validate_chain(prepared["store"], prepared["binding"], claim)
            if request.get("control_recovery"):
                self._guard(claim, stored.control.generation)
                observed = {resource: capture(self.root / relative, resource)
                            for resource, relative in prepared["roots"].items()}
                verify_candidate_resources(prepared["store"], request["control_recovery"],
                                           prepared["binding"], prepared["roots"], observed)
                members = [item for item in members if item.member_id != "EVD-RECOVERY"]
                members.append(member("EVD-RECOVERY", recovery_evidence(prepared["store"], state, observed)))
            after, applied = execute(
                self.root, prepared["binding"], prepared["planned"], prepared["roots"], prepared["snapshots"],
                guard=lambda: self._guard(claim, stored.control.generation),
            )
            verify_replayed_candidates(after, prepared["candidates"])
            state["completed_operations"] = list(dict.fromkeys((*state["completed_operations"], *applied)))
            state["actions"].extend(operation for operation, _ in prepared["planned"]
                                    if operation_digest(operation) in applied)
            members = [item for item in members if not item.member_id.startswith(("RESULT-", "CHANGE-", "EVD-CHK-"))]
            for row in state["resources"]:
                baseline = snapshot_from_member(stored, row["baseline_member"], row["resource"])
                paths = changed_paths(baseline, after[row["resource"]])
                row["changed_paths"] = paths
                row["changed_scope"] = changed_scope(row["resource"], paths, prepared["binding"].execution_scope)
                row["steps"] = sorted({op["step"] for op in state["actions"]
                                       if op["resource"] == row["resource"] and op["path"] in paths}) if paths else []
                if paths:
                    row["result_reference"] = f"{claim.artifact_id}@{claim.revision}/{row['result_member']}"
                    row["change_reference"] = f"{claim.artifact_id}@{claim.revision}/{row['change_member']}"
                    members.extend((
                        member(row["result_member"], after[row["resource"]], directory="snapshots"),
                        member(row["change_member"], {"resource": row["resource"], "changed_paths": paths}),
                    ))
                else:
                    row["result_reference"] = row["baseline_reference"]
                    row["change_reference"] = "N/A"
            local, evidence = execute_checks(
                self.root, state["method"], prepared["roots"], after,
            )
            require(all(capture(self.root / prepared["roots"][resource], resource) == snapshot
                        for resource, snapshot in after.items()),
                    "IMP_BASELINE_UNRESOLVED", "Workspace changed while local Checks were executing")
            state["checks"], state["stage"] = local, "executed"
            members.extend(evidence)
        final = invocation["inputs"].get("final_confirmation", state.get("final_confirmation"))
        stored, build = self._persist(store, stored.control, claim, state, members, final)
        if build.status in {"ready", "ready_with_exception"}:
            try:
                validate_chain(prepared["store"], prepared["binding"], claim)
            except ImpError as exc:
                self._abandon_open(store, provider, claim, str(exc))
                return self._error(invocation, exc, stored=stored, claim=provider.resolve(claim.binding_reference))
            store.freeze_revision(claim.artifact_id, claim.revision, verifier=self.verifier)
            frozen = store.read_revision(claim.artifact_id, claim.revision)
            return self._complete(invocation, prepared["binding"], claim, frozen)
        errors = ([{"code": "IMP_FINAL_CONFIRMATION_STALE", "message": "Final Confirmation does not bind the current Method, Result, Checks and Claim"}]
                  if final and not build.final_confirmation_valid else [])
        return self._result(
            invocation, stored=stored, claim=claim, build=build, errors=errors,
            status="failed" if build.gate_result == "fail" else "action_required",
            action={"code": "COMPLETE_IMP", "message": "补齐局部检查或确认当前实施结果",
                    "requires_user": True, "command": f"/sdlc-400-imp revise -r {claim.artifact_id}@{claim.revision}"},
        )

    def _complete(self, invocation, binding, claim, stored):
        require(stored is not None and stored.control.state == "frozen", "IMP_COMPLETE_FAILED",
                "Artifact must be frozen before Claim complete")
        self.verifier.verify_payload(stored)
        verify_claim_snapshot(stored, read_state(stored), claim)
        provider = self._provider()
        try:
            validate_chain(ArtifactStore.open_read_only(self.root), binding, claim)
            current = provider.complete(claim.binding_lineage, attempt=claim.attempt, owner=claim.owner,
                                        artifact_id=claim.artifact_id, revision=claim.revision,
                                        generation=claim.generation)
        except Exception as exc:
            latest = provider_read_only(self.root).resolve(binding.reference)
            if latest == claim and latest.state == "active":
                try:
                    validate_chain(ArtifactStore.open_read_only(self.root), binding, claim)
                except ImpError:
                    try:
                        latest = provider.abandon(claim.binding_lineage, attempt=claim.attempt, owner=claim.owner,
                                                  artifact_id=claim.artifact_id, revision=claim.revision,
                                                  generation=claim.generation)
                    except Exception as terminal_error:
                        return self._error(invocation, ImpError("IMP_COMPLETE_FAILED", f"{exc}; Claim termination failed: {terminal_error}"),
                                           stored=stored, claim=claim)
            return self._error(invocation, ImpError("IMP_COMPLETE_FAILED", f"Frozen Artifact retained; complete failed: {exc}"),
                               stored=stored, claim=latest)
        return self._check(invocation, binding, current, stored)

    def check(self, invocation):
        try:
            require(invocation.get("artifact_reference"), "IMP_BINDING_MISMATCH", "check requires --reference IMP@Revision")
            store = ArtifactStore.open_read_only(self.root)
            binding, claim, stored = self._selection(invocation, store)
            require(claim and stored, "IMP_RESULT_INCOMPLETE", "Exact IMP Revision is not materialized")
            require(binding.reference == claim.binding_reference, "IMP_BINDING_MISMATCH",
                    "Requested Binding differs from the Artifact Reference")
            if invocation["inputs"].get("owner") is not None:
                require(resolve_owner(invocation["inputs"]["owner"]) == claim.owner, "IMP_OWNER_MISMATCH", "Owner does not match Current Claim")
            return self._check(invocation, binding, claim, stored)
        except Exception as exc:
            return self._error(invocation, exc)

    def _check(self, invocation, binding, claim, stored):
        require(stored is not None, "IMP_RESULT_INCOMPLETE", "Exact Revision is not materialized")
        state = self.verifier.verify_payload(stored)
        verify_claim_snapshot(stored, state, claim)
        validate_chain(ArtifactStore.open_read_only(self.root), binding, claim)
        unsigned = self.builder.build(
            artifact_id=claim.artifact_id,
            revision=claim.revision,
            state=state,
            members=stored.payload.members,
            final_confirmation=None,
        )
        final = final_confirmation_from_payload(
            stored.payload.primary_blob, state, unsigned.subject_digest
        )
        build = self.builder.build(
            artifact_id=claim.artifact_id,
            revision=claim.revision,
            state=state,
            members=stored.payload.members,
            final_confirmation=final,
        )
        ok = stored.control.state == "frozen" and claim.state == "completed"
        return self._result(
            invocation, stored=stored, claim=claim, build=build, ok=ok,
            status="completed" if ok else "action_required",
            action={"code": "VFY_READY" if ok else "RESOLVE_IMP_STATE",
                    "message": "VFY ready：局部实施记录完整" if ok else "IMP 尚未同时满足 frozen Artifact 与 completed Claim",
                    "requires_user": not ok, "command": None},
        )

    def _abandon_open(self, store, provider, claim, reason):
        controls = ArtifactCatalog(ArtifactStore.open_read_only(self.root)).list_revisions(claim.artifact_id)
        control = next(item for item in controls if item.revision == claim.revision)
        if control.state == "open":
            store.abandon_revision(claim.artifact_id, claim.revision, reason=reason)
        else:
            require(control.state == "abandoned" and control.abandon_reason == reason,
                    "IMP_ABANDON_NOT_ALLOWED", "Only the matching abandoned Revision can resume Claim termination")
        return provider.abandon(claim.binding_lineage, attempt=claim.attempt, owner=claim.owner,
                                artifact_id=claim.artifact_id, revision=claim.revision,
                                generation=claim.generation, reason=reason)

    def abandon(self, invocation):
        try:
            require(invocation.get("artifact_reference"), "IMP_ABANDON_NOT_ALLOWED", "abandon requires an exact IMP Reference")
            store = ArtifactStore.open_read_only(self.root)
            binding, claim, stored = self._selection(invocation, store)
            owner = resolve_owner(invocation["inputs"].get("owner"))
            require(claim and claim.state == "active" and claim.owner == owner
                    and binding.reference == claim.binding_reference,
                    "IMP_ABANDON_NOT_ALLOWED", "Only the Owner of this exact active Claim may abandon")
            require(invocation["inputs"].get("expected_attempt", claim.attempt) == claim.attempt,
                    "IMP_ABANDON_NOT_ALLOWED", "Abandon Attempt CAS mismatch")
            require(not stored or stored.control.state in {"open", "abandoned"},
                    "IMP_ABANDON_NOT_ALLOWED", "Ordinary abandon cannot terminate a frozen Artifact")
            require(invocation["options"].get("write_policy", "auto") != "deny" and
                    not invocation["options"].get("dry_run"), "IMP_ABANDON_NOT_ALLOWED", "Write policy denies abandonment")
            reason = invocation["inputs"].get("abandon_reason") or "Explicit Owner abandonment"
            require(isinstance(reason, str) and reason.strip(), "IMP_ABANDON_NOT_ALLOWED", "Abandon reason is required")
            with self._lock():
                require(provider_read_only(self.root).resolve(binding.reference) == claim,
                        "IMP_ABANDON_NOT_ALLOWED", "Claim changed before abandonment")
                writer = ArtifactStore.open_read_write(self.root)
                self._reserve(writer, claim)
                current = self._abandon_open(writer, self._provider(), claim, reason)
                if stored:
                    stored = ArtifactStore.open_read_only(self.root).read_revision(claim.artifact_id, claim.revision)
                return self._result(invocation, stored=stored, claim=current, ok=True, status="completed")
        except Exception as exc:
            return self._error(invocation, exc)

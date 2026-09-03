"""Current dependency-chain and Rework validation before any IMP mutation."""
from __future__ import annotations

from dataclasses import asdict

from packages.sdlc_artifact_store.catalog import ArtifactCatalog
from packages.sdlc_claim_provider import ClaimNotFoundError, ClaimProvider, binding_lineage
from packages.sdlc_phasekit import refs
from packages.sdlc_phasekit.render import EVIDENCE_HEADERS
from packages.sdlc_runtime import ControlInputResolver, VFYReturnControlInput, parse_canonical_artifact
from packages.sdlc_runtime.canonical import require_single_table

from imp_binding import read_authority, resolve_binding
from imp_common import ImpError, base_ref, exact_base, require
from imp_result import read_member, read_state


def provider_read_only(root):
    try:
        return ClaimProvider.open_read_only(root)
    except ClaimNotFoundError:
        return None


def claim_identity(claim):
    return {key: value for key, value in asdict(claim).items() if key in {
        "binding_lineage", "binding_reference", "artifact_id", "revision", "attempt",
        "owner", "execution_scope", "dependency_results", "rework_references",
    }}


def verify_claim_snapshot(stored, state, claim):
    from imp_common import canonical
    require(canonical(state["claim"]) == canonical(claim_identity(claim)),
            "IMP_BINDING_MISMATCH", "Artifact Claim Snapshot differs from the Current Claim")
    reservation = stored.control.claim
    require(reservation is not None and (
        reservation.binding_lineage, reservation.attempt, reservation.owner,
        stored.control.artifact_id, stored.control.revision,
    ) == (claim.binding_lineage, str(claim.attempt), claim.owner, claim.artifact_id, claim.revision),
        "IMP_BINDING_MISMATCH", "Revision Reservation differs from the Current Claim")


def current_result(store, provider, reference, *, stack=()):
    artifact, revision = exact_base(reference, "IMP")
    require(provider is not None, "IMP_DEPENDENCY_INCOMPLETE", "Dependency Claim Store is missing")
    current = provider.resolve_artifact(artifact)
    require(current is not None and current.state == "completed" and current.revision == revision,
            "IMP_DEPENDENCY_INCOMPLETE", "Dependency is not its Current completed IMP Revision",
            details={"reference": reference})
    require(current.binding_lineage not in stack, "IMP_DEPENDENCY_INCOMPLETE", "Dependency Claim cycle")
    from imp_verifier import ImpVerifier
    stored = store.read_revision(artifact, revision)
    verifier = ImpVerifier(store.project_root)
    state = verifier.verify_payload(stored)
    require(stored.control.state == "frozen", "IMP_DEPENDENCY_INCOMPLETE", "Dependency Revision is not frozen")
    verify_claim_snapshot(stored, state, current)
    binding = resolve_binding(store, current.binding_reference)
    dependencies = resolve_dependencies(store, provider, binding, stack=(*stack, current.binding_lineage))
    expected = tuple(item[0] for item in dependencies)
    require(current.dependency_results == expected, "IMP_DEPENDENCY_INCOMPLETE",
            "Dependency Claim no longer matches its complete current upstream chain")
    front_inputs = parse_canonical_artifact(stored.payload.primary_blob).front_matter.get("inputs", [])
    require(set(expected).issubset(front_inputs), "IMP_DEPENDENCY_INCOMPLETE",
            "Successor inputs do not include the Current predecessor Results")
    return stored, state


def resolve_dependencies(store, provider, binding, *, stack=()):
    results = []
    for reference in binding.dependencies:
        require(provider is not None, "IMP_DEPENDENCY_INCOMPLETE", "Work Item dependency has not completed")
        claim = provider.resolve(reference)
        require(claim is not None and claim.state == "completed" and claim.binding_reference == reference,
                "IMP_DEPENDENCY_INCOMPLETE", "Every predecessor must match the exact Plan Revision and be completed")
        result = f"{claim.artifact_id}@{claim.revision}"
        stored, state = current_result(store, provider, result, stack=stack)
        results.append((result, stored, state))
    return results


def _control_evidence(store, reference, *, seen=()):
    require(reference not in seen, "IMP_READINESS_FAILED", "Control Evidence contains a reference cycle")
    base = base_ref(reference)
    evidence_stored, parsed = read_authority(store, base)
    suffix = reference[len(base):]
    if suffix.startswith("/") and "#" not in suffix:
        return read_member(evidence_stored, suffix[1:])
    require(suffix.startswith("#"), "IMP_READINESS_FAILED", "Control Evidence requires an exact member or Evidence item")
    rows = require_single_table(parsed, EVIDENCE_HEADERS, "Control Evidence").rows
    matches = [row for row in rows if row["ID"] == suffix[1:]]
    require(len(matches) == 1, "IMP_READINESS_FAILED", "Control Evidence item is missing or ambiguous")
    row = matches[0]
    target = _control_evidence(store, row["Reference"], seen=(*seen, reference))
    require(row["Integrity or Digest"] == target.sha256, "IMP_READINESS_FAILED",
            "Control Evidence digest does not match its immutable source")
    return target


def _control_rework(store, reference, binding, current, *, subject_reference=None):
    require(current is not None, "IMP_BINDING_MISMATCH", "Rework requires an existing IMP Lineage")
    control = ControlInputResolver(store.project_root).resolve_for_phase(store, reference, "IMP")
    _, parsed = read_authority(store, control.artifact_reference)
    require(parsed.front_matter.get("context") == binding.context_reference,
            "IMP_BINDING_MISMATCH", "Rework belongs to another Context")
    artifact, revision = exact_base(control.artifact_reference)
    require(not any(item.state == "frozen" and item.revision > revision
                    for item in ArtifactCatalog(store).list_revisions(artifact)),
            "IMP_BINDING_MISMATCH", "Rework is superseded by a later frozen control Revision")
    expected = subject_reference or f"{current.artifact_id}@{current.revision}"
    identity, source_revision = exact_base(expected, "IMP")
    require(identity == current.artifact_id and source_revision <= current.revision,
            "IMP_BINDING_MISMATCH", "Rework Subject must be an exact retained Result in this IMP Lineage")
    subject, _ = read_authority(store, expected)
    subject_state = read_state(subject)
    require(subject_state["binding"]["lineage"] == binding.lineage, "IMP_BINDING_MISMATCH",
            "Rework Subject belongs to another Binding Lineage")
    if isinstance(control, VFYReturnControlInput):
        require(binding_lineage(control.imp_binding_reference) == binding.lineage,
                "IMP_BINDING_MISMATCH", "VFY Return belongs to another IMP Lineage")
        require(expected in {base_ref(item) for item in control.subject_references},
                "IMP_BINDING_MISMATCH", "VFY Return does not refer to the Current IMP Result")
        require(control.imp_binding_reference in {binding.reference, subject_state["binding"]["reference"]},
                "IMP_BINDING_MISMATCH", "VFY Return has a stale Binding")
    else:
        sources = {base_ref(item) for item in control.source_references if item.startswith("IMP-")}
        require(sources == {expected}, "IMP_BINDING_MISMATCH",
                "RLS Issue cannot be uniquely traced to the Current IMP Result", action="RETURN_TO_PLAN")
        conclusions = [row.get("Release Conclusion") or row.get("Conclusion") or row.get("Value")
                       for table in parsed.tables for row in table.rows
                       if "Release Conclusion" in row or "Conclusion" in row or row.get("Field") == "Release Conclusion"]
        require(len(conclusions) == 1 and conclusions[0] in {"failed", "partial", "cancelled"},
                "IMP_BINDING_MISMATCH", "RLS Issue requires a failed, partial or cancelled Release Conclusion")
    require(expected in refs(parsed.front_matter.get("inputs"), "control inputs"),
            "IMP_BINDING_MISMATCH", "Control Artifact inputs do not trace the Current IMP")
    for evidence in control.evidence_references:
        _control_evidence(store, evidence)
    return control, expected


def resolve_request(store, binding, inputs, owner, *, previous=None):
    provider = provider_read_only(store.project_root)
    current = provider.resolve(binding.reference) if provider else None
    if current and current.state == "active":
        require(current.owner == owner, "IMP_OWNER_MISMATCH", "Only the Current active Claim Owner may resume")
        require(current.binding_reference == binding.reference, "IMP_BINDING_MISMATCH",
                "The active Claim uses a different exact Binding")
    dependencies = resolve_dependencies(store, provider, binding)
    dependency_refs = tuple(item[0] for item in dependencies)
    supplied = inputs.get("input_references")
    if supplied is None and previous and current and (current.state == "active" or
            (current.state == "abandoned" and inputs.get("retry_abandoned") is True)):
        supplied = previous["request"]["input_references"]
    references = refs(supplied, "input references")
    rework, rework_subjects, recovery = [], {}, None
    for reference in references:
        if reference.startswith(("VFY-", "RLS-")):
            retained = (previous["request"].get("rework_subjects", {}).get(reference)
                        if previous and current and reference in current.rework_references else None)
            _, subject = _control_rework(store, reference, binding, current, subject_reference=retained)
            rework_subjects[reference] = subject
            rework.append(reference)
        elif reference == binding.reference and current and reference != current.binding_reference:
            rework.append(reference)
        elif reference.startswith("IMP-"):
            artifact, _ = exact_base(reference, "IMP")
            if current and artifact == current.artifact_id:
                from imp_recovery import resolve_recovery
                require(recovery is None, "IMP_CONTROL_RECOVERY_INVALID", "Only one exact recovery candidate is allowed")
                resolve_recovery(store, binding, current, reference, previous=previous)
                recovery = reference
                rework.append(reference)
            else:
                require(reference in dependency_refs, "IMP_BINDING_MISMATCH",
                        "Input is not an exact Current direct predecessor Result")
                if current and reference not in current.dependency_results:
                    rework.append(reference)
        elif reference in binding.basis_references:
            # Supporting upstream references cannot enlarge the Binding Scope.
            read_authority(store, base_ref(reference))
        else:
            raise ImpError("IMP_BINDING_MISMATCH", "Input is outside the exact Binding or Rework chain")
    if (current and current.binding_reference == binding.reference and current.dependency_results == dependency_refs
            and set(current.rework_references).issubset(references)):
        # References that started this sequence remain causal even after the
        # updated predecessor has become this Attempt's registered dependency.
        rework = list(dict.fromkeys((*rework, *current.rework_references)))
    if current and current.state == "active":
        if previous is not None:
            require(tuple(previous["request"]["input_references"]) == references,
                    "IMP_BINDING_MISMATCH", "Active Input Set differs from the materialized request")
        require(current.execution_scope == binding.execution_scope and
                current.dependency_results == dependency_refs and
                current.rework_references == tuple(sorted(set(rework))),
                "IMP_BINDING_MISMATCH", "Active Binding, Scope, Dependency or Rework mismatch")
    elif current and current.state in {"completed", "abandoned"}:
        changed = set(dependency_refs) - set(current.dependency_results)
        if current.binding_reference != binding.reference:
            changed.add(binding.reference)
        require(changed.issubset(rework), "IMP_BINDING_MISMATCH",
                "Rework must include every changed Binding and predecessor Result")
        if current.state == "abandoned" and inputs.get("retry_abandoned") is True:
            require(not changed and current.execution_scope == binding.execution_scope,
                    "IMP_BINDING_MISMATCH",
                    "Retry cannot replace the Binding, Dependency or Scope set")
            if not rework:
                rework = list(current.rework_references)
        if current.state == "abandoned":
            normalized_rework = tuple(sorted(set(rework)))
            same_sequence = (
                not changed
                and current.execution_scope == binding.execution_scope
                and normalized_rework == current.rework_references
            )
            if inputs.get("retry_abandoned") is True:
                require(same_sequence, "IMP_BINDING_MISMATCH",
                        "Abandoned retry must preserve the exact Rework sequence")
            else:
                require(normalized_rework and not same_sequence,
                        "IMP_BINDING_MISMATCH",
                        "Abandoned Claim sequence requires explicit retry",
                        status="action_required")
    request = {
        "input_references": list(references),
        "dependencies": list(dependency_refs),
        "rework": sorted(set(rework)),
        "rework_subjects": rework_subjects,
        "artifact_inputs": list(dict.fromkeys((
            binding.upstream_reference, *dependency_refs,
            *(base_ref(item) for item in references if item not in {binding.reference, recovery}),
        ))),
    }
    if recovery:
        require(not rework_subjects, "IMP_CONTROL_RECOVERY_INVALID",
                "A product Return or Issue requires execution, not no-change recovery")
        request["control_recovery"] = recovery
    return current, request, dependencies


def validate_chain(store, binding, claim):
    provider = provider_read_only(store.project_root)
    dependencies = resolve_dependencies(store, provider, binding)
    require(tuple(item[0] for item in dependencies) == claim.dependency_results,
            "IMP_DEPENDENCY_INCOMPLETE", "Dependency Chain changed after acquisition")
    return dependencies

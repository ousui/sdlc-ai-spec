# IMP → VFY Interface Contract

## 1. Current Integration Binding

| Dimension | Binding |
|---|---|
| Git physical base | `main@3a2f13082fe2f661081ded74e45f860da2046bd1` |
| Integrated main tree | `a5b0898738d749db9238f13f8bedb471a251ee6b` |
| Semantic IMP implementation subject | `207a4a16bea8979faee0474cc43cb642cef1f655` |
| IMP delivery checkpoint | `impl/imp-v2@86aaa04a0238d3151606073e89219eea0d60b7d3` |
| IMP delivery tree | `a5b0898738d749db9238f13f8bedb471a251ee6b` |
| VFY implementation parent | `design/sdlc-500-vfy-goal@<DESIGN_HEAD_SHA>` |
| VFY PR base | `main` |

The equal trees prove delivery-content equivalence; they do not make the two
commit identities interchangeable.

## 2. Delivery Scope

VFY accepts one complete authoritative Delivery Scope:

1. exact frozen PLN Revision and all its Work Items when PLN is `required`;
2. otherwise one exact complete REQ or DSN Revision plus the authoritative
   PLN disposition/Exception;
3. an already-aggregated exact complete scope when multiple full scopes are
   delivered together.

VFY cannot select part of a Work Item Set, merge candidates, or use a branch
diff as scope.

## 3. Frozen IMP input chain

For every `Target Phase=IMP` Work Item, VFY resolves:

```text
PLN WI Reference
→ Binding Lineage
→ Current Attempt
→ Claim state=completed
→ frozen IMP Artifact Revision
→ immutable Result Member(s)
→ Product Resource Result(s)
→ result digest and cumulative changed scope
→ dependency result references
```

All elements must agree on Context, scope, owner/attempt, frozen revision and
dependency closure. A completed Claim whose artifact/result is absent, open,
abandoned, malformed or stale is not a Subject.

## 4. Object distinctions

### IMP Artifact Reference

`IMP-...@N` names a whole exact frozen canonical revision. It is an Artifact
input and contains binding/result metadata. It does not alone identify every
product result.

### IMP Result Member Reference

`IMP-...@N/RES-*` names an immutable canonical member within that exact revision.
It is the precise record for one or more Resource Results.

### Product Resource Result

The product-level result contains:

- canonical Resource identifier;
- initial baseline locator/digest;
- exact terminal result locator/digest;
- cumulative changed scope from baseline to terminal state;
- execution approach references and Evidence;
- Binding Lineage, Attempt and frozen IMP Revision;
- dependency Result References.

It is a VFY Subject when exact, immutable and current.

### Claim Record

The Claim Provider owns Binding Lineage, Attempt, Owner and state. Only the
unique current terminal `completed` Claim is eligible. VFY reads its public
projection and never mutates or copies the Claim state machine.

### Lifecycle Projection

A read-only derived view of current stage/next action. It is not canonical
product evidence and cannot authorize a Subject.

### VFY Subject

A normalized immutable Product Resource Result or explicitly registered
immutable product-result locator that is included by the full Delivery Scope
and bound to the current completed IMP chain.

## 5. IMP Context and Resource Baseline

VFY carries the exact CTX reference from the current chain and verifies that all
Scope Sources and Subjects belong to it. For each Resource, baseline and terminal
result are immutable locators with digests. A no-change Resource remains an
input when the entire scoped Resource never changed; a Resource that changed in
any Attempt remains a Subject even when the final Attempt itself has no delta.

## 6. Current validity and stale Subject

A Subject is stale when any of these is true:

- its Claim is no longer the unique Current Attempt;
- current Claim state is not `completed`;
- its IMP Revision is no longer frozen/current for the Binding;
- a dependency has a newer current terminal Result not absorbed by this Result;
- scope source, baseline, result digest, cumulative changed scope or dependency
  references differ from the persisted pre-execution contract;
- an unresolved Return or product-correction RLS Issue was omitted;
- a branch/tag/symbolic selector was used rather than the exact locator.

Validity is checked on resolve, immediately before and after execution, before
freeze, and on `check`.

## 7. Evidence and digest

Each Method Result binds:

```text
Method ID + Target References + actual Subject References
+ environment/data + executor identity + observed result + time
+ command/procedure + immutable Supporting Member digest
```

A reused upstream Evidence item is admissible only when its exact Subject,
contract and observation remain independently reviewable. A digest mismatch,
missing environment/data/time, unverifiable human observation or changed Subject
invalidates reuse.

## 8. Return to IMP and other phases

A Return records exact Target/Method/Subject/Evidence and one owning phase.
For `return_imp`, additionally record:

- IMP Binding Reference and Binding Lineage;
- failed Product Resource Result;
- Current completed Attempt and frozen IMP Revision;
- observed gap and required outcome;
- all dependency result references relevant to the gap.

The Return Reference is immutable after the VFY revision freezes. IMP may accept
it as a Rework Reference, but acceptance and a new completed result are not
resolution.

## 9. Rework / Control Recovery

A later VFY revision:

1. includes the frozen prior Return or RLS Issue owner Revision as Control Input;
2. maps it in Method Obligation References;
3. resolves the new current terminal Subject and chain;
4. executes/reviews the required Method;
5. proves the required outcome using new Evidence;
6. marks the Return resolved in the later revision without altering history.

## 10. Authority exclusions

The following are routing or delivery metadata only and cannot select a Subject:

```text
branch | tag | latest | current | PR number | Draft PR head
| IMP delivery branch SHA | integrated-main SHA
```

Repository SHAs may bind implementation/evidence attestation, while product
Subjects remain exact product result objects in the Artifact Store.

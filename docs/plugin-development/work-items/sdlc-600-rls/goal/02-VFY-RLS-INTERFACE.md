# VFY → RLS Interface Contract

## 1. Frozen authority

The parallel design input is exactly
`design/sdlc-500-vfy-goal@ea49c1df955bc71ec1af84d6104f3cd801c73ea2`
(tree `f37bc0790b2fe589fe6b1f2e535f4ed929ed91f4`). It is read from the actual
remote Ref, not from historical PR prose. Branch names, tags, PR numbers, Draft
heads, `latest` and `current` are routing metadata and cannot identify a VFY
Artifact or Release Candidate.

## 2. Object distinctions

| Object | Meaning |
|---|---|
| VFY Artifact Revision | exact frozen `VFY-...@N` canonical record |
| VFY Scope | one complete upstream Delivery Scope |
| VFY Subject Set | current immutable Product Resource Results validated against IMP lineage |
| IMP Product Resource Result | resource baseline/result/digest/cumulative scope/dependency chain |
| VFY Method Result | actual method observation and immutable Evidence |
| Target Conclusion | purpose-compatible target aggregation |
| `CON-VER` / `CON-VAL` | independent verification and validation aggregates |
| VFY Product Conclusion | product pass/fail/waived/n/a, never inferred from Artifact status |
| VFY Artifact Status | record lifecycle status |
| VFY Artifact Gate | trustworthiness of the VFY record |
| VFY Return | immutable upstream gap and required outcome |
| early-stop | credible frozen failure record that is permanently not RLS-ready |
| RLS Applicability | required/n/a/waived/pending disposition |
| Release Candidate | normalized exact downstream input object |
| Release Result Set | exact Result References carried into one RLS Contract |

## 3. Acceptance predicate

RLS accepts input only when all are true:

1. exact VFY Revision is frozen;
2. Artifact Gate is downstream-usable (`pass|pass_with_exception`);
3. `early_stop=false`;
4. no required Method has an impermissible pending result;
5. all Target Conclusions are complete;
6. `CON-VER` and `CON-VAL` satisfy the RLS-entry condition;
7. Subject Set is current-valid;
8. the IMP Result chain remains current-valid;
9. no unresolved Return exists;
10. Scope and Release Result Set agree completely with the VFY Subject Set;
11. RLS Applicability is required, or n/a/waived has a legal no-effect disposition;
12. Evidence and Supporting Member closure resolves and digests match.

A VFY product fail enters RLS only under a current scoped Exception; the VFY
conclusion remains fail. Early-stop never enters RLS. RLS never changes Scope or
Result Set and never reruns complete VFY as a substitute for exact readback.

## 4. Stable internal object

Only `skills/sdlc-600-rls/scripts/rls_vfy_adapter.py` may parse provisional VFY
wire fields. Every other module receives:

```text
VfyReleaseCandidate(
  vfy_reference, scope_reference, subject_references, result_references,
  con_ver, con_val, product_result, artifact_status, artifact_gate,
  early_stop, unresolved_returns, rls_applicability,
  release_target_obligations, evidence_references, source_digest)
```

## 5. Assumption Ledger

| ID | Frozen VFY source | Provisional field | RLS mapping | Post-merge validation | Only module changed on mismatch | Blocks final Gate |
|---|---|---|---|---|---|---|
| PROVISIONAL_VFY_INTERFACE-A01 | DESIGN §4/12 | `reference` | `vfy_reference` | read exact final VFY projection | `rls_vfy_adapter.py` | yes |
| PROVISIONAL_VFY_INTERFACE-A02 | STATE dimensions | `revision_state=frozen` | readiness flag | compare final Store projection | adapter | yes |
| PROVISIONAL_VFY_INTERFACE-A03 | Architecture state | `scope_reference` | exact Scope | compare final VFY STATE schema | adapter | yes |
| PROVISIONAL_VFY_INTERFACE-A04 | IMP/VFY interface | `subjects[]` | Subject/Result Set | verify final Result Member references | adapter | yes |
| PROVISIONAL_VFY_INTERFACE-A05 | DESIGN §8 | `con_ver`,`con_val` | fixed conclusions | compare final enum and purpose projection | adapter | yes |
| PROVISIONAL_VFY_INTERFACE-A06 | STATE dimensions | `product_result` | product outcome | compare final lifecycle projection | adapter | yes |
| PROVISIONAL_VFY_INTERFACE-A07 | STATE normal guard | `artifact_gate` | downstream record Gate | compare final verifier output | adapter | yes |
| PROVISIONAL_VFY_INTERFACE-A08 | early-stop guard | `early_stop` | hard RLS rejection | execute final early-stop fixture | adapter | yes |
| PROVISIONAL_VFY_INTERFACE-A09 | Return contract | `unresolved_returns[]` | RLS prohibition | resolve final Return projection | adapter | yes |
| PROVISIONAL_VFY_INTERFACE-A10 | Lifecycle table | `rls_applicability` | required/n/a/waived/pending | compare final lifecycle query | adapter | yes |
| PROVISIONAL_VFY_INTERFACE-A11 | VFY RLS obligations | `release_target_obligations[]` | RCF source obligations | compare final Method/Target/Exception members | adapter | yes |
| PROVISIONAL_VFY_INTERFACE-A12 | Evidence contract | `evidence_references[]` and closure flag | closure references | verify final Supporting Manifest | adapter | yes |

Every row is provisional until VFY is merged, the delta review is complete and
all final fixtures are produced by the real VFY Runtime.

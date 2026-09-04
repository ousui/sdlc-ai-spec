# VFY State Machine

## State dimensions

VFY has independent dimensions:

1. Artifact revision control: absent / open / frozen / abandoned;
2. Artifact status: draft / waiting_input / failed / ready / ready_with_exception;
3. product result: pending / pass / fail / waived / n/a;
4. Artifact Gate: pending / pass / pass_with_exception / fail;
5. RLS readiness: false / true.

No dimension may be inferred from another.

## States and transitions

| State | Entry | Permitted transitions | RLS |
|---|---|---|---|
| no VFY | no complete matching VFY | create after one complete scope | no |
| open / waiting_input | scope allocated; required method contract/input not executable | run, revise-in-place for contract input, abandon | no |
| open / running | pre-execution readback complete; selected method active | result pass/fail/pending, failed | no |
| open / failed | executor/store/domain error prevents trustworthy finalization | corrective run/rewrite of open revision, abandon | no |
| frozen / product pass | all required dimensions terminal; gate pass; current subject | revise on new subject/control, no-change check | according to RLS applicability |
| frozen / product fail | failure/evidence/return complete; gate pass | upstream rework then new VFY revision | no |
| frozen / early-stop | immutable fail; attribution fixed; remainder pending and mapped | upstream rework then new VFY revision | never |
| frozen / unresolved return | prior/current Return not proven resolved | new subject/control revision | no |
| revised due to new subject | frozen base plus changed exact current Subject Set | open waiting/running, then frozen/abandoned | no while open |
| revised due to return/issue | frozen Control Input added | open waiting/running, then frozen/abandoned | no while open |
| no-change | normalized scope/subject/control binding equals frozen base | no write; return exact existing reference | unchanged |
| abandoned reservation | allocation cannot safely materialize or explicit safe abandon | new independent create/revise attempt | no |

## Method execution transitions

```text
required/pending
  → automated running → pass|fail|pending(error/timeout)
  → manual action_required → pass|fail only with real evidence
  → hybrid partial → action_required → pass|fail with combined evidence
embedded → pass|fail after independent evidence review
n/a     → n/a only with authority basis
waived  → waived only with valid Exception
```

A Method's Disposition never becomes `pending` to represent unexecuted work.
Its Result is pending.

## Aggregation

For each compatible Target dimension:

```text
any fail      => fail
else pending  => pending
else waived   => waived
else pass     => pass
else all n/a  => n/a
```

`CON-VER` and `CON-VAL` independently aggregate their Target projections.

## Normal freeze guard

All of these must be true:

- exact current Subject Set and dependency chain;
- complete Target and Method obligation coverage;
- no required Method Result, Target or fixed conclusion pending;
- valid Evidence and Supporting Member closure;
- accurate Return attribution/resolution;
- current Final Confirmation;
- VFY-G-001..008 pass or allowed pass_with_exception.

## Early-stop freeze guard

Additionally:

- at least one necessary current-subject Method has immutable sufficient fail Evidence;
- unresolved facts cannot reverse the fail or change Return phase/lineage;
- all remaining required Method Results stay pending and cite the fail/Return;
- open items that affect validity/attribution remain open and therefore block freeze;
- lifecycle explicitly records `early_stop=true`, `rls_ready=false`;
- no output says product pass, accepted, releasable or RLS-ready.

## Product fail / Artifact pass example

```text
Method Result     = fail
Target Conclusion = fail
CON-VER           = fail
Artifact Status   = ready
Artifact Gate     = pass
RLS readiness     = false
Next action       = RETURN_TO_IMP
```

The Gate pass means the failure record is accurate and actionable.

## Read-only invariant

For `check`, before/after digests of the Store, project tree, untracked files,
HEAD and refs are identical. A missing Store or malformed bytes returns a stable
error and creates nothing.

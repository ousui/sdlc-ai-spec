# VFY Design Handoff

## Frozen preparation baseline

```text
Repository                  = ousui/sdlc-ai-spec
BASE_MAIN_SHA               = 3a2f13082fe2f661081ded74e45f860da2046bd1
BASE_MAIN_TREE              = a5b0898738d749db9238f13f8bedb471a251ee6b
IMP_IMPLEMENTATION_SUBJECT  = 207a4a16bea8979faee0474cc43cb642cef1f655
IMP_DELIVERY_SHA            = 86aaa04a0238d3151606073e89219eea0d60b7d3
IMP_DELIVERY_TREE           = a5b0898738d749db9238f13f8bedb471a251ee6b
IMP_INTEGRATION_MODE        = TREE_EQUIVALENT
OLD_VFY_REF                 = a12382c2d0f0dc6ca54021b4fec26d5874eb169f
```

Formal IMP inputs:

- `docs/plugin-development/work-items/sdlc-400-imp/evidence/207a4a16bea8979faee0474cc43cb642cef1f655/impl-imp-v2-handoff.md`
- `docs/plugin-development/work-items/sdlc-400-imp/evidence/207a4a16bea8979faee0474cc43cb642cef1f655/impl-imp-v2-final-result.json`
- `docs/plugin-development/work-items/sdlc-400-imp/evidence/207a4a16bea8979faee0474cc43cb642cef1f655/impl-imp-v2-repository.sha256`

## Current Integration Binding

```text
Git physical base          = current main
Semantic IMP subject       = 207a4a16bea8979faee0474cc43cb642cef1f655
IMP delivery checkpoint    = 86aaa04a0238d3151606073e89219eea0d60b7d3
VFY implementation parent  = this design branch final head
VFY PR base                = main
```

## Design result

- stable v1.1 VFY requirements preserved;
- all Blocker and Major design findings closed;
- architecture, state machine and exact interface contract complete;
- `VFY-E001..VFY-E080` mapped 80/80;
- one local validation entry point and two report schemas defined;
- local Codex Goal and independent Web Review prompts complete.

## Implementation authorization and boundary

The initiating Maintainer work order explicitly authorizes the initial
implementation after this design commit. Create `impl/vfy-v2` from this design
head, not from the old placeholder, IMP branch, implementation subject or
historical branches.

The initial Web-created implementation is not closed-loop Evidence. Its status is:

```text
LOCAL_VALIDATION_REQUIRED
```

No Evidence commit may be created until local exact-SHA validation actually
passes. No PR is merged and RLS does not start.

## Merge and ancestry rule

The design Draft PR must be merged first using **Create a merge commit**.
Squash/rebase are forbidden. Keep the implementation branch's existing ancestry;
do not rebase it after design merge. GitHub should naturally remove the shared
design commit from the implementation PR diff.

## Next executor

Run `goal/09-LOCAL-CODEX-GOAL.md` in local Codex `/goal`, then review its output
with `goal/10-WEB-REPORT-REVIEW.md`.

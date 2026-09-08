# SDLC v2 structured runtime implementation

## Authority and baseline

- Baseline: `main@f25ed518f662c0ac7306c94f845297f5642c44b2` (read and confirmed from GitHub).
- Approved design: user-reviewed `sdlc-v2-detailed-design.zip`, design dated 2026-09-09, including DESIGN.md, DATABASE.md, schema-model.sql, ACCEPTANCE.md and HANDOFF.md.
- Current user explicitly authorizes implementation, testing, two additional complex-demand rounds, commits, pushes and PR progress within this work package. This supersedes the older per-session single-stage stop rule for this package only.
- Do not merge main, tag or publish a release. Preserve the baseline and use this isolated branch.

## Checkpoints

1. A: normative contracts, initialization, CTX, structured SQLite model and diagnostic entry.
2. B: REQ / DSN / PLN domain commands and projections.
3. C: IMP / VFY execution evidence, findings and convergence.
4. D: RLS local delivery, assets, snapshot/copy/return and baseline evolution.
5. E: replace superseded runtime/tests/manifests and validate installed-copy behavior.
6. Baseline closure against the recorded projects in ousui/test-sdlc.
7. Complex round 1: evidence-backed requirements selected after reading project records.
8. Complex round 2: additional requirements and repair/regression as needed.

## Evidence boundaries

- Local schema or deterministic fixture PASS is not actual host Skill execution PASS.
- Record exact source commit and the commands/exit codes/files used for each result.
- Product repositories are disposable verification workspaces. No product deployment, product remote writes or credential exposure.
- Read retained test-sdlc project requirements before selecting scenarios.
- Do not mark the user's core acceptance met until actual Skill-guided REQ -> DSN -> PLN -> IMP -> VFY -> RLS on those projects has run and evidence is retained.

## Current progress

- Design package is accessible locally; main baseline and root engineering instructions read.
- Implementation branch created.
- The execution container cannot resolve github.com; GitHub connector reads/writes work. Networked execution/download alternatives are being checked.
- No v2 runtime code or product verification has yet passed. No existing code/tests have been deleted.

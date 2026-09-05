# RLS-WEB-003 propagation repair — Client handoff

RLS_REPAIR_CLOSED_LOOP = PASS (local exact-Subject validation and evidence)
RLS_CLOSED_LOOP = PASS (local exact-Subject validation and evidence)
WEB_RLS_REVIEW = REQUIRED
PR_MERGED = NO
REAL_TARGET_EFFECTS = 0

- Repair source: `ac0c3a8abbb975b8f1d7b4b630a5a902e4603759` / tree `4bca19ff957415cacc8a427678cfbddd528fa768`.
- B: `f171118380535d8c27a1929d0ef061510f82305f`; ordered parents=[`46509eb6688df30e71ed094132b2d10e81ceb2ac`, `644218e02876c5649fd87cfca12e1876d3b3b8bf`], all three Trees equal.
- D: `c9615cec2da3b39949a3fdd8be32396eae6db3aa`; sole parent=B.
- S3: `b790af812cd8d317675d264583711aed59e1460c`; tree `817bb68a30c4179fc11e0235a82dec55e200bda8`; sole parent=D.
- E3: the commit containing this handoff, with sole parent=S3; its full SHA is recorded in the final PR #10 readback and the external delivery package publication receipt. A commit cannot embed its own SHA.

New source consists of 85 selectively migrated paths. S1/E1/S2/E2/provisional/repair histories are excluded from S3 ancestry; historical objects are independently restored from the local bundle. No old Evidence was migrated into S3.

Actual verification: 74/74 propagation+redaction; 46/46 confirmation+batch+real Store; 12/12 independent probes at repair source and S3; RLS 87/87; strict VFY 80/80 including real OS containment for E041/E046; RLS private 435/435; repository 1068/1068; Web repair 120/120 (64+56); Source Lock 14; A01..A12; VFY/RLS installed independence; independent effect checks. All five profiles and new detached exact-S3 fresh attest passed, with zero required-suite skips or expected failures.

Both fixed projects completed real CTX→REQ→DSN→PLN→IMP→VFY→RLS in local disposable copies. File bytes/modes, HEAD/refs/status and .sdlc were restored; Sandbox targets, temporary directories and fresh-worktree registration were removed. These are lifecycle probes, not full product acceptance or actual human product approval.

Evidence: `../evidence/b790af812cd8d317675d264583711aed59e1460c/`. Its complete Manifest covers all archive files and this handoff, the independent-review prompt, and exact 26/27 source documents. Receipts bind the original final archived UTF-8 bytes; no sensitive-value context or unredacted raw duplicate is archived.

Only next work package: independent Web Review using 29-WEB-PROPAGATION-REVIEW.md. Keep PR #10 Draft; do not merge, alter main/VFY/B/D or PR #8/#7/#9, or sign Web ACCEPTED.

Precommit failure retention: the complete review package includes the checksummed precommit-probe-archives.tar.gz with both untouched first-probe output directories and initial harness. The final probes were re-executed after removing an extra print-generated newline; assertions, S3 and all formal profile logs were unchanged. See Evidence/precommit-discovery/ for the failed diff check, correction reason and byte Manifest.

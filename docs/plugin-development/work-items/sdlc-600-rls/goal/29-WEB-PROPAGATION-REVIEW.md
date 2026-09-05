# Independent Web Review — new RLS propagation S3/E3

Read actual origin/impl/rls-v2 and PR #10 head. Require S3=`b790af812cd8d317675d264583711aed59e1460c`, S3 sole parent D=`c9615cec2da3b39949a3fdd8be32396eae6db3aa`, E3 sole parent S3, preserved B=`f171118380535d8c27a1929d0ef061510f82305f` ordered parents [`46509eb6688df30e71ed094132b2d10e81ceb2ac`, `644218e02876c5649fd87cfca12e1876d3b3b8bf`] and Tree equality. Read the final publication receipt for exact E3; do not infer a head from historical PR body text.

Review all changed source and new Evidence independently. Reproduce the reopened review 5120883644 probes against exact S3, especially separate/equals password argument echoes, explicitly sensitive JSON plus bypass fields, cross-stream/timeout/error propagation, duplicate keys, original execution argv/environment, nested first writes and legal audit bindings. Use synthetic values only. Confirm v2 memory-only context does not invalidate already-bound nested receipts.

Obtain the byte-complete E3 Evidence/Handoff package and Git/source archives. Verify every Manifest entry and all top-level/nested receipts against stdout/stderr bytes, SHA-256, exact source SHA/tree, returned/persisted JSON and zero-skip real execution identities. Run `verify_evidence.py`; inspect its checks independently rather than accepting a claimed PASS. Required actual counts: RLS87, strict VFY80 with OS E041/E046, private435, repository1068, Web repair120=64+56, Store10, Source Lock14, interface A01..A12. Check both normal and detached fresh profiles, real external lifecycle artifacts and restoration/cleanup.

Scope limits remain explicit: no production/remote Target effect; the external projects are lifecycle integration probes, not product acceptance. No evidence proves a real-credential leak in E2; do not rewrite history or invent such a claim. #7/#9 are historical and need not be merged. Keep PR #10 Draft and leave PR #8/#7/#9, main/VFY/B/D and workflows unchanged.

Only independent review may set WEB_RLS_REVIEW=ACCEPTED or CHANGES_REQUIRED. This handoff grants no acceptance and authorizes no PR merge.

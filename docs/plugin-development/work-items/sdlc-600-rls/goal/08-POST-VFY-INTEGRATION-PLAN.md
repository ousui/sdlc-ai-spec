# Post-VFY Integration Plan

After VFY Web Review is accepted and `impl/vfy-v2` plus this design are merged to
`main` using merge commits, local Codex shall:

1. fetch and verify latest `origin/main` and integrated VFY Design/Runtime/Evidence/Handoff;
2. merge `origin/main` into `impl/rls-v2` with a merge commit; never rebase;
3. run `VFY_RLS_INTERFACE_DELTA_REVIEW` against every Assumption Ledger row;
4. treat final VFY as authority and adapt RLS, normally only in `rls_vfy_adapter.py`;
5. return to VFY only when its implementation violates approved Spec;
6. implement shared `packages/sdlc_lifecycle/query_rls.py` and `sdlc-status` integration;
7. freeze the final Source Lock and complete installed-boundary Runtime Independence;
8. run Fixed Eval 87/87 and the entire Fake Target matrix;
9. rerun all VFY gates, then full repository regression;
10. run both exact external projects through CTX→REQ→DSN→PLN→IMP→VFY→RLS;
11. use only local sandbox release targets and perform zero production/remote effect;
12. run fresh exact-SHA attestation, generate formal Evidence and update the Draft PR.

Every RLS result produced before this sequence is provisional and cannot support
final RLS PASS.

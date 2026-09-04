# IMP v2 Independent Design Review

- Review candidate: `ee5a2bbcbca8b5683fc6ce36ae7f3e1c91df5c7a`
- Direct parent: `9656b8b95b3ca182a96aa0960ef99161e43187c0`
- Frozen PLN baseline: `cff49f3fe265f102fc545bcf3c7f7515c035b2d6`
- Review mode: fresh, independent, read-only design and correctness review
- Skill: `karpathy-guidelines`

## Result

- Blocker: 0
- Major: 0
- Minor: 0
- Observation: 3
- External integration gate: PASS

The previous Major is closed. The IMP handler no longer manufactures a
`complete:<code>:<detail>` value. During the same `BEGIN IMMEDIATE` Claim
transition, the Provider re-runs the recursive dependency and complete frozen
IMP validation, rejects a still-completable frozen Claim, derives the failure
reason itself, and requires any supplied reason to match exactly before CAS.

Blank or non-canonical `owner`, `abandoned_by`, and `abandon_reason` values now
fail closed. Regression coverage includes forged failure rejection,
Provider-derived failure, idempotent terminal retry, mismatched reason
rejection, malformed persisted identity fields, and real IMP dependency
invalidation recovery.

## Verified gates on the exact candidate

- Checkpoint gates: 17/17 PASS
- Late foundations: 57/57 PASS
- IMP focused tests: 163/163 PASS
- Fixed IMP Eval: 259 tests PASS
- Critical Cases: 82/82 PASS
- Full regression gates: 20/20 PASS
- Full repository unittest discovery: 425 tests PASS
- Source Lock: PASS
- Runtime Independence: PASS
- `git diff --check`: PASS
- Worktree: clean

The review does not claim that SpringGear or gin-vue-admin external integration
has run; it only authorizes that next gate.

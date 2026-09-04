# IMP v2 Handoff

## Authoritative references

- main: `0c38135e3e8bdad0d60d674c93ad42078e880134`
- PLN: `cff49f3fe265f102fc545bcf3c7f7515c035b2d6`
- IMP: `207a4a16bea8979faee0474cc43cb642cef1f655`
- IMP parent: `cff49f3fe265f102fc545bcf3c7f7515c035b2d6`
- IMP Draft PR: https://github.com/ousui/sdlc-ai-spec/pull/5

## Verification

- Source Lock: PASS (16 contracts)
- Runtime Independence: PASS
- Fixed Eval Critical Cases: 82/82 PASS
- IMP Fixed Eval: 259 tests PASS
- Full regression: 426 tests PASS
- SpringGear: PASS at `e855096ff19dcdb303dc4250ba19c30acd743ac7`
- gin-vue-admin: PASS at `a6882210a80bb27e3aa5dff0b4c21aa4afe8988a`
- Independent Design Review: Blocker 0 / Major 0 / Minor 0
- Fresh exact-SHA attestation: 21/21 gates PASS
- Remote IMP unique parent: PASS
- main unchanged: PASS

## Next stage

`impl/vfy-v2`

Rules:

- Use formal IMP SHA `207a4a16bea8979faee0474cc43cb642cef1f655` as the only parent.
- Implement only `sdlc-500-vfy`.
- Do not enter RLS.
- Create an `impl/vfy-v2` to `impl/imp-v2` Draft PR.

GitHub Actions are not delivery authority for this handoff and were not awaited.

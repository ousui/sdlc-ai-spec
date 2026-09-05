# Post-integration Skill Conformance — Work Package

## Authority and scope

Maintainer request: re-analyse the stage-completion matrix after integration; repair suitable gaps on one new Web-owned branch, then hand off only work requiring a real Client. This package is an explicitly authorized cross-skill conformance repair, not a restart of accepted IMP/VFY/RLS implementations.

- Repository: `ousui/sdlc-ai-spec`
- Baseline main: `0289a5ee8d702450fb3f3bc73c89f30a11664bdb`
- Baseline tree: `bb1aa513fe9a67a6cbec0775a6570fae6e50f877`
- Tree-equivalent accepted RLS E3: `2db5b77288ea890f60ed7b07fc8e01b955ebaa13`
- Owned ref: `fix/post-integration-skill-conformance`
- Scope: seven Phase Skills and `sdlc-status`; build/source traceability, read-only status behavior, process documentation and per-skill Client evidence.

The branch is created directly from exact main. No historical side branch is merged or rebased. main, historical accepted subjects and their Evidence stay read-only. Connector reads confirmed only main existed at start and there were no open PRs.

## Reassessment rules

Directory presence is not semantic correctness. Missing optional `evals/` directories are not missing tests. Historical Eval Plans are design-time records, not live status. Installed-copy Python tests do not prove native Client discovery/invocation. A CTX Codex CLI report does not verify the other seven Skills or Codex Desktop. Different repository homepage metadata is not automatically wrong: deployment provenance must be recorded rather than silently changing the distribution target.

## Planned checkpoints

1. Reproduce the exact main tree from the uploaded byte-complete E3 bundle; run portable baseline checks. Review authoritative requirements and classify confirmed defects, documentation drift and unexecuted host certification separately.
2. Repair `sdlc-status` defects only when reproduced; add strict source traceability, fixed coverage and installed-copy verification without changing its read-only domain or calling sibling Skills.
3. Add a per-skill/per-surface compatibility ledger with explicit evidence scope; add automated guards preventing missing skills, invented Verified claims and missing evidence. Preserve prior signed-off phase artifacts.
4. Correct global Handoff and layout guidance; link immutable historical records rather than rewriting results. Supply one exact-source Client verification package and independent review procedure.
5. Run available portable checks, record actual results and limits, push normal fast-forward checkpoints and open a Draft PR to main. Stop; never merge.

## Allowed paths

- `docs/plugin-development/work-items/post-integration-conformance/**`
- `docs/plugin-development/work-items/sdlc-status/**` (additive review/evaluation records; original case expectations retained)
- `docs/plugin-development/HANDOFF.md`, `COMPATIBILITY.md` and additive structured compatibility data
- `AGENTS.md`, `skills/AGENTS.md`, `skills/README.md`, `docs/plugin-development/DEVELOPMENT.md` (clarify development-only eval placement, no lowered behavior requirements)
- `skills/sdlc-status/**`, `tests/skill_status/**`
- dedicated conformance/status tools and tests under `tools/**`, `tests/evals/**`, `tests/conformance/**`

## Forbidden

No modifications to `docs/v1.x/**`, accepted phase Evidence, `.github/**`, product repositories, shared ArtifactStore/schema internals or accepted Phase Runtime semantics. No Actions executor, credential installation, real release/deployment, new release assets or history rewriting. No placeholder PASS, no skipped/expected-failure test counted as success. Native Client behavior is NOT_RUN until direct installation, discovery, invocation and behavioral evidence exists for that exact Skill and surface.

## Current result

Planning checkpoint only. No new test PASS or independent final acceptance is claimed by this document. The user-visible final report and subsequent machine-readable checkpoint must name the tested source and distinguish runtime checks from native host certification.

# Repository instructions

This repository is the SDLC user-scoped Spec Kit core port. Product metadata is
in `plugin-metadata.json`; keep version `1.0.0-beta` during the debugging period.
The declared plugin repository is `https://github.com/goedgecloud/sdlc-ai-spec`
and the port author is Blade. Git transport may use a different authorized
working repository; never silently change the declared metadata or claim a
repository transfer from a metadata edit.

## Source and scope

- Read README.md, docs/DEVELOPMENT.md, docs/MIGRATION.md and upstream.lock.json.
- Before naming changes or upstream upgrades, also read docs/NAMING.md and
  docs/naming-map.json. Apply the approved context-specific product/Skill mapping
  in the generation layer, preserve raw upstream provenance, and update all
  callers together. Naming changes do not authorize behavior changes. An approved
  target name is not evidence that the runtime migration has shipped.
- Preserve the nine pinned upstream English commands and the documented path,
  name and packaging deltas. No translation, new process rules or legacy runtime.
- Project-only INIT is authorized and implemented by adapters/INIT.md plus the
  bundled stdlib initializer. Preserve existing project data; never install tools.
- GitHub integration, real-project execution and native client installation remain
  outside automated engineering verification. They require separate authority.
- Shared resources are read-only; project state belongs to `.sdlc`. Never infer
  the business project root from the plugin installation directory.
- Keep src/upstream byte-identical to the locked upstream. Edit adapters/ and tools/;
  regenerate derived source, the single dist package and root marketplaces. Never
  hand-edit generated wrappers, host fragments or shared workflow bodies.
- Preserve upstream copyright, license and provenance. Plugin authorship does not
  replace the original authorship of the copied Spec Kit source.
- Development/build/test/upgrade tooling outside `dist/` is uv-managed. Keep
  `pyproject.toml` and `uv.lock` synchronized, use `uv sync --locked` /
  `uv run --locked`, and do not reintroduce a requirements.txt dependency source.
  `dist/` must remain uv-independent at runtime.

## Verification and delivery

Verify the repository, branch, HEAD and worktree before writes. Preserve unrelated
user work. Commit/push only within the explicitly authorized branch. Do not merge,
retag, release, rewrite history or modify other branches without authorization.

Use tools/upgrade.py for detached upstream candidates; never overwrite the accepted
worktree during preparation or weaken comparisons to accept a new version.

Use the installed pinned upstream CLI only to produce independent empty-project
baselines. Never use migrated output as its own upstream oracle. Engineering
checks may use synthetic temporary directories, not business projects or LLMs.
Run the complete verifier, repository tests and `git diff --check`. CI is read-only
and reports the exact source SHA. Keep evidence outside the checkout and do not
replace raw evidence with a historical PASS statement.

A valid manifest is not native host compatibility, and engineering success is
not business acceptance. State the environment, source SHA, counts and unperformed
checks precisely. Keep docs current without adding a separate process platform.

Use the work package PR as the decision, implementation and verification record.
Keep its body current and append milestone comments with exact source SHAs,
actual tests, failures/corrections and unperformed checks. README and naming
contracts hold lasting definitions; do not create a duplicate progress platform.
Record actual Git author/committer separately from product authorship. Never
claim merge-readiness, native-host acceptance or business acceptance from a
naming-documentation check alone.

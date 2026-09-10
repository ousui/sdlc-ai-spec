# SDLC AI Spec — v1.0.0-beta

Author: **Blade**. Declared repository: **https://github.com/goedgecloud/sdlc-ai-spec**.
An independent, user-scoped source port of **Spec Kit by GitHub, Inc.**, MIT.
Upstream remains pinned to `v1.0.5`, commit
`a4e25ce6b96dc8e85f84206c6a54353fa9c5260b`.

## One package, three host entrypoints

Members install the prebuilt **dist/** package through a marketplace; they do not
run a build, install specify-cli or fetch upstream on installation. Root catalogs
for Codex, Claude Code and Cursor all select `./dist`. The package has one copy
of workflows, scripts and templates. Explicit native manifests select disjoint,
thin host entrypoints; those pass a literal host to a stdlib-only read-only text
binder. Business workflow content is shared without asking the model to guess
which host it is running in.

Ten skills: init (project bootstrap), constitution, specify, clarify, plan, tasks, analyze, checklist,
implement and converge. English instructions and substantive template content
remain upstream-derived. Project state belongs in `.sdlc`, never in the plugin.
Bash, Python 3.9+ and standard POSIX tools are runtime dependencies. No uv,
specify-cli, LLM API, MCP service or background process is required by the package.

**Project initialization is included.** Run the installed `sdlc-init` entry once
per project; repeat calls preserve existing work and complete compatible partial
state. It does not copy tools or create features. See
[Project initialization](docs/INITIALIZATION.md). There is no GitHub integration,
translation, new lifecycle or automatic project migration. Native installation
and model-driven behavior must be verified separately; see the small isolated
[smoke test](docs/SMOKE-TEST.md).

## Layout

```text
.agents/plugins/marketplace.json
.claude-plugin/marketplace.json
.cursor-plugin/marketplace.json
src/upstream/             Original, pinned source and renderer references
src/scripts/              Shared migrated runtime plus small local helpers
src/templates/            Derived template source
adapters/                Strict migration and host-binding rules
tools/                   Deterministic port, build, upgrade and comparison
tests/                   Synthetic engineering tests, not business acceptance
dist/                    Entire installed plugin boundary
  .codex-plugin/         Explicit Codex entrypoint selection
  .claude-plugin/        Explicit Claude entrypoint selection
  .cursor-plugin/        Explicit Cursor entrypoint selection
  adapters/<host>/skills/  Thin native wrappers (no copied business bodies)
  references/workflows/  One factored body per capability
  bindings/              Literal host differences generated at build time
  scripts/               One shared runtime
  templates/             One shared template collection
  BUILD.json             Deterministic source build identity
```

The native manifests deliberately replace the previous portable root manifest:
portable fixed skill discovery cannot select different host entrypoints. No
root/default `skills` directory is used inside dist, preventing duplicate scans.
The runtime loader only binds precompiled literal fragments; it does not compile
upstream, run a workflow or write state. Full output must be read before execution.

## Documentation

- [Project initialization and safe repeated calls](docs/INITIALIZATION.md)
- [Installation and beta cache handling](docs/INSTALLATION.md)
- [Build and independent engineering verification](docs/DEVELOPMENT.md)
- [Exact migration differences](docs/MIGRATION.md)
- [Controlled upstream upgrade candidates](docs/UPGRADING.md)
- [Verification boundaries](docs/VERIFICATION.md)
- [Codex/Cursor comparison project and requirement](docs/SMOKE-TEST.md)

The presently authorized working repository can differ from the declared product
address. Updating metadata is not a GitHub transfer. Install from an accessible
repository/ref containing this implementation, not an old default branch.

## Attribution

Original Spec Kit copyright and MIT terms remain in LICENSE and NOTICE; original
upstream files retain their attribution. Each package includes UPSTREAM.json.
This is not an official release of GitHub, OpenAI, Anthropic or Cursor.

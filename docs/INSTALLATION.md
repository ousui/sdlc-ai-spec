# Installation and fixed-beta updates

Product: `sdlc`, version `1.0.0-beta`, author Blade. Marketplace: `sdlc-ai-spec`.
Declared repository: https://github.com/goedgecloud/sdlc-ai-spec.
The working implementation is currently hosted on the explicitly authorized
`ousui/sdlc-ai-spec` branch `impl/spec-kit-plugin-v0`. A repository metadata field
is not a transfer. Use a repository/ref you can actually access; do not add its
old default branch and assume it contains this build.

## One installed package

All three repository-root marketplace catalogs point to `./dist`.
The package has three native manifests selecting `./adapters/<host>/skills/`.
There is deliberately no portable root `plugin.json` and no default `skills/`
inside dist: portable fixed discovery and Claude's additive default scan would
otherwise undermine disjoint host selection. Scripts, templates, and nine
workflow bodies are shared. Thin entrypoints retain native metadata and pass a
literal host to the read-only loader. No CLI install, build or download happens
when a member installs this package.

## Codex

Add the intended Git repository/ref or its local checkout using the client's
marketplace management UI. Its catalog is `.agents/plugins/marketplace.json`.
Find `sdlc` in marketplace `sdlc-ai-spec`, install at user scope, and start a new
session. Actual discoverable commands should include `$sdlc-specify` and
`$sdlc-plan`; use the command identifiers displayed by that client build.
Do not install the Codex IDE extension and call that native plugin verification.

## Claude Code

For a reproducible branch test, clone/check out the exact implementation commit,
then add that checkout as a local marketplace:

```text
/plugin marketplace add /absolute/path/to/sdlc-ai-spec
/plugin install sdlc@sdlc-ai-spec
```

Choose user scope. Native invocation is `/sdlc:sdlc-specify`, etc. After the desired
branch is available as the distribution source, adding its Git URL is also possible.
For direct session-only diagnosis: `claude --plugin-dir /absolute/path/to/checkout/dist`.

## Cursor

Team marketplace: Dashboard > Plugins > Add Marketplace > Import from Repo;
select the intended repository and ref, then find `sdlc` in Customize and install
at user scope. Team marketplace availability depends on plan and permissions.
For a local test independent of team-marketplace availability, copy the complete
`dist` package to a fresh `~/.cursor/plugins/local/sdlc` directory, reload the
window, and inspect Customize. Do not copy only the skills or merge files from a
previous beta into the same directory. Native invocation is `/sdlc-specify`.
Local loading is a documented diagnostic path, not proof that team distribution
was tested.

## Verify what is actually installed

The plugin must expose exactly nine intended skills, from this host's adapter.
Read the installed `UPSTREAM.json` and `BUILD.json`. `BUILD.json.build_id` identifies
source-derived bytes while the product version remains fixed. Record the source
commit, build_id, client version, model and loaded plugin directory for each test.
Never inspect only the checkout: test the installed cache copy.

Claude can skip updates when its explicit version string is unchanged. During
this fixed-beta period, do not assume Update picked up a new commit; use a fresh
installation or documented uninstall/reinstall/reload flow and verify build_id.
Do not automatically delete users' plugin caches or project `.sdlc` directories.

## Current stop point

INIT is still not implemented. Use only the isolated test fixture procedure in
[SMOKE-TEST.md](SMOKE-TEST.md) for the user's first workflow comparison. Installing
this package does not initialize arbitrary business projects. Native client
installation and model-driven behavior remain user verification tasks.

## Primary references

- OpenAI packaging and Codex compatibility paths: https://developers.openai.com/plugins/build/plugins
- Claude component paths, cache and versions: https://code.claude.com/docs/en/plugins-reference
- Claude marketplace sources: https://code.claude.com/docs/en/plugin-marketplaces
- Cursor native manifests and explicit discovery: https://cursor.com/docs/reference/plugins
- Cursor team and local installation: https://cursor.com/docs/plugins

Reviewed 2026-09-10. These references justify format choices, not an installed
client certification. Never put all host adapters under one default skill scan.

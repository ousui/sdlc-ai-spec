# Installation and fixed-beta updates

Product: **SDLC AI SPEC**, plugin ID `sdlc-ai-spec`, version `1.0.0-beta`, author Blade. Marketplace: `sdlc-ai-spec`.
Declared repository: https://github.com/goedgecloud/sdlc-ai-spec.
The working implementation is currently hosted on the explicitly authorized
`ousui/sdlc-ai-spec` branch `impl/spec-kit-plugin-v0`. A repository metadata field
is not a transfer. Use a repository/ref you can actually access; do not add its
old default branch and assume it contains this build.

## One installed package

All three repository-root marketplace catalogs point to `./dist`.
Nine shared core entries live in `dist/skills/`. Only INIT keeps three host-specific
wrappers because its previous invocation policies differ. Each host loads nine
shared cores plus its own INIT, never another host's INIT.

Codex and Cursor use `skills: ["./skills/", "./adapters/<host>/skills/"]`.
Claude automatically scans `skills/` and adds its custom `./adapters/claude/skills/`.
There is no portable root plugin.json. Do not separately install both the root
workspace and the dist package. Remove the old cached plugin version through the
host's normal uninstall/update UI rather than merging old folders into the new one.
Runtime dependencies remain Bash and Python 3.9+; installation does not build or
translate anything. Chinese is precompiled; template structure remains English.

## Codex

Add the intended Git repository/ref or its local checkout using the client's
marketplace management UI. Its catalog is `.agents/plugins/marketplace.json`.
Find `sdlc-ai-spec` in marketplace `sdlc-ai-spec`, install at user scope, and start a new
session. Actual discoverable commands should include `$sdlc-100-spec` and
`$sdlc-200-plan`; use the command identifiers displayed by that client build.
Do not install the Codex IDE extension and call that native plugin verification.

## Claude Code

For a reproducible branch test, clone/check out the exact implementation commit,
then add that checkout as a local marketplace:

```text
/plugin marketplace add /absolute/path/to/sdlc-ai-spec
/plugin install sdlc-ai-spec@sdlc-ai-spec
```

Choose user scope. Native invocation is `/sdlc-ai-spec:sdlc-100-spec`, etc. After the desired
branch is available as the distribution source, adding its Git URL is also possible.
For direct session-only diagnosis: `claude --plugin-dir /absolute/path/to/checkout/dist`.

## Cursor

Team marketplace: Dashboard > Plugins > Add Marketplace > Import from Repo;
select the intended repository and ref, then find `sdlc-ai-spec` in Customize and install
at user scope. Team marketplace availability depends on plan and permissions.
For a local test independent of team-marketplace availability, copy the complete
`dist` package to a fresh `~/.cursor/plugins/local/sdlc-ai-spec` directory, reload the
window, and inspect Customize. Do not copy only the skills or merge files from a
previous beta into the same directory. Native invocation is `/sdlc-100-spec`.
Local loading is a documented diagnostic path, not proof that team distribution
was tested.

## Verify what is actually installed

The plugin must expose exactly ten intended skills, from this host's adapter.
Read the installed `UPSTREAM.json` and `BUILD.json`. `BUILD.json.build_id` identifies
source-derived bytes while the product version remains fixed. Record the source
commit, build_id, client version, model and loaded plugin directory for each test.
Never inspect only the checkout: test the installed cache copy.

Claude can skip updates when its explicit version string is unchanged. During
this fixed-beta period, do not assume Update picked up a new commit; use a fresh
installation or documented uninstall/reinstall/reload flow and verify build_id.
Do not automatically delete users' plugin caches or project `.sdlc` directories.

## Current stop point

Project-only INIT is included. Run the installed `sdlc-000-init` once per selected
project; see [INITIALIZATION.md](INITIALIZATION.md). Existing compatible minimal
`.sdlc` data can be completed without deleting documents. Installing this package
does not itself initialize arbitrary business projects. Native INIT invocation
and model-driven behavior remain user verification tasks.

## Primary references

- OpenAI packaging and Codex compatibility paths: https://developers.openai.com/plugins/build/plugins
- Claude component paths, cache and versions: https://code.claude.com/docs/en/plugins-reference
- Claude marketplace sources: https://code.claude.com/docs/en/plugin-marketplaces
- Cursor native manifests and explicit discovery: https://cursor.com/docs/reference/plugins
- Cursor team and local installation: https://cursor.com/docs/plugins

Reviewed 2026-09-10. These references justify format choices, not an installed
client certification. Never put all host adapters under one default skill scan.

## Naming migration in PR #24

The plugin ID changed from `sdlc` to `sdlc-ai-spec`; display name is **SDLC AI SPEC**.
All ten entry directories and `SKILL.md.name` now use the numbered IDs in README.
The three native manifests still select their own adapters; this is not the
shared `dist/skills` redesign. Native metadata controls and literal host identity
are unchanged. `sdlc-status` is reserved, not an installed eleventh skill.

Treat the old and new IDs as different installations. Remove/disable the old
plugin via the client's normal management flow, install the new ID from the
intended exact source, then verify ten entries and the new build_id. Do not
combine both package trees or assume a fixed beta version invalidated caches.
No automatic cache removal or business-data migration is performed. Old public
command aliases are not advertised or installed. Existing documents are not
rewritten by installing/updating the plugin; historical command references in
user-authored overrides need deliberate review.

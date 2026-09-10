# v0 engineering handoff

Fixed repository: https://github.com/ousui/sdlc-ai-spec
Implementation branch: impl/spec-kit-plugin-v0
Upstream: v1.0.5 @ a4e25ce6b96dc8e85f84206c6a54353fa9c5260b

The current work package is the source port of nine core Skills plus three
host packages, with only engineering verification and synthetic fixtures.
Use the completed v0-engineering Actions run and its exact-source artifact for
results. Do not substitute the earlier baseline-only acquisition pass.

Read README.md, MIGRATION.md and upstream.lock.json. Core source is in src/;
build-time adaptations are in adapters/ and tools/. Dist packages are generated,
not three manually maintained workflows. Do not install the legacy repository-root
plugin as this implementation.

STOP before INIT: sdlc-init has not been implemented. The tests' synthetic project
seeding is a fixture, not an initialization product. Native host loading and
real-project behavior remain untested. Only after review of this engineering
stage should a separately scoped INIT work package be authorized.

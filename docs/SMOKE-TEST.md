# Small, comparable Codex / Cursor workflow test

## Project (fixed source; no feature implemented by this migration)

Use **golang/example/helloserver**, a standalone Go module with two files:
`server.go` (simple HTTP greetings and `/version`) and `go.mod` (`go 1.19`).
Its imports are standard library only. Pin the parent repository to:

`7f05d217867b2af52b0a28c6d1c91df97e1b5b39`

Sources:
- https://github.com/golang/example/tree/7f05d217867b2af52b0a28c6d1c91df97e1b5b39/helloserver
- https://github.com/golang/example/blob/7f05d217867b2af52b0a28c6d1c91df97e1b5b39/LICENSE

Use the SAME project, SHA and requirement in two independent directories, not two
different requirements. Otherwise host effects and task difficulty are confounded.
Do not run the upstream entire examples repository: only this isolated module.
The migration work does not run or modify this project; the user performs the test.

## Prepare disposable copies

Obtain the pinned example checkout outside the plugin repository:

```sh
git clone https://github.com/golang/example.git /tmp/sdlc-example-source
git -C /tmp/sdlc-example-source checkout --detach 7f05d217867b2af52b0a28c6d1c91df97e1b5b39
```

Choose two NEW directories that do not already contain user work. Copy the
`helloserver` folder to each and copy the source LICENSE and PATENTS into each
copy. Open one in Codex and the other in Cursor. Use Go 1.19 or newer, and record
`go version`. For offline testing use an already installed Go toolchain rather
than triggering a toolchain download.

Initialize using the installed plugin entry, not hand-written scaffolding:

- Codex: `$sdlc-000-init` (select the disposable helloserver directory explicitly).
- Cursor: `/sdlc-000-init` (or the exact name exposed by its plugin menu).
- Claude, when tested: `/sdlc-ai-spec:sdlc-000-init`.

Require a report of the selected project and created/preserved files. Reinvoke
once: the second result must be `unchanged`, with no file content or mtime changes.
No feature/spec or business changes should exist yet. If you previously used the
manual fixture setup or already started a requirement, rerun INIT to complete
missing compatible data; do not remove `.sdlc` or reset the existing feature.
See [INITIALIZATION.md](INITIALIZATION.md) for the file contract and failure cases.
Optional: create a local Git repository in a NEW disposable copy before starting;
INIT itself does not create or change repositories or branches. No remote writes.

## Fixed requirement (paste unchanged in both hosts)

> Add a health-check endpoint to this existing helloserver.
>
> GET /healthz must return HTTP 200, Content-Type application/json, and exactly
> {"status":"ok"} followed by one newline. The endpoint must not access network
> services, databases, files, or build information.
>
> Every method other than GET on exactly /healthz must return 405 with Allow: GET.
> /healthz/ must continue to use the pre-existing greeting behavior, not health.
> Preserve the current /, /<name>, /version, -g, and -addr behavior. Preserve HTML
> escaping in greetings. Do not add third-party packages or change the Go version.
>
> Add isolated tests with net/http/httptest, including GET, POST/HEAD 405, the
> /healthz/ boundary and regression checks for existing greetings. Tests must not
> bind a real TCP port or depend on Internet connectivity. It is acceptable to
> extract handler registration into a small function to test routing.
>
> Use the installed SDLC plugin. First produce the specification only and stop
> for review. Do not implement until I explicitly request implementation. Work
> only in this disposable project; do not commit/push, modify the plugin, install
> dependencies or enable other plugins. Report actual checks and unverified items.

## Run stages, deliberately checking stop behavior

| Step | Codex | Cursor |
| --- | --- | --- |
| Initialize project once | `$sdlc-000-init` | `/sdlc-000-init` |
| Establish minimal project principles | `$sdlc-010-rule` | `/sdlc-010-rule` |
| Paste the fixed requirement | `$sdlc-100-spec` | `/sdlc-100-spec` |
| Clarify only meaningful gaps | `$sdlc-110-clar` | `/sdlc-110-clar` |
| Technical design (stdlib net/http) | `$sdlc-200-plan` | `/sdlc-200-plan` |
| Generate tasks | `$sdlc-300-task` | `/sdlc-300-task` |
| Cross-document consistency | `$sdlc-310-xchk` | `/sdlc-310-xchk` |
| Requirements-quality checklist (review it before implementation) | `$sdlc-320-huma` | `/sdlc-320-huma` |
| Authorize implementation | `$sdlc-400-impl` | `/sdlc-400-impl` |
| Assess remaining gaps | `$sdlc-500-conv` | `/sdlc-500-conv` |

For constitution: keep standard-library-only Go, preserve existing behavior,
require isolated automated tests, and prohibit secrets/remote publication. Do not
invent extra team rules. Preserve the upstream reviewer-owned checklist semantics;
do not instruct implementation to check off its own review gate.

`go test ./...` and `go vet ./...` should pass after implementation. Initial tests
may be absent; report that instead of inventing baseline test coverage. A clean
`converge` report does not substitute for the actual test results.

## Record results independently

Record exact plugin commit/build_id, installed cache path, client version,
model/reasoning settings, number of intended skills discovered, whether the thin
entry loaded its COMPLETE workflow, questions/repeated questions, phase stop
behavior, .sdlc file paths, actual checks and final implementation diff.

Compare capability and acceptance outcomes, not prose SHA or runtime duration.
Do not transfer one host's generated spec/code to the other until the independent
comparison finishes. A later sequential handoff can be tested separately. Stop
and retain evidence if the loader is truncated, the wrong host entry appears, or
project paths point inside the installed plugin.

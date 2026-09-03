# sdlc-300-pln Runtime Contract

`PLN` converts complete frozen REQ/DSN scope authority into one immutable Plan
Artifact containing delivery scope, lifecycle applicability and stable `WI-NNN`
work-item bindings. It never stores live task status and never executes product
changes. `create` allocates only when authoritative PLN applicability is
`required`; `n/a`, `embedded`, `waived` and `pending` return without a Plan
Artifact. `check` is strictly read-only.

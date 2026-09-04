# Local Claim Provider Contract

Contract ID: `sdlc-ai-spec/runtime/imp-claim/v1`
Contract Version: `1`

`packages/sdlc_claim_provider` is the local execution authority for IMP Binding Lineages.
It owns Current Attempt, Owner, Resource Scope, stable IMP Artifact ID, exact target Revision Reservation and Claim State.
ArtifactStore remains the authority for Canonical Artifact bytes and does not grant execution rights.

Operations: `resolve`, `acquire`, `abandon`, `complete`.
The implementation owns namespaced `imp_claims` tables in the shared local
SQLite Artifact Store at `.sdlc/store.sqlite3`. It validates the Artifact Store
through its public API, manages only its own tables and transactions, fails
closed on malformed Schema, State or Current/Resource invariants, and does not
provide distributed leases or remote providers. It does not read or migrate a
legacy standalone Claim database.

Every Attempt records immutable `created_at`, mutable `updated_at` and an
integer `generation`. A newly acquired active Attempt starts at generation `0`;
one successful terminal transition atomically increments it to `1`. All stored
timestamps use valid RFC 3339 values and preserve creation/terminal ordering;
non-canonical stored sets, references or timestamps fail closed on read.

Scope and Dependency Result References are de-duplicated while preserving their
authoritative order. Rework References are a canonical sorted set: equivalent
orderings identify the same request and cannot allocate another Attempt.

`complete` and `abandon` use an active-state generation CAS and validate the
exact Lineage, Attempt, expected Owner, Artifact ID and Revision before both the
first transition and an idempotent terminal retry. A retry may present the
pre-transition or returned terminal generation, but no unrelated generation.
Before `complete`, the Provider re-reads the exact matching ArtifactStore
Reservation and independently verifies frozen Gate and Final Confirmation
Authority. Before ordinary `abandon`, it requires the exact Revision to be
already abandoned with the same reason. For a frozen finalization failure, the
Provider runs the exact completion checks in the same transition transaction;
only a Provider-observed failure may derive the authoritative
`complete:<code>:<detail>` reason, and an optional caller-supplied reason must
match it exactly. A still-completable frozen Claim cannot be abandoned.
`abandon` records `abandoned_by` separately from the expected Owner so an
authorized recovery caller can be audited without impersonating the blocked
Owner; an idempotent retry must preserve both Actor and Reason.

`open_read_only` only reads an existing, quiescent rollback-journal database.
It never initializes a Schema or creates a database, journal, WAL or SHM file.
WAL mode, journal sidecars and a database image changed during a query fail closed;
they are not repaired or silently read as an older checkpoint.
`initialize`, `acquire`, `complete` and `abandon` require the read-write API.

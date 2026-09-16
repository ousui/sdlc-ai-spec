# Upgrade semantic review checklist

Use this after deterministic `localize.py precheck` and before `localize.py record`.

For every changed source/translation pair, compare the complete new source to the complete proposed Chinese text. Check all applicable items:

- **Obligations:** every MUST / required / always / never obligation keeps the same force.
- **Prohibitions:** MUST NOT / do not / forbidden statements are not weakened or reversed.
- **Actors:** maintainer, reviewer, Agent, user, SPEC/CLAR/HUMA/IMPL/CONV and other owners remain attached to the same responsibility.
- **Conditions:** before/after/if/unless/only-when branches and fallback conditions are preserved.
- **Interaction:** ask/wait/stop/continue behavior, maximum question count and confirmation semantics are unchanged.
- **Writes:** files, directories and data that may or may not be written are unchanged.
- **Machine values:** statuses, severity, booleans, numeric limits, exit codes, command arguments and config/protocol values retain meaning.
- **Compatibility:** existing English inputs and approved Chinese aliases still map to the same outcome; no new alias is inferred silently.
- **Scope:** prose introduced upstream remains in scope only when the supported profile includes it; unsupported extension/event/preset behavior is not silently enabled.

Fail the review with `REVIEW_REQUIRED` when a high-impact meaning is ambiguous, when a new structural alias/machine contract is required, or when correct handling would require changing non-localization candidate files.

Record the real reviewer identity. If one Agent translated and reviewed, say so; do not describe it as independent-model or user approval.

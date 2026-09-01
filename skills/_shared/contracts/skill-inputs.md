# Shared Repeatable Input Reference Extension

| Field | Value |
|---|---|
| Extension | `sdlc-ai-spec/runtime/skill-inputs/v1` |
| Scope | Phase Skills that accept multiple Scope or Control Inputs |

The shared interface accepts repeatable exact input references:

```text
--input REF
--input=REF
-i REF
-i=REF
input REF
input=REF
```

The parser preserves first-seen order, removes exact duplicates with a warning, and exposes:

```json
{"input_references": ["REQ-...@1", "VFY-...@1#RET-001"]}
```

`--reference/-r` continues to identify the target Artifact Revision for `revise/check`.
`--input/-i` identifies Scope or Control Inputs. The phase Runtime, not the parser, validates Artifact type, exact Revision, item kind and authority.

Conflicting or malformed references fail closed. Existing Skills that do not use the extension retain their current behavior.

# RLS Runtime Architecture

## Module map

| Module | Owns | Must not own |
|---|---|---|
| `rls_common.py` | exact refs, canonical JSON, digest, stable errors, redaction | persistence, target effects |
| `rls_vfy_adapter.py` | all VFY wire parsing and provisional assumptions | release execution |
| `rls_scope.py` | exact Scope/Result normalization | scope invention |
| `rls_contract.py` | release binding/effect digest/revision invariants | ArtifactStore implementation |
| `rls_items.py` | RLI/RCF identity, coverage and result validation | executor behavior |
| `rls_authorization.py` | issue/verify exact Effect Authorization | credentials or target access |
| `rls_target.py` | target protocol and Fake/Sandbox implementation | production adapters |
| `rls_executor.py` | authorized RLI dispatch and evidence collection | authorization decisions |
| `rls_confirmation.py` | target-side RCF observations | pipeline-as-pass shortcut |
| `rls_conclusion.py` | deterministic conclusion/follow-up aggregation | Artifact Gate |
| `rls_builder.py` | pure provisional artifact construction | private Store/SQL |
| `rls_verifier.py` | recomputed contract/Gate/freeze checks | persisted claims as authority |
| `rls_handler.py` | create/execute/confirm/revise/check/cancel choreography | CLI rendering |
| `runtime.py` | shared parser and operation dispatch | domain semantics |

## Installed layout

```text
skills/sdlc-600-rls/
├── SKILL.md
├── agents/openai.yaml
├── assets/rls-template.md
├── references/{600-rls-spec.md,contract.md,interface.json,source-lock.json}
└── scripts/{rls_common.py,rls_vfy_adapter.py,rls_scope.py,rls_contract.py,
             rls_items.py,rls_authorization.py,rls_target.py,rls_executor.py,
             rls_confirmation.py,rls_conclusion.py,rls_builder.py,
             rls_verifier.py,rls_handler.py,runtime.py}
```

The provisional implementation is private and deterministic. Canonical
ArtifactStore and Lifecycle Query remain shared authorities and are not copied.
The Web phase does not modify their paths. `runtime.py` uses the installed shared
argument parser; all domain modules remain importable without repository docs.

## Effect boundary

Production target adapters are a deferred protocol implementation. The only
initial adapter is `SandboxReleaseTarget`, which rejects paths outside the OS
temporary directory, performs no network or subprocess call, stores immutable
evidence with exclusive creation and supports cleanup. No Git push/tag/release,
deployment, database, cloud or external API target is addressable.

## Independence

Runtime code contains no `docs/` read, fixed developer path, credential, package
installer or network operation. The final independence test copies the whole
installed Plugin boundary, removes docs/tests, and runs meta plus sandbox flows.

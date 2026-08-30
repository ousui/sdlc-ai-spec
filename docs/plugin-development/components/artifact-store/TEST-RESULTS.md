# ArtifactStore Foundation Test Results

## Baseline

| Field | Value |
|---|---|
| Date | `2026-08-30` |
| Python | `3.14.7` |
| SQLite Schema Version | `1` |
| Third-party dependencies | `None` |

## Commands

```text
python3 -m compileall packages scripts
```

Result：`PASS`

```text
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

- Tests：`34`
- Passed：`34`
- Failed：`0`
- Errors：`0`

```text
git diff --check
```

Result：`PASS`

## Covered

- initialize create / idempotency / Schema failure；
- Artifact ID 与 Revision 分配；
- single open Revision；
- Control Reservation；
- full Payload atomic write；
- materialized open rewrite；
- transaction rollback；
- primary / Member digest；
- Manifest-Member closure；
- frozen / abandoned；
- exact Reference；
- verifier required / rejected / stale / pass；
- generation conflict；
- strict read-only no-create；
- Git-tracked `.sdlc` fail closed；
- CLI JSON protocol；
- no network / no dependency installation；
- IMP external ID / Revision reservation boundary。

## Not Covered

- 真实 Phase Domain Validator；
- 正式 Phase Skill 行为 Eval；
- Agent 宿主 Discovery / Invocation / Behavior；
- Human Review View / Projection；
- performance and multi-process benchmark。

测试全部使用临时项目，不写真实项目 `.sdlc/`。

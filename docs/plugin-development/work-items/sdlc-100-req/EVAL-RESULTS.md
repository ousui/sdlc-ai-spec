# Skill Eval Results — `sdlc-100-req`

## 1. Verdict

**PASS — Portable Runtime；Codex Client 维持准确的 `Partial`。**

| Field | Value |
|---|---|
| Evaluated Branch | `skill/sdlc-100-req` |
| Main Baseline | `a0ca56769d12cec5d6d6d76e1f63c2fd1f5c1030` |
| Main-precedence Merge | `c69e1f37118e84905bd7b2de1163fb608082a986` |
| Evaluated Runtime Commit | `58885cb6d83ab9ac36979295f58b808ac41a496a` |
| Eval Plan | `EVAL-PLAN.md` — approved and unchanged during evaluation |
| Runtime Contract Validator | PASS — 5 shared contracts, 2 formal Skills |
| REQ Source Lock | PASS — 8 exact contracts |
| Runtime Independence | PASS — `docs copied: 0`, external dependencies installed: 0 |
| Full Repository Suite | `118/118 PASS` |
| GitHub Actions | Run `33358330282` — success |
| Runtime Host | Python 3.12 / GitHub Actions Ubuntu 24.04 |
| Codex Host Behavior | Not executed; static adapter evidence only |

## 2. Evaluation Method

1. 先以当前 `main` 为第一父提交，将旧 REQ 分支作为第二父提交合并；所有公共文件和共享 Runtime 以 `main` 为准，只带回 REQ 私有 Skill、测试、工具和工作项。
2. 编译全部 `packages/`、`scripts/` 和 `skills/`，而不是只编译 REQ。
3. 执行 Runtime Contract Validator、REQ Source Lock、删除 `docs/**` 后的 Runtime Independence Fixture，以及完整 unittest discovery。
4. 对冻结 Eval Plan 中原先没有独立断言的四项补充固定回归：frozen effective revise、AC 覆盖缺口、stale Final Confirmation、non-frozen CTX。
5. 未修改 Eval Plan 或把失败案例降级为 warning。

## 3. Critical Case Matrix

| Case | Result | Deterministic Evidence |
|---|---|---|
| EV-C01 | PASS | `test_complete_create_freezes_ready_requirement`：frozen / ready / Gate pass |
| EV-C02 | PASS | `test_missing_content_persists_waiting_input`：materialized open / waiting_input / OPI |
| EV-C03 | PASS | `test_missing_write_authorization_creates_no_req`：零 REQ 分配 |
| EV-R01 | PASS | `test_open_revision_is_revised_in_place`：Revision 不增加 |
| EV-R02 | PASS | `test_frozen_effective_revise_allocates_next_revision`：Revision 2、Base Revision 1、frozen |
| EV-R03 | PASS | `test_frozen_no_change_does_not_allocate_new_revision`：NO_CHANGE、Revision 数不变 |
| EV-K01 | PASS | `test_frozen_check_is_read_only_and_complete`：完整 REQ Domain Check |
| EV-K02 | PASS | `test_check_missing_store_does_not_create_runtime`：STORE_NOT_FOUND、无 `.sdlc` |
| EV-F01 | PASS | `test_cycle_fails_requirement_gate`：`REQ-G-005=fail` |
| EV-F02 | PASS | `test_acceptance_criteria_gap_fails_req_g_006`：`REQ-G-006=fail` |
| EV-F03 | PASS | `test_stale_final_confirmation_persists_core_g_009_failure`：open / failed / `CORE-G-009=fail`，不冻结 |
| EV-I01 | PASS | `test_non_frozen_ctx_fails_without_fallback_or_req_allocation`：不选择其他 CTX、零 REQ 分配 |
| EV-I02 | PASS | `test_vfy_return_phase_mismatch_fails`：Return Phase 非 REQ 时失败 |
| EV-I03 | PASS | `test_rls_follow_up_mismatch_fails`：非 `return_req` 时失败 |
| EV-X01 | PASS | `tools/test_sdlc_100_req_runtime_independence.py`：运行包无 `docs/**` 仍执行 |
| EV-X02 | PASS (static contract) | `disable-model-invocation: true` 与 `allow_implicit_invocation: false`；未冒充真实 Codex 行为 |
| EV-X03 | PASS | Runtime 只依赖共享 Package，不包含兄弟业务 Skill Invocation |
| EV-S01 | PASS | `tools/validate_sdlc_100_req_source_lock.py`：集合、版本、排序、原始字节摘要全等 |
| EV-P01 | PARTIAL (expected) | Codex Manifest / Skill metadata 静态合法；真实 Discovery 与 Invocation 未执行 |

## 4. Findings Closed During Evaluate-fix

### EVAL-REQ-001 — Stale Final Confirmation did not persist the required failed Gate

旧行为会让 stale `subject_digest` 抛出 Runtime 错误，并可能只留下 abandoned Reservation，无法形成 Eval Plan 要求的 `CORE-G-009=fail` 事实。

修复后：

- stale Final Confirmation 被转换为 `CORE-G-009=fail`；
- Artifact Status=`failed`；Gate=`fail`；Revision State=`open`；
- Result Envelope=`ok=false/status=failed`；
- 不执行 freeze；
- Control Input Digest 和 Check Set Digest 仍绑定准确当前内容。

### EVAL-REQ-002 — Main and REQ had not been jointly evaluated

REQ 分支此前只在旧公共基线上运行。现已使用真实两父 merge，`main` 为第一父和公共文件来源，并在包含 CTX + REQ 的状态下完成 118 项全量回归。

## 5. Remaining Limits

- Codex 真实安装、Discovery、显式 Invocation 和未调用对照没有在本次 GitHub 执行环境运行；兼容性只能记录为 `Partial`。
- Cursor 与 Claude Code 未验证。
- `runtime.py → runtime_entry.py → review_fixes.py → cleanup_fix.py → runtime_final.py` 的分层是可工作的兼容收口，但后续公共重构可将补丁合并为更单一的 Runtime；该维护性问题不影响当前 Contract 或行为正确性。

## 6. Evaluation Decision

全部 Portable Critical Case、Source Lock、Runtime Independence 和联合全仓回归均通过。未发现需要返回 Design 的 Contract 问题；下一阶段为 `adapt-codex`，并必须保持真实宿主行为 `Unknown`、静态状态 `Partial`，不得伪造 Verified。

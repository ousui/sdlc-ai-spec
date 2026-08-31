# Skill Design Contract — `sdlc-100-req`

## 1. 元数据

| Field | Value |
|---|---|
| Skill Name | `sdlc-100-req` |
| Stage | `design` |
| Status | `approved` |
| Intended Plugin | `sdlc-ai-spec` |
| Design-time Source | `docs/v1.1/core-spec.md`；`docs/v1.1/artifact-store-spec.md`；`docs/v1.1/100-req-spec.md` |
| Shared Runtime Contract | `skills/_shared/contracts/registry.json` 及其登记内容 |
| Shared Package | `packages/sdlc_runtime/`；`packages/sdlc_artifact_store/` |
| Work Item | `docs/plugin-development/work-items/sdlc-100-req/` |
| Maintainer Decision | `approved` — 用户已明确要求无人值守完整开发本 Skill |

## 2. 用户结果

用户显式调用后，可以创建、修订或只读检查一个 REQ Artifact：

- 原始输入、Goal、Scope、Requirement 与 Acceptance Criteria 可追溯；
- 输入不足时形成结构完整的 materialized open Revision 与 Open Item；
- 准确绑定 frozen CTX，以及适用的 VFY Return / RLS Issue Control Input；
- 只有完整 Check、Final Confirmation 和 Gate 通过时才冻结并提供 Authority；
- 输出统一 Result Envelope 和一条明确下一动作。

## 3. 单一职责

### In Scope

- `create / revise / check`；
- REQ 固定 Markdown/YAML、ID、来源图、AC 覆盖、Open Item、Exception、Gate 和 Final Confirmation；
- 共享 ArtifactStore 的 ID、Revision、事务、摘要和冻结；
- 共享 Runtime 的 Envelope、上游 Authority、Control Input 和 source-lock；
- 标准 JSON CLI 与中文摘要。

### Out of Scope

- 创建 CTX、DSN、PLN、IMP、VFY、RLS；
- 自动修改产品、Git、远端系统或兄弟 Skill；
- 运行时读取 `docs/**`；
- 直接 SQL、私有 Store 或私有 Schema；
- 自动批准 Exception、业务目标或 Final Confirmation。

## 4. Trigger Contract

只接受显式调用：

| ID | 场景 | 结果 |
|---|---|---|
| TRG-P01 | 创建需求 | 执行 `create` |
| TRG-P02 | 修订准确 REQ Reference | 执行 `revise` |
| TRG-P03 | 检查准确 REQ Reference | 执行 `check` |
| TRG-N01 | 普通需求讨论但未调用 Skill | 不执行 Runtime |
| TRG-N02 | 创建其他阶段 Artifact | 说明边界并停止 |

调用后进入 Exclusive Execution，不调用兄弟业务 Skill。

## 5. Runtime Independence

安装后 Runtime 仅依赖：

```text
skills/sdlc-100-req/**
skills/_shared/**
packages/sdlc_runtime/**
packages/sdlc_artifact_store/**
```

`docs/v1.1/**` 只用于 design、build、review 和 source-lock 校验。删除 `docs/**` 后，已构建 Runtime 的 create/revise/check Critical Fixture 必须仍能执行。

## 6. 输入

公共 Envelope 使用 `sdlc-ai-spec/runtime-invocation/v1`。

`inputs` 固定包含：

- `context_reference`：准确 frozen CTX Reference；
- `requirement`：当前 Revision 的完整结构化 REQ 候选；
- `control_inputs`：可选准确 VFY Return / RLS Issue Item Reference；
- `final_confirmation`：可选 human/delegated 最终确认；
- `expected_generation`：修订 materialized open Revision 时可选并发代次。

`create/revise` 还必须在 `confirmations` 中包含当前请求的 `artifact_store_write` 授权。缺失时零写入。

## 7. 输出

公共 Result Envelope 使用 `sdlc-ai-spec/runtime-result/v1`：

- `completed`：请求完成且没有必要用户动作；
- `action_required`：输入或确认不足；
- `blocked`：并发、唯一性或不可继续的运行时条件；
- `failed`：Schema、Store、Integrity 或领域 Contract 失败。

成功写入不等于领域成功；`failed` Gate 必须返回 `ok=false/status=failed`。

## 8. 工作流

1. 校验 Envelope、目标与权限；
2. 只读解析准确 frozen CTX 与 Control Input；
3. 规范化结构化 REQ 数据；
4. 构造固定 Markdown 与 Canonical Payload；
5. 执行 REQ Domain Validator；
6. create/revise 原子写入、读回并验证；
7. 满足 Authority 条件时完成 Final Confirmation、Gate 和 freeze；
8. check 严格只读地复核指定 Revision；
9. 返回同一事实的 Result、Gate、Status 和下一动作。

## 9. 私有资源

```text
skills/sdlc-100-req/
├── SKILL.md
├── agents/openai.yaml
├── references/contract.md
├── references/source-lock.json
├── assets/req-template.md
└── scripts/runtime.py
```

## 10. 失败边界

- 缺少明确目标、写入授权或必要事实：`action_required`，不猜测；
- CTX / Control Input 非准确、未冻结或 Authority 无效：`failed`；
- Requirement 来源图循环、无根或 AC 未覆盖：`failed`；
- 并发代次或 open Revision 冲突：`blocked`；
- check 不存在 Store：`failed` 且不创建任何文件；
- 不使用 `latest/current`、标题相似度或文件 fallback。

## 11. Design DoD

- [x] 单一职责与显式触发明确；
- [x] Runtime 与设计文档解耦；
- [x] 标准 Envelope、Store 和共享 Kernel 边界明确；
- [x] create/revise/check、权限、失败和输出可判定；
- [x] Eval Plan 已定义；
- [x] 阻塞 Open Item 为零；
- [x] Maintainer 已授权无人值守推进全部阶段。

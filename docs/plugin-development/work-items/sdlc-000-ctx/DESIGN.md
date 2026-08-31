# Skill Design Contract — `sdlc-000-ctx`

## 1. 元数据

| Field | Value |
|---|---|
| Skill Name | `sdlc-000-ctx` |
| Stage | `design` |
| Status | `approved` |
| Intended Plugin | `sdlc-ai-spec` |
| Design-time Source | `docs/v1.1/core-spec.md`；`docs/v1.1/artifact-store-spec.md`；`docs/v1.1/000-ctx-spec.md` |
| Shared Runtime Contract | `skills/_shared/contracts/registry.json` 及其登记的 Contract |
| Shared Schema | `skills/_shared/schemas/invocation.schema.json`；`result.schema.json`；`source-lock.schema.json` |
| Shared Package | `packages/sdlc_runtime/`；`packages/sdlc_artifact_store/` |
| Work Item | `docs/plugin-development/work-items/sdlc-000-ctx/` |
| Maintainer Decision | `approved` |

Maintainer 已明确批准当前 Design Contract 与 Eval Plan；实现仍必须由后续
`implement` 工作包独立执行。

## 2. 问题与用户结果

### Problem

后续 REQ、DSN、PLN、IMP、VFY 和 RLS 必须绑定稳定、准确且可解析的
Project Context。当前 Plugin 已具备共享 Runtime Kernel、Local SQLite
ArtifactStore 和 CTX Lineage Registry，但尚无正式 CTX Skill 将项目事实、领域校验、
ArtifactStore 操作和用户交互组合成一个自包含 SOP。

### Intended User Outcome

用户显式调用 `sdlc-000-ctx` 后，可以：

- 为一个已明确确认的 Project Boundary 创建唯一 CTX Lineage；
- 修订准确的 materialized open Revision，或基于 frozen Revision 创建新 Revision；
- 严格只读检查准确 CTX Reference；
- 在输入不足时获得 `waiting_input`、Open Items 与唯一下一动作；
- 在冲突、Store 故障、内容不合规或授权不足时得到结构化失败，而不是猜测或 fallback；
- 获得符合共享 Result Envelope 的机器结果和简明中文摘要。

## 3. 单一职责

### In Scope

- 支持 `create / revise / check` 三种操作；
- 收集并分类 Project Identity、Resource、Technology、Engineering Entry、Topology、Rule、Environment 与 Constraint；
- 为正式 Context 数据登记 `observed / confirmed / referenced` Basis 和 Evidence；
- 构造固定 CTX Markdown、Canonical Manifest 和完整 Canonical Revision Payload；
- 校验 CTX Identity、固定结构、Item ID、Reference、Open Items、Evidence、Exception、Final Confirmation、Gate 与 Status；
- 通过共享 Runtime Kernel 编排共享 ArtifactStore；
- 输出标准 Result Envelope 和一个明确下一动作。

### Out of Scope

- 创建或修改 REQ、DSN、PLN、IMP、VFY、RLS；
- 自动修改下游 Context Reference；
- 维护完整依赖清单、完整目录树、临时调试记录或 Secret；
- 直接 SQL、私有 Store、私有 Schema、Provider 配置或文件系统 Artifact fallback；
- 修改共享 Runtime、ArtifactStore API、Schema 或 Contract；
- 调用兄弟业务 Skill、联网、安装依赖、commit、push、release 或外部系统写入；
- 在 design 阶段创建任何正式 Runtime 文件。

## 4. Trigger Contract

首版只允许显式调用。

### 应触发

| ID | 场景 | 示例 |
|---|---|---|
| TRG-P01 | 首次创建 CTX | “使用 `$sdlc-000-ctx` 为这个项目创建 Context” |
| TRG-P02 | 修订准确 CTX | “使用 `$sdlc-000-ctx` 修订 `CTX-...@2`” |
| TRG-P03 | 只读检查准确 CTX | “使用 `$sdlc-000-ctx` 检查 `CTX-...@3`” |

### 不应触发

| ID | 场景 | 行为 |
|---|---|---|
| TRG-N01 | 未显式调用的一般项目问答 | 不加载 Skill |
| TRG-N02 | 创建其他 Phase Artifact | 说明边界并交还控制权 |
| TRG-N03 | 只要求代码或架构分析 | 普通分析，不写 CTX |
| TRG-N04 | 修改共享 Runtime 或 Store | 要求独立 Foundation 工作包 |

显式调用开始后进入 Exclusive Execution；授权不传递给其他 Skill 或 Plugin。

## 5. 已满足的 Foundation Contract

### 5.1 Shared Runtime Kernel

`packages/sdlc_runtime/` 已提供：

- Invocation / Result Envelope 校验；
- `create / revise / check` 单操作路由；
- 稳定结构化错误结果；
- Runtime Contract Registry；
- 构建期 `source-lock.json` 生成与验证。

当前 Skill 必须使用这些公共能力，不复制外围协议或 Source Lock 逻辑。

### 5.2 CTX Lineage Registry

`packages/sdlc_artifact_store/context_lineage.py` 已提供：

- `ContextLineageRegistry.find(boundary_key)`：严格只读发现；
- `ContextLineageRegistry.reserve(boundary_key, now=...)`：原子发现或保留唯一 CTX Lineage。

`reserve` 在同一 SQLite 写事务内建立 Boundary Key 与 CTX Artifact ID 绑定；重复或并发调用返回同一 Artifact ID，不得创建第二条 Lineage。

Skill 负责先确认 Project Boundary 业务语义。Registry 只接受确定性的
`sha256:<64 lowercase hex>` Boundary Key，不理解路径、名称或业务含义。

### 5.3 Boundary Key

只有 Project Boundary 已由合法 `confirmed` Basis 明确后，Runtime 才生成 Boundary Key：

1. 将已确认 Boundary 文本转换为 Unicode NFC；
2. 将 `CRLF / CR` 转为 `LF`；
3. 删除整体首尾空白，保留内部字符和空白；
4. 空结果无效；
5. 对 UTF-8 原始字节计算 SHA-256，表示为 `sha256:<lowercase hex>`。

Project Root、仓库名称或目录路径不得自动代替 Project Boundary。后续 revise/check
以准确 CTX Reference 定位，不重新根据自然语言相似度选择 Lineage。

### 5.4 Read-only Catalog

`ArtifactCatalog` 已作为未来 `sdlc-status` 的只读底座存在，但不是本 Skill 的必需依赖。
本 Skill 不通过 Catalog 猜测 create/revise/check 的目标。

## 6. Runtime Independence 与资源结构

`docs/v1.1/**` 只用于 design、build 和 review。安装后的 Runtime 不读取 `docs/**`。

实现阶段预期创建：

```text
skills/sdlc-000-ctx/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── contract.md
│   └── source-lock.json
├── assets/
│   └── ctx-template.md
└── scripts/
    └── runtime.py
```

职责：

| Resource | Responsibility |
|---|---|
| `SKILL.md` | 显式触发、输入收集、三种操作核心 SOP、失败停止与结果解释 |
| `contract.md` | CTX 固定字段、Basis、ID、Open Item、Exception、Final Confirmation、Gate、Status 与错误映射 |
| `source-lock.json` | 构建时锁定设计来源和 Runtime Contract 的 ID、Version、SHA-256；运行时不读取 Source |
| `ctx-template.md` | 固定 Front Matter、章节、表头和规范空表示；不预填业务事实 |
| `runtime.py` | Envelope、Builder、Domain Validator、Store 编排、readback、错误和 Result 映射 |
| `openai.yaml` | Codex 显式调用策略；只在 adapt-codex 阶段验证 |

Plugin 是最小部署单元。Skill 可以使用 `skills/_shared/**` 和 `packages/**`，但不读取兄弟业务 Skill 私有目录。

### 6.1 Source Lock

`source-lock.json` 必须符合：

```text
skills/_shared/schemas/source-lock.schema.json
```

顶层固定：

```json
{
  "contract": "sdlc-ai-spec/runtime-source-lock/v1",
  "contracts": []
}
```

每个条目只允许：

```json
{
  "contract_id": "...",
  "contract_version": "...",
  "sha256": "64-lowercase-hex"
}
```

必须包含：

- `skills/_shared/contracts/registry.json` 登记的全部共享 Runtime Contract；
- 三个设计来源的构建锁：
  - `sdlc-ai-spec/build-source/core/v1.1`
  - `sdlc-ai-spec/build-source/artifact-store/v1.1`
  - `sdlc-ai-spec/build-source/ctx/v1.1`

三份设计来源最终摘要固定为：

| Build Source ID | SHA-256 |
|---|---|
| `sdlc-ai-spec/build-source/core/v1.1` | `1eefa7a138f2d221140137a5fac0f5429b7f847273fe9d70e891ace6c3b7a89b` |
| `sdlc-ai-spec/build-source/artifact-store/v1.1` | `b340ca2a38dfe0f7409acaa8f9ac559e8872bed44725037889528e3d167d4764` |
| `sdlc-ai-spec/build-source/ctx/v1.1` | `1d98e7cce686664cbf9897cbac852c425644ba3ea81a0d9c1db5e27b0e530470` |

这些 Build Source ID 只用于构建追踪，不新增领域 Contract。`contract.md` 内必须固化 CTX Artifact 所需的三个准确 Spec Reference 字符串；Runtime 使用打包常量，不读取对应文件。

## 7. Input Contract

公共输入符合 `sdlc-ai-spec/runtime-invocation/v1`。

| Input | create | revise | check | 规则 |
|---|---:|---:|---:|---|
| `project_root` | required | required | required | 现存绝对目录，必须唯一 |
| `artifact_reference` | null | required | required | 必须是准确数字 Revision CTX Reference；禁止 `latest/current` |
| `inputs.context` | required | required | ignored | 候选 CTX 字段、Basis、Basis References |
| `inputs.evidence` | as needed | as needed | ignored | 稳定 Evidence 与不可变来源 |
| `inputs.supporting_members` | optional | optional | ignored | 完整 Member 元数据、原始字节和摘要 |
| `inputs.refresh` | no | required | no | Base、Reason、Effective Change 与 Evidence |
| `confirmations` | as needed | as needed | no write authority | Project Identity、Final Confirmation、Exception、写入授权必须分别明确 |
| `options.dry_run` | optional | optional | optional | `true` 禁止初始化、分配、写入、冻结和放弃 |

### 7.1 目标与内容分离

- `project_root` 和准确 Store 是执行目标；
- Project Identity 中的 Name、Purpose、Boundary 是正式业务内容；
- 目标目录已知不等于 Boundary 已确认；
- create 在 Boundary 未确认时不得调用 Lineage Registry 或分配 Artifact；
- Project Root、Store 或 revise/check Reference 不唯一时，返回 `TARGET_AMBIGUOUS`，零 Store 写入；
- 只有目标和 Boundary 已确认后，其他必要 Context 事实缺失才允许创建 materialized open Revision，并以 Open Item 派生 `waiting_input`。

## 8. Operation Contract

### create

1. 校验显式调用和 Invocation Envelope；
2. 唯一确定 Project Root 和写入授权；
3. 校验 Project Boundary 的 confirmed Basis；
4. 生成 Boundary Key；
5. 打开读写 ArtifactStore，并在授权内 `initialize`；
6. 调用 `ContextLineageRegistry.reserve`：
   - 已存在绑定时返回 `CTX_LINEAGE_EXISTS`，不得创建新 Revision；
   - 首次绑定时取得唯一 CTX Artifact ID；
7. 为该 ID 分配 Revision 1 Control Record；
8. Builder 构造完整 Payload，Validator 执行领域检查；
9. 原子写入并 read-after-write；
10. 输入不足则保持 materialized open / `waiting_input`；全部 Gate 与 Final Confirmation 合法时 freeze。

### revise

1. 校验准确 CTX Reference、写入授权和 Base；
2. materialized open Revision 使用当前 generation 原地修订；
3. frozen Revision 仅在存在有效变化时创建最大 Revision + 1；
4. abandoned 或 Control Reservation 不提供内容 Authority；
5. 重建完整 Payload、重跑全部检查、原子写入并读回；
6. 内容变化使旧 Check、Gate Summary 和 Final Confirmation 失效；
7. 不自动修改下游 Context Reference。

### check

1. 校验准确 CTX Reference；
2. 使用 `ArtifactStore.open_read_only`；
3. 不调用 initialize，不创建 `.sdlc`、数据库、Schema、绑定表或 Revision；
4. 对指定 Revision 执行读取、摘要、结构和领域检查；
5. frozen 且可解析时报告可作为 Context Authority；
6. materialized open 或 abandoned 只报告准确状态，不作为下游 Authority；
7. 不修复、不写入、不回退到其他 Revision。

## 9. Domain Validator Contract

Domain Validator 必须确定性检查：

- CTX Front Matter 字段集合、顺序、Contract ID、ID、Revision 与 Status；
- 固定章节与表格；
- Project Identity、Resource、Technology、Engineering Entry、Topology、Rule、Environment、Constraint；
- `observed / confirmed / referenced` Basis 及 Basis Reference；
- Item ID / Evidence ID / Supporting Artifact ID / Exception ID / Open Item ID 的稳定性和唯一性；
- Refresh Summary 与有效变化；
- Open Items、Evidence、Supporting Manifest、Exceptions；
- Final Confirmation、Core Check、CTX Check、Gate 与 Status 映射；
- primary Blob、Member、Media Type、摘要和 Manifest-Member closure；
- Runtime 固化的三个准确 Spec Reference：
  - `docs/v1.1/core-spec.md@sha256:1eefa7a138f2d221140137a5fac0f5429b7f847273fe9d70e891ace6c3b7a89b`
  - `docs/v1.1/artifact-store-spec.md@sha256:b340ca2a38dfe0f7409acaa8f9ac559e8872bed44725037889528e3d167d4764`
  - `docs/v1.1/000-ctx-spec.md@sha256:1d98e7cce686664cbf9897cbac852c425644ba3ea81a0d9c1db5e27b0e530470`

Validator 不确认业务事实，不生成 Exception，不冒充人工 Final Confirmation。

## 10. Output 与错误映射

公共输出符合 `sdlc-ai-spec/runtime-result/v1`。

| Condition | Status | Error / Next Action |
|---|---|---|
| Envelope 非法 | `failed` | `INVALID_ENVELOPE` |
| 目标不唯一 | `action_required` | `TARGET_AMBIGUOUS` / 提供唯一目标 |
| revise/check 缺少 Reference | `action_required` | `ARTIFACT_REFERENCE_REQUIRED` |
| Reference 格式非法 | `action_required` | `ARTIFACT_REFERENCE_INVALID` |
| create 的 Boundary 未确认 | `action_required` | `PROJECT_BOUNDARY_CONFIRMATION_REQUIRED` |
| create 已有 CTX Binding | `blocked` | `CTX_LINEAGE_EXISTS` / 使用已有 ID |
| check Store 不存在 | `failed` | `STORE_NOT_FOUND` |
| 只有 Control Reservation | `failed` | `CONTROL_RESERVATION` |
| Store/Schema/事务/摘要失败 | `failed` | 使用共享稳定错误码 |
| 必要 Context 事实缺失 | `action_required` | materialized open + Open Items + `waiting_input` |
| Gate fail | `failed` | 准确 failed checks，不降级为 warning |
| no-change revise | `completed` | 保留原 Reference，不创建 Revision |
| 成功冻结 | `completed` | frozen Reference 与下一 Phase 建议 |

Result 必须包含：`artifact`、`gate`、`open_items`、`warnings`、`errors`、`next_action`，并生成一致的中文摘要。没有 Authority 时 `artifact.reference` 必须为 `null`。

## 11. 权限与副作用

| Operation | Read | Write | Other Side Effects |
|---|---:|---:|---|
| create | current project + bundled runtime | 仅准确 `.sdlc/store.sqlite3` | 不联网、不提交 Git |
| revise | current project + exact CTX | 仅准确 open/new Revision | 不修改下游 |
| check | exact Store / Revision | none | 不创建任何持久化状态 |
| dry-run | allowed inputs | none | 只返回非权威候选结果 |

禁止读取无关敏感信息、保存 Secret、安装依赖、修改全局配置、执行远程写入或自动调用其他 Skill。

## 12. Portability

Portable Core 使用同一 Skill 源码、Runtime、Fixture 和输出 Contract。平台 Adapter 只处理 Discovery、显式调用元数据、路径和宿主能力，不改变 CTX 语义。

- Cursor / Claude Code：`disable-model-invocation: true`；
- Codex：`agents/openai.yaml` 中 `policy.allow_implicit_invocation: false`；
- 一个 Client 的证据不能证明其他 Client；
- design 不声明任何宿主已验证。

## 13. Eval 与资源边界

对应 Eval：`docs/plugin-development/work-items/sdlc-000-ctx/EVAL-PLAN.md`。

本阶段不创建 `SKILL.md`、Runtime、Asset、Reference、Fixture 或 Eval Result。

## 14. Design DoD

- [x] 单一职责、范围和触发可判定；
- [x] `create / revise / check` 输入、输出和副作用明确；
- [x] Runtime 不读取 `docs/**`；
- [x] Shared Runtime Kernel、Source Lock、ArtifactStore 和 CTX Lineage Registry 已绑定到准确公共 API；
- [x] Boundary Key 的生成与人工确认边界明确；
- [x] Builder / Validator / Store 责任分离；
- [x] Gate、Final Confirmation、Exception 与失败映射可判定；
- [x] Runtime Independence、并发、只读和 Source Lock Eval 已设计；
- [x] 阻塞 Open Item 为零；
- [x] 未创建正式 Runtime。

## 15. Open Items

| ID | Question | Blocks | Status |
|---|---|---|---|
| None | 当前没有阻塞 Design Approval 的 Open Item | N/A | closed |

## 16. Maintainer Decision

| Role | Decision | Basis |
|---|---|---|
| Maintainer | `approved` | 2026-08-30 明确 `approve-design`：Shared Runtime Kernel 已实现并通过 CI；Runtime Contract Registry 与 Source Lock Schema 已稳定；`ContextLineageRegistry.find/reserve` 已提供只读查找与原子保留，且同一 Project Boundary 的重复及并发创建只会得到一个 CTX Artifact ID；Boundary Key 的 `confirmed` Basis、规范化和摘要规则已明确；Runtime 不读取 `docs/**`；`create / revise / check` 的输入、输出、错误、权限和副作用边界可判定；Eval Plan 已覆盖 Runtime Independence、Source Lock、并发创建、`open/frozen/abandoned` Revision、严格只读、Exception、delegated Final Confirmation 和三端适配；Design DoD 已满足，阻塞 Open Item 为零。 |

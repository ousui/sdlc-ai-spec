---
title: Project Context Spec
status: stable
version: "1.1"
scope: Project Context 的结构、Revision、引用、刷新与 Gate
---

# Project Context Spec

## 目标

Project Context（CTX）以一个固定 Markdown Artifact 保存项目长期稳定、可重复使用的事实、规则与约束，减少后续 Lifecycle Phase 对相同项目背景的重复获取和推断。

CTX 是 Lifecycle 的前置上下文，不是 Phase，不参与 `REQ → DSN → PLN → IMP → VFY → RLS` 的阶段顺序，也不使用 Lifecycle Profile。

规范阅读顺序使用 `000-ctx` 表示固定前置位置并保持自然排序；`000` 不是 Phase Order，`CTX` 也不进入 Phase Code 枚举，不作为 Canonical Store 中的物理定位依据。

## 边界

CTX 负责记录：

- 项目身份、用途和边界；
- 稳定 Resource 及其定位方式；
- 主要技术、工程入口和项目结构；
- 已确认的项目规则、环境能力和约束；
- 信息依据、待确认项、刷新变化和 Gate 结论。

CTX 不负责记录：

- 单次业务 Requirement；
- 针对具体 Requirement 的 Design Decision；
- Work Item、实施过程、验证结果或发布状态；
- 完整依赖列表、完整代码目录或临时调试信息；
- Agent、宿主或派生适配指令；

宿主适配指令是非权威派生视图，不是 CTX，不得作为 Context Reference。不同执行方处理同一 Artifact Revision 时必须读取其 Front Matter 绑定的同一 CTX Revision。

## Contract 关系

- CTX Artifact 同时受 Core Spec、Artifact Store Spec 与 Project Context Spec 约束；
- CTX 的 Evaluation Contract Set 至少包含这三个 Spec 的准确不可变引用；
- Lifecycle Artifact 只在 Front Matter 中保存准确 Context Reference，并通过该 CTX Revision 自身的 Evaluation Contract Set 验证上下文，不复制 CTX 内容或重复绑定 Project Context Spec；
- CTX 复用 Core 的 Artifact Lineage、Revision Control Record、Canonical Revision Payload、Artifact Status、Evidence、Supporting Artifact Manifest、Exceptions、Open Items、Final Confirmation 和 Gate Summary，不另建平行控制结构。

## Front Matter

字段和顺序固定：

```yaml
---
contract: sdlc-ai-spec/project-context/v1
id: CTX-20260828143025-01
revision: 1
status: draft
---
```

| 字段 Field | 规则 Rule |
|---|---|
| `contract` | 固定为当前 Project Context Contract 版本 |
| `id` | 项目 Artifact Store 内唯一且长期稳定的 CTX ID |
| `revision` | 正整数，从 `1` 开始 |
| `status` | 使用 `draft / waiting_input / failed / ready / ready_with_exception` |

CTX 不使用 `phase`、`profile` 或 `inputs`。

Lifecycle Artifact Front Matter 必须使用独立字段绑定准确 Context Reference：

```yaml
context: CTX-20260828143025-01@1
```

`context` 不能由 Lifecycle `inputs`、文件路径、宿主适配指令或动态 `latest/current` 引用替代。

## Identity

CTX ID 固定格式：

```text
CTX-<YYYYMMDDHHMMSS>-<NN>
```

规则：

- 一个 Project Boundary 只创建一个 CTX ID；
- Context 更新只增加 Revision，不创建新 CTX ID；
- 项目重命名、目录迁移或仓库地址变化不改变 CTX ID；
- 原 Project Boundary 被明确拆分为独立项目时，新项目分别创建 CTX ID；
- 同一 Artifact Store 中不得存在两个描述同一 Project Boundary 的 CTX Lineage。

## Revision 与存储

一个 Project Boundary 在 Canonical Store 中只维护一个 CTX Lineage。`000-ctx` 只表示规范阅读中的 Lifecycle 前置位置，不是 Phase，也不提供物理 Artifact Authority。

每个 CTX Revision 使用 Artifact Store Spec 定义的 Revision Control Record 与完整 Canonical Revision Payload。primary Canonical Blob 是使用本 Spec 固定模板的 CTX Markdown 原始字节；当前 Revision locally owned 的 Supporting Member、稳定 Member 身份、Canonical Member Name 或等价稳定名称、Media Type、逐 Member SHA-256 和 Manifest-Member closure 必须随同保存并读回。外部不可变 Reference 保留既有准确 Reference、摘要和访问边界，不要求复制为本地 Member。

Revision Control Record 复用 Core 固定结构：

```markdown
| Revision | State | Base Revision | Allocated At | Frozen At | Abandon Reason |
|---|---|---|---|---|---|
| 1 | open | None | 2026-08-28T14:30:25+08:00 | N/A | N/A |
```

规则：

- `State` 只允许 `open / frozen / abandoned`；
- 同时最多存在一个 Open Revision；
- 新 Revision 为已持久化最大 Revision 加 `1`；
- Revision 1 的 `Base Revision` 固定为 `None`；
- 后续 Base Revision 必须是同一 CTX 的 Frozen Revision；
- 未冻结的 `draft`、`waiting_input` 或 `failed` 内容可以继续修正；
- `ready` 或 `ready_with_exception` 冻结后不得原地修改；
- 没有有效内容变化时不得创建空 Revision；
- 不建立 `current`、`latest` 或可移动副本。
- Revision 分配、open Revision 写入、读回、冻结、放弃和准确解析使用 Artifact Store Spec 的对应逻辑操作；`allocate revision` 只在 Revision Control Record 已建立并读回后完成控制预留，不形成可读取、可解析或可执行 Gate 的 CTX Revision。只有第一次 `write open revision` 已将完整 Canonical Revision Payload 原子持久化，并由 `read revision` 完整读回验证后，该 `open` Revision 才完成物化，可进入 CTX Check、Final Confirmation、Gate 与 `freeze revision`。

## Context Reference

完整引用：

```text
CTX-20260828143025-01@1
```

Item Reference：

```text
CTX-20260828143025-01@1#RSC-001
```

有效 Context Reference 必须同时满足：

1. CTX ID、Artifact Lineage、Front Matter 和 Revision 一致；
2. Revision Control Record 中存在唯一对应记录且 `State=frozen`；
3. Status 为 `ready` 或 `ready_with_exception`；
4. primary Canonical Blob、全部本地 Member、稳定 Member 身份、Media Type、Manifest-Member closure、逐项 SHA-256、Evidence、Final Confirmation 和 Gate 可以验证；
5. Item Reference 可以解析到当前 Revision 内唯一 Item。

创建 Lifecycle Artifact 或新 Revision 时，选择当时最高的、已冻结且可解析的 `ready` 或 `ready_with_exception` CTX Revision，并立即持久化为准确 Context Reference。新 CTX Revision 不自动改写或使既有 Lifecycle Artifact 失效。

直接上游与当前 Artifact 绑定不同 CTX Revision 时，必须根据 Refresh Summary 判断变化是否影响当前 Scope、Resource、Rule、Engineering Entry 或 Constraint。无影响时以 Evidence 保存复核依据；有影响时修订最早受影响的 Lifecycle Artifact，不为统一 Revision 而重建无关 Artifact。

## 固定模板

```markdown
# <Project Name> Project Context

## 摘要 Summary

## 项目标识 Project Identity

## 资源登记 Resource Registry

## 技术与工程基线 Technical and Engineering Baseline

### 技术基线 Technology Baseline

### 工程入口 Engineering Entry Points

## 项目结构 Project Topology

## 项目规则 Project Rules

## 环境与约束 Environment and Constraints

### 环境 Environment

### 约束 Constraints

## 待确认项 Open Items

## 证据 Evidence

## 刷新摘要 Refresh Summary

## 支撑产物清单 Supporting Artifact Manifest

## 豁免 Exceptions

## 门禁 Gate
```

所有固定章节必须保留。正文保持精炼，长文档、完整目录树、完整依赖清单和工具原始输出使用不可变引用或 Supporting Artifact，不复制进入主文件。

## Basis

所有正式 Context 数据必须使用一个 Basis：

| Basis | 含义 | Basis References |
|---|---|---|
| `observed` | 可从代码、配置、工具结果或项目状态重复验证 | 必须引用 Evidence |
| `confirmed` | 由具备相应权威的人明确确认 | 必须引用确认 Evidence |
| `referenced` | 来自既有权威文档、Artifact 或规则来源 | 必须填写准确不可变引用 |

不使用置信度分数，也不允许把 `inferred` 作为正式 Context 数据。候选推断必须转为 `observed`、`confirmed` 或 `referenced`；否则建立 Open Item。

除固定控制表外，CTX 数据表最后两个字段统一为 `Basis` 和 `Basis References`。

## 项目标识

```markdown
| Field | Value | Basis | Basis References |
|---|---|---|---|
| Project Name | | confirmed | |
| Purpose | | confirmed | |
| Boundary | | confirmed | |
| Primary Resource Reference | RSC-001 | observed | |
| Authoritative References | None | confirmed | <EVD-ID> |
```

字段顺序固定。`Project Name`、`Purpose`、`Boundary` 和 `Primary Resource Reference` 不允许为 `None` 或 `N/A`。

## 资源登记

```markdown
| ID | Type | Name | Role | Locator | Baseline Reference | Basis | Basis References |
|---|---|---|---|---|---|---|---|
| RSC-001 | repository | | primary | | | observed | |
```

- `Type` 使用 `repository / module / service / application / library / database / infrastructure / document-set / other`；
- `Role` 使用 `primary / supporting`；
- 至少存在一个 `Role=primary` 的 Resource；
- 同一 Resource 只分配一个 RSC ID；
- Locator 必须在 Project Boundary 内唯一且可解析；
- 版本化 Resource 必须具有不可变 Baseline Reference。

## 技术与工程基线

### 技术基线

```markdown
| ID | Category | Name | Version or Constraint | Purpose | Basis | Basis References |
|---|---|---|---|---|---|---|
| TEC-001 | language | | | | observed | |
```

`Category` 使用 `language / runtime / framework / package / build / test / quality / other`。只登记后续工作会重复使用的主要技术，不复制完整依赖清单。

### 工程入口

```markdown
| ID | Purpose | Command or Entry Point | Working Scope | Preconditions | Basis | Basis References |
|---|---|---|---|---|---|---|
| ENG-001 | build | | | | observed | |
```

`Purpose` 使用 `build / test / run / format / lint / package / other`。Command 不得包含密码、Token 或个人绝对路径；无法以安全、可复用形式记录时保存准确入口引用。

## 项目结构

```markdown
| ID | Name | Type | Resource Reference | Responsibility | Entry Point | Depends On | Authority Reference | Basis | Basis References |
|---|---|---|---|---|---|---|---|---|---|
| CMP-001 | | module | RSC-001 | | | None | None | observed | |
```

只登记主要组件、职责、入口和关系，不复制完整目录树。`Depends On` 为空时写 `None`；存在依赖时只使用当前 CTX 内 CMP ID 的固定 Reference Set。

## 项目规则

```markdown
| ID | Category | Rule Summary | Scope | Authority Reference | Basis | Basis References |
|---|---|---|---|---|---|---|
| RUL-001 | code | | | | referenced | |
```

`Category` 使用 `code / branch / commit / test / documentation / compatibility / security / release / other`。Rule Summary 只保存必须常驻理解的精炼规则，并绑定权威来源，不复制整份规则文档。

## 环境与约束

### 环境

```markdown
| ID | Environment | Purpose | Accessibility | Data and Network Boundary | Basis | Basis References |
|---|---|---|---|---|---|---|
| ENV-001 | local | | available | | observed | |
```

`Environment` 使用 `local / development / test / staging / production / other`；`Accessibility` 使用 `available / restricted / unavailable`。未知可访问性建立 Open Item，不创建正式 ENV 行。CTX 不保存凭证。

### 约束

```markdown
| ID | Constraint | Scope | Impact | Required Handling | Authority Reference | Basis | Basis References |
|---|---|---|---|---|---|---|---|
| CON-001 | | | | | | referenced | |
```

Constraint 只记录后续工作必须持续考虑的真实限制；未来设想和临时提醒不进入本表。

## Refresh Summary

```markdown
| Base Revision | Observed At | Observation Baseline | Refresh Reason | Effective Change References | Evidence References |
|---|---|---|---|---|---|
| None | | | initial | None | |
```

- Revision 1 的 `Base Revision=None`、`Refresh Reason=initial`；
- 后续 Revision 只登记相对 Base Revision 的有效变化；
- `Observed At` 使用 RFC 3339；
- `Observation Baseline` 使用准确 Resource Baseline 或 Evidence Reference Set；
- 新增、调整和移除使用完整、可解析的当前或历史 Item Reference；
- 更新周期、提交阈值和变化检测方式不属于本 Contract；
- 项目变化本身不自动创建 Revision，只有权威内容发生有效变化时才创建 Revision。

## Item ID 与排序

| 内容 | ID 格式 | 排序 |
|---|---|---|
| Resource | `RSC-001` | 按 ID 升序 |
| Technology | `TEC-001` | 按 ID 升序 |
| Engineering Entry | `ENG-001` | 按 ID 升序 |
| Component | `CMP-001` | 按 ID 升序 |
| Project Rule | `RUL-001` | 按 ID 升序 |
| Environment | `ENV-001` | 按 ID 升序 |
| Constraint | `CON-001` | 按 ID 升序 |
| Open Item | `OPI-001` | 按 ID 升序 |
| Evidence | `EVD-001` | 按 ID 升序 |
| Supporting Artifact | `SUP-001` | 按 ID 升序 |
| Exception | `EX-001` | 按 ID 升序 |

同一语义跨 Revision 保持 ID；新增条目使用当前前缀已分配最大编号加 `1`；删除后不得复用；语义被替代、Resource 拆分或合并时创建新 ID。排序、改名、Locator 或普通属性变化不单独改变对象 ID。Refresh Summary 必须准确登记新增、调整和移除。

Project Identity 使用固定字段顺序，Refresh Summary 在当前 Revision 只保留一行。业务依赖顺序使用显式字段表达，不通过重排已分配 ID 表达。

## 空值与 Open Items

统一使用：

| 值 | 含义 |
|---|---|
| `None` | 已确认集合为空或客观不存在 |
| `N/A` | 当前字段按 Contract 明确不适用 |
| `Pending — OPI-001` | 仅允许用于自由文本单元格或正文，并指向真实 Open Item |

禁止空白 typed value，以及 `TBD / Unknown / - / 待定` 等自由占位。

必要事实尚未确认时，不创建对应正式数据行，使用 Core Open Items Contract 并将 Open Item ID 统一为 `OPI-<NNN>`。任一 `State=open` 的 Open Item 派生 `status: waiting_input`。客观不存在某类内容时保留表头和唯一 `None` 行，并用 Basis 证明；`None` 不表示未知，`N/A` 不表示尚未填写。

## Evidence、Supporting Artifact 与 Exceptions

CTX 复用同一 Spec Snapshot 中 Core 定义的 Evidence、Supporting Artifact Manifest、Exceptions、Final Confirmation 和 Gate Summary Contract。

Exception 可以接受已知限制，但不能替代 Project Boundary、Primary Resource、Resource Identity、Basis 或事实来源，也不能把未知事实转换为已知事实。

## CTX Gate

```markdown
| Check ID | Check | Result | Basis References |
|---|---|---|---|
| CTX-G-001 | Contract、ID、Revision、Status 和 Context Snapshot 结构合法 | pending | |
| CTX-G-002 | Project Name、Purpose、Boundary 和 Primary Resource 已准确确定 | pending | |
| CTX-G-003 | Resource ID 唯一，Locator 可解析，版本化 Resource 具有准确观察基线 | pending | |
| CTX-G-004 | 技术、工程入口、结构、规则、环境和约束已按适用范围登记 | pending | |
| CTX-G-005 | 所有正式信息具有合法 Basis 和可解析 Basis References，不含未确认推断 | pending | |
| CTX-G-006 | Open Items、Evidence、Exceptions 和 Refresh Summary 完整且一致 | pending | |
```

CTX Check Result 只使用 `pending / pass / fail`。Exception 由独立 Exception Contract 处理，不把 Contract Integrity Check 标记为 `waived`。

Gate 与 Status 固定映射：

| 条件 | Gate Result | CTX Status |
|---|---|---|
| 存在确认冲突、无效引用或 Check=`fail` | `fail` | `failed` |
| 存在 `State=open` 的 Open Item | `pending` | `waiting_input` |
| 内容或检查尚未完成 | `pending` | `draft` |
| 全部 Check 通过且不存在有效 Exception | `pass` | `ready` |
| 必要工作完成且存在有效 Exception | `pass_with_exception` | `ready_with_exception` |

Artifact Gate 按全部 Core Check、CTX Check、Final Confirmation 和唯一 Gate Summary 的固定顺序完成。CTX 没有 `context`、`inputs` 或 Disposition 时，相关 Core Check 通过确认字段按 Contract 正确缺省、引用集合为空且不存在未承接义务完成，不使用 `n/a` 绕过。Final Confirmation 不作为 CTX Check 重复登记。只有 `ready` 或 `ready_with_exception` Revision 可以冻结并供 Lifecycle Artifact 使用。

---
contract: sdlc-ai-spec/runtime/design/v1
contract_version: "1"
source_contract_id: sdlc-ai-spec/spec/design/v1.1
source_version: "1.1"
source_sha256: 998b76ebf72714706bca045d22f2b5b09ac655404f324cb904edcc241bc4f0ee
scope: installed sdlc-200-dsn runtime contract
---

# DSN Bundled Runtime Contract

本文件是随 Plugin 分发的 DSN 运行合同。它由稳定 Design Phase Spec 派生，生产运行时只读取本 Skill 自带的 `references/`、`assets/` 与确定性程序，不依赖开发仓库目录。

## 1. 目标与边界

DSN 将一个或多个已确认 Requirement 转换为可实施、可验证的设计结果。它负责：

- 明确独立 Design Boundary；
- 记录 Current Baseline、Target State 与完整 Change Set；
- 建立 Requirement、Acceptance Criteria、Design Item、Decision 与 VFY Objective 的双向追踪；
- 判断固定 16 个 Design Domain 的适用性；
- 构造父 primary Blob、required Domain Member、Supporting Member 与 Manifest-Member closure；
- 生成父 Gate、Final Confirmation 和准确 Revision 状态。

DSN 不得静默修改 Requirement 业务语义，不拆任务、不编码、不执行验证或发版。上游 Requirement 存在缺失、冲突或不可实现内容时返回 REQ。

## 2. Artifact 关系

允许：

```text
一个 REQ → 多个 DSN
多个 REQ → 一个共享 DSN
多个 REQ → 多个 DSN
```

独立 DSN 的依据是独立边界、可独立评审、可独立修改或复用，以及独立 Gate；不能因为存在多个 Domain 就拆成多个 DSN。

新 DSN 在分配 Artifact ID 前必须确定 Boundary。Boundary 已确定但详细设计不足时，可以形成 materialized open Revision，并以 `waiting_input` 和 Open Items 表达缺口。

## 3. Front Matter

```yaml
---
contract: sdlc-ai-spec/artifact/v1
phase: DSN
id: DSN-<timestamp>-<sequence>
revision: <positive integer>
status: draft|waiting_input|failed|ready|ready_with_exception
context: CTX-...@<revision>
profile: full|lite|hotfix
inputs:
  - REQ-...@<revision>
---
```

至少一个准确 frozen REQ 是 Scope Input。Return Phase=DSN 的 frozen VFY Return 与 `return_dsn` RLS Issue 是 Control Input，其所属 frozen Revision 进入 Front Matter `inputs`，但不会自动扩大 Design Scope。

所有 Scope REQ 必须绑定同一个准确 CTX Revision。

## 4. primary Canonical Blob

固定章节顺序：

1. Summary
2. Scope
3. Design Baseline and Change
4. Requirement Traceability
5. Design Decisions
6. Design Index
7. Composite Domain Subdomain Applicability
8. Artifact Set Manifest
9. Open Items
10. Evidence
11. Exceptions
12. Lifecycle Applicability
13. Gate
14. Final Confirmation
15. Artifact Gate Summary

核心章节不得删除或整体标记为不适用。不存在 Design Decision 时使用 `None — <客观原因>`，不得虚构决策。

## 5. Baseline、Change 与简单性

`Change Type` 使用 `new`、`incremental` 或 `reuse`；Change Item 使用 `add`、`modify`、`remove` 或 `reuse`。

- `incremental/reuse` 必须绑定准确不可变 Baseline；
- `Scope + Baseline + Change Set` 必须唯一确定 Target State；
- Change Set 不包含任务、顺序、工期或实施负责人；
- Affected Domains 只使用固定 `DOM-<number>`；
- 不得顺手重构或引入未被 Requirement、Baseline 或已确认约束要求的能力；
- 比直接实现更复杂的方案必须说明必要性、代价与残余风险。

## 6. Requirement Traceability

当前 Scope 中每个 Requirement Item 必须至少关联一个 Design Item 或 Domain Member。每个 Acceptance Criterion 必须映射到 Design Item 或准确 N/A Reason，并始终映射到后续 VFY Objective。

不得存在：

- 无上游来源的孤立设计；
- 未覆盖的 Requirement 或 AC；
- 自引用、循环或不存在的 Reference；
- 在 DSN 中新增未经 REQ 确认的业务规则。

## 7. Design Decisions

仅在存在真实选择时创建 `DEC-NNN`。每项 Decision 必须记录：

- Requirement、约束或 Evidence 来源；
- 问题；
- 候选方案；
- 选择结果；
- 选择依据；
- 受影响 Domain；
- 关键 Decision 对应的 VFY Point。

默认 `decision_policy=user`。模型可推荐方案，但不能静默决定业务边界、风险接受、Waiver、法律适用性或 Final Confirmation。

## 8. 固定 Domain Matrix

固定顺序：

```text
DOM-110 Workflow and State
DOM-120 UX and Interaction
DOM-130 UI and Content
DOM-140 Accessibility and Internationalization
DOM-210 System and Architecture
DOM-220 Components and Modules
DOM-230 Interfaces and Integration
DOM-240 Data Design
DOM-310 Security, Privacy and Compliance
DOM-320 Performance and Capacity
DOM-330 Reliability and Recovery
DOM-340 Compatibility and Migration
DOM-350 Maintainability and Extensibility
DOM-410 Deployment and Configuration
DOM-420 Observability and Operability
DOM-510 Verifiability and VFY Strategy
```

每行 Disposition 只能是 `required`、`n/a`、`waived` 或 `pending`。只为 `required` Domain 创建本地 Member；`DOM-510` 在 DSN 存在时固定 `required`。

`DOM-140` 与 `DOM-310` 的 5 行复合子领域表保存在父 primary Blob。父 Disposition 必须由子领域结果确定；不创建子领域 Artifact 或独立 Gate。

详细 Domain 合同位于同目录的 `200-dsn-domains/`，按需加载，不形成兄弟 Skill 调用。

## 9. Domain Member

每个 required Domain Member：

- 使用稳定 `DOM-<number>` Member ID；
- Canonical Member Name 使用 `domains/<domain-file>`；
- 记录父 DSN、准确 Revision、Requirement References 与 Decision References；
- 包含 Domain 固定 Design Result；
- 110 至 420 包含至少一个 VFY Point；
- 510 包含 VFY Objectives、Methods、Pass Criteria 和 Evidence Contract；
- 不重复 Summary、Scope、Open Items、Exceptions 或 Gate；
- 不记录 Secret、Token、密码或私钥。

Supporting Member 使用 `SUP-NNN`，必须具有稳定名称、Media Type、原始字节和 SHA-256。

## 10. Manifest-Member closure

父 Artifact Set Manifest 必须精确登记全部本地 Domain 与 Supporting Member：

- Member ID；
- Type；
- Domain；
- 稳定 Domain Contract ID 与摘要；
- Canonical Member Name；
- Media Type；
- Purpose；
- 原始字节 SHA-256。

声明集合与真实集合必须完全一致。缺失、额外、重复 ID、重复 Canonical Name、Media Type 或摘要不一致时失败关闭。

## 11. Open Items、Exceptions 与状态

- Boundary 未确定：不分配 Artifact；
- Boundary 已确定但存在未决事实或 required Domain 未完成：`waiting_input`；
- Contract Integrity Check 失败：`failed`；
- 全部 Check 通过、无 Open Item、无 active Exception：`ready`；
- 全部 Check 通过、无 Open Item、有合法 active/carried Exception：`ready_with_exception`。

`ready` 和 `ready_with_exception` 必须具有有效 Final Confirmation，且绑定当前 subject、Control Input Digest、Check Set Result Digest 和准确 Authority Reference。

## 12. Lifecycle Applicability

固定后续 Phase：PLN、IMP、VFY、RLS；VFY 固定 `required`。

默认下一阶段是 PLN。只有 PLN 明确 `n/a/waived`、IMP=`required`、依据闭合且当前 Scope 满足直接实施合同，Lifecycle Query 才可投影为直接进入 IMP。

## 13. Gate

父 Gate 顺序：

1. Core Checks；
2. DSN-G-001 至 DSN-G-010；
3. 只展开 required Domain 注册的 subordinate Checks；
4. Final Confirmation；
5. 唯一 Artifact Gate Summary。

每个 Check ID 在当前 Revision 只出现一次。Domain 子检查不是独立 Gate。

## 14. Revision 与副作用

- `create`：分配新 DSN Artifact 和 Revision；
- materialized open Revision：原地 revise，Revision 不增加；
- frozen Revision 有有效变化：创建下一个 Revision；
- frozen Revision 无变化：不创建空 Revision；
- build 或首次写入失败：新 Control Reservation 必须 abandon；
- `check`：严格只读，不 initialize、不修复、不写旁车文件；
- Runtime 不直接 SQL、不使用文件 fallback、不调用兄弟 Skill、不联网、不安装依赖、不执行 Git。

## 15. Runtime Independence

正式 Runtime 依赖：

```text
skills/sdlc-200-dsn/**
skills/_shared/**
packages/sdlc_runtime/**
packages/sdlc_artifact_store/**
packages/sdlc_lifecycle/**
scripts/sdlc_skill_interface.py
```

删除开发期文档、测试和 Handoff 后，Help、参数解析、create/revise/check、Domain Member、Manifest、Gate 与生命周期查询必须继续执行。

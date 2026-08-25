---
title: Design Phase Spec
status: draft
scope: 已确认的 DSN 边界、结构与 Design Applicability Matrix
---

# Design Phase Spec（草稿）

## Phase 目标

DSN 将已确认的 Requirement 转换为可实施、可验证的设计结果。

DSN 不是单指架构设计、概要设计或详细设计，而是这些设计活动的统一承载 Phase。它负责提前发现问题、明确边界、记录设计选择，并防止后续实施偏离 Requirement。

DSN 是高判断密度的 Phase，但 Spec 不限定由人工还是 AI 生成设计。关键选择和边界必须显式记录，最终确认者对已接受的设计结果和风险负责；是否逐项阅读不改变该责任。

## Phase 边界

DSN 负责：

- 将 Requirement 映射为明确的设计边界；
- 记录关键 Design Decision、候选方案和选择依据；
- 确定适用的 Design Domain；
- 形成可以被 PLN、IMP 和 VFY 使用的设计结果；
- 发现 Requirement 中的缺失、冲突或不可实现内容。

DSN 不负责：

- 静默修改 Requirement 目标、范围或 Acceptance Criteria；
- 拆分具体实施任务；
- 制定执行排期；
- 编写实现代码；
- 给出最终交付结论。

发现 Requirement 存在问题时，必须返回 REQ，不能在 DSN 中自行改变业务语义。

## Artifact 关系

DSN 不强制一项 Requirement 对应一个 Design。

```text
一个 REQ → 多个 DSN
多个 REQ → 一个共享 DSN
多个 REQ → 多个 DSN
```

创建独立 DSN Artifact 的判断依据：

- 具有独立设计边界；
- 可以独立评审和确认；
- 可能独立修改或复用；
- 具有独立 Design Result 和 Gate。

仅仅因为存在多个 Design Domain，不需要拆成多个 DSN Artifact。

## Front Matter

```yaml
---
contract: sdlc-ai-spec/artifact/v0.1
phase: DSN
id: DSN-20260823150010-01
revision: 1
status: draft
profile: full
inputs:
  - REQ-20260823143025-01@1
---
```

DSN 必须至少绑定一个准确的 Requirement Revision。输入为 `ready_with_exception` 时，DSN 必须逐项处理与当前 Design Scope 相交的上游未关闭 Exception，并将其记为 `carried`，或用 Evidence 证明不相交、已 `resolved` / `superseded`；无法确定是否相交时仍按相关处理。

## 固定模板

DSN 使用“主文件 + Domain 子文件”的 Artifact Set。主文件负责总览、追踪、决策、适用性和 Gate；详细设计只写入适用 Domain 的子文件。

```markdown
# <设计标题>

## 摘要 Summary

## 范围 Scope

## 设计基线与变更 Design Baseline and Change

## 需求追踪 Requirement Traceability

## 设计决策 Design Decisions

## 设计关注评估 Design Concern Assessment

## 设计总纲 Design Index

<固定全量 Domain 矩阵>

## 产物集清单 Artifact Set Manifest

## 领域明细记录 Domain Detail Records

## 待确认项 Open Items

## 证据 Evidence

## 豁免 Exceptions

## 生命周期适用性 Lifecycle Applicability

## 门禁 Gate
```

推荐阅读顺序为：摘要与边界 → 方案与决策 → 全量 Domain 索引 → 按需打开 Domain 子文件 → 控制和 Gate。

Domain 子文件不设置强制阅读对象。参与者按需要选择阅读范围；未逐项阅读不改变 Domain 的适用性、完成状态、Gate 要求，也不减轻最终确认者对结果和风险的责任。

## DSN Artifact Set

```text
artifacts/200-dsn/DSN-20260823150010-01/
├── revision-index.md
└── revisions/
    └── 000001/
        ├── DSN-20260823150010-01.md
        ├── domains/
        │   ├── 110-workflow-state.md
        │   ├── 210-system-architecture.md
        │   └── ...
        ├── controls/
        │   └── domain-gates.md
        └── assets/
```

规则：

- `<DSN-ID>.md` 是唯一主要 Artifact，也是总纲和索引；
- 只为 `required` Domain 创建子文件；
- Domain 子文件属于父 DSN Artifact Set，不分配独立 Artifact ID 或 Revision；
- 存在 `required`、`embedded` 或历史 DGR 时创建唯一 `controls/domain-gates.md`，集中保存全部完整 DGR；它是 control member，不是 Domain 子文件；
- Domain 子文件的语义变化会触发父 DSN Revision 变化；
- 图片、图表、Schema 和其他原生文件放入 `assets/`，并由 Domain 子文件引用；
- Domain 如果需要独立复用、评审或 Revision，应创建新的 DSN Artifact，而不是继续作为子文件。
- 主文件的 Artifact Set Manifest 必须列出全部 Domain 子文件和 Supporting Artifact；frozen Revision 通过 Manifest 固定其成员关系和内容摘要。

## 核心章节

以下章节不得删除或标记为 `n/a`：

- Summary；
- Scope；
- Design Baseline and Change；
- Requirement Traceability；
- Design Decisions；
- Design Concern Assessment；
- Design Index；
- Artifact Set Manifest；
- Domain Detail Records；
- Open Items；
- Evidence；
- Exceptions；
- Lifecycle Applicability；
- Gate。

固定章节始终保留，但允许的内容基数不同：

| 章节类型 | 章节 | 规则 |
|---|---|---|
| `required_nonempty` | Summary、Scope、Design Baseline and Change、Requirement Traceability、Design Index、Artifact Set Manifest、Lifecycle Applicability、Gate | 必须包含支持当前 DSN 的有效内容 |
| `empty_allowed` | Design Decisions、Design Concern Assessment、Domain Detail Records、Open Items、Evidence、Exceptions | 没有条目时使用本节或 Core 规定的唯一空表示，不得创建伪记录 |

`empty_allowed` 表示合法空集合，不表示该章节 Disposition 为 `n/a`。Design Decisions、Design Concern Assessment 或 Domain Detail Records 无条目时，章节正文固定写作 `None — <客观原因>`；Core 已定义空行的章节继续使用 Core 表格。Lifecycle Applicability 必须始终逐项填写。

## Design Baseline and Change

DSN 必须明确当前状态、目标状态和两者之间的设计变化，避免 PLN、IMP 或 VFY 重新猜测范围。

```markdown
| Change Type | Current Baseline Reference | Target State Summary | Impact Summary |
|---|---|---|---|
| incremental | | | |

| Change ID | Object or Boundary | Change | Baseline Reference | Baseline State | Target State | Affected Domains |
|---|---|---|---|---|---|---|
| CHG-001 | | modify | | | | |
```

规则：

- `Change Type` 使用 `new`、`incremental` 或 `reuse`；
- `Change` 使用 `add`、`modify`、`remove` 或 `reuse`；
- `new` 可以将 Current Baseline 标记为 `N/A`，但必须说明不存在有效基线的原因；
- `incremental` 的 Baseline 与 Change Set 必须足以还原 Target State；
- `reuse` 必须引用准确基线，并记录其对当前 Requirement 的适配结论和 Evidence；
- Project Context Contract 未定义前，Baseline 使用不可变 Artifact Reference 或 Evidence，不得引用会静默变化的描述；
- 当前 Scope 内的 Change Set 必须完整枚举；未列入 Change Set 的 Baseline 内容保持不变；
- 每个 Change Item 必须具有准确 Baseline Reference；`new` 项使用 `N/A` 并说明没有既有对象；
- `Scope + Baseline + Change Set` 必须唯一确定 Target State；
- `Impact Summary` 只是从 Change Set、Concern Assessment 和 Design Applicability Matrix 派生的阅读摘要，不得引入这些结构化记录中不存在的新影响；
- Change Set 只描述设计对象和变化，不包含任务、顺序、工期或实施负责人。
- 当 DSN 是直接 Binding 来源、建议 `PLN=n/a/waived` 且 `IMP=required` 时，每个 Change Item 的 `Object or Boundary` 必须使用 PLN Scope Token 语法；全部 Change Item 的并集是直接 IMP Execution Scope，且必须只包含一个 `resource:<versioned-resource-id>`。无法确定、涉及多个版本化 Resource 或需要协调时，PLN 必须为 `required`。

## Requirement Traceability

```markdown
| Source References | Design Item or Member References | Decision References | VFY Point or Objective References | N/A Reason |
|---|---|---|---|---|
| REQ-...@1#R-001 | DSN-...@1#CHG-001 | DEC-001 | VFP-230-001 | N/A |
```

规则：

- 每个 Requirement Item 必须至少关联一个稳定 Design Item 或 Member Reference；
- 当前 DSN Scope 内的每个 Acceptance Criterion 必须能够追踪到 Design Item 和后续 VFY Objective；无需独立 Design Item 时，`Design Item or Member References` 填写 `N/A`，`N/A Reason` 填写客观原因，但仍必须映射 VFY Objective；正常映射的 `N/A Reason` 固定写 `N/A`；
- `Source References` 可以引用 Requirement、Acceptance Criterion、Goal（含 Intended Use）、Affected Party 中的 Stakeholder Need、Constraint 或 Baseline；Operational Context 只作为补充 Evidence 或 Constraint，不单独充当 Validation 目标；
- 不需要设计的 Requirement Item 必须明确说明原因；
- 多值字段使用 Core Reference Set；跨 Artifact 引用使用准确 `Artifact ID@Revision#Item ID`；
- v0.1 不允许用可改名的 Markdown 标题或自然语言章节名充当引用；跨文件设计结果使用完整 Member Reference，文件内结果使用已分配 Item ID；
- Design Item、Decision 和 VFY Point 必须能够反向查到 Requirement、Acceptance Criterion、Goal、约束或准确 Baseline；
- 无上游来源或 Baseline 依据的孤立设计内容不能通过 Gate；
- DSN 不得创建未经过 REQ 确认的新业务规则。

## Design Decisions

```markdown
| ID | Requirement or Constraint References | 决策问题 Decision Question | 候选方案 Options | 选择结果 Decision | 选择依据 Rationale | 影响 Domain Affected Domains |
|---|---|---|---|---|---|---|
| DEC-001 | | | | | | |
```

规则：

- Design Decision 使用 `DEC-001` 顺序编号；
- 不得只写最终方案而完全不记录依据；
- 强制约束必须引用 Requirement 或 Evidence；
- 设计偏好不得伪装成 Requirement；
- 所有需要比较和确认的技术选型统一记录为 Design Decision；
- 选型结果由受影响的 Domain 引用同一个 `DEC-ID`，不得在多个 Domain 重复选择过程；
- 项目规范已经强制指定的技术属于既有约束，只需准确引用，不得虚构候选方案重新比较；
- `Affected Domains` 使用注册表中的英文标准名，以 `, ` 分隔、去重并按 Design Applicability Matrix 固定顺序排列；同一选型影响多个 Domain 时必须完整列出；
- Project Context Contract 闭合后，已生效且会被后续重复使用的项目级 Decision，可以由 Context 登记完整 `DSN-ID@Revision#DEC-ID` 引用；原 DSN 仍是唯一权威来源；
- Design Pattern 不是独立 Domain，Pattern 名称本身也不是选择依据；
- 局部、可逆且不影响稳定边界或质量属性的实现方式，可以留给 IMP 在项目约束内决定；
- 改变系统、组件、稳定 Contract、扩展点或质量属性的 Pattern，必须记录为 Design Decision；
- 存在可行的直接实现时，应将其作为候选方案；选择更复杂方案时，选择依据必须说明直接实现为何不足以及新增代价；
- 项目规范已经强制采用的 Pattern 属于既有约束，只需准确引用，不得重复进行虚假选型；
- 只有存在真实选择时才创建新 Decision，不得为了通过模板虚构候选方案；没有新 Decision 时使用本 Spec 的唯一 `None — <客观原因>` 空表示，并在原因中引用覆盖当前设计的既有 Decision 或强制约束。
- 一个 DSN Artifact 至少包含一个可追踪的 Design Result；当 REQ 与准确 Baseline 已完整确定结果，且不存在独立设计选择、边界变化、动态规则或质量影响时，DSN 应为 `n/a`，不创建空 DSN。固定静态内容只是该情形的一个示例。

## Scope and Simplicity

- 每项设计内容必须追踪到 Requirement、准确 Baseline 或已确认约束；Project Context Contract 闭合前，Context 不能作为可验证来源，只能改用不可变 Artifact Reference 或 Evidence；
- 不得增加未被要求的功能、配置能力、扩展点或抽象层；
- 不得顺手重构、替换或优化当前范围之外的内容；
- 发现相邻问题时，只有其阻塞当前目标或改变当前风险时才能进入当前 DSN，否则仅报告，不纳入设计；
- 存在歧义、缺失或多种合理解释时必须显式记录，不得静默选择后继续扩张；
- 采用比直接实现更复杂的方案时，必须说明简单方案为何不足；
- 每项关键 Design Decision 必须具有对应 VFY Point；
- 最小设计表示满足全部 Requirement 和适用质量约束的最小充分设计，不表示省略必要的安全、可靠性或验证工作。

## Design Concern Assessment

先记录影响事实，再依据 Core Disposition 顺序生成 Design Applicability Matrix，避免同一事实在不同执行过程中被直接解释成不同 Disposition。

```markdown
| Concern ID | Category | Source Reference | Related Change or Design Reference | Concern or Changed Object | Impact | Baseline Reference | Deviation | Mapped Domains | Evidence Reference |
|---|---|---|---|---|---|---|---|---|---|
| CON-001 | contract | REQ-...@1#R-001 | CHG-001 | | yes | | | Interfaces and Integration | EVD-001 |
```

规则：

- `Category` 使用 `behavior`、`interaction`、`structure`、`contract`、`data`、`quality`、`runtime`、`verification` 或 `other`；
- `Impact` 使用 `yes`、`no` 或 `unknown`；`unknown` 形成阻塞 Open Item；
- `Related Change or Design Reference` 引用 `CHG-ID`、`DEC-ID`、`DDR-ID`、Domain Item、Member Reference 或准确 Baseline；没有新 Change 的复用型 Concern 使用 Baseline 或 Member Reference，不引用自然语言章节名；
- 已由 Requirement、Change 或 Decision 直接表达且能够作为 Matrix Basis 的影响不再重复创建 Concern；只有跨领域、存在歧义、无法直接表达或需要独立评估的影响才创建记录。没有独立 Concern 时使用统一空表示；
- `Mapped Domains` 使用注册表英文标准名，以 `, ` 分隔、去重并按 Matrix 固定顺序排列；`yes` 必须映射到一个或多个已注册 Domain，无法映射时只填写 `unsupported` 并阻塞 Gate；
- Baseline 已完整覆盖且无偏差时，相关 Domain 可以为 `embedded`；存在独立新增设计义务或 Baseline 偏差时为 `required`；
- Concern Assessment 记录 Applicability 的输入事实和分类；Change Set 记录权威设计变化，Requirement Traceability 记录其来源与 VFY 去向，不再维护重复的 Impact Register。

## Design Applicability Matrix

| 分组 Group | 设计领域 Design Domain | 处置 Disposition | 完成状态 Completion | 责任角色 Responsible Role | 内容引用 Content Reference | 适用性依据引用 Applicability Basis References | Domain Gate Record Reference |
|---|---|---|---|---|---|---|---|
| 行为设计 Behavior | 流程与状态 Workflow and State | pending | not_started | | | | |
| 行为设计 Behavior | 用户体验与交互 UX and Interaction | pending | not_started | | | | |
| 行为设计 Behavior | 界面与内容 UI and Content | pending | not_started | | | | |
| 行为设计 Behavior | 可访问性与国际化 Accessibility and Internationalization | pending | not_started | | | | |
| 技术设计 Technical | 系统与架构 System and Architecture | pending | not_started | | | | |
| 技术设计 Technical | 组件与模块 Components and Modules | pending | not_started | | | | |
| 技术设计 Technical | 接口与集成 Interfaces and Integration | pending | not_started | | | | |
| 技术设计 Technical | 数据设计 Data Design | pending | not_started | | | | |
| 质量属性 Quality | 安全、隐私与合规 Security, Privacy and Compliance | pending | not_started | | | | |
| 质量属性 Quality | 性能与容量 Performance and Capacity | pending | not_started | | | | |
| 质量属性 Quality | 可靠性与恢复 Reliability and Recovery | pending | not_started | | | | |
| 质量属性 Quality | 兼容与迁移 Compatibility and Migration | pending | not_started | | | | |
| 质量属性 Quality | 可维护性与扩展性 Maintainability and Extensibility | pending | not_started | | | | |
| 运行设计 Operations | 部署与配置 Deployment and Configuration | pending | not_started | | | | |
| 运行设计 Operations | 可观测性与可运维性 Observability and Operability | pending | not_started | | | | |
| 验证设计 Verification | 可验证性与 VFY 策略 Verifiability and VFY Strategy | pending | not_started | | | | |

固定章节名、分组名、Domain 名、公共字段和公共枚举同时提供中文名称与英文标准名称；Domain 专属说明以中文为主，保留稳定英文术语，不要求逐句双语复制。

本矩阵是 `sdlc-ai-spec` 的设计承载分类，不声称穷尽任何外部质量模型。发现无法映射到已注册 Domain 的设计或质量关注时，必须进入阻塞 Open Item，直到映射到现有 Domain 或由后续扩展机制登记。

### Completion

| 值 Value | 含义 Meaning |
|---|---|
| `not_started` | 尚未开始 |
| `in_progress` | 正在设计 |
| `complete` | 必填内容完整、适用规则满足且 Domain Gate 已关闭 |
| `not_applicable` | Domain 客观不适用 |
| `waived` | Domain 适用但经授权未执行 |

Completion 是根据 Disposition、Content Reference 和 Domain Gate 派生的状态，不由生成者自由选择：

| 条件 Condition | Completion |
|---|---|
| Disposition 为 `pending` | `not_started` |
| `required` 且尚无 `DOM-ID`，或 `embedded` 且尚无有效 `DDR-ID` | `not_started` |
| 复合 Domain 为 `n/a` 或 `waived`，但尚无有效 `DDR-ID` | `in_progress` |
| 已有 Content Reference，但 Domain Gate 为 `pending`、`fail`，或任一绑定 Digest 已失效 | `in_progress` |
| `required` 或 `embedded`，且 Domain Gate 为 `pass` 或 `pass_with_exception` | `complete` |
| Disposition 为 `n/a`，且复合 Domain 已有有效 DDR 或当前 Domain 非复合 | `not_applicable` |
| Disposition 为 `waived`，且复合 Domain 已有有效 DDR 或当前 Domain 非复合 | `waived` |

### 一致性规则

- `required` 最终必须对应 `complete`，Content Reference 填写完整 `DSN-ID@Revision/DOM-<DOMAIN-NO>` Member Reference；
- `embedded` 最终必须对应 `complete`，Content Reference 填写完整 `DSN-ID@Revision#DDR-<DOMAIN-NO>-001` Item Reference；具体 Host 只在 DDR 保存；
- `n/a` 必须对应 `not_applicable`：非复合 Domain 的 Content Reference 填写 `N/A`，复合 Domain 填写完整 `DSN-ID@Revision#DDR-<DOMAIN-NO>-001` Item Reference；Applicability Basis References 保存客观依据；
- `waived` 必须对应 `waived`：非复合 Domain 的 Content Reference 填写 `N/A`，复合 Domain 填写完整 `DSN-ID@Revision#DDR-<DOMAIN-NO>-001` Item Reference；Applicability Basis References 必须引用有效 Exception；
- `pending`、`not_started` 或 `in_progress` 不能进入 `ready` 或 `ready_with_exception`；
- `required` 和 `embedded` Domain 必须填写 Matrix 的 `Responsible Role`；Host Owner 只能作为确定该角色的依据，不能替代该字段；
- 所有核心 Domain 必须在矩阵中恰好出现一次；
- 核心 Domain 不允许删除或改名；
- Domain 适用性由 Requirement 和影响范围决定，不能因为参与者选择不阅读、不熟悉该领域或直接接受 AI 设计而标记为 `n/a`；
- 责任角色表示对设计结果和下游衔接负责，不表示该角色必须逐项阅读 Domain 子文件；
- 责任角色是 Design Owner，不自动成为 PLN 或 IMP 的任务负责人；
- 最终确认表示确认者接受当前 Artifact Set 及其风险，不表示所有 Domain 内容均经过人工逐行审阅；
- 项目扩展 Domain 必须有中英文名称和固定子模板；
- Applicability Basis References 保存 Disposition 的输入依据：优先引用 `CON-ID` 或 `CHG-ID`，也可以引用 Requirement、Baseline、Evidence 或 Exception，并使用 Core Reference Set；
- Domain Gate Record Reference 是派生字段：只有 `required` 或 `embedded` 填写 `DGR-ID`；`n/a` 和 `waived` 填写 `N/A`，不得在 Matrix 复制逐项 Gate Evidence；
- Domain Gate 为 `fail` 时，Completion 仍为 `in_progress`，同时父 Artifact Gate 必须为 `fail`；只有有效的 `pass` 或 `pass_with_exception` 才能派生 `complete`。

### 产物集清单 Artifact Set Manifest

```markdown
| Member ID | Type | Domain | Domain Spec Reference or Digest | Path or Reference | Media Type | Purpose | Design Input Digest | SHA-256 Digest | Empty Reason |
|---|---|---|---|---|---|---|---|---|---|
| DGC-001 | control | Multiple | N/A | controls/domain-gates.md | text/markdown | Domain Gate Records | N/A | | N/A |
| DOM-110 | domain | Workflow and State | drafts/200-dsn-domains/110-workflow-state.md@sha256:... | domains/110-workflow-state.md | text/markdown | | | | |
```

Manifest 只登记父 DSN 之外的 Artifact Set 成员。DSN 注册 `DOM-<DOMAIN-NO>` 作为 Domain Member ID、`DGC-001` 作为全部 DGR 的 control member，其他 Supporting Artifact 继续使用 `SUP-001`；同一逻辑成员跨 Revision 保持 ID。Domain Markdown 不再包含 Gate，`Design Input Digest` 与其原始字节 SHA-256 相同；图片、Schema 和其他不含 Gate 派生内容的成员也使用原始字节 SHA-256；control member 是 Gate 派生结果，Design Input Digest 固定为 `N/A`。Domain Member 必须填写其 Spec 的 Spec Reference，其他成员填 `N/A`。

`DGC-001` 在首次 Domain Gate Attempt 前登记并在计算 Parent Design Input Digest 时保留，原始 SHA-256 暂时留空；全部 DGR 完成后再填写。只要当前或历史 DGR 存在，该成员就不得删除。frozen Revision 中的路径或引用、Spec、Design Input Digest 和原始字节 SHA-256 必须固定；无成员时按 Core 空清单规则填写。

### 领域明细记录 Domain Detail Records

`embedded` 不创建 Domain 子文件，但必须在主文件中保存一个固定 Domain Detail Record Block；准确 Host 只作为引用，不能代替该记录。非 `required` 的复合 Domain 使用一个 Block，并按子规范固定顺序为每个 Subdomain 保存一行，不在 Matrix 单元格中拼接自由文本：

```markdown
### DDR-<DOMAIN-NO>-001

| Domain Spec Reference or Digest | Domain or Subdomain | Disposition | Obligation or Impact | Applicability Basis References | Baseline or Host Reference | Host Content Digest | Deviation or N/A Reason | VFY Point References | Exception References |
|---|---|---|---|---|---|---|---|---|---|
| drafts/200-dsn-domains/230-interfaces-integration.md@sha256:... | Interfaces and Integration | embedded | | CON-001 | | | none | | |

| Supporting Member Reference | Purpose |
|---|---|
| DSN-...@1/SUP-001 | |

<仅当 Domain Spec 明确定义额外 embedded 表时追加；不得自由增加字段>
```

规则：

- Domain Detail Record ID 使用 `DDR-<DOMAIN-NO>-001`，在父 DSN Artifact 内稳定且不得复用；每个简单 `embedded` Domain 创建一个 Block，每个非 `required` 的复合 Domain 也只创建一个 Block；
- 复合 Domain Block 必须包含子规范登记的全部 Subdomain，每个 Subdomain 恰好一行并按子规范固定顺序排列；不得为每个 Subdomain 再创建相互冲突的 DDR ID；
- 每个 Block 从 `### DDR-...` 标题开始，到下一个三级或更高层级标题之前结束；整个 Block 使用 UTF-8、LF 且无 BOM 的原有字节计算 Domain Control Input Digest；
- v0.1 的 Host 只允许指向另一不可变 Artifact 的完整 Item Reference、当前 Artifact Set 中已登记 Design Input Digest 的 Member，或具有内容摘要的不可变外部引用；
- 父 DSN 主文件中的章节或 Item 不能作为 Host：当前 Contract 未定义不引入摘要循环的主文件 Item Digest。若设计结果只存在于父主文件，应将内容移入已登记 Member 并引用，或把该 Domain 改为 `required`；
- `Host Content Digest` 使用被引用 Artifact Item 所属 Revision 的 Control Input Digest、Member 的 Design Input Digest，或外部不可变内容摘要；
- 所有参与该 embedded 设计的 Supporting Member 必须在 Block 内使用完整 Member Reference 并按 Member ID 升序登记；其 Design Input Digest 只从 Manifest 解析，不在 DDR 重复维护；
- `embedded` 只有在 Block 完整覆盖适用义务、没有未处理偏差、VFY Point 可追踪且同版 Domain Gate 已关闭时才能标记为 `complete`；
- 复合 Domain 的 `n/a` Subdomain 保存原因和 Evidence，`waived` Subdomain 保存 Exception；聚合 Domain 为 `required` 时使用 Domain 子文件中字段相同的 Subdomain Control Record，其他聚合结果使用父主文件的单一 DDR Block；非复合顶层 Domain 的 `n/a` 或 `waived` 只在 Matrix 保存，不创建 Detail Block；
- 通用 DDR 表是 `embedded` 的默认最小 Contract，因为实际设计结果必须已由准确 Host 完整承载；Domain Spec 只有在通用字段不足时才增加固定 embedded 表；
- 需要记录新的 Domain 专属设计内容、但 Domain Spec 没有固定 embedded 字段时，该 Domain 必须改为 `required`，不得自由增加字段；当前 Verifiability Domain 明确定义了额外最小表。

### Parent Design Input Digest

Parent Design Input Digest 在执行任何 Domain Gate 前计算，按 Core Control Input Digest 的文本规则处理父 DSN 主文件，并使用以下额外规则：

1. Design Applicability Matrix 的 `Completion` 和 `Domain Gate Record Reference` 单元格视为空值；Disposition、Content Reference、Applicability Basis References 等设计输入仍保留；
2. Artifact Set Manifest 的 `SHA-256 Digest` 单元格视为空值，`Design Input Digest`、Domain Spec Reference 和其他成员字段仍保留；`DGC-001` 行必须已经登记且其 Design Input Digest 为 `N/A`；
3. 其他主文件内容均保留原有顺序和字节。

任一 Domain、Host、Schema、原型或其他设计输入发生变化，其 Design Input Digest 或父文件内容随之变化，所有绑定旧 Parent Design Input Digest 的 Domain Gate Record 均失效。

### Domain Gate Control Member

所有 `required` 和 `embedded` Domain 的完整 Gate Record 固定保存在 `DGC-001` 对应的 `controls/domain-gates.md`；Domain 子文件只保存设计输入。文件使用以下结构：

```markdown
# Domain Gate Records

## DGR-<DOMAIN-NO>-001

| Gate Record ID | Parent DSN Revision | Parent Design Input Digest | Domain Evaluation Contract Set | Domain Control Input Digest | Result | Exception References | Evaluator | Evaluated At |
|---|---|---|---|---|---|---|---|---|
| DGR-<DOMAIN-NO>-001 | 1 | | | | pending | None | | |

| Check ID | Result | Evidence or Notes |
|---|---|---|
| DSN-DG-<DOMAIN-NO>-<CHECK-NO> | pending | |
```

规则：

- Domain Gate Record Reference 必须指向完整记录，不能只填写聚合结果或单条 Evidence；
- 每次重新执行 Domain Gate 都分配下一个 `DGR-<DOMAIN-NO>-<NNN>`，旧 Attempt 保留在 control member 中，不能原地改写为新结果；
- 完整记录必须包含该 Domain 全部适用 Check ID、逐项结果和 Evidence；
- `Domain Evaluation Contract Set` 至少包含 Core Spec、DSN Phase Spec 和当前 Domain Spec；实际启用的 Extension Contract 也必须加入，并使用 Core Reference Set 语法；
- Parent Design Input Digest 只保留已登记、原始 SHA 留空的 `DGC-001` Manifest 行；全部 DGR 写入后刷新 control member 原始 SHA，最终 Artifact Control Input Digest 通过 Manifest 绑定它，因此记录变化会使人工确认和父 Artifact Gate 失效；
- Design Applicability Matrix 对 `required` 和 `embedded` 只引用 `DGR-ID`；逐项 Evidence 只由 Gate Check 引用，避免多处复制；
- 每个 Domain 全局编号最大的 DGR 是唯一 Current Attempt；只有它同时匹配当前 Parent DSN Revision、Parent Design Input Digest、Domain Evaluation Contract Set 和 Domain Control Input Digest 时才有效；
- Matrix 只能引用 Current Attempt。最新 Attempt 的输入组合不匹配、Result 为 `fail` 或 `pending` 时，Domain Gate 无效；不得向后搜索或恢复更早的 `pass`，重新执行必须分配更大的 DGR ID；
- 任一 Current Domain Gate 为 `pass_with_exception`，或任一 Subdomain 存在未关闭 Waiver，其 Exception 必须进入 Parent Exception Set，父 Gate 只能为 `pass_with_exception`。

## Domain 子文件

每个 `required` Domain 使用相同的精简外壳，具体设计结果使用该 Domain 的固定专属模板：

```markdown
# <中文名称 English Name>

| 关联项 Relation | 值 Value |
|---|---|
| 父 DSN ID Parent DSN ID | DSN-... |
| Requirement References | REQ-...@1#R-001 |
| Decision References | DEC-001 |
| Supporting Member References | None |

<当前 Domain 的固定专属模板，从 Design Result 开始>

## 约束与影响 Constraints and Impact

| 类型 | 内容 | 影响的下游 Phase |
|---|---|---|
| | | |

## VFY 要点 VFY Points

| ID | Requirement, AC or Design References | 验证对象 Verification Object | 可观察结果 Observable Result | 预期 Evidence Expected Evidence |
|---|---|---|---|---|
| VFP-<DOMAIN-NO>-001 | | | | |

```

规则：

- 只创建 Disposition 为 `required` 的 Domain 子文件；
- Domain 子文件按照 Design Applicability Matrix 的固定顺序编号；
- `embedded` 通过矩阵引用 DDR，不重复完整 Domain 模板；DDR 保存适用义务、Host、偏差和 VFY Point；所有完整 DGR 只保存在 `DGC-001`；
- 非复合 Domain 的 `n/a` 只在矩阵说明原因；复合 Domain 的 `n/a` 还必须在主文件创建单一 DDR Block，按固定子领域顺序保存各自原因与 Evidence；两者都不创建 Domain 子文件；
- 非复合 Domain 的 `waived` 只在矩阵引用 Exception；复合 Domain 的 `waived` 还必须在主文件创建单一 DDR Block，按固定子领域顺序保存各自 Disposition 与 Exception；两者都不创建 Domain 子文件；
- Domain 子文件不得重复 Summary、Scope 和候选方案；
- 候选方案与选择依据统一记录在主文件 Design Decisions；
- Domain 子文件必须显式记录稳定父 `DSN-ID`；准确 Revision 及成员摘要由父 Artifact Set Manifest 绑定，不只依赖目录关系；
- Domain 中所有 Item ID 在父 DSN Artifact Set 内必须唯一，跨 Artifact 引用使用 `DSN-ID@Revision#Item-ID`；
- VFY Point ID 使用 `VFP-<DOMAIN-NO>-<NNN>`，例如 `VFP-110-001`；
- VFY Points 只描述需要观察的结果，不提前指定测试工具和执行计划；
- DGR `Result` 使用 Aggregate Gate Result：`pending`、`pass`、`pass_with_exception` 或 `fail`；Domain 整体 `n/a` 和 `waived` 只保存在 Design Index，不伪装为 Domain Gate `pass`；
- Gate Record ID 使用 `DGR-<DOMAIN-NO>-001`；每次重新执行都分配下一个 ID，旧 Attempt 作为历史记录保留且不得覆盖；Current Attempt 与 Matrix 引用使用上文相同的确定规则；
- Domain 子文件的 Domain Control Input Digest 对完整原始字节计算；embedded Domain 继续对完整 DDR Block 计算；
- `required` 或 `embedded` Domain 只有在 Current Attempt 不存在 `pending` 或 `fail`，且已绑定父 Revision、Parent Design Input Digest、当前 Domain Evaluation Contract Set 和 Domain Control Input Digest 时才能标记为 `complete`；
- Parent Design Input Digest、Domain 内容、Domain Evaluation Contract Set 或 Domain Control Input Digest 任一变化后，旧 Gate Record 失效；
- Domain Gate 为 `pass_with_exception` 时，Exception References 不得为空，并按父 Gate 聚合规则传播；
- Domain 与 Subdomain 的 Exception 都使用父 DSN 主文件中的 `EX-ID`；Domain 子文件不得建立第二套 Exception 表；
- 所有 `DSN-DG-<DOMAIN-NO>-<NNN>` 都是 Contract Integrity Check，只允许 `pass`、`fail` 或 `pending`。DGR 只为顶层 `required` 或 `embedded` Domain 生成；其中的内容 Check 只检查未被豁免的 Domain/Subdomain 义务，复合 Domain 内的 `n/a` 子领域只检查原因与 Evidence，`waived` 子领域只检查有效 Exception。顶层 `n/a` 或 `waived` 不生成 DGR，由 `DSN-G-007` 检查；不得把单个 Gate Check 直接标为 `n/a` 或 `waived`；
- 不得创建未注册 Domain 子文件。

Domain 整体适用但某个可选子章节不适用时，保留该子章节标题，以固定文本 `N/A — <客观原因>` 代替整张空表。仅个别非 Reference 字段不适用时，该单元格写作 `N/A — <客观原因>`；Reference 字段继续按 Core 固定为精确 `N/A`，原因由相邻 Reason 字段或当前子章节文本承载。当同一行的固定枚举已唯一决定互斥字段不适用时，互斥字段也可以只写 `N/A`，原因由该枚举承担。不得保留空白占位行或把原因任意写入其他字段。

### Parent Exception Set

Parent Exception Set 是父 DSN 主文件 `Exceptions` 表中全部 `active` 和 `carried` 的本地 `EX-ID`，去重后按编号升序排列。它是确定性派生集合，不另建第二张人工维护的表。

- 与当前 Design Scope 相交的上游未关闭 Exception 必须先在父表建立 `carried` 记录并保存 Origin Exception Reference；只有可确定性证明不相交的记录可以排除，无法确定时仍按相关处理；
- Matrix、DDR 和 Current DGR 只能引用父表中可解析的 `EX-ID`；Current DGR 的 Exception References 必须恰好包含该 Domain Attempt 所涉及的未关闭 Exception；
- Domain、Subdomain 或具体设计义务的 Waiver 必须进入 Parent Exception Set；一般性 DSN Exception 也按同一状态规则进入该集合；
- Human Confirmation 和最终 Artifact Gate Summary 都绑定同一个 Parent Exception Set。任何集合变化都会使旧确认和汇总失效；
- `resolved` 或 `superseded` 记录保留在父表中，但不进入当前集合。

## 核心 Domain 子规范

主文件只定义 DSN 公共 Contract、Domain 注册表和聚合 Gate。各 Domain 的适用性、固定模板、规则及专属 Gate 分别保存在以下子规范中。

| 顺序 Order | 分组 Group | 设计领域 Design Domain | 子规范 Domain Spec |
|---|---|---|---|
| 110 | 行为设计 Behavior | 流程与状态 Workflow and State | [110-workflow-state.md](200-dsn-domains/110-workflow-state.md) |
| 120 | 行为设计 Behavior | 用户体验与交互 UX and Interaction | [120-ux-interaction.md](200-dsn-domains/120-ux-interaction.md) |
| 130 | 行为设计 Behavior | 界面与内容 UI and Content | [130-ui-content.md](200-dsn-domains/130-ui-content.md) |
| 140 | 行为设计 Behavior | 可访问性与国际化 Accessibility and Internationalization | [140-accessibility-i18n.md](200-dsn-domains/140-accessibility-i18n.md) |
| 210 | 技术设计 Technical | 系统与架构 System and Architecture | [210-system-architecture.md](200-dsn-domains/210-system-architecture.md) |
| 220 | 技术设计 Technical | 组件与模块 Components and Modules | [220-components-modules.md](200-dsn-domains/220-components-modules.md) |
| 230 | 技术设计 Technical | 接口与集成 Interfaces and Integration | [230-interfaces-integration.md](200-dsn-domains/230-interfaces-integration.md) |
| 240 | 技术设计 Technical | 数据设计 Data Design | [240-data-design.md](200-dsn-domains/240-data-design.md) |
| 310 | 质量属性 Quality | 安全、隐私与合规 Security, Privacy and Compliance | [310-security-privacy-compliance.md](200-dsn-domains/310-security-privacy-compliance.md) |
| 320 | 质量属性 Quality | 性能与容量 Performance and Capacity | [320-performance-capacity.md](200-dsn-domains/320-performance-capacity.md) |
| 330 | 质量属性 Quality | 可靠性与恢复 Reliability and Recovery | [330-reliability-recovery.md](200-dsn-domains/330-reliability-recovery.md) |
| 340 | 质量属性 Quality | 兼容与迁移 Compatibility and Migration | [340-compatibility-migration.md](200-dsn-domains/340-compatibility-migration.md) |
| 350 | 质量属性 Quality | 可维护性与扩展性 Maintainability and Extensibility | [350-maintainability-extensibility.md](200-dsn-domains/350-maintainability-extensibility.md) |
| 410 | 运行设计 Operations | 部署与配置 Deployment and Configuration | [410-deployment-configuration.md](200-dsn-domains/410-deployment-configuration.md) |
| 420 | 运行设计 Operations | 可观测性与可运维性 Observability and Operability | [420-observability-operability.md](200-dsn-domains/420-observability-operability.md) |
| 510 | 验证设计 Verification | 可验证性与 VFY 策略 Verifiability and VFY Strategy | [510-verifiability-vfy-strategy.md](200-dsn-domains/510-verifiability-vfy-strategy.md) |

所有子规范均受本文件中的 Artifact Set、Disposition、Completion、Scope and Simplicity 以及主 Gate 约束；子规范不得重定义这些公共语义。

各 Domain 的 Applicability 仍按 Core 固定顺序判断；子规范中的“通常 required”只表示存在潜在独立设计义务，不能覆盖有效 `embedded` Host。DSN Artifact 的最终 Evaluation Contract Set 必须绑定本注册表全部 Domain Spec，确保 `n/a`、`waived` 与适用 Domain 使用同一组规则；单个 DGR 仍只绑定当前 Domain Spec。

## DSN 最终化顺序

DSN 在 Core 通用最终化顺序内使用以下确定步骤：

1. 冻结本次设计输入，并分配稳定的 `DDR-ID` 和 Member ID；
2. 计算所有 Domain、Host 与 Supporting Member 的 Design Input Digest；Domain Markdown 和其他不含 Gate 派生内容的成员均使用原始字节摘要；
3. 刷新 Manifest 的 Design Input Digest，并计算 Parent Design Input Digest；
4. 为每个顶层 `required` 或 `embedded` Domain 执行逐项 Gate，先分配下一个 `DGR-ID` 再保存完整 DGR；DGR 只能引用步骤 1 至 3 已登记的 Evidence 与 Exception；
5. 选择每个顶层 `required` 或 `embedded` Domain 的 Current Attempt，由其派生 Completion 和 Matrix 中的 DGR Reference；顶层 `n/a` 或 `waived` 不选择 Attempt。Parent Exception Set 始终从父 Exceptions 表的 `active`、`carried` 记录派生，并校验每个 Current DGR 的 Exception References 是其准确子集；
6. 刷新并验证 Manifest 的最终原始字节 SHA-256；
7. 执行 Core 与 DSN Check，`CORE-G-009` 暂时保持 `pending`；
8. 计算最终父 Artifact Control Input Digest；
9. 按 Core 计算 Check Set Result Digest，人工确认两个 Digest、Evaluation Contract Set 及全部未关闭 Exception；
10. 关闭 `CORE-G-009`，聚合唯一 Artifact Gate Summary 并派生 Status；只在结果为 `pass` 或 `pass_with_exception` 时冻结 Snapshot，其他结果保持 open，并在冻结前复核全部摘要和映射。

步骤 1 至 8 中发现需要新增或修改设计内容、Evidence、Exception 或其他被摘要覆盖的输入时，当前 DGR 只保留为历史 Attempt，返回步骤 2 后重新计算，并在下一次步骤 4 分配更大的 DGR ID；不得只重写 Digest、Completion 或 Gate Result。

## Lifecycle Applicability

```markdown
| Phase | Disposition | Host | 判断依据 Basis |
|---|---|---|---|
| PLN | pending | N/A | Pending — <OI-ID> |
| IMP | pending | N/A | Pending — <OI-ID> |
| VFY | required | N/A | VFY Artifact 为固定控制点 |
| RLS | pending | N/A | Pending — <OI-ID> |
```

该表只记录当前 DSN 覆盖范围对后续 Phase 的建议，不负责排期、任务分配，也不能覆盖同一交付范围内其他 Artifact 的判断。多个完整 Scope Input 共同交付时，按 Core Delivery Scope Aggregation Contract 执行并将 PLN 标记为 `required`。

## AI 与人工协作 AI and Human Collaboration

本节是 Phase 执行指导，不进入 DSN Artifact 模板，也不作为 Gate 或 AI 使用率指标。

| 工作 Activity | AI 适合做什么 | 人工适合做什么 | 原因 Reason |
|---|---|---|---|
| Baseline 与 Domain 分析 | 发现现状、影响范围和跨 Domain 关系 | 确认关键现状和业务限制 | AI 擅长全量关联，人工掌握隐含约束 |
| 方案与影响比较 | 生成候选、分析一致性和代价 | 决定架构、接口、数据和体验取舍 | 关键设计决定需要权威与责任 |
| 详细设计 | 按 Domain 模板形成可追踪设计 | 重点评审高风险或主观领域 | AI 提高完整度，人工校准方向和风险 |
| Gate 与缺口检查 | 检查追踪、冲突、VFY Point 和复杂度 | 确认 Exception 与最终设计 | AI 适合一致性检查，风险接受必须人工完成 |

## Gate

```markdown
| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |
|---|---|---|---|
| DSN-G-001 | 直接 Input 至少包含一个准确 Requirement Revision，且当前 Design Scope 与 Input 一致 | pending | |
| DSN-G-002 | Design Boundary、Current Baseline、Target State 和 Change Set 完整且可还原 | pending | |
| DSN-G-003 | Requirement、Acceptance Criteria、Design Item、Decision 与 VFY Objective 双向可追踪，不存在孤立项或被静默修改的 Requirement | pending | |
| DSN-G-004 | Summary、Design Decisions 与各 Domain 设计结果一致，不存在重复权威来源 | pending | |
| DSN-G-005 | Change、独立 Concern 与 Design Applicability Matrix 映射完整一致，不存在未处理的 unsupported concern | pending | |
| DSN-G-006 | required 和 embedded Domain 的责任角色、Content、Current DGR、摘要绑定、Completion 及固定 N/A 表示完整一致 | pending | |
| DSN-G-007 | Domain 与 Subdomain 的 n/a、waived、Exception 和 Parent Exception Set 完整一致 | pending | |
| DSN-G-008 | 各 Design Domain 不存在冲突、重复定义或相互矛盾的边界 | pending | |
| DSN-G-009 | 所有设计均在当前范围内，复杂度必要，未引入推测性能力或未授权相邻改动 | pending | |
| DSN-G-010 | Lifecycle Applicability、Host、Basis 和已注册 Host Contract 完整一致 | pending | |
```

Artifact Gate 先包含 Core Gate Checks，再包含以上 DSN Gate Checks；之后按 Core Spec 固定顺序保存 Human Confirmation 和唯一 Artifact Gate Summary，不得只修改 Front Matter `status`。DSN Gate Checks 均为 Contract Integrity Check，不允许直接标记为 `n/a` 或 `waived`；Domain 或具体设计义务的 Waiver 由 Design Index、Domain Detail Record 和 Exception 表达，Gate Check 只验证这些记录是否合规。

## 内部编号

| 内容 Item | 格式 Format |
|---|---|
| Change Item | `CHG-001` |
| Design Decision | `DEC-001` |
| Design Concern | `CON-001` |
| Domain Detail Record | `DDR-<DOMAIN-NO>-001` |
| Domain Gate Control Member | `DGC-001` |
| Domain Gate Record Attempt | `DGR-<DOMAIN-NO>-001` |
| Domain VFY Point | `VFP-<DOMAIN-NO>-001` |
| Open Item | `OI-001` |
| Evidence | `EVD-001` |
| Exception | `EX-001` |
| DSN Gate Check | `DSN-G-001` |

## 当前未定义

- Design Domain 项目扩展的注册方式；
- 大型 Supporting Design Artifact 的最终目录结构；
- 后续 Project Bootstrap Contract：Project Context 的固定模板、状态、Revision 和更新复用规则；定义前只使用不可变 Artifact Reference 或 Evidence，不阻塞当前 DSN Contract。

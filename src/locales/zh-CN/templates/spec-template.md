# Feature Specification: [FEATURE NAME]（功能规格）

**Feature Branch**: `[###-feature-name]`

**Created**: [DATE]

**Status**: Draft

**Input**: 用户描述："$ARGUMENTS"

## User Scenarios & Testing *(mandatory)*（用户场景与测试，必填）

<!--
  重要：用户故事应作为用户旅程，按重要性排列优先级。
  每个用户故事／旅程必须可独立测试；即使只实现其中一个，
  也应得到能够交付价值的可用 MVP（最小可行产品）。

  为各故事分配优先级（P1、P2、P3 等），P1 最重要。
  将每个故事视为可独立交付的功能切片，能够：
  - 独立开发
  - 独立测试
  - 独立部署
  - 独立向用户演示
-->

### User Story 1 - [Brief Title] (Priority: P1)（用户故事一）

[用通俗语言描述这段用户旅程]

**Why this priority**: [说明价值，以及采用该优先级的原因]

**Independent Test**: [说明如何独立测试，例如“通过某个具体操作即可完整验证，并交付某种具体价值”]

**Acceptance Scenarios**:

1. **Given** [初始状态]，**When** [执行动作]，**Then** [预期结果]
2. **Given** [初始状态]，**When** [执行动作]，**Then** [预期结果]

---

### User Story 2 - [Brief Title] (Priority: P2)（用户故事二）

[用通俗语言描述这段用户旅程]

**Why this priority**: [说明价值，以及采用该优先级的原因]

**Independent Test**: [说明如何独立测试]

**Acceptance Scenarios**:

1. **Given** [初始状态]，**When** [执行动作]，**Then** [预期结果]

---

### User Story 3 - [Brief Title] (Priority: P3)（用户故事三）

[用通俗语言描述这段用户旅程]

**Why this priority**: [说明价值，以及采用该优先级的原因]

**Independent Test**: [说明如何独立测试]

**Acceptance Scenarios**:

1. **Given** [初始状态]，**When** [执行动作]，**Then** [预期结果]

---

[按需增加用户故事，并分别指定优先级]

### Edge Cases（边界情况）

<!--
  必须处理：本节内容是占位示例。
  请填写实际的边界情况。
-->

- 当出现[边界条件]时会发生什么？
- 系统如何处理[错误场景]？

## Requirements *(mandatory)*（需求，必填）

<!--
  必须处理：本节内容是占位示例。
  请填写实际的功能需求。
-->

### Functional Requirements（功能需求）

- **FR-001**: 系统必须[具体能力，例如“允许用户创建账号”]
- **FR-002**: 系统必须[具体能力，例如“验证电子邮箱地址”]
- **FR-003**: 用户必须能够[关键交互，例如“重置密码”]
- **FR-004**: 系统必须[数据要求，例如“持久化用户偏好”]
- **FR-005**: 系统必须[行为要求，例如“记录所有安全事件”]

*需求不清晰时的标记示例：*

- **FR-006**: 系统必须通过以下方式认证用户：[NEEDS CLARIFICATION: 尚未指定认证方式——邮箱／密码、SSO 还是 OAuth？]
- **FR-007**: 系统必须将用户数据保留以下时长：[NEEDS CLARIFICATION: 尚未指定保留期限]

### Key Entities *(include if feature involves data)*（涉及数据时填写关键实体）

- **[Entity 1]**: [实体含义及关键属性，不包含实现细节]
- **[Entity 2]**: [实体含义及与其他实体的关系]

## Success Criteria *(mandatory)*（成功标准，必填）

<!--
  必须处理：定义可衡量的成功标准。
  标准必须与具体技术无关，并且可以度量。
-->

### Measurable Outcomes（可衡量的结果）

- **SC-001**: [可衡量指标，例如“用户可在 2 分钟内完成账号创建”]
- **SC-002**: [可衡量指标，例如“系统处理 1000 个并发用户而不降级”]
- **SC-003**: [用户满意度指标，例如“90% 的用户首次尝试即可完成主要任务”]
- **SC-004**: [业务指标，例如“与 [X] 相关的支持工单减少 50%”]

## Assumptions（假设）

<!--
  必须处理：本节内容是占位示例。
  对功能描述中没有明确的细节，采用合理默认值，
  并据此填写适当的假设。
-->

- [目标用户假设，例如“用户具有稳定的网络连接”]
- [范围边界假设，例如“v1 不包含移动端支持”]
- [数据／环境假设，例如“复用现有认证系统”]
- [现有系统／服务依赖，例如“需要访问现有用户资料 API”]

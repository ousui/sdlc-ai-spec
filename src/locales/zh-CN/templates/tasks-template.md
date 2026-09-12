---

description: "功能实现任务清单模板"
---

# Tasks: [FEATURE NAME]（实施任务）

**Input**: 设计文档来源：`.sdlc/specs/[###-feature-name]/`

**Prerequisites**: plan.md（必需）、spec.md（用户故事必需）、research.md、data-model.md、contracts/

**Tests**: 以下示例含测试任务。测试是可选项，仅在功能规格明确要求时加入。

**Organization**: 按用户故事组织任务，使每个故事均可独立实现和测试。

## Format: `[ID] [P?] [Story] Description`（任务格式）

- **[P]**: 可并行执行（不同文件，且无依赖）
- **[Story]**: 本任务所属的用户故事（例如 US1、US2、US3）
- 描述中应包含准确的文件路径

## Path Conventions（路径约定）

- **Single project**: 仓库根目录下的 `src/`、`tests/`
- **Web app**: `backend/src/`、`frontend/src/`
- **Mobile**: `api/src/`、`ios/src/` 或 `android/src/`
- 下方路径按单项目展示，请根据 plan.md 的结构调整

<!--
  ============================================================================
  重要：以下是示例任务，仅用于说明。

  sdlc-300-task 必须根据以下来源替换为真实任务：
  - spec.md 的用户故事及其 P1、P2、P3 等优先级
  - plan.md 的功能需求
  - data-model.md 的实体
  - contracts/ 的接口端点

  任务必须按用户故事组织，确保每个故事都能够：
  - 独立实现
  - 独立测试
  - 作为 MVP 增量交付

  不得在生成的 tasks.md 文件中保留这些示例任务。
  ============================================================================
-->

## Phase 1: Setup (Shared Infrastructure)（准备：共享基础设施）

**Purpose**: 项目初始化和基础结构

- [ ] T001 按实施计划创建项目结构
- [ ] T002 初始化 [language] 项目并配置 [framework] 依赖
- [ ] T003 [P] 配置代码检查和格式化工具

---

## Phase 2: Foundational (Blocking Prerequisites)（基础：阻塞性前置条件）

**Purpose**: 在实现任何用户故事之前，必须完成的核心基础设施

**⚠️ CRITICAL**: 本阶段完成之前，不得开始用户故事工作

基础任务示例（根据项目调整）：

- [ ] T004 配置数据库模式和迁移框架
- [ ] T005 [P] 实现认证／授权框架
- [ ] T006 [P] 配置 API 路由和中间件结构
- [ ] T007 创建所有故事依赖的基础模型／实体
- [ ] T008 配置错误处理和日志基础设施
- [ ] T009 配置环境配置管理

**Checkpoint**: 基础就绪，现在可以并行开始用户故事实现

---

## Phase 3: User Story 1 - [Title] (Priority: P1) 🎯 MVP（用户故事一）

**Goal**: [简述本故事交付的内容]

**Independent Test**: [如何独立验证本故事]

### Tests for User Story 1 (OPTIONAL - only if tests requested) ⚠️（可选测试，仅在要求测试时加入）

> **说明：先编写这些测试，并确保它们在实现前失败**

- [ ] T010 [P] [US1] 在 tests/contract/test_[name].py 中编写 [endpoint] 的契约测试
- [ ] T011 [P] [US1] 在 tests/integration/test_[name].py 中编写 [user journey] 的集成测试

### Implementation for User Story 1（用户故事一的实现）

- [ ] T012 [P] [US1] 在 src/models/[entity1].py 中创建 [Entity1] 模型
- [ ] T013 [P] [US1] 在 src/models/[entity2].py 中创建 [Entity2] 模型
- [ ] T014 [US1] 在 src/services/[service].py 中实现 [Service]（依赖 T012、T013）
- [ ] T015 [US1] 在 src/[location]/[file].py 中实现 [endpoint/feature]
- [ ] T016 [US1] 添加校验和错误处理
- [ ] T017 [US1] 为用户故事一的操作添加日志

**Checkpoint**: 此时，用户故事一应功能完整并可独立测试

---

## Phase 4: User Story 2 - [Title] (Priority: P2)（用户故事二）

**Goal**: [简述本故事交付的内容]

**Independent Test**: [如何独立验证本故事]

### Tests for User Story 2 (OPTIONAL - only if tests requested) ⚠️（可选测试，仅在要求测试时加入）

- [ ] T018 [P] [US2] 在 tests/contract/test_[name].py 中编写 [endpoint] 的契约测试
- [ ] T019 [P] [US2] 在 tests/integration/test_[name].py 中编写 [user journey] 的集成测试

### Implementation for User Story 2（用户故事二的实现）

- [ ] T020 [P] [US2] 在 src/models/[entity].py 中创建 [Entity] 模型
- [ ] T021 [US2] 在 src/services/[service].py 中实现 [Service]
- [ ] T022 [US2] 在 src/[location]/[file].py 中实现 [endpoint/feature]
- [ ] T023 [US2] 根据需要与用户故事一的组件集成

**Checkpoint**: 此时，用户故事一和二都应能够独立工作

---

## Phase 5: User Story 3 - [Title] (Priority: P3)（用户故事三）

**Goal**: [简述本故事交付的内容]

**Independent Test**: [如何独立验证本故事]

### Tests for User Story 3 (OPTIONAL - only if tests requested) ⚠️（可选测试，仅在要求测试时加入）

- [ ] T024 [P] [US3] 在 tests/contract/test_[name].py 中编写 [endpoint] 的契约测试
- [ ] T025 [P] [US3] 在 tests/integration/test_[name].py 中编写 [user journey] 的集成测试

### Implementation for User Story 3（用户故事三的实现）

- [ ] T026 [P] [US3] 在 src/models/[entity].py 中创建 [Entity] 模型
- [ ] T027 [US3] 在 src/services/[service].py 中实现 [Service]
- [ ] T028 [US3] 在 src/[location]/[file].py 中实现 [endpoint/feature]

**Checkpoint**: 此时所有用户故事都应能够独立工作

---

[按需采用同一模式增加更多用户故事阶段]

---

## Phase N: Polish & Cross-Cutting Concerns（完善与跨领域事项）

**Purpose**: 改进影响多个用户故事的共性内容

- [ ] TXXX [P] 更新 docs/ 中的文档
- [ ] TXXX 清理并重构代码
- [ ] TXXX 优化所有故事的性能
- [ ] TXXX [P] 根据要求在 tests/unit/ 中增加单元测试
- [ ] TXXX 安全加固
- [ ] TXXX 执行 quickstart.md 验证

---

## Dependencies & Execution Order（依赖与执行顺序）

### Phase Dependencies（阶段依赖）

- **Setup (Phase 1)**: 无依赖，可以立即开始
- **Foundational (Phase 2)**: 依赖 Setup 完成，并阻塞所有用户故事
- **User Stories (Phase 3+)**: 均依赖 Foundational 完成
  - 人员充足时，随后可以并行开展用户故事
  - 也可以按优先级顺序执行（P1 → P2 → P3）
- **Polish (Final Phase)**: 依赖全部计划交付的用户故事完成

### User Story Dependencies（用户故事依赖）

- **User Story 1 (P1)**: Foundational（Phase 2）完成后可开始，不依赖其他故事
- **User Story 2 (P2)**: Foundational（Phase 2）完成后可开始，可与 US1 集成，但应可独立测试
- **User Story 3 (P3)**: Foundational（Phase 2）完成后可开始，可与 US1/US2 集成，但应可独立测试

### Within Each User Story（每个用户故事内部）

- 如包含测试，必须先编写测试并确认失败，再实施
- 模型先于服务
- 服务先于接口端点
- 核心实现先于集成
- 完成本故事后，再进入下一优先级

### Parallel Opportunities（并行机会）

- 所有标记 [P] 的 Setup 任务可以并行
- 所有标记 [P] 的 Foundational 任务可在 Phase 2 内并行
- Foundational 完成后，团队容量允许时可并行开始所有用户故事
- 同一用户故事中标记 [P] 的测试可以并行
- 同一故事中标记 [P] 的模型可以并行
- 不同团队成员可并行处理不同用户故事

---

## Parallel Example: User Story 1（并行示例：用户故事一）

```bash
# 如要求测试，同时启动用户故事一的所有测试：
Task: "Contract test for [endpoint] in tests/contract/test_[name].py"
Task: "Integration test for [user journey] in tests/integration/test_[name].py"

# 同时启动用户故事一的所有模型：
Task: "Create [Entity1] model in src/models/[entity1].py"
Task: "Create [Entity2] model in src/models/[entity2].py"
```

---

## Implementation Strategy（实施策略）

### MVP First (User Story 1 Only)（MVP 优先，只实现用户故事一）

1. 完成 Phase 1: Setup
2. 完成 Phase 2: Foundational（关键阶段，阻塞所有故事）
3. 完成 Phase 3: User Story 1
4. **STOP and VALIDATE**: 停止并独立验证用户故事一
5. 准备就绪后部署／演示

### Incremental Delivery（增量交付）

1. 完成 Setup + Foundational → 基础就绪
2. 加入用户故事一 → 独立测试 → 部署／演示（MVP）
3. 加入用户故事二 → 独立测试 → 部署／演示
4. 加入用户故事三 → 独立测试 → 部署／演示
5. 每个故事增加价值，且不破坏已有故事

### Parallel Team Strategy（团队并行策略）

有多名开发者时：

1. 团队共同完成 Setup + Foundational
2. Foundational 完成后：
   - 开发者 A：用户故事一
   - 开发者 B：用户故事二
   - 开发者 C：用户故事三
3. 各故事独立完成并集成

---

## Notes（说明）

- [P] 任务表示不同文件且无依赖
- [Story] 将任务关联到具体用户故事，便于追溯
- 每个用户故事均应可独立完成和测试
- 在实现前确认测试失败
- 每完成一个任务或逻辑组后提交
- 可在任何检查点停下，独立验证故事
- 避免：模糊任务、同文件冲突、破坏独立性的跨故事依赖

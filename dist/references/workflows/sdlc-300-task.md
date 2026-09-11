
<!-- SDLC-PACKAGE-BINDING:BEGIN -->
## 已安装插件与业务项目绑定

本次调用宿主为 c@@SDLC_BIND_0004@@。先完成路径绑定，再执行下面的原有流程。

- @@SDLC_BIND_0006@@。 `SDLC_PLUGIN_ROOT` 是已加载核心 Skill 目录向上两级的插件包目录（`skills/<name>/SKILL.md`）。不得从业务工作目录推断、扫描其他安装版本，或假定变量已导出。
- 保持 shell 工作目录位于选定的业务项目。执行 `SDLC_HOST=c@@SDLC_BIND_0007@@ bash "${SDLC_PLUGIN_ROOT:?}/scripts/bash/project-paths.sh"` 解析最近的已初始化 `.sdlc`。用户明确选定项目时，以命令局部变量 `SDLC_INIT_DIR` 传入其绝对路径。将返回的 `PROJECT_ROOT` 作为 `SDLC_PROJECT_ROOT`。项目不存在或无效时停止，明确运行 `sdlc-000-init` 初始化或补全；不得回退到其他工具。
- 每次使用这些变量的 shell 调用都显式传入已解析的绝对值；工具调用之间不保证 shell 状态持久化。`${VAR:?}` 有意在变量未解析时失败。非 shell 文件工具使用实际绝对路径，不把 `${VAR}` 字面量传给工具。不得通过切换到插件目录来修复资源定位。
- 创建或更新需求文件前，通过命令局部 `SDLC_INIT_DIR` 调用同一 `project-paths.sh --feature <resolved-feature-directory>`，检查显式路径和符号链接不会指向本插件。该脚本只读，不执行初始化。项目状态、当前需求和宪法不得写到插件内。
- 本包沿用仅核心、无 Preset、无 Extension、无事件的既有 profile。不得为满足引用而安装或调用扩展、上游 CLI。项目包含 `.sdlc/extensions.yml`、已安装预设或扩展状态时，停止并说明该 profile 不受支持。下面保留上游条件钩子文本用于来源等价，不构成启用可选子系统的授权。
- `$ARGUMENTS` 表示本次调用的用户输入。宿主没有替换它时，从当前对话读取这次输入；不得将占位符字面量作为需求描述。
<!-- SDLC-PACKAGE-BINDING:END -->

<!-- SDLC-OUTPUT-LANGUAGE:BEGIN -->
## 输出语言（仅呈现层）

向使用者解释流程、提问及总结时使用简体中文。仅在下面原流程要求创建或修改产物时，以简体中文填写自然语言内容；不得为了翻译新增写入或重写其他已有内容。模板固定骨架、章节定位名、占位符、状态值、任务语法、代码、路径、变量、参数、事件名及配置键保持原样。用户明确指定其他语言的内容按其要求保留。

例如保留 `User Story`、`Success Criteria`、`NEEDS CLARIFICATION`、`FR-001`、`T001`、`[US1]`、`[P]` 等机器或结构标记，业务描述、理由、测试说明和任务内容填写中文。代码块中的英文示例用于保留格式和定位约定，不要求将实际填写的自然语言也写成英文。刚复制且尚未填写的模板可以保持英文；不增加一次翻译回写动作。

此语言约定不改变后续步骤、条件、数量限制、权限、停止条件或上游既有缺陷；尤其不授权只读阶段修改文件。
<!-- SDLC-OUTPUT-LANGUAGE:END -->



## 用户输入

```text
$ARGUMENTS
```

继续之前，**必须**考虑用户输入（如果非空）。

## 执行前检查

**检查扩展钩子（任务生成前）**：
- 检查项目根目录是否存在 `.sdlc/extensions.yml`。
- 如果存在，读取文件并查找 `hooks.before_tasks` 键下的条目。
- 如果 YAML 无法解析或无效，静默跳过钩子检查，正常继续。
- 排除 `enabled` 明确为 `false` 的钩子。未包含 `enabled` 字段的钩子默认启用。
- 对每个剩余钩子，**不要**尝试解释或求值其 `condition` 表达式：
  - 如果钩子没有 `condition` 字段，或该字段为 null／空，将其视为可执行。
  - 如果钩子定义了非空 `condition`，跳过该钩子，将条件求值留给 HookExecutor 实现。
- 根据钩子命令名构造调用时，将点号（`.`）替换为连字符（`-`）。例如，`sdlc.git.commit` → `@@SDLC_BIND_0044@@sdlc-git-commit`。
- 对每个可执行钩子，根据其 `optional` 标志输出以下内容：
  - **可选钩子**（`optional: true`）：
    ```
    ## Extension Hooks

    **Optional Pre-Hook**: {extension}
    Command: `/{command}`
    Description: {description}

    Prompt: {prompt}
    To execute: `/{command}`
    ```
  - **必需钩子**（`optional: false`）：
    ```
    ## Extension Hooks

    **Automatic Pre-Hook**: {extension}
    Executing: `/{command}`
    EXECUTE_COMMAND: {command}

    Wait for the result of the hook command before proceeding to the Outline.
    ```
    输出以上内容后，必须实际调用钩子，等待执行完成后才能继续。按照在当前 Agent／会话中自行执行命令的方式调用（调用方式可能不同于上面显示的字面 `{command}` 标识，例如 Skills 模式的 Agent 使用 `/skill:sdlc-...` 或 `$sdlc-...`）。仅输出代码块并不会执行钩子。
- 如果没有注册钩子，或 `.sdlc/extensions.yml` 不存在，静默跳过。

## 执行概要

1. **准备**：从仓库根目录运行 `SDLC_HOST=c@@SDLC_BIND_0072@@ SDLC_INIT_DIR="${SDLC_PROJECT_ROOT:?}" bash "${SDLC_PLUGIN_ROOT:?}/scripts/bash/setup-tasks.sh" --json`，解析 FEATURE_DIR、TASKS_TEMPLATE_CONTENT、TASKS_TEMPLATE 及 AVAILABLE_DOCS 列表。提供了 `FEATURE_DIR` 和 `TASKS_TEMPLATE` 时，它们必须为绝对路径。`AVAILABLE_DOCS` 是 `FEATURE_DIR` 下可用文档名称／相对路径的列表，例如 `research.md` 或 `contracts/`。参数包含单引号（如 "I'm Groot"）时，使用转义语法，如 'I'\''m Groot'；可以使用双引号时也可写作 "I'm Groot"。

2. **加载设计文档**：从 FEATURE_DIR 读取：
   - **必需**：plan.md（技术栈、库、结构）、spec.md（带优先级的用户故事）。
   - **可选**：data-model.md（实体）、contracts/（接口契约）、research.md（决策）、quickstart.md（测试场景）。
   - **如果存在**：加载 `.sdlc/memory/constitution.md`，获取项目原则和治理约束。
   - 注意：不是所有项目都有全部文档，依据实际可用内容生成任务。

3. **执行任务生成流程**：
   - 加载 plan.md，提取技术栈、库及项目结构。
   - 加载 spec.md，提取用户故事及优先级（P1、P2、P3 等）。
   - data-model.md 存在时：提取实体并映射到用户故事。
   - contracts/ 存在时：将接口契约映射到用户故事。
   - research.md 存在时：提取决策，用于准备任务。
   - 按用户故事组织任务，遵循下方任务生成规则。
   - 生成显示用户故事完成顺序的依赖图。
   - 为每个用户故事创建并行执行示例。
   - 验证任务完整性：每个用户故事具备全部必要任务，并能独立测试。

4. **生成 tasks.md**：以上述 JSON 输出中的 TASKS_TEMPLATE_CONTENT 为结构。兼容未输出 TASKS_TEMPLATE_CONTENT 的旧准备脚本时，改为读取 TASKS_TEMPLATE。填充：
   - 来自 plan.md 的正确功能名称。
   - Phase 1：准备任务（项目初始化）。
   - Phase 2：基础任务（所有用户故事的阻塞性前置条件）。
   - Phase 3+：每个用户故事一个阶段，按 spec.md 优先级排序。
   - 每个阶段包含：故事目标、独立测试标准、测试（如果要求）、实现任务。
   - 最终阶段：完善和横切关注点。
   - 所有任务必须遵循严格的清单格式，见下文规则。
   - 每项任务给出清晰文件路径。
   - 依赖章节显示故事完成顺序。
   - 每个故事的并行执行示例。
   - 实施策略章节：MVP 优先、增量交付。

## 必需的执行后钩子

**在向用户报告完成之前，必须完成本节。**

检查项目根目录是否存在 `.sdlc/extensions.yml`。
- 如果不存在，或 `hooks.after_tasks` 下没有注册钩子，跳转到完成报告。
- 如果存在，读取文件并查找 `hooks.after_tasks` 键下的条目。
- 如果 YAML 无法解析或无效，静默跳过钩子检查，继续到完成报告。
- 排除 `enabled` 明确为 `false` 的钩子。未包含 `enabled` 字段的钩子默认启用。
- 对每个剩余钩子，**不要**尝试解释或求值其 `condition` 表达式：
  - 如果钩子没有 `condition` 字段，或该字段为 null／空，将其视为可执行。
  - 如果钩子定义了非空 `condition`，跳过该钩子，将条件求值留给 HookExecutor 实现。
- 根据钩子命令名构造调用时，将点号（`.`）替换为连字符（`-`）。例如，`sdlc.git.commit` → `@@SDLC_BIND_0116@@sdlc-git-commit`。
- 对每个可执行钩子，根据其 `optional` 标志输出以下内容：
  - **必需钩子**（`optional: false`）——**必须为每个必需钩子输出 `EXECUTE_COMMAND:`**：
    ```
    ## Extension Hooks

    **Automatic Hook**: {extension}
    Executing: `/{command}`
    EXECUTE_COMMAND: {command}
    ```
    输出以上内容后，必须实际调用钩子，等待执行完成后才能继续。按照在当前 Agent／会话中自行执行命令的方式调用（调用方式可能不同于上面显示的字面 `{command}` 标识，例如 Skills 模式的 Agent 使用 `/skill:sdlc-...` 或 `$sdlc-...`）。仅输出代码块并不会执行钩子。
  - **可选钩子**（`optional: true`）：
    ```
    ## Extension Hooks

    **Optional Hook**: {extension}
    Command: `/{command}`
    Description: {description}

    Prompt: {prompt}
    To execute: `/{command}`
    ```

## 完成报告

输出生成的 tasks.md 路径及摘要：
- 任务总数。
- 每个用户故事的任务数。
- 识别出的并行机会。
- 每个故事的独立测试标准。
- 建议的 MVP 范围，通常仅用户故事 1。
- 格式验证：确认所有任务均符合清单格式，包含复选框、ID、标签及文件路径。

任务生成上下文：$ARGUMENTS

生成的 tasks.md 应能立即执行；每项任务必须足够具体，使 LLM 无需额外上下文即可完成。

## 任务生成规则

**关键**：任务必须按用户故事组织，以支持独立实现和测试。

**测试是可选的**：仅当功能规格明确要求，或用户要求采用 TDD 时，才生成测试任务。

### 清单格式（必需）

每项任务必须严格遵循以下格式：

```text
- [ ] [TaskID] [P?] [Story?] Description with file path
```

**格式组成：**

1. **复选框**：始终以 `- [ ]` 开头（Markdown 复选框）。
2. **任务 ID**：按执行顺序递增编号（T001、T002、T003……）。
3. **[P] 标记**：仅在任务可并行时添加，即涉及不同文件、不依赖未完成任务。
4. **[Story] 标签**：仅用户故事阶段的任务必须包含。
   - 格式：[US1]、[US2]、[US3] 等，对应 spec.md 中的用户故事。
   - 准备阶段：不加故事标签。
   - 基础阶段：不加故事标签。
   - 用户故事阶段：必须有故事标签。
   - 完善阶段：不加故事标签。
5. **描述**：清晰的动作及准确文件路径。

**示例：**

- ✅ 正确：`- [ ] T001 Create project structure per implementation plan`
- ✅ 正确：`- [ ] T005 [P] Implement authentication middleware in src/middleware/auth.py`
- ✅ 正确：`- [ ] T012 [P] [US1] Create User model in src/models/user.py`
- ✅ 正确：`- [ ] T014 [US1] Implement UserService in src/services/user_service.py`
- ❌ 错误：`- [ ] Create User model`（缺少 ID 和故事标签）。
- ❌ 错误：`T001 [US1] Create model`（缺少复选框）。
- ❌ 错误：`- [ ] [US1] Create User model`（缺少任务 ID）。
- ❌ 错误：`- [ ] T001 [US1] Create model`（缺少文件路径）。

### 任务组织

1. **来自用户故事（spec.md）——主要组织依据**：
   - 每个用户故事（P1、P2、P3……）具有独立阶段。
   - 将所有相关组件映射到对应故事：
     - 故事需要的模型。
     - 故事需要的服务。
     - 故事需要的接口／UI。
     - 要求测试时，添加该故事的专属测试。
   - 标明故事依赖；多数故事应能独立进行。

2. **来自契约**：
   - 每个接口契约映射到其服务的用户故事。
   - 要求测试时，在该故事阶段的实现之前，为每个接口契约安排契约测试任务 [P]。

3. **来自数据模型**：
   - 将每个实体映射到需要它的用户故事。
   - 实体服务多个故事时，放在最早的故事或准备阶段。
   - 关系映射到适当故事阶段的服务层任务。
   - 对 data-model.md 中具有约束的每个字段（最大长度、可空／必填、枚举值、校验规则），在任务描述中逐字引用约束，不能留给实现时自行决定。

4. **来自准备／基础设施**：
   - 共享基础设施 → 准备阶段（Phase 1）。
   - 基础／阻塞任务 → 基础阶段（Phase 2）。
   - 故事专属准备 → 对应故事的阶段内。

### 阶段结构

- **Phase 1**：准备（项目初始化）。
- **Phase 2**：基础（阻塞性前置条件，必须在用户故事之前完成）。
- **Phase 3+**：按优先级排序的用户故事（P1、P2、P3……）。
  - 每个故事内部：测试（如果要求）→ 模型 → 服务 → 端点 → 集成。
  - 每个阶段应是完整、可独立测试的增量。
- **最终阶段**：完善及横切关注点。

## 完成条件

- [ ] tasks.md 已生成，包含全部阶段、任务 ID 及文件路径。
- [ ] 已按上文“必需的执行后钩子”规则分派或跳过扩展钩子。
- [ ] 已向用户报告任务数、故事分解及 MVP 范围。

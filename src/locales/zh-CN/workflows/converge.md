


## 用户输入

```text
$ARGUMENTS
```

继续之前，**必须**考虑用户输入（如果非空）。

## 执行前检查

**检查扩展钩子（收敛前）**：

- 检查项目根目录是否存在 `.sdlc/extensions.yml`。
- 如果存在，读取文件并查找 `hooks.before_converge` 键下的条目。
- 如果 YAML 无法解析或无效，静默跳过钩子检查，正常继续。
- 排除 `enabled` 明确为 `false` 的钩子。未包含 `enabled` 字段的钩子默认启用。
- 对每个剩余钩子，**不要**尝试解释或求值其 `condition` 表达式：
  - 如果钩子没有 `condition` 字段，或该字段为 null／空，将其视为可执行。
  - 如果钩子定义了非空 `condition`，跳过该钩子，将条件求值留给 HookExecutor 实现。
- 根据钩子命令名构造调用时，将点号（`.`）替换为连字符（`-`）。例如，`sdlc.git.commit` → `{{SDLC:HOOK_EXAMPLE}}`。
- 对每个可执行钩子，根据其 `optional` 标志输出以下内容：
  - **可选钩子**（`optional: true`）：

    ```text
    ## Extension Hooks

    **Optional Pre-Hook**: {extension}
    Command: `/{command}`
    Description: {description}

    Prompt: {prompt}
    To execute: `/{command}`
    ```

  - **必需钩子**（`optional: false`）：

    ```text
    ## Extension Hooks

    **Automatic Pre-Hook**: {extension}
    Executing: `/{command}`
    EXECUTE_COMMAND: {command}

    Wait for the result of the hook command before proceeding to the Goal.
    ```
    输出以上内容后，必须实际调用钩子，等待执行完成后才能继续。按照在当前 Agent／会话中自行执行命令的方式调用（调用方式可能不同于上面显示的字面 `{command}` 标识，例如 Skills 模式的 Agent 使用 `/skill:sdlc-...` 或 `$sdlc-...`）。仅输出代码块并不会执行钩子。

- 如果没有注册钩子，或 `.sdlc/extensions.yml` 不存在，静默跳过。

## 目标

缩小功能规格、方案和任务要求与当前代码实现之间的差距。将 `spec.md`、`plan.md`、`tasks.md` 作为**意图的唯一来源**，并以宪法作为治理约束；评估当前代码，确定哪些需求、验收标准、方案决策和既有任务尚未满足、未完成或仅部分满足。将**每项剩余工作作为可追溯的新任务追加**到 `tasks.md` 底部，供 `{{SDLC:IMPLEMENT}}` 完成。本命令**只能**在 `{{SDLC:IMPLEMENT}}` 已针对当前 `tasks.md` 运行，且 `{{SDLC:TASKS}}` 已生成完整 `tasks.md` 之后执行。

这**不是**差异工具，也**不**追踪变更。它相对于功能产物评估代码的当前状态：不使用 Git，不比较分支，不查看历史。

## 操作约束

**只追加，绝不重写（APPEND-ONLY, NEVER REWRITE）**：本命令**唯一**的写入，是向 `tasks.md` 追加新的 `## Phase N: Convergence` 章节。**不得**：

- 以任何方式修改 `spec.md` 或 `plan.md`。
- 重写、重新编号、重排或删除任何既有任务，包括之前 Convergence 阶段的任务。
- 修改、创建或删除任何应用代码；完成追加任务是 `{{SDLC:IMPLEMENT}}` 的职责。

代码已经满足全部要求时，必须保持 `tasks.md` **逐字节不变**，不能追加空的 Convergence 标题，并报告无差距结果。

**宪法权威**：项目宪法（`.sdlc/memory/constitution.md`）**不可协商**。违反 MUST 原则的代码属于最高严重级别发现，必须产生对应整改任务。宪法尚未填写、只是模板时，正常跳过宪法检查，而不是失败。

## 执行步骤

### 1. 初始化收敛上下文

在仓库根目录运行一次 `SDLC_HOST={{SDLC:HOST}} SDLC_INIT_DIR="${SDLC_PROJECT_ROOT:?}" bash "${SDLC_PLUGIN_ROOT:?}/scripts/bash/check-prerequisites.sh" --json --require-spec --require-tasks --include-tasks`，解析 JSON 中的 FEATURE_DIR 和 AVAILABLE_DOCS。推导绝对路径：

- SPEC = FEATURE_DIR/spec.md
- PLAN = FEATURE_DIR/plan.md
- TASKS = FEATURE_DIR/tasks.md
- CONSTITUTION = `.sdlc/memory/constitution.md`（如果存在）。
如果 `spec.md`、`plan.md` 或 `tasks.md` 缺失，停止并给出明确、可执行的信息，指出需要运行的前置命令：缺规格用 `{{SDLC:SPECIFY}}`，缺方案用 `{{SDLC:PLAN}}`，缺任务用 `{{SDLC:TASKS}}`。不输出不完整结果。
参数包含单引号（如 "I'm Groot"）时，使用转义语法，如 'I'\''m Groot'；可以使用双引号时也可写作 "I'm Groot"。

### 2. 加载产物（渐进式读取）

仅从各产物加载最少且必要的上下文：

**从 spec.md：**

- Functional Requirements（FR-###）。
- Success Criteria（SC-###）：仅包括需要可构建工作的项；排除上线后的结果指标和业务 KPI。
- 用户故事及验收场景。
- 边界情况（若存在）。

**从 plan.md：**

- 架构／技术栈选择和技术决策。
- Data Model 引用。
- 阶段及指定修改点，即方案声明会创建或修改的文件／组件。
- 技术约束。

**从 tasks.md：**

- 任务 ID，用于计算下一个 ID 和阶段编号。
- 描述、阶段分组及引用的文件路径。

**从宪法（不是未填写模板时）：**

- 原则名称及 MUST／SHOULD 规范性陈述。

### 3. 建立意图清单

创建内部模型，不回显原始产物：

- **需求清单**：为每个 FR-###、SC-###、用户故事验收场景（如 `US1/AC2`）建立稳定键，并纳入形成可构建义务的方案决策和宪法原则。
- **代码范围映射**：依据 `plan.md` 和 `tasks.md` 指定的文件路径，并搜索各需求所描述概念的关键词，推导评估范围内的源文件与组件。评估仅限这些对象；**不要**推断产物定义以外的范围。

### 4. 评估代码并归类发现

对意图清单中的每一项，检查范围内的当前代码，仅在存在差距时产生 `Finding`。每项发现按**差距类型**分类：

- **`missing`**：代码完全缺少要求的工作。
- **`partial`**：工作已存在，但尚未完全满足需求／验收标准／方案决策。
- **`contradicts`**：代码行为与明确意图或宪法 MUST 原则冲突。
- **`unrequested`**：代码包含规格、方案或任务未要求的工作。仅提示关注；收敛命令**不删除代码**，只追加任务，要求评审、说明理由或移除它。

每个 `Finding` 记录：稳定 ID、可追溯的 `source-ref`、`gap-type`、严重级别，以及包含证据（观察到的文件／区域）的简短可读描述。

**边界情况：**

- **代码很少或尚无代码**：将全部已规定范围视为 `missing` 剩余工作，不因此失败。
- **没有剩余工作**：产生零项发现，执行第 7 步的已收敛分支。

### 5. 分配严重级别

- **CRITICAL**：违反宪法 MUST，或阻塞 P1 用户故事基础功能的 `missing`／`contradicts` 差距。
- **HIGH**：核心功能需求或验收标准上的 `missing` 或 `partial` 差距。
- **MEDIUM**：次要需求的 `partial` 差距，或理由不明确的 `unrequested` 新增内容。
- **LOW**：轻微的部分缺口、完善项，或低风险的 `unrequested` 新增内容。

### 6. 在会话中展示发现摘要

追加任何内容前，输出简洁且按严重级别划分的摘要，此时不写文件：

## 收敛发现

| ID | 差距类型 | 严重级别 | 来源 | 证据 | 剩余工作 |
|----|----------|----------|------|------|----------|
| F1 | missing | HIGH | FR-008 | 例如：path/to/module.py 写入 tasks.md 时未检测到只追加保护 | 添加只追加约束 |

**汇总指标：**

- 已检查的需求／验收标准数量。
- 已检查的方案决策数量。
- 已检查的宪法原则数量，或“已跳过——模板”。
- 按差距类型统计：missing／partial／contradicts／unrequested。
- 按严重级别统计。

### 7. 追加收敛任务，或报告已收敛

**存在一项或多项可执行发现时**（`tasks_appended` 结果）：

按照追加契约，在 `tasks.md` **末尾**追加：

1. 扫描全部既有任务 ID，令 `M` 为最大值。确定下一阶段编号 `N`，即已有最大阶段号加 1。
2. 写入单个新章节标题 `## Phase N: Convergence`。
3. 每项可执行发现生成一个清单条目，优先排列 CRITICAL／HIGH，分配补零的 ID：`T{M+1:03d}, T{M+2:03d}, …`：

   ```markdown
   - [ ] T042 <imperative description> per <source-ref> (<gap-type>)
   ```

   `<source-ref>` 将任务追溯到来源，例如 `FR-003`、`SC-002`、`US1/AC2`、`plan: storage decision`、`Constitution II`。

   `<gap-type>` 必须是 `missing`、`partial`、`contradicts`、`unrequested` 之一。

   宪法违规任务必须最先输出，并明确标为 `CRITICAL`。
4. 绝不复用或重新编号既有 ID。此前存在 Convergence 阶段时，在其下方新增独立编号的阶段，不触碰旧阶段。

**没有可执行发现时**（`converged` 结果）：

- 完全**不**修改 `tasks.md`，不产生空阶段标题。
- 报告：**“✅ 已收敛——实现满足规格、方案和任务要求。”**
- 包含已检查内容的汇总计数。

### 8. 提供后续行动（交接）

- 结果为 `tasks_appended`：说明在哪个阶段追加了多少任务，建议运行 `{{SDLC:IMPLEMENT}}` 完成；说明后续再次收敛时，剩余项应减少或归零。
- 结果为 `converged`：建议进入评审／创建 PR。对于本功能已规定范围，不需要再次实施。

### 9. 检查扩展钩子

生成结果后，检查项目根目录是否存在 `.sdlc/extensions.yml`。

- 如果存在，读取文件并查找 `hooks.after_converge` 键下的条目。
- 如果 YAML 无法解析或无效，静默跳过钩子检查，正常继续。
- 排除 `enabled` 明确为 `false` 的钩子。未包含 `enabled` 字段的钩子默认启用。
- 对每个剩余钩子，**不要**尝试解释或求值其 `condition` 表达式：
  - 如果钩子没有 `condition` 字段，或该字段为 null／空，将其视为可执行。
  - 如果钩子定义了非空 `condition`，跳过该钩子，将条件求值留给 HookExecutor 实现。
- 列出任何钩子之前，先在会话中报告收敛结果（`converged` 或 `tasks_appended`），让用户决定是否执行可选的后续命令。
- 根据钩子命令名构造调用时，将点号（`.`）替换为连字符（`-`）。例如，`sdlc.git.commit` → `{{SDLC:HOOK_EXAMPLE}}`。
- 对每个可执行钩子，根据其 `optional` 标志输出以下内容：
  - **可选钩子**（`optional: true`）：

    ```text
    ## Extension Hooks

    **Optional Hook**: {extension}
    Command: `/{command}`
    Description: {description}

    Prompt: {prompt}
    To execute: `/{command}`
    ```

  - **必需钩子**（`optional: false`）：

    ```text
    ## Extension Hooks

    **Automatic Hook**: {extension}
    Executing: `/{command}`
    EXECUTE_COMMAND: {command}
    ```
    输出以上内容后，必须实际调用钩子，等待执行完成后才能继续。按照在当前 Agent／会话中自行执行命令的方式调用（调用方式可能不同于上面显示的字面 `{command}` 标识，例如 Skills 模式的 Agent 使用 `/skill:sdlc-...` 或 `$sdlc-...`）。仅输出代码块并不会执行钩子。

- 如果没有注册钩子，或 `.sdlc/extensions.yml` 不存在，静默跳过。

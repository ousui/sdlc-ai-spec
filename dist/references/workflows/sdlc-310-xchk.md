
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

向使用者解释流程、提问及总结时使用简体中文。仅在下面原流程要求创建或修改产物时，以简体中文填写自然语言内容；不得为了翻译新增写入或重写其他已有内容。模板固定骨架、章节层级和定位用英文锚点保留，标题可附中文释义；占位符、状态值、任务语法、实际代码、路径、变量、参数、事件名及配置键保持原样。用户明确指定其他语言的内容按其要求保留。

使用插件中已审查的本地化模板。`User Story`、`Success Criteria`、`NEEDS CLARIFICATION`、`FR-001`、`T001`、`[US1]`、`[P]` 等机器或结构标记保留；模板说明、业务描述、理由、测试说明和任务内容使用中文。代码块中的格式示例不强制自然语言使用英文；SPEC 的内置 requirements.md 清单采用流程中的本地化条目，条目顺序、数量、条件和勾选责任不变。用户自定义模板仍按原流程处理，不为本地化新增覆盖动作。

文档、注释与说明直接表达业务内容，不添加“中文注释”“中文说明”“中文版本”等语言标签。确需标签时使用“注释”或“说明”。不要为了标明语言新增 HTML 注释；只有原流程本来要求的注释才按其规则处理。保留有语义的注释，不做全文件删除或批量清理。不得插入 U+FFFC 等对象替换字符。

此语言约定不改变后续步骤、条件、数量限制、权限、停止条件或上游既有缺陷；尤其不授权只读阶段修改文件。它是给执行者的指引，不是待复制进业务产物的正文。
<!-- SDLC-OUTPUT-LANGUAGE:END -->



## 用户输入

```text
$ARGUMENTS
```

继续之前，**必须**考虑用户输入（如果非空）。

## 执行前检查

**检查扩展钩子（分析前）**：
- 检查项目根目录是否存在 `.sdlc/extensions.yml`。
- 如果存在，读取文件并查找 `hooks.before_analyze` 键下的条目。
- 如果 YAML 无法解析或无效，静默跳过钩子检查，正常继续。
- 排除 `enabled` 明确为 `false` 的钩子。未包含 `enabled` 字段的钩子默认启用。
- 对每个剩余钩子，**不要**尝试解释或求值其 `condition` 表达式：
  - 如果钩子没有 `condition` 字段，或该字段为 null／空，将其视为可执行。
  - 如果钩子定义了非空 `condition`，跳过该钩子，将条件求值留给 HookExecutor 实现。
- 根据钩子命令名构造调用时，将点号（`.`）替换为连字符（`-`）。例如，`sdlc.git.commit` → `@@SDLC_BIND_0046@@sdlc-git-commit`。
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

    Wait for the result of the hook command before proceeding to the Goal.
    ```
    输出以上内容后，必须实际调用钩子，等待执行完成后才能继续。按照在当前 Agent／会话中自行执行命令的方式调用（调用方式可能不同于上面显示的字面 `{command}` 标识，例如 Skills 模式的 Agent 使用 `/skill:sdlc-...` 或 `$sdlc-...`）。仅输出代码块并不会执行钩子。
- 如果没有注册钩子，或 `.sdlc/extensions.yml` 不存在，静默跳过。

## 目标

在实施前，识别三个核心产物（`spec.md`、`plan.md`、`tasks.md`）之间的不一致、重复、歧义和定义不足。本命令**只能**在 `@@SDLC_BIND_0074@@sdlc-300-task` 成功生成完整 `tasks.md` 之后运行。

## 操作约束

**严格只读（STRICTLY READ-ONLY）**：**不要**修改任何文件。输出结构化分析报告。可以提供可选的整改计划；后续编辑命令手动调用之前，必须获得用户明确批准。

**宪法权威**：项目宪法（`.sdlc/memory/constitution.md`）在本分析范围内**不可协商**。宪法冲突自动归为 CRITICAL，必须调整规格、方案或任务，而不是弱化、重新解释或静默忽略原则。原则本身需要变更时，必须在 `@@SDLC_BIND_0080@@sdlc-310-xchk` 之外单独、明确地更新宪法。

## 执行步骤

### 1. 初始化分析上下文

从仓库根目录运行一次 `SDLC_HOST=c@@SDLC_BIND_0086@@ SDLC_INIT_DIR="${SDLC_PROJECT_ROOT:?}" bash "${SDLC_PLUGIN_ROOT:?}/scripts/bash/check-prerequisites.sh" --json --require-spec --require-tasks --include-tasks`，解析 JSON 中的 FEATURE_DIR 和 AVAILABLE_DOCS。推导绝对路径：

- SPEC = FEATURE_DIR/spec.md
- PLAN = FEATURE_DIR/plan.md
- TASKS = FEATURE_DIR/tasks.md

任何必需文件缺失时，中止并报告错误，指导用户运行缺少的前置命令。
参数包含单引号（如 "I'm Groot"）时，使用转义语法，如 'I'\''m Groot'；可以使用双引号时也可写作 "I'm Groot"。

### 2. 加载产物（渐进式读取）

仅从各产物加载最少且必要的上下文：

**从 spec.md：**

- Overview／Context（概述／背景）。
- Functional Requirements（功能需求）。
- Success Criteria（可衡量结果，例如性能、安全、可用性、用户成功和业务影响）。
- User Stories（用户故事）。
- Edge Cases（若存在）。

**从 plan.md：**

- 架构／技术栈选择。
- Data Model 引用。
- 阶段划分。
- 技术约束。

**从 tasks.md：**

- 任务 ID。
- 描述。
- 阶段分组。
- 并行标记 [P]。
- 引用的文件路径。

**从宪法：**

- 加载 `.sdlc/memory/constitution.md`，用于验证原则。

### 3. 构建语义模型

构建内部表示，不在输出中包含原始产物全文：

- **需求清单**：为每个功能需求（FR-###）和成功标准（SC-###）记录稳定键。存在明确 FR-／SC- 标识时，用它作为主键；也可额外派生祈使短语 slug 以提高可读性，例如“用户可以上传文件” → `user-can-upload-file`。仅纳入需要可构建工作的成功标准，例如负载测试基础设施、安全审计工具；排除上线后的结果指标和业务 KPI，例如“支持工单减少 50%”。
- **用户故事／操作清单**：带验收标准的独立用户操作。
- **任务覆盖映射**：将每项任务映射到一个或多个需求或故事，可依据关键词、ID 或关键短语等明确引用模式推断。
- **宪法规则集**：提取原则名称和 MUST／SHOULD 规范性陈述。

### 4. 检查轮次（节省 Token 的分析）

聚焦高价值发现。发现总数最多 50 项，其余汇总到溢出摘要。

#### A. 重复检测

- 识别近似重复的需求。
- 标记质量较低的表述，供合并处理。

#### B. 歧义检测

- 标记缺少衡量标准的模糊形容词，例如快速、可扩展、安全、直观、健壮。
- 标记未解决的占位符，例如 TODO、TKTK、???、`<placeholder>` 等。

#### C. 定义不足

- 有动词但缺少对象或可衡量结果的需求。
- 未与验收标准对齐的用户故事。
- 引用了规格／方案中未定义文件或组件的任务。

#### D. 宪法对齐

- 与 MUST 原则冲突的任何需求或方案要素。
- 缺少宪法强制要求的章节或质量门禁。

#### E. 覆盖缺口

- 没有关联任务的需求。
- 没有映射需求／故事的任务。
- 需要可构建工作、却未体现在任务中的成功标准，如性能、安全、可用性。

#### F. 不一致

- 术语漂移：同一概念在不同文件中名称不同。
- 方案引用的数据实体在规格中缺失，或反之。
- 任务顺序矛盾：例如集成任务排在基础准备之前，却未说明依赖。
- 冲突需求：例如一处要求 Next.js，另一处要求 Vue。

### 5. 分配严重级别

使用以下启发规则确定优先级：

- **CRITICAL**：违反宪法 MUST、缺少核心规格产物，或零覆盖需求阻塞基础功能。
- **HIGH**：需求重复或冲突、安全／性能属性有歧义、验收标准不可测试。
- **MEDIUM**：术语漂移、缺少非功能任务覆盖、边界情况定义不足。
- **LOW**：风格／措辞改进，不影响执行顺序的轻微冗余。

### 6. 生成紧凑分析报告

输出以下结构的 Markdown 报告，不写入文件：

## 规格分析报告

| ID | 类别 | 严重级别 | 位置 | 摘要 | 建议 |
|----|------|----------|------|------|------|
| A1 | 重复 | HIGH | spec.md:L120-134 | 两条相似需求…… | 合并表述，保留更清晰的版本 |

每项发现一行；使用类别首字母作为前缀生成稳定 ID。

**覆盖汇总表：**

| 需求键 | 是否有任务 | 任务 ID | 备注 |
|--------|------------|---------|------|

**宪法对齐问题：**若存在。

**未映射的任务：**若存在。

**指标：**

- 需求总数。
- 任务总数。
- 覆盖率 %：至少有 1 个任务的需求占比。
- 歧义数量。
- 重复数量。
- 严重问题数量。

### 7. 提供后续行动

在报告末尾输出简洁的 Next Actions：

- 存在 CRITICAL 时：建议在 `@@SDLC_BIND_0216@@sdlc-400-impl` 之前解决。
- 只有 LOW／MEDIUM 时：用户可以继续，但仍应提供改进建议。
- 给出明确命令建议，例如“运行 @@SDLC_BIND_0218@@sdlc-200-plan 调整架构”“手动编辑 tasks.md，补充 performance-metrics 的覆盖”。

### 8. 提供整改建议

询问用户：“是否需要我为优先级最高的 N 项问题提出具体修改建议？”**不要**自动应用这些修改。

### 9. 检查扩展钩子

报告后，检查项目根目录是否存在 `.sdlc/extensions.yml`。

- 如果存在，读取文件并查找 `hooks.after_analyze` 键下的条目。
- 如果 YAML 无法解析或无效，静默跳过钩子检查，正常继续。
- 排除 `enabled` 明确为 `false` 的钩子。未包含 `enabled` 字段的钩子默认启用。
- 对每个剩余钩子，**不要**尝试解释或求值其 `condition` 表达式：
  - 如果钩子没有 `condition` 字段，或该字段为 null／空，将其视为可执行。
  - 如果钩子定义了非空 `condition`，跳过该钩子，将条件求值留给 HookExecutor 实现。
- 根据钩子命令名构造调用时，将点号（`.`）替换为连字符（`-`）。例如，`sdlc.git.commit` → `@@SDLC_BIND_0234@@sdlc-git-commit`。
- 对每个可执行钩子，根据其 `optional` 标志输出以下内容：
  - **可选钩子**（`optional: true`）：
    ```
    ## Extension Hooks

    **Optional Hook**: {extension}
    Command: `/{command}`
    Description: {description}

    Prompt: {prompt}
    To execute: `/{command}`
    ```
  - **必需钩子**（`optional: false`）：
    ```
    ## Extension Hooks

    **Automatic Hook**: {extension}
    Executing: `/{command}`
    EXECUTE_COMMAND: {command}
    ```
    输出以上内容后，必须实际调用钩子，等待执行完成后才能继续。按照在当前 Agent／会话中自行执行命令的方式调用（调用方式可能不同于上面显示的字面 `{command}` 标识，例如 Skills 模式的 Agent 使用 `/skill:sdlc-...` 或 `$sdlc-...`）。仅输出代码块并不会执行钩子。
- 如果没有注册钩子，或 `.sdlc/extensions.yml` 不存在，静默跳过。

## 操作原则

### 上下文效率

- **最少且高价值的 Token**：聚焦可执行发现，而非面面俱到的文档。
- **渐进式读取**：逐步加载产物，不把全部内容一次性倾倒到分析中。
- **节省 Token 的输出**：发现表最多 50 行，其余汇总。
- **确定性结果**：内容未变化时重新运行，应产生一致的 ID 和计数。

### 分析准则

- **绝不修改文件**：这是只读分析。
- **绝不臆造缺失章节**：缺失就准确报告。
- **优先处理宪法违规**：它们始终是 CRITICAL。
- **用实例代替穷举规则**：引用具体案例，而非泛泛模式。
- **没有问题时正常报告**：输出包含覆盖统计的成功报告。

## 上下文

$ARGUMENTS


<!-- SDLC-PACKAGE-BINDING:BEGIN -->
## 已安装插件与业务项目绑定

本次调用宿主为 c@@SDLC_BIND_0004@@。先完成路径绑定，再执行下面的原有流程。

- @@SDLC_BIND_0006@@。 `SDLC_PLUGIN_ROOT` 是已加载核心 Skill 目录向上两级的插件包目录（`skills/<name>/SKILL.md`）。不得从业务工作目录推断或假定变量已导出。正常执行期间使用同一完整包。更新移除该包时，从宿主当前 Skill 清单、安装记录或用户明确路径定位当前包，不按缓存版本排序猜选。读取其入口和 `skills/sdlc-refine/references/compatibility.md`，评估兼容性及先前操作结果，再从选定包完整重载流程。不得混用包或重放未经核实的写入。版本不同或旧包缺失本身不要求迁移或用户重新调用。
- 保持 shell 工作目录位于选定的业务项目。执行 `SDLC_HOST=c@@SDLC_BIND_0007@@ bash "${SDLC_PLUGIN_ROOT:?}/scripts/bash/project-paths.sh"` 解析选定代码项目及其有效 `.sdlc` 资料库。用户明确选定项目时，以命令局部变量 `SDLC_INIT_DIR` 传入其绝对路径。将返回的 `PROJECT_ROOT` 作为 `SDLC_PROJECT_ROOT`。项目不存在或无效时停止，明确运行 `sdlc-000-init` 初始化或补全；不得回退到其他工具。
- 每次使用这些变量的 shell 调用都显式传入已解析的绝对值；工具调用之间不保证 shell 状态持久化。`${VAR:?}` 有意在变量未解析时失败。非 shell 文件工具使用实际绝对路径，不把 `${VAR}` 字面量传给工具。不得通过切换到插件目录来修复资源定位。
- 创建或更新需求文件前，通过命令局部 `SDLC_INIT_DIR` 调用同一 `project-paths.sh --feature <resolved-feature-directory>`，检查显式路径和符号链接不会指向本插件。该脚本只读，不执行初始化。项目状态、当前需求和宪法不得写到插件内。
- 本包沿用仅核心、无 Preset、无 Extension、无事件的既有 profile。不得为满足引用而安装或调用扩展、上游 CLI。项目包含 `.sdlc/extensions.yml`、已安装预设或扩展状态时，停止并说明该 profile 不受支持。下面保留上游条件钩子文本用于来源等价，不构成启用可选子系统的授权。
- `$ARGUMENTS` 表示本次调用的用户输入。宿主没有替换它时，从当前对话读取这次输入；不得将占位符字面量作为需求描述。
<!-- SDLC-PACKAGE-BINDING:END -->

## 工作区存储扩展

选定代码项目仍为 `SDLC_PROJECT_ROOT`；解析器还返回 `SDLC_DIR`、`AUTHORITY_DIR`、`FEATURE_JSON`、`mode` 和 `can_collect`。独立本地 `.sdlc` 优先；没有本地时，普通命令读写权威库。只有 main 可以归拢副本。不得通过指定权威库绕过本地资料或无效的本地需求选择。main 指主工作区，不是分支名称。

main 的登记不可用时，有效的独立本地工作可以继续：`AUTHORITY_DIR` 和 `authority_exists` 为 null，`authority_error` 说明原因。不得猜测权威路径；导入权威资料、无法核实的外部需求目标或本地目录别名仍然停止。

以下所有 `.sdlc/` 资料引用都相对于 `SDLC_DIR`；`.sdlc/feature.json` 解释为 `FEATURE_JSON`。代码、实施、测试及其他非资料相对路径仍位于 `SDLC_PROJECT_ROOT`。使用 `project-paths.sh --feature` 解析显式需求并使用返回的 `FEATURE_DIR`。有效库存在 `memory/long-term.md` 时，将其作为项目上下文读取；它不覆盖宪法或用户指令。不复制其他工作区的当前需求选择。

显式需求输入优先于已保存的选择。仅解析资料库、创建新需求或编辑明确指定的文件，不要求未使用的旧选择有效。流程需要已保存的选择时，只使用本工作区的记录，不回退到其他资料库。保留既有持久化及只读规则。显式 `.` 或 `./` 表示代码项目目录，仍受相同路径校验约束。独立本地库与权威库的资料根不得重叠。

模型编写有效库内的文件时，在编辑文档前准备候选：

```sh
python3 -I -B "${SDLC_PLUGIN_ROOT:?}/scripts/python/store_changes.py" prepare --project "${SDLC_PROJECT_ROOT:?}" --kind edit --path '<store-relative-file>'
```

本次涉及多个文件时重复传入 `--path`。只编辑返回的 `proposal.json`：每个已准备文件使用 `{"action":"replace","text":"complete candidate text"}`、`{"action":"skip"}`，或对已明确授权废弃的文档使用 `{"action":"delete"}`。删除移除普通文档，不删除控制文件或末级软链接；空文本替换仍会保留文件。把活动引用纳入同一项已审查变更。导入和归拢不因来源缺文件推导删除。随后通过程序发布：

```sh
python3 -I -B "${SDLC_PLUGIN_ROOT:?}/scripts/python/store_changes.py" apply --project "${SDLC_PROJECT_ROOT:?}" --transaction '<returned-transaction-directory>'
```

普通编辑的快照只包含选定文件、编辑 `tasks.md` 时对应的任务编号记录、`init-options.json` 和当前工作区的 `FEATURE_JSON`。无关产物及其他 worktree 的需求选择不使候选失效；本次目标或必要绑定变化仍阻止应用。导入和归拢保留来源与目标快照检查。

梳理后的任务编号续接是明确的本地存储扩展。TASK、CONV 或已授权修订在分配新任务编号前，读取选定需求的活动编号和保留上界：

```sh
python3 -I -B "${SDLC_PLUGIN_ROOT:?}/scripts/python/task_ids.py" --project "${SDLC_PROJECT_ROOT:?}" --feature '<resolved-feature-directory>'
```

以返回的 `high_water` 作为分配最大值（CONV 中的 `M`），新编号从 `next_id` 开始。保留仍然有效的义务编号，不得把已退役编号分配给不同工作。没有历史的新需求仍从 `T001` 开始。只读工具会计入 `tasks.md` 同目录的 `.task-ids.json`；它是编号元数据，不是活动任务或完成证据。不得从事务快照恢复废弃任务，也不把保留编号视为实现缺口。TASK 重新生成既有需求时保留该记录；IMPL 只执行活动任务复选框。编辑事务在移除编号时及此后维护上界，即使删除整个任务文件也保留，并拒绝复用已退役编号。它不保存废弃业务正文，也不为编号集合未变的任务创建历史记录。不得手动重置或删除编号记录；它随任务变更一起应用或恢复。记录不可读时停止分配，不能重新从 `T001` 开始。

沿用既有流程授权，不增加改动其他产物的权限。未决事项或输入变化阻止发布；重新准备，不强行应用过期变更。包内写入脚本使用同一把资料库锁。显式外部需求目录保留既有路径检查；存在本地副本时，不得将其指向权威库。只读阶段不准备或应用写入候选。应用中断后先诊断，可使用同一程序的 `recover` 动作恢复；不得删除其他操作的锁或覆盖后来的编辑以强行恢复。

INIT 或准备过程停止后若遗留锁，以选定项目使用 `sdlc_store.py recover-lock --project`。它只释放已记录进程不再运行的锁；中断的资料应用仍须使用 `store_changes.py recover`。归属信息不完整或进程仍存活时停止恢复。

<!-- SDLC-OUTPUT-LANGUAGE:BEGIN -->
## 输出语言（仅呈现层）

向使用者解释流程、提问及总结时使用简体中文。仅在原流程要求创建或修改产物时，以简体中文填写自然语言内容；不得为了翻译新增写入或重写其他已有内容。

新生成的默认产物使用已审查的中文展示标题、字段标签和固定提示，不再在同一标题后重复附加另一种语言。章节层级、顺序、必填／可选含义和业务内容保持不变。定位标题只使用已审查的有限映射；读取已有产物时兼容上游英文、历史双语和当前中文标题，已有章节必须继续使用，不重复创建同义章节。

默认写入采用中文 canonical presentation。机器契约保持原样：Skill/命令 ID、文件名与路径、JSON/YAML key、环境变量、CLI 参数、事件名、配置键、状态枚举、严重级别、任务／需求编号、复选框语法、`[US1]`、`[P]`、`[NEEDS CLARIFICATION: ...]` 标记、实际代码/API/schema 标识均不得因翻译改名。API Token、Cloudflare、DNS、HTTP、JSON、Python、Go 等必要技术术语按项目实际用法保留。

固定交互文案属于本地化范围；输出使用中文，同时保留原流程已有英文输入，并可增加已审查的中文等价输入别名。例如 CLAR 可接受 `yes`／`recommended`／`suggested`，并兼容“采用推荐”／“采用建议”；IMPL 的继续／停止类回答同样保留旧英文词。新增别名不得改变问题数量、等待用户确认、停止条件或写入权限。

使用插件中已审查的本地化模板。自然语言标题、字段、说明、理由、测试描述、任务内容和固定响应使用中文；机器语法按上段保留。代码块中的自然语言示例允许按已审查映射翻译，但可执行命令、参数、路径、变量、机器 token 及代码标识必须保持。用户自定义模板仍按原流程处理，不为本地化新增覆盖动作。

文档、注释与说明直接表达业务内容，不添加“中文注释”“中文说明”“中文版本”等语言标签。确需标签时使用“注释”或“说明”。不要为了标明语言新增 HTML 注释；只有原流程本来要求的注释才按其规则处理。保留有语义的注释，不做全文件删除或批量清理。不得插入 U+FFFC 等对象替换字符。

此语言约定只改变呈现，不改变后续步骤、条件、数量限制、权限、停止条件或上游既有缺陷；尤其不授权只读阶段修改文件。它是给执行者的指引，不是待复制进业务产物的正文。
<!-- SDLC-OUTPUT-LANGUAGE:END -->



## 用户输入

```text
$ARGUMENTS
```

继续之前，**必须**考虑用户输入（如果非空）。

## 执行前检查

**检查扩展钩子（收敛前）**：

- 检查项目根目录是否存在 `.sdlc/extensions.yml`。
- 如果存在，读取文件并查找 `hooks.before_converge` 键下的条目。
- 如果 YAML 无法解析或无效，不得静默跳过：告知用户 `.sdlc/extensions.yml` 无法读取（包含解析器错误），并且未检查任何钩子，包括其中登记的任何强制（`optional: false`）钩子，然后正常继续。
- 排除 `enabled` 明确为 `false` 的钩子。未包含 `enabled` 字段的钩子默认启用。
- 对每个剩余钩子，**不要**尝试解释或求值其 `condition` 表达式：
  - 如果钩子没有 `condition` 字段，或该字段为 null／空，将其视为可执行。
  - 如果钩子定义了非空 `condition`，跳过该钩子，将条件求值留给 HookExecutor 实现。
- 根据钩子命令名构造调用时，将点号（`.`）替换为连字符（`-`）。例如，`sdlc.git.commit` → `@@SDLC_BIND_0089@@sdlc-git-commit`。
- 对每个可执行钩子，根据其 `optional` 标志输出以下内容：
  - **可选钩子**（`optional: true`）：

    ```text
    ## 扩展钩子

    **可选前置钩子**: {extension}
    命令：`/{command}`
    说明：{description}

    提示：{prompt}
    执行：`/{command}`
    ```

  - **必需钩子**（`optional: false`）：

    ```text
    ## 扩展钩子

    **自动前置钩子**: {extension}
    正在执行：`/{command}`
    EXECUTE_COMMAND: {command}

    等待钩子命令返回结果后，再继续执行目标。
    ```
    输出以上内容后，必须实际调用钩子，等待执行完成后才能继续。按照在当前 Agent／会话中自行执行命令的方式调用（调用方式可能不同于上面显示的字面 `{command}` 标识，例如 Skills 模式的 Agent 使用 `/skill:sdlc-...` 或 `$sdlc-...`）。仅输出代码块并不会执行钩子。

- 如果没有注册钩子，或 `.sdlc/extensions.yml` 不存在，静默跳过。

## 目标

缩小功能规格、方案和任务要求与当前代码实现之间的差距。将 `spec.md`、`plan.md`、`tasks.md` 作为**意图的唯一来源**，并以宪法作为治理约束；评估当前代码，确定哪些需求、验收标准、方案决策和既有任务尚未满足、未完成或仅部分满足。将**每项剩余工作作为可追溯的新任务追加**到 `tasks.md` 底部，供 `@@SDLC_BIND_0121@@sdlc-300-task` 已生成完整 `tasks.md` 之后执行。

这**不是**差异工具，也**不**追踪变更。它相对于功能产物评估代码的当前状态：不使用 Git，不比较分支，不查看历史。

## 操作约束

**只追加，绝不重写（APPEND-ONLY, NEVER REWRITE）**：本命令**唯一**的写入，是向 `tasks.md` 追加新的 `## 阶段 N：收敛` 章节。**不得**：

- 以任何方式修改 `spec.md` 或 `plan.md`。
- 重写、重新编号、重排或删除任何既有任务，包括之前 Convergence 阶段的任务。
- 修改、创建或删除任何应用代码；完成追加任务是 `@@SDLC_BIND_0131@@sdlc-400-impl` 的职责。

代码已经满足全部要求时，必须保持 `tasks.md` **逐字节不变**，不能追加空的 Convergence 标题，并报告无差距结果。

**宪法权威**：项目宪法（`.sdlc/memory/constitution.md`）**不可协商**。违反 MUST 原则的代码属于最高严重级别发现，必须产生对应整改任务。宪法尚未填写、只是模板时，正常跳过宪法检查，而不是失败。

## 执行步骤

### 1. 初始化收敛上下文

在仓库根目录运行一次 `SDLC_HOST=c@@SDLC_BIND_0141@@ SDLC_INIT_DIR="${SDLC_PROJECT_ROOT:?}" bash "${SDLC_PLUGIN_ROOT:?}/scripts/bash/check-prerequisites.sh" --json --require-spec --require-tasks --include-tasks`，解析 JSON 中的 FEATURE_DIR 和 AVAILABLE_DOCS。推导绝对路径：

- SPEC = FEATURE_DIR/spec.md
- PLAN = FEATURE_DIR/plan.md
- TASKS = FEATURE_DIR/tasks.md
- CONSTITUTION = `.sdlc/memory/constitution.md`（如果存在）。
如果 `spec.md`、`plan.md` 或 `tasks.md` 缺失，停止并给出明确、可执行的信息，指出需要运行的前置命令：缺规格用 `@@SDLC_BIND_0147@@sdlc-300-task`。不输出不完整结果。
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

将所有既有任务都纳入意图清单，不论其复选框状态或所属收敛阶段：完成声明并非证据。对照规格、方案、任务和宪法验证当前行为；对于纠正性任务链，应评估其形成的行为，而不是已被替代的实现细节。既要检查尚未履行的义务，也要检查与声明的意图相矛盾、超出该意图或落在其范围之外的实现。

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
2. 写入单个新章节标题 `## 阶段 N：收敛`。
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

- 结果为 `tasks_appended`：说明在哪个阶段追加了多少任务，建议运行 `@@SDLC_BIND_0256@@sdlc-400-impl` 完成；说明后续再次收敛时，剩余项应减少或归零。
- 结果为 `converged`：建议进入评审／创建 PR。对于本功能已规定范围，不需要再次实施。

### 9. 检查扩展钩子

生成结果后，检查项目根目录是否存在 `.sdlc/extensions.yml`。

- 如果存在，读取文件并查找 `hooks.after_converge` 键下的条目。
- 如果 YAML 无法解析或无效，不得静默跳过：告知用户 `.sdlc/extensions.yml` 无法读取（包含解析器错误），并且未检查任何钩子，包括其中登记的任何强制（`optional: false`）钩子，然后正常继续。
- 排除 `enabled` 明确为 `false` 的钩子。未包含 `enabled` 字段的钩子默认启用。
- 对每个剩余钩子，**不要**尝试解释或求值其 `condition` 表达式：
  - 如果钩子没有 `condition` 字段，或该字段为 null／空，将其视为可执行。
  - 如果钩子定义了非空 `condition`，跳过该钩子，将条件求值留给 HookExecutor 实现。
- 列出任何钩子之前，先在会话中报告收敛结果（`converged` 或 `tasks_appended`），让用户决定是否执行可选的后续命令。
- 根据钩子命令名构造调用时，将点号（`.`）替换为连字符（`-`）。例如，`sdlc.git.commit` → `@@SDLC_BIND_0270@@sdlc-git-commit`。
- 对每个可执行钩子，根据其 `optional` 标志输出以下内容：
  - **可选钩子**（`optional: true`）：

    ```text
    ## 扩展钩子

    **可选钩子**: {extension}
    命令：`/{command}`
    说明：{description}

    提示：{prompt}
    执行：`/{command}`
    ```

  - **必需钩子**（`optional: false`）：

    ```text
    ## 扩展钩子

    **自动钩子**: {extension}
    正在执行：`/{command}`
    EXECUTE_COMMAND: {command}
    ```
    输出以上内容后，必须实际调用钩子，等待执行完成后才能继续。按照在当前 Agent／会话中自行执行命令的方式调用（调用方式可能不同于上面显示的字面 `{command}` 标识，例如 Skills 模式的 Agent 使用 `/skill:sdlc-...` 或 `$sdlc-...`）。仅输出代码块并不会执行钩子。

- 如果没有注册钩子，或 `.sdlc/extensions.yml` 不存在，静默跳过。

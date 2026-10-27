
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

本次涉及多个文件时重复传入 `--path`。只编辑返回的 `proposal.json`：每个已准备文件使用 `{"action":"replace","text":"complete candidate text"}` 或 `{"action":"skip"}`。随后通过程序发布：

```sh
python3 -I -B "${SDLC_PLUGIN_ROOT:?}/scripts/python/store_changes.py" apply --project "${SDLC_PROJECT_ROOT:?}" --transaction '<returned-transaction-directory>'
```

普通编辑的快照只包含选定文件、`init-options.json` 和当前工作区的 `FEATURE_JSON`。无关产物及其他 worktree 的需求选择不使候选失效；本次目标或必要绑定变化仍阻止应用。导入和归拢保留来源与目标快照检查。

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

**检查扩展钩子（规划前）**：
- 检查项目根目录是否存在 `.sdlc/extensions.yml`。
- 如果存在，读取文件并查找 `hooks.before_plan` 键下的条目。
- 如果 YAML 无法解析或无效，不得静默跳过：告知用户 `.sdlc/extensions.yml` 无法读取（包含解析器错误），并且未检查任何钩子，包括其中登记的任何强制（`optional: false`）钩子，然后正常继续。
- 排除 `enabled` 明确为 `false` 的钩子。未包含 `enabled` 字段的钩子默认启用。
- 对每个剩余钩子，**不要**尝试解释或求值其 `condition` 表达式：
  - 如果钩子没有 `condition` 字段，或该字段为 null／空，将其视为可执行。
  - 如果钩子定义了非空 `condition`，跳过该钩子，将条件求值留给 HookExecutor 实现。
- 根据钩子命令名构造调用时，将点号（`.`）替换为连字符（`-`）。例如，`sdlc.git.commit` → `@@SDLC_BIND_0080@@sdlc-git-commit`。
- 对每个可执行钩子，根据其 `optional` 标志输出以下内容：
  - **可选钩子**（`optional: true`）：
    ```
    ## 扩展钩子

    **可选前置钩子**: {extension}
    命令：`/{command}`
    说明：{description}

    提示：{prompt}
    执行：`/{command}`
    ```
  - **必需钩子**（`optional: false`）：
    ```
    ## 扩展钩子

    **自动前置钩子**: {extension}
    正在执行：`/{command}`
    EXECUTE_COMMAND: {command}

    等待钩子命令返回结果后，再继续执行概要。
    ```
    输出以上内容后，必须实际调用钩子，等待执行完成后才能继续。按照在当前 Agent／会话中自行执行命令的方式调用（调用方式可能不同于上面显示的字面 `{command}` 标识，例如 Skills 模式的 Agent 使用 `/skill:sdlc-...` 或 `$sdlc-...`）。仅输出代码块并不会执行钩子。
- 如果没有注册钩子，或 `.sdlc/extensions.yml` 不存在，静默跳过。

## 执行概要

1. **准备**：在仓库根目录运行 `SDLC_HOST=c@@SDLC_BIND_0108@@ SDLC_INIT_DIR="${SDLC_PROJECT_ROOT:?}" bash "${SDLC_PLUGIN_ROOT:?}/scripts/bash/setup-plan.sh" --json`，从 JSON 解析 FEATURE_SPEC、IMPL_PLAN、FEATURE_DIR、BRANCH。参数包含单引号（如 "I'm Groot"）时，使用转义语法，如 'I'\''m Groot'；可以使用双引号时也可写作 "I'm Groot"。

2. **加载上下文**：读取 FEATURE_SPEC 和 `.sdlc/memory/constitution.md`。加载已经复制好的 IMPL_PLAN 模板。

3. **执行规划流程**：按照 IMPL_PLAN 模板结构：
   - 填写 Technical Context，将未知项标为 "NEEDS CLARIFICATION"。
   - 依据宪法填写 Constitution Check 章节。
   - 评估门禁，违规且没有充分理由时返回 ERROR。
   - 阶段 0：生成 research.md，解决全部 NEEDS CLARIFICATION。
   - 阶段 1：生成 data-model.md、contracts/、quickstart.md。
   - 设计完成后重新评估 Constitution Check。

## 必需的执行后钩子

**在向用户报告完成之前，必须完成本节。**

检查项目根目录是否存在 `.sdlc/extensions.yml`。
- 如果不存在，或 `hooks.after_plan` 下没有注册钩子，跳转到完成报告。
- 如果存在，读取文件并查找 `hooks.after_plan` 键下的条目。
- 如果 YAML 无法解析或无效，不得静默跳过：告知用户 `.sdlc/extensions.yml` 无法读取（包含解析器错误），并且未检查任何钩子，包括其中登记的任何强制（`optional: false`）钩子，然后继续到完成报告。
- 排除 `enabled` 明确为 `false` 的钩子。未包含 `enabled` 字段的钩子默认启用。
- 对每个剩余钩子，**不要**尝试解释或求值其 `condition` 表达式：
  - 如果钩子没有 `condition` 字段，或该字段为 null／空，将其视为可执行。
  - 如果钩子定义了非空 `condition`，跳过该钩子，将条件求值留给 HookExecutor 实现。
- 根据钩子命令名构造调用时，将点号（`.`）替换为连字符（`-`）。例如，`sdlc.git.commit` → `@@SDLC_BIND_0132@@sdlc-git-commit`。
- 对每个可执行钩子，根据其 `optional` 标志输出以下内容：
  - **必需钩子**（`optional: false`）——**必须为每个必需钩子输出 `EXECUTE_COMMAND:`**：
    ```
    ## 扩展钩子

    **自动钩子**: {extension}
    正在执行：`/{command}`
    EXECUTE_COMMAND: {command}
    ```
    输出以上内容后，必须实际调用钩子，等待执行完成后才能继续。按照在当前 Agent／会话中自行执行命令的方式调用（调用方式可能不同于上面显示的字面 `{command}` 标识，例如 Skills 模式的 Agent 使用 `/skill:sdlc-...` 或 `$sdlc-...`）。仅输出代码块并不会执行钩子。
  - **可选钩子**（`optional: true`）：
    ```
    ## 扩展钩子

    **可选钩子**: {extension}
    命令：`/{command}`
    说明：{description}

    提示：{prompt}
    执行：`/{command}`
    ```

## 完成报告

命令在阶段 1 设计完成后结束。报告分支、IMPL_PLAN 路径及生成的产物。

## 各阶段

### 阶段 0：概要与研究

1. **从上面的 Technical Context 提取未知项**：
   - 每个 NEEDS CLARIFICATION → 一项研究任务。
   - 每项依赖 → 一项最佳实践任务。
   - 每项集成 → 一项模式研究任务。

2. **生成并分派研究 Agent**：

   ```text
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. 在 `research.md` 中**汇总发现**，使用以下格式：
   - 决策：[选定的方案]。
   - 理由：[选择理由]。
   - 替代方案：[还评估过哪些方案]。

**输出**：research.md，全部 NEEDS CLARIFICATION 均已解决。

### 阶段 1：设计与契约

**前置条件：**`research.md` 已完成。

1. **从功能规格提取实体** → `data-model.md`：
   - 新生成的自然语言标题、字段说明、关系说明使用中文；实体名、字段名、代码类型和其他项目真实标识保持项目原样。
   - 实体名称、字段、关系。
   - 需求中的验证规则。
   - 适用时的状态转换。

2. **定义接口契约**（项目存在外部接口时）→ `/contracts/`：
   - 新生成的自然语言标题和说明使用中文；HTTP 方法、路径、schema、字段名、协议及代码标识保持原样。
   - 识别项目向用户或其他系统暴露的接口。
   - 使用适合项目类型的契约格式记录。
   - 例如：库的公共 API、CLI 工具的命令模式、Web 服务端点、解析器的语法、应用的 UI 契约。
   - 纯内部项目（构建脚本、一次性工具等）跳过此项。

3. **创建快速开始验证指南** → `quickstart.md`：
   - 新生成的自然语言标题和说明使用中文；命令、路径、参数和代码保持原样。
   - 记录可运行的验证场景，以证明功能端到端可用。
   - 包含前置条件、准备命令、测试／运行命令及预期结果。
   - 使用链接或引用指向契约与数据模型细节，不重复它们。
   - 不包含完整实现代码、模型／服务／控制器实现体、迁移脚本或完整测试套件。
   - 将该产物保持为验证／运行指南；实现细节属于 `tasks.md` 和实施阶段。

**输出**：data-model.md、/contracts/*、quickstart.md。

## 关键规则

- 文件系统操作使用绝对路径；文档引用使用项目相对路径。
- 门禁失败或存在未解决澄清项时返回 ERROR。

## 完成条件

- [ ] 已执行规划流程并生成设计产物。
- [ ] 已按照上文“必需的执行后钩子”规则分派或跳过扩展钩子。
- [ ] 已向用户报告完成，包括分支、方案路径及生成的产物。

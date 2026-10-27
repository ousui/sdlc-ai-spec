
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

## 范围约束

本命令自身的工作仅限于更新项目宪法。依赖它的模板与命令在运行时读取宪法，不在此处修改。

- 将用户输入的每一部分归类为宪法内容，或独立的非治理意图。
- 如果输入包含功能实现、代码生成、重构、构建或部署请求，**不得**执行；应提取为待后续处理的意图。
- **不得**创建、修改或删除应用源码、功能路由、组件、测试、部署文件或其他与宪法流程无关的产物。
- 如果无法判断某条指示是否属于宪法内容，在修改之前先澄清。
- 完成宪法更新后，为各项待处理意图列出 `后续行动` 章节。保留原始意图，建议合适的后续 SDLC AI SPEC 命令，例如 `@@SDLC_BIND_0078@@sdlc-100-spec`，但不调用它。
- 如果没有非治理意图，省略 `后续行动` 章节。

## 执行前检查

**检查扩展钩子（宪法更新前）**：
- 检查项目根目录是否存在 `.sdlc/extensions.yml`。
- 如果存在，读取文件并查找 `hooks.before_constitution` 键下的条目。
- 如果 YAML 无法解析或无效，不得静默跳过：告知用户 `.sdlc/extensions.yml` 无法读取（包含解析器错误），并且未检查任何钩子，包括其中登记的任何强制（`optional: false`）钩子，然后正常继续。
- 排除 `enabled` 明确为 `false` 的钩子。未包含 `enabled` 字段的钩子默认启用。
- 对每个剩余钩子，**不要**尝试解释或求值其 `condition` 表达式：
  - 如果钩子没有 `condition` 字段，或该字段为 null／空，将其视为可执行。
  - 如果钩子定义了非空 `condition`，跳过该钩子，将条件求值留给 HookExecutor 实现。
- 根据钩子命令名构造调用时，将点号（`.`）替换为连字符（`-`）。例如，`sdlc.git.commit` → `@@SDLC_BIND_0091@@sdlc-git-commit`。
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

你正在更新 `.sdlc/memory/constitution.md` 中的项目宪法。执行命令时，通过 SDLC AI SPEC 的预设／模板解析栈，从 `constitution-template` 解析当前生效的宪法骨架。

按以下流程执行：

1. 在仓库根目录运行 `SDLC_HOST=c@@SDLC_BIND_0123@@ SDLC_INIT_DIR="${SDLC_PROJECT_ROOT:?}" bash "${SDLC_PLUGIN_ROOT:?}/scripts/bash/resolve-template.sh" constitution-template --json`，解析 `TEMPLATE_CONTENT`，作为生效模板。
   - 共享解析器在回退至核心模板之前，依次应用项目覆盖、组合预设层和扩展层。解析必须成功后才能继续。
   - 如果失败，停止并报告解析错误；不得仅使用其中一层模板继续。
   - 如果 `.sdlc/memory/constitution.md` 已存在，将其作为当前项目特定值和修订内容的来源。应用新解析的骨架时，保留仍然适用的信息。
   - 如果不存在，使用解析出的模板作为初始文档。
   - 不得回写任何受版本管理的模板层。
   - 识别所有形如 `[ALL_CAPS_IDENTIFIER]` 的占位符。
   **重要**：用户要求的原则数量可能少于或多于模板。用户指定数量时，应尊重该数量并遵循模板的总体结构，相应更新文档。

2. 收集或推导占位符的值：
   - 用户输入（对话）提供了值时，使用该值。
   - 否则从现有仓库上下文推导，包括 README、文档、已嵌入的历史宪法版本。
   - 治理日期：`RATIFICATION_DATE` 是最初采用日期（未知时询问或标记 TODO）；发生修改时，`LAST_AMENDED_DATE` 为今天，否则保留原值。
   - `CONSTITUTION_VERSION` 必须按语义版本规则递增：
     - MAJOR：不向后兼容的治理／原则删除或重新定义。
     - MINOR：新增原则／章节，或实质性扩展指导内容。
     - PATCH：澄清、措辞、拼写修正及不改变语义的细化。
   - 无法确定升级类型时，先提出理由，再最终确定。

3. 以解析出的模板为必需结构，起草更新后的宪法内容：
   - 将每个占位符替换为具体文本。除项目有意暂不定义并保留的模板槽位外，不留下方括号标记；保留的标记必须明确说明理由。
   - 保持标题层级；替换后的注释可以删除，除非仍有澄清作用。
   - 每个原则章节都应有简洁名称、表述不可协商规则的段落或列表；理由不明显时明确说明。
   - 治理章节必须列出修订程序、版本策略及合规评审要求。

4. 在宪法更新后，将同步影响报告以 HTML 注释写在文件顶部。
   该报告是供人工审查本次修订的临时草稿，不是治理内容；修订后的宪法文件提交前应删除该报告。
   - 版本变化：旧 → 新。
   - 修改的原则列表（改名时列出旧标题 → 新标题）。
   - 新增章节。
   - 删除章节。
   - 有意推迟填写占位符时的后续 TODO。

5. 最终输出前验证：
   - 不存在未说明的方括号标记。
   - 版本行与报告一致。
   - 日期采用 ISO 格式 YYYY-MM-DD。
   - 原则具有明确陈述、可测试，避免模糊语言（适当时把含糊的 should 改为有理由支撑的 MUST／SHOULD）。

6. 将完成的宪法写回 `.sdlc/memory/constitution.md`（覆盖）。

7. 向用户输出最终摘要，包含：
   - 新版本及升级理由。
   - 需要人工跟进的 TODO 占位符或推迟项。
   - 建议的提交消息，例如 `docs: amend constitution to vX.Y.Z (principle additions + governance update)`。
   - 对推迟的非治理意图提供 `后续行动` 章节。

格式与风格要求：

- Markdown 标题严格使用模板中的层级，不升级或降级。
- 为提高可读性，对较长的理由行适当换行（理想情况下少于 100 个字符），但不要生硬强制换行。
- 章节之间保留一个空行。
- 避免尾随空白。

用户只提供部分更新（例如仅修订一条原则）时，仍须执行验证和版本判断步骤。

缺少关键信息（例如确实无法得知批准日期）时，插入 `TODO(<FIELD_NAME>): explanation`，并在同步影响报告的推迟项中列出。

只写入 `.sdlc/memory/constitution.md`；不得创建或修改模板源文件。

## 执行后检查

**检查扩展钩子（宪法更新后）**：
检查项目根目录是否存在 `.sdlc/extensions.yml`。
- 如果存在，读取文件并查找 `hooks.after_constitution` 键下的条目。
- 如果 YAML 无法解析或无效，不得静默跳过：告知用户 `.sdlc/extensions.yml` 无法读取（包含解析器错误），并且未检查任何钩子，包括其中登记的任何强制（`optional: false`）钩子，然后正常继续。
- 排除 `enabled` 明确为 `false` 的钩子。未包含 `enabled` 字段的钩子默认启用。
- 对每个剩余钩子，**不要**尝试解释或求值其 `condition` 表达式：
  - 如果钩子没有 `condition` 字段，或该字段为 null／空，将其视为可执行。
  - 如果钩子定义了非空 `condition`，跳过该钩子，将条件求值留给 HookExecutor 实现。
- 根据钩子命令名构造调用时，将点号（`.`）替换为连字符（`-`）。例如，`sdlc.git.commit` → `@@SDLC_BIND_0193@@sdlc-git-commit`。
- 对每个可执行钩子，根据其 `optional` 标志输出以下内容：
  - **可选钩子**（`optional: true`）：
    ```
    ## 扩展钩子

    **可选钩子**: {extension}
    命令：`/{command}`
    说明：{description}

    提示：{prompt}
    执行：`/{command}`
    ```
  - **必需钩子**（`optional: false`）：
    ```
    ## 扩展钩子

    **自动钩子**: {extension}
    正在执行：`/{command}`
    EXECUTE_COMMAND: {command}
    ```
    输出以上内容后，必须实际调用钩子，等待执行完成后才能继续。按照在当前 Agent／会话中自行执行命令的方式调用（调用方式可能不同于上面显示的字面 `{command}` 标识，例如 Skills 模式的 Agent 使用 `/skill:sdlc-...` 或 `$sdlc-...`）。仅输出代码块并不会执行钩子。
- 如果没有注册钩子，或 `.sdlc/extensions.yml` 不存在，静默跳过。

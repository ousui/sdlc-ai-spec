


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
- 完成宪法更新后，为各项待处理意图列出 `Next Actions` 章节。保留原始意图，建议合适的后续 SDLC AI SPEC 命令，例如 `{{SDLC:SPECIFY}}`，但不调用它。
- 如果没有非治理意图，省略 `Next Actions` 章节。

## 执行前检查

**检查扩展钩子（宪法更新前）**：
- 检查项目根目录是否存在 `.sdlc/extensions.yml`。
- 如果存在，读取文件并查找 `hooks.before_constitution` 键下的条目。
- 如果 YAML 无法解析或无效，静默跳过钩子检查，正常继续。
- 排除 `enabled` 明确为 `false` 的钩子。未包含 `enabled` 字段的钩子默认启用。
- 对每个剩余钩子，**不要**尝试解释或求值其 `condition` 表达式：
  - 如果钩子没有 `condition` 字段，或该字段为 null／空，将其视为可执行。
  - 如果钩子定义了非空 `condition`，跳过该钩子，将条件求值留给 HookExecutor 实现。
- 根据钩子命令名构造调用时，将点号（`.`）替换为连字符（`-`）。例如，`sdlc.git.commit` → `{{SDLC:HOOK_EXAMPLE}}`。
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

你正在更新 `.sdlc/memory/constitution.md` 中的项目宪法。执行命令时，通过 SDLC AI SPEC 的预设／模板解析栈，从 `constitution-template` 解析当前生效的宪法骨架。

按以下流程执行：

1. 在仓库根目录运行 `SDLC_HOST={{SDLC:HOST}} SDLC_INIT_DIR="${SDLC_PROJECT_ROOT:?}" bash "${SDLC_PLUGIN_ROOT:?}/scripts/bash/resolve-template.sh" constitution-template --json`，解析 `TEMPLATE_CONTENT`，作为生效模板。
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

4. 生成 Sync Impact Report（同步影响报告），在宪法更新后以 HTML 注释置于文件顶部：
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
   - 对推迟的非治理意图提供 `Next Actions` 章节。

格式与风格要求：

- Markdown 标题严格使用模板中的层级，不升级或降级。
- 为提高可读性，对较长的理由行适当换行（理想情况下少于 100 个字符），但不要生硬强制换行。
- 章节之间保留一个空行。
- 避免尾随空白。

用户只提供部分更新（例如仅修订一条原则）时，仍须执行验证和版本判断步骤。

缺少关键信息（例如确实无法得知批准日期）时，插入 `TODO(<FIELD_NAME>): explanation`，并在 Sync Impact Report 的推迟项中列出。

只写入 `.sdlc/memory/constitution.md`；不得创建或修改模板源文件。

## 执行后检查

**检查扩展钩子（宪法更新后）**：
检查项目根目录是否存在 `.sdlc/extensions.yml`。
- 如果存在，读取文件并查找 `hooks.after_constitution` 键下的条目。
- 如果 YAML 无法解析或无效，静默跳过钩子检查，正常继续。
- 排除 `enabled` 明确为 `false` 的钩子。未包含 `enabled` 字段的钩子默认启用。
- 对每个剩余钩子，**不要**尝试解释或求值其 `condition` 表达式：
  - 如果钩子没有 `condition` 字段，或该字段为 null／空，将其视为可执行。
  - 如果钩子定义了非空 `condition`，跳过该钩子，将条件求值留给 HookExecutor 实现。
- 根据钩子命令名构造调用时，将点号（`.`）替换为连字符（`-`）。例如，`sdlc.git.commit` → `{{SDLC:HOOK_EXAMPLE}}`。
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

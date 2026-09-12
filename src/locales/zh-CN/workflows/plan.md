


## 用户输入

```text
$ARGUMENTS
```

继续之前，**必须**考虑用户输入（如果非空）。

## 执行前检查

**检查扩展钩子（规划前）**：
- 检查项目根目录是否存在 `.sdlc/extensions.yml`。
- 如果存在，读取文件并查找 `hooks.before_plan` 键下的条目。
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

1. **准备**：在仓库根目录运行 `SDLC_HOST={{SDLC:HOST}} SDLC_INIT_DIR="${SDLC_PROJECT_ROOT:?}" bash "${SDLC_PLUGIN_ROOT:?}/scripts/bash/setup-plan.sh" --json`，从 JSON 解析 FEATURE_SPEC、IMPL_PLAN、FEATURE_DIR、BRANCH。参数包含单引号（如 "I'm Groot"）时，使用转义语法，如 'I'\''m Groot'；可以使用双引号时也可写作 "I'm Groot"。

2. **加载上下文**：读取 FEATURE_SPEC 和 `.sdlc/memory/constitution.md`。加载已经复制好的 IMPL_PLAN 模板。

3. **执行规划流程**：按照 IMPL_PLAN 模板结构：
   - 填写 Technical Context，将未知项标为 "NEEDS CLARIFICATION"。
   - 依据宪法填写 Constitution Check 章节。
   - 评估门禁，违规且没有充分理由时返回 ERROR。
   - Phase 0：生成 research.md，解决全部 NEEDS CLARIFICATION。
   - Phase 1：生成 data-model.md、contracts/、quickstart.md。
   - 设计完成后重新评估 Constitution Check。

## 必需的执行后钩子

**在向用户报告完成之前，必须完成本节。**

检查项目根目录是否存在 `.sdlc/extensions.yml`。
- 如果不存在，或 `hooks.after_plan` 下没有注册钩子，跳转到完成报告。
- 如果存在，读取文件并查找 `hooks.after_plan` 键下的条目。
- 如果 YAML 无法解析或无效，静默跳过钩子检查，继续到完成报告。
- 排除 `enabled` 明确为 `false` 的钩子。未包含 `enabled` 字段的钩子默认启用。
- 对每个剩余钩子，**不要**尝试解释或求值其 `condition` 表达式：
  - 如果钩子没有 `condition` 字段，或该字段为 null／空，将其视为可执行。
  - 如果钩子定义了非空 `condition`，跳过该钩子，将条件求值留给 HookExecutor 实现。
- 根据钩子命令名构造调用时，将点号（`.`）替换为连字符（`-`）。例如，`sdlc.git.commit` → `{{SDLC:HOOK_EXAMPLE}}`。
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

命令在 Phase 1 设计完成后结束。报告分支、IMPL_PLAN 路径及生成的产物。

## 各阶段

### Phase 0：概要与研究

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
   - Decision：[选定的方案]。
   - Rationale：[选择理由]。
   - Alternatives considered：[还评估过哪些方案]。

**输出**：research.md，全部 NEEDS CLARIFICATION 均已解决。

### Phase 1：设计与契约

**前置条件：**`research.md` 已完成。

1. **从功能规格提取实体** → `data-model.md`：
   - 实体名称、字段、关系。
   - 需求中的验证规则。
   - 适用时的状态转换。

2. **定义接口契约**（项目存在外部接口时）→ `/contracts/`：
   - 识别项目向用户或其他系统暴露的接口。
   - 使用适合项目类型的契约格式记录。
   - 例如：库的公共 API、CLI 工具的命令模式、Web 服务端点、解析器的语法、应用的 UI 契约。
   - 纯内部项目（构建脚本、一次性工具等）跳过此项。

3. **创建快速开始验证指南** → `quickstart.md`：
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

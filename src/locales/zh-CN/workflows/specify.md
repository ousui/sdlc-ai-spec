


## 用户输入

```text
$ARGUMENTS
```

继续之前，**必须**考虑用户输入（如果非空）。

## 执行前检查

**检查扩展钩子（规格编写前）**：
- 检查项目根目录是否存在 `.sdlc/extensions.yml`。
- 如果存在，读取文件并查找 `hooks.before_specify` 键下的条目。
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

触发消息中，用户在 `{{SDLC:SPECIFY}}` 后输入的文本**就是**功能描述。即使下面出现字面 `$ARGUMENTS`，也应视为本会话中已经有该输入。除非用户提交了空命令，否则不要要求重复描述。

根据该功能描述执行：

1. 为功能**生成简洁短名称**，2–4 个词：
   - 分析功能描述，提取最有意义的关键词。
   - 用 2–4 个词概括功能核心。
   - 尽量采用动作－名词形式，例如 add-user-auth、fix-payment-bug。
   - 保留技术术语及缩写，例如 OAuth2、API、JWT。
   - 简洁，同时让人能一眼理解功能。
   - 示例：
     - “添加用户认证” → user-auth。
     - “为 API 实现 OAuth2 集成” → oauth2-api-integration。
     - “创建分析看板” → analytics-dashboard。
     - “修复支付处理超时” → fix-payment-timeout。

2. **创建分支**，可选、通过钩子进行：

   如果上述执行前检查中的 `before_specify` 钩子成功运行，它会创建／切换 Git 分支，并输出包含 `BRANCH_NAME`、`FEATURE_NUM` 的 JSON。记录这些值以便引用，但分支名称**不决定**规格目录名称。

   用户明确提供 `GIT_BRANCH_NAME` 时，原样传递给钩子，让分支脚本直接使用该值，绕过所有前缀／后缀生成。

3. **创建规格功能目录**：

   除非用户明确提供 `SDLC_FEATURE_DIRECTORY`，否则规格位于默认 `.sdlc/specs/` 目录下。

   **`SDLC_FEATURE_DIRECTORY` 解析顺序**：
   1. 用户通过环境变量、参数或配置明确提供 `SDLC_FEATURE_DIRECTORY` 时，原样使用。
   2. 否则在 `.sdlc/specs/` 下自动生成：
      - 读取 `.sdlc/init-options.json` 中的 `feature_numbering`（优先），或 `branch_numbering`（已弃用，仅供迁移，未来版本将移除）。
      - 为 `"timestamp"` 时：前缀是 `YYYYMMDD-HHMMSS`，使用当前时间戳。
      - 为 `"sequential"` 或缺省时：前缀是 `NNN`，扫描 `.sdlc/specs/` 下既有目录后得到下一个可用三位数。
      - 构造目录名 `<prefix>-<short-name>`，例如 `003-user-auth` 或 `20260319-143022-user-auth`。
      - 将 `SDLC_FEATURE_DIRECTORY` 设置为 `.sdlc/specs/<directory-name>`。
      - 使用了 `branch_numbering` 且没有 `feature_numbering` 时，输出一行警告：“⚠️ init-options.json 中的 `branch_numbering` 已弃用，请重命名为 `feature_numbering`。”

   **创建目录和规格文件**：
   - `mkdir -p SDLC_FEATURE_DIRECTORY`
   - 通过 SDLC AI SPEC 预设／模板解析栈解析当前生效的 `spec-template`，等价于 `SDLC_HOST={{SDLC:HOST}} SDLC_INIT_DIR="${SDLC_PROJECT_ROOT:?}" bash "${SDLC_PLUGIN_ROOT:?}/scripts/bash/resolve-template.sh" spec-template`。
   - 将解析出的 `spec-template` 文件复制到 `SDLC_FEATURE_DIRECTORY/spec.md`，作为起点。
   - 把 `SPEC_FILE` 设置为 `SDLC_FEATURE_DIRECTORY/spec.md`。
   - 将解析后的路径持久化到 `.sdlc/feature.json`：
     ```json
     {
       "feature_directory": "<resolved feature dir>"
     }
     ```
     写入实际解析的目录路径，例如 `.sdlc/specs/003-user-auth`，而不是字面字符串 `SDLC_FEATURE_DIRECTORY`。
     这样后续命令（`{{SDLC:PLAN}}`、`{{SDLC:TASKS}}` 等）无需依赖 Git 分支命名惯例即可定位功能目录。

   **重要**：
   - 每次 `{{SDLC:SPECIFY}}` 调用只能创建一个功能。
   - 规格目录名称与 Git 分支名称互相独立；可以相同，但由用户选择。
   - 规格目录和文件始终由本命令创建，绝不由钩子创建。

4. 加载解析出的生效 `spec-template` 文件，了解必需章节。

5. **如果存在**：加载 `.sdlc/memory/constitution.md`，获取项目原则和治理约束。

6. 按以下流程执行：
    1. 从参数解析用户描述。
       为空时，返回 ERROR：“未提供功能描述”。
    2. 提取关键概念：角色、动作、数据、约束。
    3. 对不清楚的方面：
       - 根据上下文及行业标准作有依据的推断。
       - 仅在以下条件下标注 [NEEDS CLARIFICATION: specific question]：
         - 选择显著影响功能范围或用户体验。
         - 存在多种合理解释，且影响不同。
         - 没有合理默认值。
       - **限制：总共最多 3 个 [NEEDS CLARIFICATION] 标记。**
       - 按影响排序：范围 > 安全／隐私 > 用户体验 > 技术细节。
    4. 填写 User Scenarios & Testing。
       无法确定清晰用户流程时，返回 ERROR：“无法确定用户场景”。
    5. 生成功能需求，每项必须可测试。
       对未说明细节采用合理默认值，在 Assumptions 中记录假设。
    6. 定义 Success Criteria。
       生成可衡量、与技术无关的结果，同时包含时间、性能、数量等定量指标及用户满意度、任务完成等定性衡量。
       每条标准必须能在不了解实现细节的情况下验证。
    7. 涉及数据时，识别 Key Entities。
    8. 返回 SUCCESS：规格已准备好进入规划。

7. 按模板结构把规格写入 SPEC_FILE，用从功能描述（参数）得到的具体细节替换占位符，保留章节顺序和标题。

8. **规格质量验证**：初稿写入后，按质量标准验证：

   a. **创建规格质量清单**：在 `SDLC_FEATURE_DIRECTORY/checklists/requirements.md` 生成清单，采用清单模板结构和以下验证项：

      ```markdown
      # Specification Quality Checklist: [FEATURE NAME]

      **Purpose**: Validate specification completeness and quality before proceeding to planning
      **Created**: [DATE]
      **Feature**: [Link to spec.md]

      ## Content Quality

      - [ ] No implementation details (languages, frameworks, APIs)
      - [ ] Focused on user value and business needs
      - [ ] Written for non-technical stakeholders
      - [ ] All mandatory sections completed

      ## Requirement Completeness

      - [ ] No [NEEDS CLARIFICATION] markers remain
      - [ ] Requirements are testable and unambiguous
      - [ ] Success criteria are measurable
      - [ ] Success criteria are technology-agnostic (no implementation details)
      - [ ] All acceptance scenarios are defined
      - [ ] Edge cases are identified
      - [ ] Scope is clearly bounded
      - [ ] Dependencies and assumptions identified

      ## Feature Readiness

      - [ ] All functional requirements have clear acceptance criteria
      - [ ] User scenarios cover primary flows
      - [ ] Feature meets measurable outcomes defined in Success Criteria
      - [ ] No implementation details leak into specification

      ## Notes

      - Items marked incomplete require spec updates before `{{SDLC:CLARIFY}}` or `{{SDLC:PLAN}}`
      ```

   b. **执行验证**：逐项检查规格。
      - 确定每项通过或失败。
      - 记录具体问题，并引用相关规格章节。

   c. **处理验证结果**：

      - **全部通过**：将清单标记为完成，继续“必需的执行后钩子”。

      - **条目失败，但不包括 [NEEDS CLARIFICATION]**：
        1. 列出失败条目和具体问题。
        2. 更新规格，逐项解决。
        3. 重新验证直到全部通过，最多 3 轮。
        4. 3 轮后仍失败，将剩余问题写入清单备注并警告用户。

      - **仍存在 [NEEDS CLARIFICATION] 标记**：
        1. 从规格提取全部 [NEEDS CLARIFICATION: ...]。
        2. **额度检查**：超过 3 个时，仅保留对范围／安全／UX 影响最大的 3 个；其余采用有依据的推断。
        3. 对每个待澄清项（最多 3 个），按以下格式向用户提供选项：

           ```markdown
           ## Question [N]: [Topic]

           **Context**: [Quote relevant spec section]

           **What we need to know**: [Specific question from NEEDS CLARIFICATION marker]

           **Suggested Answers**:

           | Option | Answer | Implications |
           |--------|--------|--------------|
           | A      | [First suggested answer] | [What this means for the feature] |
           | B      | [Second suggested answer] | [What this means for the feature] |
           | C      | [Third suggested answer] | [What this means for the feature] |
           | Custom | Provide your own answer | [Explain how to provide custom input] |

           **Your choice**: _[Wait for user response]_
           ```

        4. **关键——表格格式**：保证 Markdown 表格有效：
           - 管道符对齐，间距一致。
           - 每个单元格内容两侧保留空格：`| Content |`，不是 `|Content|`。
           - 表头分隔线至少 3 个连字符：`|--------|`。
           - 在 Markdown 预览中检查表格能正确呈现。
        5. 问题依次编号 Q1、Q2、Q3，总计最多 3 个。
        6. 先一起展示全部问题，再等待回答。
        7. 等待用户给出全部选择，例如“Q1: A, Q2: Custom - [详情], Q3: B”。
        8. 用用户选择或提供的答案替换每个 [NEEDS CLARIFICATION] 标记，更新规格。
        9. 所有澄清解决后重新验证。

   d. **更新清单**：每轮验证后，把当前通过／失败状态更新到清单文件。

## 必需的执行后钩子

**在向用户报告完成之前，必须完成本节。**

检查项目根目录是否存在 `.sdlc/extensions.yml`。
- 如果不存在，或 `hooks.after_specify` 下没有注册钩子，跳转到完成报告。
- 如果存在，读取文件并查找 `hooks.after_specify` 键下的条目。
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

向用户报告完成，包含：
- `SDLC_FEATURE_DIRECTORY`：功能目录路径。
- `SPEC_FILE`：规格文件路径。
- 清单结果摘要。
- 是否准备好进入下一阶段（`{{SDLC:CLARIFY}}` 或 `{{SDLC:PLAN}}`）。

**注意**：分支创建由 `before_specify` 钩子（Git 扩展）负责。规格目录和文件始终由本核心命令创建。

## 简要准则

- 聚焦用户需要**什么**以及**为什么**。
- 避免描述如何实现，不写技术栈、API 或代码结构。
- 面向业务相关者，而非开发者撰写。
- 不要在规格内嵌入任何核对清单；清单由独立命令处理。

### 章节要求

- **必需章节**：每个功能都必须完成。
- **可选章节**：仅与本功能相关时包含。
- 章节不适用时，直接删除整个章节，不保留 N/A。

### AI 生成准则

根据用户提示创建规格时：

1. **有依据地推断**：依据上下文、行业标准和常见模式填补空缺。
2. **记录假设**：在 Assumptions 中记录合理默认值。
3. **限制澄清**：最多 3 个 [NEEDS CLARIFICATION]，只用于以下关键决策：
   - 显著影响功能范围或用户体验。
   - 存在影响不同的多种合理解释。
   - 没有任何合理默认值。
4. **澄清优先级**：范围 > 安全／隐私 > 用户体验 > 技术细节。
5. **像测试者一样思考**：模糊需求应无法通过“可测试且无歧义”的清单项。
6. **常见待澄清领域**，仅无合理默认值时询问：
   - 功能范围和边界：包括／排除哪些用例。
   - 用户类型和权限：存在多种冲突解释时。
   - 安全／合规要求：具有显著法律／财务影响时。

**合理默认值示例，不要为这些提问：**

- 数据保留：采用该领域行业惯例。
- 性能目标：无特别要求时，采用常见 Web／移动应用预期。
- 错误处理：用户友好的信息及合适的回退。
- 认证方式：Web 应用采用标准会话认证或 OAuth2。
- 集成模式：选用适合项目的模式，如 Web 服务 REST／GraphQL、库函数调用、工具 CLI 参数。

### 成功标准准则

成功标准必须：

1. **可衡量**：包含具体时间、百分比、数量或速率。
2. **技术无关**：不提框架、语言、数据库或工具。
3. **以用户为中心**：从用户／业务角度描述结果，而非系统内部实现。
4. **可验证**：无需知道实现细节即可测试／验证。

**良好示例：**

- 用户能在 3 分钟内完成结账。
- 系统支持 10,000 名并发用户。
- 95% 的搜索在 1 秒内返回结果。
- 任务完成率提高 40%。

**不佳示例，过于关注实现：**

- API 响应时间低于 200ms：过于技术化，改为用户能立即看到结果。
- 数据库能处理 1000 TPS：实现细节，应采用用户可感知指标。
- React 组件高效渲染：绑定具体框架。
- Redis 缓存命中率超过 80%：绑定具体技术。

## 完成条件

- [ ] 规格已写入 `SPEC_FILE`，并通过质量清单验证。
- [ ] 已按上文“必需的执行后钩子”规则分派或跳过扩展钩子。
- [ ] 已向用户报告功能目录、规格文件路径及清单结果。

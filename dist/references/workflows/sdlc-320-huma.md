
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



## 清单用途：“自然语言需求的单元测试”

**核心概念**：清单是**需求写作的单元测试**，用于验证特定领域需求的质量、清晰度和完整性。

**不是实现验证／测试：**

- ❌ 不是“验证按钮能正确点击”。
- ❌ 不是“测试错误处理正常工作”。
- ❌ 不是“确认 API 返回 200”。
- ❌ 不检查代码／实现是否匹配规格。

**用于需求质量验证：**

- ✅ “是否为所有卡片类型定义了视觉层级要求？”（完整性）
- ✅ “‘突出显示’是否量化为具体尺寸／位置？”（清晰度）
- ✅ “所有交互元素的悬停状态要求是否一致？”（一致性）
- ✅ “是否定义了键盘导航的无障碍要求？”（覆盖）
- ✅ “规格是否定义了徽标图片加载失败时的行为？”（边界情况）

**比喻**：如果规格是用英文写成的代码，清单就是它的单元测试套件。检查的是需求是否写得好、完整、无歧义并可进入实现，而**不是**实现是否正常工作。

**责任归属与复选框生命周期：**

- 本命令生成的自定义清单，是评审者负责的需求质量评审产物。
- `[x]` 表示评审者判定需求质量条件已满足。
- `[x]` **不**表示实现工作已经完成。
- 本命令生成或追加清单条目；**不得**把新生成条目标为 `[x]`。
- 只有评审者明确要求时，Agent 才能协助评估条目。
- `checklists/requirements.md` 是独立的内置规格质量清单，由 `@@SDLC_BIND_0056@@sdlc-110-clar` 维护；不能将这一例外套用于此处生成的自定义清单。

## 用户输入

```text
$ARGUMENTS
```

继续之前，**必须**考虑用户输入（如果非空）。

## 执行前检查

**检查扩展钩子（清单生成前）**：
- 检查项目根目录是否存在 `.sdlc/extensions.yml`。
- 如果存在，读取文件并查找 `hooks.before_checklist` 键下的条目。
- 如果 YAML 无法解析或无效，静默跳过钩子检查，正常继续。
- 排除 `enabled` 明确为 `false` 的钩子。未包含 `enabled` 字段的钩子默认启用。
- 对每个剩余钩子，**不要**尝试解释或求值其 `condition` 表达式：
  - 如果钩子没有 `condition` 字段，或该字段为 null／空，将其视为可执行。
  - 如果钩子定义了非空 `condition`，跳过该钩子，将条件求值留给 HookExecutor 实现。
- 根据钩子命令名构造调用时，将点号（`.`）替换为连字符（`-`）。例如，`sdlc.git.commit` → `@@SDLC_BIND_0076@@sdlc-git-commit`。
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

    Wait for the result of the hook command before proceeding to the Execution Steps.
    ```
    输出以上内容后，必须实际调用钩子，等待执行完成后才能继续。按照在当前 Agent／会话中自行执行命令的方式调用（调用方式可能不同于上面显示的字面 `{command}` 标识，例如 Skills 模式的 Agent 使用 `/skill:sdlc-...` 或 `$sdlc-...`）。仅输出代码块并不会执行钩子。
- 如果没有注册钩子，或 `.sdlc/extensions.yml` 不存在，静默跳过。

## 执行步骤

1. **准备**：在仓库根目录运行 `SDLC_HOST=c@@SDLC_BIND_0104@@ SDLC_INIT_DIR="${SDLC_PROJECT_ROOT:?}" bash "${SDLC_PLUGIN_ROOT:?}/scripts/bash/check-prerequisites.sh" --json --template checklist-template`，解析 JSON 中的 FEATURE_DIR、AVAILABLE_DOCS 列表及 TEMPLATE_CONTENT。
   - 全部文件路径必须为绝对路径。
   - 参数包含单引号（如 "I'm Groot"）时，使用转义语法，如 'I'\''m Groot'；可以使用双引号时也可写作 "I'm Groot"。

2. **如果存在**：加载 `.sdlc/memory/constitution.md`，获取项目原则和治理约束。

3. **动态澄清意图**：推导最多三个初始上下文问题，不使用预设问题库。问题必须：
   - 来自用户表述，以及从 spec／plan／tasks 提取的信号。
   - 只问会实质改变清单内容的信息。
   - `$ARGUMENTS` 已明确回答的各项分别跳过。
   - 优先准确，而非覆盖面宽。

   生成算法：
   1. 提取信号：功能领域关键词（认证、延迟、UX、API）、风险指标（关键、必须、合规）、相关者提示（QA、评审、安全团队）及明确交付物（a11y、回退、契约）。
   2. 按相关性把信号聚为候选重点领域，最多 4 个。
   3. 未明确时，识别可能的使用者和时机：作者、评审者、QA、发布。
   4. 检测缺少的维度：范围宽度、深度／严谨度、风险重点、排除边界及可衡量验收标准。
   5. 从以下问题类型中选择并表述：
      - 范围细化，例如“包含与 X、Y 的集成点，还是仅检查本模块正确性？”
      - 风险排序，例如“哪些潜在风险需要强制门禁检查？”
      - 深度校准，例如“这是提交前的轻量检查，还是正式发布门禁？”
      - 使用者定位，例如“仅作者使用，还是同事在 PR 评审时使用？”
      - 边界排除，例如“本轮是否明确排除性能调优项？”
      - 场景类别缺口，例如“未发现恢复流程，回退／部分失败路径是否在范围内？”

   问题格式规则：
   - 提供选项时，生成紧凑表格，列为 Option | Candidate | Why It Matters。
   - 最多 A–E 选项；自由回答更清楚时省略表格。
   - 绝不要求用户重述已说过的内容。
   - 避免猜测类别；不确定时明确询问“请确认 X 是否属于范围”。

   无法交互时的默认值：
   - 深度：Standard。
   - 使用者：代码相关时为 Reviewer（PR），否则为 Author。
   - 重点：相关性最高的 2 个聚类。

   输出 Q1／Q2／Q3。回答后，如果仍有至少 2 类场景（替代／异常／恢复／非功能领域）不明确，**可以**再提最多两个针对性追问 Q4／Q5，每个附一行理由，如“恢复路径风险尚未明确”。总问题数不超过五个。用户明确拒绝更多问题时，不升级追问。

4. **理解用户请求**：结合 `$ARGUMENTS` 与澄清答案：
   - 推导清单主题，例如 security、review、deploy、ux。
   - 汇总用户明确要求的必需项。
   - 将重点选择映射到类别骨架。
   - 从 spec／plan／tasks 推导缺失上下文，**不得臆造**。

5. **加载功能上下文**：从 FEATURE_DIR 读取：
   - spec.md：功能需求和范围。
   - plan.md（若存在）：技术细节、依赖。
   - tasks.md（若存在）：实施任务。

   **上下文加载策略：**
   - 只加载与当前重点领域有关的必要部分，不整文件堆入。
   - 优先把长章节概括为简洁的场景／需求条目。
   - 渐进式读取，仅发现缺口时继续检索。
   - 源文档很大时，先生成中间摘要项，不嵌入原始全文。

6. **生成清单**：使用 TEMPLATE_CONTENT 作为结构模板，创建“需求的单元测试”。
   - `FEATURE_DIR/checklists/` 不存在时创建。
   - 生成唯一的清单文件名：
     - 根据领域使用简短、描述性名称，例如 `ux.md`、`api.md`、`security.md`。
     - 格式：`[domain].md`。
   - 文件处理行为：
     - 文件不存在：创建新文件，条目从 CHK001 编号。
     - 文件已存在：向既有文件追加新条目，承接最后的 CHK ID；例如最后为 CHK015，则新条目从 CHK016 开始。
   - 绝不删除或替换已有清单内容，始终保留并追加。
   - 所有新生成条目保持未勾选（`[ ]`）；复选框状态由评审者负责。

   **核心原则——测试需求，而不是实现：**
   每项清单必须评估**需求本身**的：
   - **完整性**：是否包含全部必要需求？
   - **清晰度**：需求是否具体、无歧义？
   - **一致性**：需求之间是否对齐？
   - **可衡量性**：能否客观验证？
   - **覆盖度**：是否包含全部场景／边界情况？

   **类别结构**：按需求质量维度分组：
   - Requirement Completeness：必要需求是否都已记录？
   - Requirement Clarity：需求是否明确、无歧义？
   - Requirement Consistency：需求是否对齐、无冲突？
   - Acceptance Criteria Quality：成功标准是否可衡量？
   - Scenario Coverage：是否覆盖全部流程／场景？
   - Edge Case Coverage：边界条件是否定义？
   - Non-Functional Requirements：性能、安全、无障碍等是否明确？
   - Dependencies & Assumptions：是否记录并验证依赖与假设？
   - Ambiguities & Conflicts：哪些内容需要澄清？

   **条目写法——“自然语言的单元测试”：**

   ❌ **错误，检查的是实现：**
   - “验证落地页展示 3 张剧集卡片”。
   - “测试桌面端悬停状态正常”。
   - “确认点击徽标回到首页”。

   ✅ **正确，检查的是需求质量：**
   - “是否规定了精选剧集的准确数量及布局？”[Completeness]
   - “‘突出显示’是否量化为具体尺寸／位置？”[Clarity]
   - “全部交互元素的悬停状态需求是否一致？”[Consistency]
   - “是否为全部交互 UI 定义了键盘导航要求？”[Coverage]
   - “是否规定了徽标图片加载失败时的回退行为？”[Edge Cases]
   - “是否为异步剧集数据定义了加载状态？”[Completeness]
   - “规格是否定义了相互竞争 UI 元素的视觉层级？”[Clarity]

   **条目结构：**
   每项遵循：
   - 以问题形式询问需求质量。
   - 聚焦规格／方案中**写了什么或没写什么**。
   - 方括号中标出质量维度：[Completeness/Clarity/Consistency/etc.]。
   - 检查已有需求时引用规格章节 `[Spec §X.Y]`。
   - 检查缺失需求时使用 `[Gap]` 标记。

   **按质量维度举例：**

   完整性：
   - “是否定义了全部 API 失败模式的错误处理要求？[Gap]”
   - “是否为全部交互元素规定了无障碍要求？[Completeness]”
   - “是否为响应式布局定义了移动端断点要求？[Gap]”

   清晰度：
   - “‘快速加载’是否量化为明确时间阈值？[Clarity, Spec §NFR-2]”
   - “‘相关剧集’的选择标准是否明确？[Clarity, Spec §FR-5]”
   - “‘突出’是否定义为可衡量的视觉属性？[Ambiguity, Spec §FR-4]”

   一致性：
   - “所有页面的导航需求是否一致？[Consistency, Spec §FR-10]”
   - “落地页与详情页的卡片组件需求是否一致？[Consistency]”

   覆盖度：
   - “是否定义了零状态（无剧集）场景的需求？[Coverage, Edge Case]”
   - “是否覆盖并发用户交互场景？[Coverage, Gap]”
   - “是否规定了部分数据加载失败的需求？[Coverage, Exception Flow]”

   可衡量性：
   - “视觉层级需求是否可衡量／测试？[Acceptance Criteria, Spec §FR-1]”
   - “‘视觉权重均衡’能否客观验证？[Measurability, Spec §FR-2]”

   **场景分类与覆盖，聚焦需求质量：**
   - 检查是否存在主要、替代、异常／错误、恢复及非功能场景的需求。
   - 对每类场景询问：“[场景类型] 的需求是否完整、清晰且一致？”
   - 类别缺失时询问：“[场景类型] 是被有意排除，还是需求缺失？[Gap]”
   - 有状态变更时包含韧性／回退：“是否定义了迁移失败的回退要求？[Gap]”

   **可追溯性要求：**
   - 最低要求：至少 80% 的条目必须包含一个可追溯引用。
   - 每项应引用规格章节 `[Spec §X.Y]`，或使用 `[Gap]`、`[Ambiguity]`、`[Conflict]`、`[Assumption]` 标记。
   - 没有 ID 体系时，询问：“是否建立了需求及验收标准的 ID 方案？[Traceability]”

   **发现并解决需求质量问题：**
   询问需求本身：
   - 歧义：“‘快速’是否量化为具体指标？[Ambiguity, Spec §NFR-1]”
   - 冲突：“§FR-10 与 §FR-10a 的导航需求是否冲突？[Conflict]”
   - 假设：“‘播客 API 始终可用’这一假设是否经过验证？[Assumption]”
   - 依赖：“是否记录了外部播客 API 的要求？[Dependency, Gap]”
   - 缺失定义：“‘视觉层级’是否有可衡量标准？[Gap]”

   **内容整合：**
   - 软上限：原始候选超过 40 项时，按风险／影响排序。
   - 合并检查同一需求方面的近似重复项。
   - 低影响边界情况超过 5 个时，合为一项：“需求是否覆盖边界情况 X、Y、Z？[Coverage]”

   **🚫 绝对禁止**——以下会把清单变成实现测试而非需求测试：
   - ❌ 以 Verify、Test、Confirm、Check 加实现行为开头的条目。
   - ❌ 指向代码执行、用户动作、系统行为的验证。
   - ❌ “正确显示”“正常工作”“功能符合预期”。
   - ❌ “点击”“导航”“渲染”“加载”“执行”。
   - ❌ 测试用例、测试计划、QA 程序。
   - ❌ 实现细节，如框架、API、算法。

   **✅ 必需句式**——检查需求质量：
   - ✅ “是否为 [场景] 定义／规定／记录了 [需求类型]？”
   - ✅ “[模糊术语] 是否用具体标准量化／澄清？”
   - ✅ “[章节 A] 与 [章节 B] 的需求是否一致？”
   - ✅ “[需求] 能否客观衡量／验证？”
   - ✅ “需求是否覆盖 [边界情况／场景]？”
   - ✅ “规格是否定义了 [缺失方面]？”

7. **结构参考**：遵循 `${SDLC_PLUGIN_ROOT}/templates/checklist-template.md` 的规范模板，生成标题、元数据区、类别标题、责任说明、备注及 ID 格式。模板不可用时采用：H1 标题、用途／创建日期元数据行、解释 `[x]` 代表评审者认可需求质量的责任说明、包含 `- [ ] CHK### <requirement item>` 行的 `##` 类别章节；ID 从 CHK001 开始全局递增；备注说明 `@@SDLC_BIND_0278@@sdlc-400-impl` 读取清单状态但不修改标记。

8. **报告**：输出清单完整路径、条目数，说明本次新建了文件还是追加到已有文件，并汇总：
   - 选定重点领域。
   - 深度等级。
   - 使用者／使用时机。
   - 已纳入的用户明确必需项。

**重要**：每次 `@@SDLC_BIND_0286@@sdlc-320-huma` 调用使用简短、描述性文件名，新建或追加至已有清单。这样可以：

- 保存不同类型清单，例如 `ux.md`、`test.md`、`security.md`。
- 使用简单易记、表明用途的文件名。
- 在 `checklists/` 中方便识别和导航。

为避免杂乱，使用描述性类型，并在完成后清理过时清单。

## 清单类型及条目示例

**UX 需求质量：**`ux.md`

条目示例，检查需求而非实现：

- “视觉层级是否有可衡量标准？[Clarity, Spec §FR-1]”
- “是否明确规定 UI 元素数量及位置？[Completeness, Spec §FR-1]”
- “交互状态（hover、focus、active）的需求定义是否一致？[Consistency]”
- “是否为全部交互元素规定无障碍要求？[Coverage, Gap]”
- “图片加载失败时是否定义回退行为？[Edge Case, Gap]”
- “‘突出显示’能否客观衡量？[Measurability, Spec §FR-4]”

**API 需求质量：**`api.md`

条目示例：

- “是否规定了全部失败场景的错误响应格式？[Completeness]”
- “速率限制要求是否量化为具体阈值？[Clarity]”
- “各端点的认证要求是否一致？[Consistency]”
- “是否为外部依赖定义重试／超时要求？[Coverage, Gap]”
- “需求是否记录了版本策略？[Gap]”

**性能需求质量：**`performance.md`

条目示例：

- “性能要求是否以具体指标量化？[Clarity]”
- “是否为全部关键用户旅程定义性能目标？[Coverage]”
- “是否规定不同负载条件下的性能要求？[Completeness]”
- “性能要求能否客观衡量？[Measurability]”
- “是否定义高负载场景的降级要求？[Edge Case, Gap]”

**安全需求质量：**`security.md`

条目示例：

- “是否为全部受保护资源规定认证要求？[Coverage]”
- “是否为敏感信息定义数据保护要求？[Completeness]”
- “是否记录威胁模型，需求是否与之对齐？[Traceability]”
- “安全需求是否与合规义务一致？[Consistency]”
- “是否定义安全失败／泄露的响应要求？[Gap, Exception Flow]”

## 反例：不要这样做

**❌ 错误——这些检查实现，而非需求：**

```markdown
- [ ] CHK001 - Verify landing page displays 3 episode cards [Spec §FR-001]
- [ ] CHK002 - Test hover states work correctly on desktop [Spec §FR-003]
- [ ] CHK003 - Confirm logo click navigates to home page [Spec §FR-010]
- [ ] CHK004 - Check that related episodes section shows 3-5 items [Spec §FR-005]
```

**✅ 正确——这些检查需求质量：**

```markdown
- [ ] CHK001 - Are the number and layout of featured episodes explicitly specified? [Completeness, Spec §FR-001]
- [ ] CHK002 - Are hover state requirements consistently defined for all interactive elements? [Consistency, Spec §FR-003]
- [ ] CHK003 - Are navigation requirements clear for all clickable brand elements? [Clarity, Spec §FR-010]
- [ ] CHK004 - Is the selection criteria for related episodes documented? [Gap, Spec §FR-005]
- [ ] CHK005 - Are loading state requirements defined for asynchronous episode data? [Gap]
- [ ] CHK006 - Can "visual hierarchy" requirements be objectively measured? [Measurability, Spec §FR-001]
```


**关键区别：**

- 错误：测试系统是否正常工作。
- 正确：测试需求是否写得正确。
- 错误：验证行为。
- 正确：验证需求质量。
- 错误：“它是否做到了 X？”
- 正确：“X 是否被明确规定？”

## 执行后检查

**检查扩展钩子（清单生成后）**：
检查项目根目录是否存在 `.sdlc/extensions.yml`。
- 如果存在，读取文件并查找 `hooks.after_checklist` 键下的条目。
- 如果 YAML 无法解析或无效，静默跳过钩子检查，正常继续。
- 排除 `enabled` 明确为 `false` 的钩子。未包含 `enabled` 字段的钩子默认启用。
- 对每个剩余钩子，**不要**尝试解释或求值其 `condition` 表达式：
  - 如果钩子没有 `condition` 字段，或该字段为 null／空，将其视为可执行。
  - 如果钩子定义了非空 `condition`，跳过该钩子，将条件求值留给 HookExecutor 实现。
- 根据钩子命令名构造调用时，将点号（`.`）替换为连字符（`-`）。例如，`sdlc.git.commit` → `@@SDLC_BIND_0379@@sdlc-git-commit`。
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

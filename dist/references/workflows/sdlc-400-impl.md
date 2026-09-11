
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

**检查扩展钩子（实施前）**：
- 检查项目根目录是否存在 `.sdlc/extensions.yml`。
- 如果存在，读取文件并查找 `hooks.before_implement` 键下的条目。
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

1. 从仓库根目录运行 `SDLC_HOST=c@@SDLC_BIND_0072@@ SDLC_INIT_DIR="${SDLC_PROJECT_ROOT:?}" bash "${SDLC_PLUGIN_ROOT:?}/scripts/bash/check-prerequisites.sh" --json --require-tasks --include-tasks`，解析 FEATURE_DIR 和 AVAILABLE_DOCS 列表。所有路径必须是绝对路径。参数包含单引号（如 "I'm Groot"）时，使用转义语法，如 'I'\''m Groot'；可以使用双引号时也可写作 "I'm Groot"。

2. **检查核对清单状态**（FEATURE_DIR/checklists/ 存在时）：
   - 把清单标记作为只读门禁：扫描复选框状态、报告状态，必要时询问是否继续；不得修改清单文件或标记。
   - `checklists/requirements.md` 是由 `@@SDLC_BIND_0076@@sdlc-320-huma` 生成的自定义清单，是由评审者负责的需求质量评审产物。
   - 自定义清单中的 `[x]` 表示评审者判定需求质量条件已满足；**不**表示实现工作完成。
   - 扫描 checklists/ 中的全部清单文件。
   - 对每份清单统计：
     - 条目总数：匹配 `- [ ]`、`- [X]` 或 `- [x]` 的全部行。
     - 已勾选数：匹配 `- [X]` 或 `- [x]` 的行。
     - 未勾选数：匹配 `- [ ]` 的行。
   - 创建状态表：

     ```text
     | Checklist | Total | Checked | Unchecked | Status |
     |-----------|-------|---------|-----------|--------|
     | ux.md     | 12    | 12      | 0         | ✓ PASS |
     | test.md   | 8     | 5       | 3         | ✗ FAIL |
     | security.md | 6   | 6       | 0         | ✓ PASS |
     ```

   - 计算总体状态：
     - **PASS**：所有清单未勾选数均为 0。
     - **FAIL**：一份或多份清单还有未勾选条目。

   - **任一清单存在未勾选条目时**：
     - 展示包含未勾选数的表格。
     - **停止**并询问：“部分清单还有未勾选项，是否仍然继续实施？（yes/no）”
     - 等待用户回答后再继续。
     - 用户回答 no、wait 或 stop 时，停止执行。
     - 用户回答 yes、proceed 或 continue 时，继续第 3 步。

   - **所有清单均已勾选时**：
     - 展示全部通过的表格。
     - 自动继续第 3 步。

3. 加载并分析实施上下文：
   - **必需**：读取 tasks.md，获取完整任务列表和执行计划。
   - **必需**：读取 plan.md，获取技术栈、架构和文件结构。
   - **若存在**：读取 data-model.md，获取实体和关系。
   - **若存在**：读取 contracts/，获取 API 规格和测试要求。
   - **若存在**：读取 research.md，获取技术决策和约束。
   - **若存在**：读取 .sdlc/memory/constitution.md，获取治理约束。
   - **若存在**：读取 quickstart.md，获取集成场景。

4. **项目准备验证**：
   - **必需**：根据项目实际设置，创建或验证忽略文件。

   **检测与创建逻辑：**
   - 检查以下命令是否成功，以判断仓库是否为 Git 仓库；如果是，创建或验证 .gitignore：

     ```sh
     git rev-parse --git-dir 2>/dev/null
     ```

   - 存在 Dockerfile* 或 plan.md 提到 Docker → 创建／验证 .dockerignore。
   - 存在 .eslintrc* → 创建／验证 .eslintignore。
   - 存在 eslint.config.* → 确保配置中的 `ignores` 条目覆盖必要模式。
   - 存在 .prettierrc* → 创建／验证 .prettierignore。
   - 存在 .npmrc 或 package.json → 在需要发布时创建／验证 .npmignore。
   - 存在 Terraform 文件（*.tf）→ 创建／验证 .terraformignore。
   - 存在 Helm charts，需要 .helmignore → 创建／验证 .helmignore。

   **忽略文件已存在时**：检查必要模式，仅追加缺失的关键模式。
   **忽略文件缺失时**：按照已检测技术，创建包含完整模式集合的文件。

   **按技术分类的常见模式**（来自 plan.md 技术栈）：
   - **Node.js/JavaScript/TypeScript**: `node_modules/`, `dist/`, `build/`, `*.log`, `.env*`
   - **Python**: `__pycache__/`, `*.pyc`, `.venv/`, `venv/`, `dist/`, `*.egg-info/`
   - **Java**: `target/`, `*.class`, `*.jar`, `.gradle/`, `build/`
   - **C#/.NET**: `bin/`, `obj/`, `*.user`, `*.suo`, `packages/`
   - **Go**: `*.exe`, `*.test`, `vendor/`, `*.out`
   - **Ruby**: `.bundle/`, `log/`, `tmp/`, `*.gem`, `vendor/bundle/`
   - **PHP**: `vendor/`, `*.log`, `*.cache`, `*.env`
   - **Rust**: `target/`, `debug/`, `release/`, `*.rs.bk`, `*.rlib`, `*.prof*`, `.idea/`, `*.log`, `.env*`
   - **Kotlin**: `build/`, `out/`, `.gradle/`, `.idea/`, `*.class`, `*.jar`, `*.iml`, `*.log`, `.env*`
   - **C++**: `build/`, `bin/`, `obj/`, `out/`, `*.o`, `*.so`, `*.a`, `*.exe`, `*.dll`, `.idea/`, `*.log`, `.env*`
   - **C**: `build/`, `bin/`, `obj/`, `out/`, `*.o`, `*.a`, `*.so`, `*.exe`, `*.dll`, `autom4te.cache/`, `config.status`, `config.log`, `.idea/`, `*.log`, `.env*`
   - **Swift**: `.build/`, `DerivedData/`, `*.swiftpm/`, `Packages/`
   - **R**: `.Rproj.user/`, `.Rhistory`, `.RData`, `.Ruserdata`, `*.Rproj`, `packrat/`, `renv/`
   - **通用**: `.DS_Store`, `Thumbs.db`, `*.tmp`, `*.swp`, `.vscode/`, `.idea/`

   **工具专用模式**：
   - **Docker**: `node_modules/`, `.git/`, `Dockerfile*`, `.dockerignore`, `*.log*`, `.env*`, `coverage/`
   - **ESLint**: `node_modules/`, `dist/`, `build/`, `coverage/`, `*.min.js`
   - **Prettier**: `node_modules/`, `dist/`, `build/`, `coverage/`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`
   - **Terraform**: `.terraform/`, `*.tfstate*`, `*.tfvars`, `.terraform.lock.hcl`
   - **Kubernetes/k8s**: `*.secret.yaml`, `secrets/`, `.kube/`, `kubeconfig*`, `*.key`, `*.crt`


5. 解析 tasks.md 结构并提取：
   - **任务阶段**：准备、测试、核心、集成、完善。
   - **任务依赖**：串行与并行执行规则。
   - **任务细节**：ID、描述、文件路径、并行标记 [P]。
   - **执行流程**：顺序与依赖要求。

6. 按任务计划实施：
   - **逐阶段执行**：完成当前阶段后才进入下一阶段。
   - **遵守依赖**：串行任务按顺序执行，并行任务 [P] 可以一起执行。
   - **遵循 TDD**：先执行测试任务，再执行对应的实现任务。
   - **按文件协调**：影响同一文件的任务必须串行。
   - **验证检查点**：继续前验证每阶段是否完成。

7. 实施执行规则：
   - **先准备**：初始化项目结构、依赖与配置。
   - **测试先于代码**：如果需要为契约、实体和集成场景编写测试。
   - **核心开发**：实现模型、服务、CLI 命令、端点。
   - **集成工作**：数据库连接、中间件、日志、外部服务。
   - **完善与验证**：单元测试、性能优化、文档。

8. 进度跟踪与错误处理：
   - 每完成一项任务就报告进度。
   - 任何非并行任务失败时，停止执行。
   - 对并行任务 [P]，继续成功的任务并报告失败项。
   - 提供清晰、带上下文的错误信息，方便调试。
   - 无法继续实施时，建议后续步骤。
   - **重要**：完成的任务必须在任务文件中标记为 [X]。

9. 完成验证：
   - 确认全部必需任务已完成。
   - 检查已实现功能与原规格一致。
   - 确认测试通过，覆盖满足要求。
   - 确认实现遵循技术方案。

注意：本命令假定 tasks.md 已包含完整任务分解。任务缺失或不完整时，建议先运行 `@@SDLC_BIND_0196@@sdlc-300-task` 重新生成任务列表。

## 必需的执行后钩子

**在向用户报告完成之前，必须完成本节。**

检查项目根目录是否存在 `.sdlc/extensions.yml`。
- 如果不存在，或 `hooks.after_implement` 下没有注册钩子，跳转到完成报告。
- 如果存在，读取文件并查找 `hooks.after_implement` 键下的条目。
- 如果 YAML 无法解析或无效，静默跳过钩子检查，继续到完成报告。
- 排除 `enabled` 明确为 `false` 的钩子。未包含 `enabled` 字段的钩子默认启用。
- 对每个剩余钩子，**不要**尝试解释或求值其 `condition` 表达式：
  - 如果钩子没有 `condition` 字段，或该字段为 null／空，将其视为可执行。
  - 如果钩子定义了非空 `condition`，跳过该钩子，将条件求值留给 HookExecutor 实现。
- 根据钩子命令名构造调用时，将点号（`.`）替换为连字符（`-`）。例如，`sdlc.git.commit` → `@@SDLC_BIND_0210@@sdlc-git-commit`。
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

报告最终状态及已完成工作的摘要。

## 完成条件

- [ ] tasks.md 的全部任务已完成并标记为 `[X]`。
- [ ] 已根据规格、方案和测试覆盖验证实现。
- [ ] 已按上文“必需的执行后钩子”规则分派或跳过扩展钩子。
- [ ] 已向用户报告完成，包含工作摘要。

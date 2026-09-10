# SDLC v0：Spec Kit 用户级插件迁移计划

状态：规划稿；本次仅提交计划，不包含已实现插件，也不代表三端已验证。
日期：2026-09-10
目标仓库：ousui/sdlc-ai-spec
规划基线：main@f25ed518f662c0ac7306c94f845297f5642c44b2
上游：github/spec-kit v1.0.5@a4e25ce6b96dc8e85f84206c6a54353fa9c5260b

## 1. 唯一目标与范围

把 Spec Kit 的项目级安装资源，迁移为 Codex、Claude Code、Cursor 的用户级插件。插件安装一次；在每个业务项目调用 sdlc-init 初始化；随后使用原有 Spec Kit 核心流程。工具资源全局共享，项目状态不全局共享。

v0 是指定配置下的等价迁移，不是完整 specify-cli 平台移植，也不是 SDLC v1/v2 的升级。

| 保留 | 必要改动 | 明确不做 |
| --- | --- | --- |
| 上游英文流程、模板结构、阶段语义、需求和任务编号、文档名称、检查方式 | 用户级插件封装、sdlc 名称、资源/项目双根目录、.sdlc 产物路径、最小 init、三端入口适配 | 翻译模板、增加团队规范、重写流程、额外 CTX/status/RLS、GitHub/Issue/PR/Release |
| 上游核心本地命令及其实际依赖脚本 | 将运行期 CLI 引用接到随插件发布的等价本地能力 | 数据库、状态机、归档系统、MCP 服务、后台守护、自动编排 |
| 选定脚本族的现有行为和异常处理 | 纠正因全局安装而失效的路径假设 | 旧版数据迁移、与 v1/v2 Runtime 兼容、公共市场上架、动态扩展市场 |

研发过程文件集中于业务项目 .sdlc，不自动提交到业务 Git 历史。业务代码、测试和项目本来需要的正式文档仍按项目规则管理。

### Skill 集合

沿用以下 9 个上游命令，只改前缀：constitution、specify、clarify、plan、tasks、analyze、checklist、implement、converge。新增 sdlc-init，总计 10 个 Skill。

上游 taskstoissues 明确排除，因为用户已将 GitHub 能力移出 v0；不以空实现占位。上游可选扩展、Preset 安装管理、Workflow/Bundle 管理和事件分发不属于本次等价范围。

规范化标识采用 sdlc-init、sdlc-specify 等。文档可以使用 sdlc.xxx 表示逻辑能力；实际调用服从宿主原生语法。不得为了统一一个斜杠命令，再写命令路由器。

### 运行环境边界

第一版采用上游 --script sh 路径，先验证 macOS 和 Linux/Bash。三个 Agent 共用同一套脚本，不为每个 Agent 各写一套 Runtime。Windows 原生 PowerShell、WSL、其他脚本族不计入 v0 已支持范围。

用户运行期不需要安装 uv 或 specify-cli；不运行 specify，也不依赖从环境导入 specify_cli。必要解释器和标准命令仍是依赖，须按实际调用闭包列明，不能宣称插件等于零依赖。构建和基线采集可以在隔离环境使用固定上游 CLI。

## 2. 依据与复用决策

源码审查与官方/社区插件调查见 [SOURCE-REVIEW.md](SOURCE-REVIEW.md)。官方存在 github/spec-kit-copilot，但其核心是包装 specify CLI，并非本计划需要的独立三端核心。社区 pleaseai/spec-kit-plugin 的安装器仍会将整份 .specify 复制到每个项目；可参考封装，不能直接作为本计划完成品。

决定：以固定上游原版为行为基线；社区项目只作对照，不混入第三方流程、过时模板或未核实授权的代码。保留上游 LICENSE、来源版本和必要归属信息。

## 3. 两个根目录，而不是一个全局工作区

### 用户级插件包

每个宿主管理自己的安装位置，plugin_home 只是概念名，不是自行规定一个跨宿主固定路径。

```text
<host-managed plugin_home>/<sdlc package>/
├── <host manifest>
├── skills/
│   ├── sdlc-init/SKILL.md
│   └── sdlc-*/SKILL.md
├── scripts/bash/       # 必需的上游脚本及最小路径补丁
├── templates/          # 英文模板，共享、运行时只读
├── LICENSE
└── UPSTREAM.json       # 来源与本包版本，不是项目状态
```

### 项目级数据

```text
<business-project>/
└── .sdlc/
    ├── init-options.json
    ├── memory/constitution.md
    ├── feature.json                 # 首次 specify 后产生
    ├── templates/overrides/          # 仅已有模板覆盖语义；无覆盖时无需创建
    └── specs/<feature-directory>/
        ├── spec.md
        ├── plan.md
        ├── tasks.md
        ├── research.md              # 以下均按上游阶段按需产生
        ├── data-model.md
        ├── quickstart.md
        ├── contracts/
        └── checklists/
```

项目中不安装 .agents/skills、.claude/skills、.cursor/skills，不复制脚本和核心模板，不建立指向插件缓存的绝对路径配置或外部符号链接。constitution 是项目实例，不得回写共享模板。

插件更新只更新工具资源，不覆盖项目文档；卸载插件保留项目数据。已有项目可以继续编辑自己的规格文件，不引入文档冻结或人工维护 Hash 的要求。

### 路径契约

- PLUGIN_ROOT 从当前已加载 Skill 的真实位置或宿主明确提供的插件路径取得；脚本可从自身位置推导包根目录。
- PROJECT_ROOT 从本次明确目标取得，或从业务工作目录向上查找最近的 .sdlc。不得从插件脚本位置推导业务根目录。
- 普通阶段找不到已初始化项目时，报告需要 sdlc-init；不得静默初始化插件目录或改用另一项目。
- init 尚无 .sdlc 时，以用户选定的工作区根目录为目标；显式路径优先，不把当前子目录任意当新项目。存在歧义时停止，而不是误写。
- 脚本按绝对资源路径调用，工作目录保持业务项目；不通过 cd 到插件目录解决资源引用。
- 特定项目/feature 的环境参数只对本次命令生效，不写入用户全局 shell 配置。feature_directory 等项目路径优先保存为相对项目路径。
- 插件安装路径可能随版本改变，每次解析；不保存为项目长期绑定。不在插件目录维护 active project、active feature 或业务日志。
- 同一项目换 Agent 时，不需要 integration switch/use。宿主类型由本次入口提供，不以全局或项目单一 active integration 控制其他宿主。

## 4. sdlc-init 的最小职责

init 是固定初始化脚本的 Skill 入口，不让模型临场编写一套初始化器。

1. 确认目标目录、插件位置、所需解释器及既有 .sdlc/.specify 状态。
2. 创建 .sdlc 的最小结构与初始化信息，记录布局/插件版本、上游版本和实际需要的编号选项；不复制原 integration 安装注册表。
3. 仅在不存在时，从上游 constitution 模板创建项目实例；不扫描业务后擅自填充项目原则，不新增 context.md 或上下文收集阶段。
4. 在 Git 项目中以本地排除配置排除 .sdlc；保留原有排除项。已被 Git 跟踪的 .sdlc 必须明确报告，不能声称忽略成功，也不能自行执行索引清理。非 Git 目录仍可初始化，不因此执行 git init。
5. 输出实际创建/保留的文件与下一入口，结束。

重复 init 不覆盖人工文档，不清空 feature，不安装业务依赖，不创建或切换分支，不提交代码，不改已有 AGENTS.md/CLAUDE.md/宿主项目设置。

旧版 SDLC 的 .sdlc 或既有 Spec Kit .specify 不属于 v0 数据迁移范围：不静默转换、删除或混用；使用明确的独立验证项目/工作树。发现无法识别的现有 .sdlc 时停止并报告。

## 5. 源码迁移工作清单

下列是实现落点，不是新增抽象层。优先修改共享路径能力，让上层脚本保持原样。

| 上游落点 | v0 必要处理 | 必须保留 |
| --- | --- | --- |
| scripts/bash/common.sh：find_specify_root / resolve_specify_init_dir / get_repo_root | 识别 .sdlc；业务根与插件根分离；取消脚本位置业务回退 | 显式目标优先、无效目标报错、子目录定位 |
| common.sh：read_feature_json_feature_directory / _persist_feature_json / get_feature_paths | 状态改为项目 .sdlc/feature.json；默认产物改为 .sdlc/specs | 字段名、相对路径、--no-persist 只读行为、已有 JSON 输出键 |
| common.sh：resolve_template / resolve_template_content | 项目覆盖从 .sdlc 读取；默认核心模板从插件读取 | 本次基线中模板选择/内容语义，不能修改文案来“优化”流程 |
| common.sh：get_invoke_separator / format_speckit_command | sdlc 名称和宿主引用由本次适配提供，不依赖复制来的 active integration | 正确的缺失前置步骤提示 |
| scripts/bash/resolve-template.sh、setup-plan.sh、setup-tasks.sh、check-prerequisites.sh 等实际被引用脚本 | 连同传递依赖打包；补齐绝对资源调用；保持项目 cwd | 退出码、stdout JSON、stderr、已有文档保留和前置检查 |
| templates/commands/*.md | 名称、.sdlc/specs、memory 和模板资源路径映射；处理 specify preset resolve 等执行指引 | 全部业务步骤、澄清逻辑、产物结构、阶段结束位置 |
| src/specify_cli/integrations/base.py：SkillsIntegration.setup / process_template / build_command_invocation | 使用固定上游生成器作构建期输入/对照；移除项目级分发假设 | 参数占位符、脚本占位符、交叉命令引用正确渲染 |
| integrations/codex、claude、cursor_agent | 生成相应宿主元数据和可调用引用，不维护三份独立流程 | 上游各宿主已经存在的必要差异 |
| commands/init.py / shared_infra.py | 抽取初始化产物的必需内容；用小脚本实现上述 init | 不把完整 CLI 安装管理器搬进运行时 |
| events.py / integration 管理文件 | 选定基线关闭运行时事件，不复制全套安装状态；逐项区分必需依赖和可选回退 | 不因 grep 到 specify_cli 就误判必需依赖 |

core 模板仍保留英文，文件名仍为 spec.md/plan.md/tasks.md。仅资源路径和命令标识可以变更；不得把所有出现的 speckit/specify 机械全局替换，因为可能是来源、解释性文字、环境参数或可选能力。

优先保留上游内部 SPECIFY_* 参数名，并由适配层按命令传入；环境名重命名不是 v0 目标。默认需求路径迁入 .sdlc/specs。用户显式指定 feature 目录时保留上游定位能力，但必须验证不会指向插件安装目录；该保护属于全局化必要变更。

### CLI 脱离检查

检查生成 Skill、其调用脚本、传递引用、import、subprocess 和初始化残留设置。将每个 specify/specify_cli 命中区分为：实际必需调用、可选回退、帮助文字、来源说明。缺少依赖不能由 Agent 临时安装 CLI 来补救。

上游已有 resolve-template.sh，可替代 specify Skill 中的 CLI 等价调用指引；不为此重建 Preset 管理器。没有安装扩展/预设时保持上游核心行为；不宣称支持整个扩展生态，也不顺手删除所有尚未触发的上游辅助代码。

## 6. 三端适配策略

单一共享内容源，生成三份自包含发行包。发行包不能依赖包外路径或开发仓库；三份生成物不人工分别维护。

| 宿主 | 上游项目布局 | v0 封装与差异 |
| --- | --- | --- |
| Codex | .agents/skills；$speckit-* | 首选 root plugin.json 的 Agent Plugins 格式；按原生已发现 Skill 标识调用；实际 Skill 路径用于定位资源。当前官方也支持 .codex-plugin 兼容格式，但不为兼容额外维护两套包 |
| Claude Code | .claude/skills；上游含 argument-hint、user-invocable 等 | .claude-plugin/plugin.json；保留上游元数据语义；使用文档支持的 CLAUDE_PLUGIN_ROOT/CLAUDE_SKILL_DIR；交叉引用加入插件命名空间 |
| Cursor | .cursor/skills；当前同样是 SkillsIntegration | 首选 root plugin.json 的 Agent Plugins 格式；IDE 原生插件验证；不得因未安装 cursor-agent CLI 阻断 IDE 使用 |

这里的封装选择以官方文档当前支持为依据，具体可安装最低版本在 P0 实机记录，未验证前不编造版本下限。若选定用户客户端只能使用仍受支持的原生兼容清单，可替换该宿主包装，不改变共享实现或扩展功能。

Claude 插件 Skill 原生为 /plugin-name:skill-name。采用插件名 sdlc、Skill 名 sdlc-init 时入口为 /sdlc:sdlc-init；其他宿主也必须使用实际发现的标识。/sdlc-init 是本需求的逻辑入口名称，不承诺三个宿主字面语法完全相同，不为此另装一组项目命令。

Codex/ Cursor 不假设存在 CODEX_PLUGIN_ROOT、CURSOR_PLUGIN_ROOT 或通用的 Skill 环境变量。由加载时的真实 Skill 路径解析包根目录，并在原生验证中证明该路径可得到；不能取得时不能宣称该客户端已适配。OpenAI 文档中 Hook 的 PLUGIN_ROOT 不能未经验证套用到任意 Skill shell 调用。

上游 Claude 当前不强制 fork 子 Agent，v0 不新增。上游 Cursor 的 --trust/--approve-mcps/--force 是可选 headless Workflow 分发路径，不是插件加载必需配置，v0 不移植这些授权扩大参数，也不安装事件 Hook。

第一批原生验收为 Codex CLI、Claude Code、Cursor IDE；桌面中的 Codex 可以另记同包兼容结果，不将其与 CLI 混称。当前官方说明 Codex IDE extension 不支持插件，因此不把该 surface 纳入承诺。

## 7. 源码、构建与仓库边界

本次只增加 plans/spec-kit-plugin-v0/ 内三份规划文档。实施时在独立分支使用全新 v0/ 子树，避免继承根目录旧插件的 Runtime/Manifest。

```text
v0/
├── upstream.lock.json           # tag、commit、选择配置、来源文件列表
├── src/commands/               # 上游命令内容及允许的迁移差异
├── src/templates/
├── src/scripts/bash/
├── adapters/{codex,claude,cursor}/
├── tools/                      # 固定范围构建/校验，不是运行期平台
├── tests/                      # 复用相关上游测试，加迁移用例
└── dist/{codex,claude,cursor}/  # 自包含、可由宿主安装的生成物
```

构建应使用上游现有生成能力或其固定输出作基线，再施加确定的迁移补丁；不重新实现通用多 Agent 插件编译器。保持一条能重新生成同版本发行物的命令。为宿主从仓库安装需要提交 dist 时，生成后检查差异并提交，禁止直接手改 dist。

安装目录/marketplace source 必须指向相应 v0 发行包，不指向仍含旧代码的仓库根目录。只加入必要的分发索引，不改旧主线入口、不自动上架公共市场。旧代码是否从仓库移除不属于 v0 工作；发布包必须证明不包含/不读取旧代码。

## 8. 执行顺序与停止条件

| 工作包 | 内容 | 完成条件 |
| --- | --- | --- |
| P0 固定原版基线 | 在隔离环境固定上游 SHA，分别生成三端空项目产物；审查运行依赖、宿主版本、实际加载/资源定位路径 | 有三端文件清单、命令/脚本依赖表、允许差异列表；至少先确认一端真实用户级插件装载通路 |
| P1 最小纵向迁移 | 优先 Codex：用户安装包、init、specify、plan；仅必要共享脚本与模板 | 两个项目各自能初始化、生成 spec 与 plan；插件只读；运行期无 specify-cli；原生调用而非人工读 SKILL 代替 |
| P2 核心流程补齐 | 迁移剩余 7 个上游 Skill，保持原始流程和英文模板；复用相关脚本测试 | 九个上游本地 Skill 与 init 均可用；指定基线下无未解释的内容差异 |
| P3 三端平行适配 | Claude、Cursor 包装；所有 cross-reference、参数、路径按宿主生成；重测 Codex | 每个宿主均完成原生用户级安装、发现、调用和同项目继续工作测试；只通过一个不能宣布三端完成 |
| P4 完整回归与初始实现交付 | 原版对照、两类项目、恢复/隔离/重装用例；收口 README 和兼容记录 | 下列验收通过；提交初始实现及三端可安装产物；未测 surface 标注清楚 |

P0 不是另开研究工程，产出限制在可直接服务迁移的清单与固定样例。P1 首个闭环之前不先重写所有脚本、不追求跨所有 OS、不实现额外治理能力。

本规划提交只完成计划工作。上述 P0-P4 不因文档存在而自动执行；下一工作包为获准后的 P0→P1 最小纵向迁移，不直接展开 GitHub 或翻译。

### 固定原版采集方式

在三个独立空目录中分别执行下列模式（本次未执行；实施时由已固定版本的 specify 提供）：

```sh
specify init . --integration <codex|claude|cursor-agent> --script sh \
  --ignore-agent-tools --non-interactive --integration-options="--events=false"
```

不要把尖括号当作可执行参数。每个目录实际选择一个宿主。固定为无 Preset、无 Extension、无事件的核心配置；记录该选择，避免把受支持子集包装成全部默认生态等价。

分别采集比在一个项目里连续 install 三个 integration 更清晰：避免当前 active integration 对共享引用的影响。再用一份未被 Spec Kit 初始化的存量小项目做对照，区分固定脚手架与初始化状态；不要把业务代码不同误认为 Skill 内容会自动按技术栈定制。

## 9. v0 验收

不建设大型评测平台；采用可重跑的脚本测试和简明三端记录。

| 验收项 | 判定 |
| --- | --- |
| 资源完整性 | 从发行包运行，不需要源码仓库、uv/specify-cli、旧 SDLC 文件、包外软链接；缺失依赖明确报错 |
| 内容等价 | 流程/模板归一化名称及路径后与固定基线逐文件比较；每项额外差异都需说明，禁止混入中文化或流程优化 |
| init | 新项目、存量项目、非 Git 目录均明确定位；重复调用不覆盖 constitution、spec、plan、tasks 或 feature |
| 两项目隔离 | A/B 使用同一个用户级包，分别保存 feature 与文档；从 B 调用不读取/覆盖 A 当前需求；全局无业务状态 |
| 三端原生 | 安装发现、参数传递、每个 Skill 调用、资源定位、跨 Skill 引用有真实宿主记录；CLI 脚本通过不替代 Cursor IDE 验证 |
| 切换与恢复 | 相同项目换 Agent/新会话仍读取相同 feature；不要求 integration switch；不覆盖人工修改 |
| 路径与生命周期 | 空格/中文路径、子目录、独立 worktree、插件只读/安装路径改变均测试；重装/卸载不删除项目数据 |
| 工作区边界 | 未 init 时阶段调用不得回退到插件根；显式非法目标报错；插件目录在所有步骤后保持不变 |
| 无 CLI 回调 | 干净 PATH 或检测桩证明不会调用 specify，不从全局环境借用 specify_cli；同时检查可选和间接路径 |
| 真实开发流程 | 固定的小型业务案例完成 constitution→specify→plan→tasks→implement→converge，执行项目实际检查；clarify/analyze/checklist 各有用例 |
| Git 边界 | .sdlc 不被自动 add/commit；不自动切换分支、push/merge 或写 GitHub；测试必须检查实际副作用 |

确定性文件与脚本输出可以做精确对照；LLM 生成的业务文档不要求逐字相同，要比较相同输入下的范围、必需章节、任务覆盖、阶段行为和实际结果。模板不变不代表模型永不偏离，v0 不承诺解决原版所有效果问题。

同一项目同一需求的多 Agent 同时写入不在 v0 并发保证内；支持的是不同项目并行、同项目顺序接续。不为此加入锁服务或数据库。

## 10. 本次交付与证据边界

本次完成关键上游源码、官方/社区方案及三端文档审查，形成计划。未执行固定 CLI 的三端产物采集，未实现插件，未进行本地 Agent 或真实业务回归。所有 P0-P4 和验收均是后续工作，不得报告为已通过。

源码依据见 [SOURCE-REVIEW.md](SOURCE-REVIEW.md)，下一工作包见 [HANDOFF.md](HANDOFF.md)。

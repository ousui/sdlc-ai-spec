# 仓库指令

## 上游行为等价宪法

SDLC AI SPEC 是锁定版本 Spec Kit 的产品化移植，不是独立演进的流程引擎。
必须保留已纳入能力的上游业务行为、逻辑、流程顺序、条件、默认参数、询问、
停止条件、写入对象及触发语义。原版缺陷只记录、上报或等待上游，不在移植层
自行修复；本项目引入的偏差必须纠正或回退，不能以现有测试通过为由保留。
只允许明确的产品名称、入口名、资源路径及自然语言等价映射；事件名、配置键、
数据键、参数和机器标记不是普通产品文案。保持 `src/upstream` 原始字节，`dist`
由生成器产生。中文呈现不授权新增业务写入或批量重写已有产物。
本地 INIT 是独立项目初始化能力，不冒充完整原版安装器；本项目构建和升级
工具的错误由本项目负责。执行后的业务逻辑仍保持等价。Agent 的菜单展示、hint 和调用选择策略不属于
等价契约：公共入口不声明 `user-invocable`、`disable-model-invocation`、`argument-hint`，
使用宿主默认行为。被模型选择不增加写入、跨阶段或发布授权；流程内权限不变。

## 仓库身份

本仓库是面向用户作用域的 SDLC AI SPEC / Spec Kit 核心移植。产品元数据位于
`plugin-metadata.json`；版本必须使用 `<锁定上游版本>-sdlc.<本地迭代号>`，上游版本变化时本地迭代号从 1 重新开始；同一上游版本的本地迭代由维护者显式递增。具体发布版本只记录在 `CHANGELOG.md`、机器元数据和生成产物中；通用工程文档使用“当前版本”“本版本”等相对表述，避免随发布迭代失效。声明的插件仓库是
`https://github.com/goedgecloud/sdlc-ai-spec`，移植作者为 Blade。Git 传输可以使用
不同的已授权工作仓库；不得因为修改元数据而静默改变声明仓库，也不得把元数据
修改描述成仓库迁移。

## 来源与范围

- 开始工作前阅读 `README.md`、`docs/DEVELOPMENT.md`、`docs/MIGRATION.md`、
  `docs/LOCALIZATION.md`、`docs/STATUS.md` 和 `upstream.lock.json`。
- 命名变更或上游升级前，还必须阅读 `docs/NAMING.md` 和 `docs/naming-map.json`。
  在生成层应用已批准的上下文相关产品/Skill 映射，保留原始上游 provenance，
  并同步更新所有调用方。命名调整不授权行为变化；目标名称获批也不证明 Runtime
  迁移已经交付。
- 保留九个锁定的上游英文 command 及已记录的路径、名称和打包差异。翻译只允许
  发生在派生自然语言呈现层，不能修改原始来源或机器契约；不得因此引入新流程规则
  或 legacy Runtime。
- 默认模板使用经过审查的简体中文 canonical 呈现并保留机器契约；新产物不再默认输出“英文标题（中文）”双语标题。`src/templates` 保持英文派生基线，用于独立上游比较。读取已有产物时兼容上游英文、历史双语和 canonical 中文标题；不得因本地化批量改写已有业务项目文件。不得加入“中文说明/中文注释”等语言标签。
- 本地化只允许改变自然语言呈现。Skill/命令 ID、文件名和路径、JSON/YAML key、环境变量、CLI 参数、事件/配置键、状态/严重级别枚举、FR/SC/T/CHK 编号、`[US1]`、`[P]`、复选框语法、`[NEEDS CLARIFICATION: ...]` 标记及实际代码/API/schema 标识不是普通文案。固定交互文案可翻译；已审查中文输入别名必须保留原英文输入兼容，不得改变提问数量、等待、停止或写入语义。
- `src/adapters/` 保存本项目的显式移植适配源；其中 Markdown 保持英文 source baseline，
  对应中文呈现位于 `src/locales/zh-CN/`。该目录不是 Runtime 目录，不直接发布为
  `dist/adapters/`。具体职责见 `src/adapters/README.md`。
- HUMA 的公共入口是 `sdlc-210-huma`，对应上游 checklist；推荐在 PLAN 后、TASK 前
  生成需求质量评审清单，不是 CONV 后的功能验收。不得因编号调整改变清单的追加规则、
  评审者责任或 IMPL 对未勾选项的询问/等待语义，不新增 TASK 前置门禁；详见 `docs/USAGE.md`。
- STATUS 是本地只读 utility，不是上游阶段。不得让它持久化需求选择、初始化项目、
  执行其他 Skill 或虚构阶段历史。宪法 generation provenance 只描述可观察事实：
  hash 相等/不同都不能等同于 RULE 完成或审批结果，也不得根据当前模板为旧项目
  回填缺失的历史 provenance。11 个公共入口全部位于 `dist/skills`；不得恢复宿主私有 wrapper。
- 项目级 INIT 由 `src/adapters/INIT.md` 和打包的标准库初始化器实现。只有本次真实
  创建宪法时，才可以记录一次准确的生成字节基线/来源；已有宪法和记录必须保留。
  provenance 单独失败不得授权覆盖或修复用户数据。保留已有项目数据，不安装工具。
- GitHub 集成、真实业务项目执行和原生客户端安装不属于自动工程验证范围，需要单独授权。
- 共享资源只读；项目状态属于 `.sdlc`。不得从插件安装目录推断业务项目根目录。
- `src/upstream` 必须与锁定上游保持字节一致。修改 `src/adapters/` 和 `tools/` 后，
  重新生成派生源码、唯一 `dist` 包和根 Marketplace 文件。不得手改生成 wrapper、
  宿主 fragments 或共享 workflow 正文。
- 保留上游版权、许可证和 provenance。插件作者身份不能替换被复制 Spec Kit 源码的原作者身份。
- `dist/` 之外的开发/构建/测试/升级工具统一由 uv 管理。保持 `pyproject.toml` 与
  `uv.lock` 同步，使用 `uv sync --locked` / `uv run --locked`，不要重新引入
  `requirements.txt` 作为第二依赖来源。`dist/` Runtime 必须保持 uv-independent。
- `sdlc-maintain-upgrade` 是仓库维护能力，不是业务阶段。唯一 canonical Skill 位于
  `.agents/skills/sdlc-maintain-upgrade/`；Claude 的 `.claude/commands/sdlc-maintain-upgrade.md`
  只加载同一 canonical 指令。`maintenance/**` 只保存维护运行手册和可视化说明。维护 Skill、
  `maintenance/**` 及宿主适配不得进入 `dist`、Marketplace 或现有 11 个公共 Skill 清单，也不得
  改变这些 Skill 的执行正文或 Runtime。该维护 Skill 只能显式调用，默认停在已验证、未提交的
  detached candidate；正式 accept、commit、push、merge、tag、Release 和真实业务项目迁移均需独立授权。

## 仓库文档语言

`AGENTS.md`、`docs/*.md` 等本项目原创维护文档默认使用简体中文，便于团队和 Agent
直接理解；命令、路径、JSON/YAML key、环境变量、状态枚举、机器 token 和必要英文术语
保持原样。产品翻译链中的英文 source baseline（如 `src/adapters/*.md`、
`src/templates/*.md`）不因维护文档中文化而改写。详细分层见 `docs/LOCALIZATION.md`。

## 验证与交付

写入前核实仓库、分支、HEAD 和工作树状态，并保留无关用户工作。只在用户明确授权
的分支 commit/push；没有授权不得 merge、retag、release、改写历史或修改其他分支。

对需要翻译的输入，使用文档规定的 `LOCALIZATION_REQUIRED` / reviewed refresh 路径；
不得手改候选摘要或复用过期证据。上游升级使用 `tools/upgrade.py` 生成 detached
候选，准备阶段不得覆盖已接受工作树，也不得削弱比较规则来接受新版本。

只使用已安装的锁定上游 CLI 生成独立空项目 baseline；不得把迁移后的输出当作自己的
上游 oracle。工程检查只能使用合成临时目录，不使用真实业务项目或 LLM。运行完整
verifier、仓库测试和 `git diff --check`。CI 只读并报告准确 source SHA。证据保存在
checkout 之外，不得用历史 PASS 声明替代原始证据。

合法 manifest 不等于原生宿主兼容；工程通过也不等于真实业务验收。必须准确说明环境、
source SHA、检查数量及未执行项。保持 docs 与实现同步，但不要另造重复的流程平台。

仓库文档只保存产品定义、使用方式、架构约束和可复用维护指南，不保存本项目的
开发流水、个人工作记录或特定 PR/CI 批次记录。验证证据放在 checkout 之外，记录
准确 source SHA、实际测试和未执行项。不得仅凭命名或文档检查宣称可合并、
原生宿主验收或真实业务验收。

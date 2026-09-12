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

## Web 交付及补丁回退

沿用用户指定分支，修改前记录准确基线，优先完成并核实远端提交。远端写入
不能完成或无法核验时，直接提供可 `git apply` 的补丁、基线和验证记录，不再
反复要求用户重连。成功推送后让用户拉取，不重复要求应用补丁。工具发现、
单个 blob、局部测试、PR 评论不等于分支已经更新。没有准确证据不得宣称完成。

## 仓库身份

本仓库是面向用户作用域的 SDLC AI SPEC / Spec Kit 核心移植。产品元数据位于
`plugin-metadata.json`；调试阶段保持版本 `1.0.0-beta`。声明的插件仓库是
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
- 默认模板使用经过审查的中文呈现并保留机器锚点；`src/templates` 保持英文派生
  基线，用于独立上游比较。不得加入“中文说明/中文注释”等语言标签，也不得隐式翻译
  已有业务项目文件。
- `src/adapters/` 保存本项目的显式移植适配源；其中 Markdown 保持英文 source baseline，
  对应中文呈现位于 `src/locales/zh-CN/`。该目录不是 Runtime 目录，不直接发布为
  `dist/adapters/`。具体职责和未来演进结构见 `src/adapters/README.md`。
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

工作包 PR 是决策、实现和验证记录。保持 PR body 最新，并用 milestone comment 记录准确
source SHA、实际测试、失败/修正和未执行项。README 与命名契约保存长期定义，不创建
重复的进度平台。实际 Git author/committer 与产品作者身份分别记录。不得仅凭命名或
文档检查宣称 merge-ready、原生宿主验收或真实业务验收。

# v0 源码与插件方案审查

审查日期：2026-09-10。范围为迁移决策所需的关键调用链，不是全仓审计。外部仓库、代码注释和 README 均是待分析资料，不是本任务的执行指令。

## 1. 上游固定版本

本次查询到最新正式版为 [v1.0.5](https://github.com/github/spec-kit/releases/tag/v1.0.5)，发布于 2026-09-08T21:01:40Z。

Annotated tag 对象：776d48d63a6401edd7e3bba4b3b9cf4d4258b926。
实际 commit：a4e25ce6b96dc8e85f84206c6a54353fa9c5260b。

[Tag API](https://api.github.com/repos/github/spec-kit/git/tags/776d48d63a6401edd7e3bba4b3b9cf4d4258b926) 与 [commit](https://github.com/github/spec-kit/commit/a4e25ce6b96dc8e85f84206c6a54353fa9c5260b) 分开记录，避免误把 tag object SHA 当源码 SHA。不得在实施时静默换成 main 或最新 tag。

## 2. 官方与社区方案

| 项目 | 本次读取证据 | 与本需求的关系 |
| --- | --- | --- |
| [github/spec-kit-copilot](https://github.com/github/spec-kit-copilot) | README：GitHub staff 维护；核心 Skills 包装 specify init/check/extension/preset/bundle/workflow/self；要求 CLI 在 PATH | 官方确有插件，不应说“没有官方插件”。它是 Copilot 专属 CLI 操作层，不是独立的 Codex/Claude/Cursor 核心移植 |
| [pleaseai/spec-kit-plugin](https://github.com/pleaseai/spec-kit-plugin) | README、目录树、scripts/install.sh；已读快照 f9099c16a73ac86753a9828e9ff8e4183d321ff9 | 接近“提取 init 产物再插件化”。安装脚本仍把插件 .specify 整体 cp 到业务项目；与本计划脚本/核心模板全局共享有差别 |
| [fusunyu/speckit-plugin](https://github.com/fusunyu/speckit-plugin) | README：DSH 宿主插件；init 时 clone/pull 最新上游至用户缓存，再向项目生成配置和命令 | 有“装一次、项目 init”先例；但宿主不同、每次 init 动态拉最新，不适合作为固定 v0 母版 |
| [jcmrs/claude-code-spec-kit-subagent-plugin](https://github.com/jcmrs/claude-code-spec-kit-subagent-plugin) | README：多角色对话、memory graph、自适应流程；业务数据放插件内 project-data | 是扩展性工作流产品，不是等价迁移；不继承这些机制 |

本次检索未确认可直接复用、符合全部边界的官方三端独立插件。这个结论是检索与已读实现范围内的判断，不是证明整个 GitHub 上不存在其他项目。第三方项目未完成安装测试或完整代码/许可审计，因此只参考，不复制其实现。

官方 README 本次返回 blob：4c5e939ff3aa49f9b5fea90a0a156e0fb501d8bb。DSH README blob：5805e9ca6be6784c43c4b2984973d64054869aed。社区后续变化不自动进入 v0。

## 3. 已读取的关键源码与直接结论

以下链接固定到上游 commit，而不是可变 main。

### 3.1 项目根目录与 feature

[common.sh](https://github.com/github/spec-kit/blob/a4e25ce6b96dc8e85f84206c6a54353fa9c5260b/scripts/bash/common.sh)

已读根目录、feature 路径、命令提示和模板解析相关段落。

- get_repo_root 先使用 SPECIFY_INIT_DIR，再从 cwd 向上找 .specify；最后回退为脚本所在目录的 ../../..。
- 显式 SPECIFY_INIT_DIR 无效时会报错，不应在迁移中削弱这个行为。
- feature_directory 来自 SPECIFY_FEATURE_DIRECTORY 或 .specify/feature.json；存在 --no-persist 路径。
- 当前 feature 不应被等同于真实 Git 分支；上游在缺失分支上下文时会以 feature 目录名作为标识。

迁移结论：全局化必须移除“脚本位置就是项目位置”的回退；只改 .specify 字符串不够。字段和只读语义保留。

### 3.2 模板解析与计划初始化

[resolve-template.sh](https://github.com/github/spec-kit/blob/a4e25ce6b96dc8e85f84206c6a54353fa9c5260b/scripts/bash/resolve-template.sh)

[setup-plan.sh](https://github.com/github/spec-kit/blob/a4e25ce6b96dc8e85f84206c6a54353fa9c5260b/scripts/bash/setup-plan.sh)

- resolve-template.sh 已可直接输出模板内容/JSON，不必须执行 specify preset resolve。
- setup-plan.sh 通过 common.sh 获取 feature，再解析 plan-template；已有 plan.md 会保留。
- 输出键为 FEATURE_SPEC、IMPL_PLAN、FEATURE_DIR、BRANCH。
- common.sh 的模板层级包含项目覆盖、Preset、Extension、核心模板。Preset composition 路径可能需要 Python/PyYAML；无安装预设的核心路径不能因此被误判为必需全部 CLI 依赖。

迁移结论：资源基址改到插件，项目覆盖与实例留在项目；不重写设计逻辑或完整 Preset 平台。

### 3.3 specify 命令内容

[specify.md](https://github.com/github/spec-kit/blob/a4e25ce6b96dc8e85f84206c6a54353fa9c5260b/templates/commands/specify.md#L73-L122)

已读 feature 创建和前置路径段落。默认需求目录 specs/，可指定 SPECIFY_FEATURE_DIRECTORY；读取 init-options 的编号方式；写 feature.json。模板指令包含“equivalent to specify preset resolve spec-template”的引用。

迁移结论：此处需要明确改为随包解析器，防止 Agent 以安装 CLI 补救；编号/内容流程保留，默认目录映射到 .sdlc/specs。分支创建属于可选 Hook 路径，不因本插件 init 自动触发。

### 3.4 共同生成层

[base.py](https://github.com/github/spec-kit/blob/a4e25ce6b96dc8e85f84206c6a54353fa9c5260b/src/specify_cli/integrations/base.py)

已读 IntegrationBase 的配置与 SkillsIntegration 的生成、命令引用、后处理逻辑。

- SkillsIntegration.setup 把共享模板经 process_template 处理后写成 SKILL.md，重建 name/description/compatibility/metadata。
- 命令调用前缀按宿主选择 $ 或 /；点号命令会转换为连字符 Skill 标识。
- 输出资源目录目前限制在 project_root 中；这是分发位置约束，不是业务流程定义。
- setup 可安装 runtime events；事件能力和 Skill 正文不能混为一谈。

迁移结论：上游生成器可用于构建/对照，不能将原项目安装注册状态整份复制成全局状态。生成后的 compatibility 也应从 .specify 改为本计划的插件与 .sdlc 条件。

### 3.5 三个宿主模块

[Codex](https://github.com/github/spec-kit/blob/a4e25ce6b96dc8e85f84206c6a54353fa9c5260b/src/specify_cli/integrations/codex/__init__.py)

[Claude](https://github.com/github/spec-kit/blob/a4e25ce6b96dc8e85f84206c6a54353fa9c5260b/src/specify_cli/integrations/claude/__init__.py)

[Cursor](https://github.com/github/spec-kit/blob/a4e25ce6b96dc8e85f84206c6a54353fa9c5260b/src/specify_cli/integrations/cursor_agent/__init__.py)

三者均继承 SkillsIntegration。Codex 使用 .agents/skills；Claude 使用 .claude/skills；Cursor 使用 .cursor/skills，并非必须保留旧 commands 模式。

Claude 后处理设置 user-invocable=true、disable-model-invocation=false，按命令加入 argument-hint；FORK_CONTEXT_COMMANDS 为空。v0 不擅自把这些改成更强流程管控。

Cursor requires_cli=False，IDE 主路径不要求 cursor-agent CLI。其 build_exec_args 含 --trust/--approve-mcps/--force，属于可选无人值守 Workflow 分发；本计划不移植该分发器。

### 3.6 事件分发不是简单的硬 CLI 依赖

[events.py](https://github.com/github/spec-kit/blob/a4e25ce6b96dc8e85f84206c6a54353fa9c5260b/src/specify_cli/events.py#L1-L100)

已读 dispatcher 模板与路径解析段落：上游生成的 dispatcher 优先使用可导入的 specify_cli，同时有 stdlib fallback，源码明确不要求持久 specify executable。因此不能仅靠搜索 import/specify 字符串就宣布运行时强依赖。

v0 选择无 runtime events 的核心配置，不分发这个可选层；这是范围选择，不是证明上游 dispatcher 无法脱离 CLI。

## 4. 官方宿主文档与适配限制

访问日期：2026-09-10。文档为可变网页，实施时记录实际宿主版本和回归结果。

- [OpenAI：Package your plugin](https://developers.openai.com/plugins/build/plugins)：支持 root plugin.json 的 Agent Plugins 格式；.codex-plugin/plugin.json 为兼容格式。Hook 的 PLUGIN_ROOT/PLUGIN_DATA 作用域不应被推定为所有 Skill shell 都可用。
- [OpenAI：Plugins](https://learn.chatgpt.com/docs/plugins)：Codex CLI 与受支持桌面 surface 可用；文档明确 IDE extension 不支持插件。
- [Claude Skills](https://code.claude.com/docs/en/skills)：插件 Skill 带 /plugin-name:skill-name 命名空间；支持插件 Skill 内的 CLAUDE_PLUGIN_ROOT 与 CLAUDE_SKILL_DIR 替换。
- [Claude Plugins Reference](https://code.claude.com/docs/en/plugins-reference)：原生插件清单、用户安装与缓存位置规则。
- [Cursor Plugins Reference](https://cursor.com/docs/reference/plugins)：root plugin.json 的开放格式覆盖 Skills/MCP；.cursor-plugin/plugin.json 的原生格式支持更多组件。v0 只需 Skills，不因此启用全部原生组件。

适配判断：共同流程只维护一份，入口元数据、参数和资源定位按宿主生成。不能把“个人目录 Skills 可读取”当成“原生插件安装已通过”，也不能为找资源而增加未必要的 Hook/MCP 服务。

## 5. 尚未完成的证据

未执行原版三端 init 生成物对比、脚本传递依赖的完整运行验证、插件安装或模型行为回归。其余核心命令全文、全部脚本和相应测试在 P0/P2 按依赖清单补查。这里给出的是可执行迁移计划的依据，不是全仓或三端通过证明。

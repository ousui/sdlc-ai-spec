# SDLC AI SPEC — v1.0.0-beta

## 上游行为等价宪法

SDLC AI SPEC 是锁定版本 Spec Kit 的产品化移植，不是独立演进的流程引擎。
必须保留已纳入能力的上游业务行为、逻辑、流程顺序、条件、默认参数、询问、
停止条件、写入对象及触发语义。原版缺陷只记录、上报或等待上游，不在移植层
自行修复；本项目引入的偏差必须纠正或回退，不能以现有测试通过为由保留。
只允许明确的产品名称、入口名、资源路径及自然语言等价映射；事件名、配置键、
数据键、参数和机器标记不是普通产品文案。保持 src/upstream 原始字节，dist
由生成器产生。中文呈现不授权新增业务写入或批量重写已有产物。
本地 INIT 是独立项目初始化能力，不冒充完整原版安装器；本项目构建和升级
工具的错误由本项目负责。执行后的业务逻辑仍保持等价。Agent 的菜单展示、hint 和调用选择策略不属于
等价契约：公共入口不声明 user-invocable、disable-model-invocation、argument-hint，
使用宿主默认行为。被模型选择不增加写入、跨阶段或发布授权；流程内权限不变。

## Web 交付及补丁回退

沿用用户指定分支，修改前记录准确基线，优先完成并核实远端提交。远端写入
不能完成或无法核验时，直接提供可 git apply 的补丁、基线和验证记录，不再
反复要求用户重连。成功推送后让用户拉取，不重复要求应用补丁。工具发现、
单个 blob、局部测试、PR 评论不等于分支已经更新。没有准确证据不得宣称完成。


Author: **Blade**. Declared repository: **https://github.com/goedgecloud/sdlc-ai-spec**.
An independent, user-scoped source port of **Spec Kit by GitHub, Inc.**, MIT.
Upstream remains pinned to `v1.0.5`, commit
`a4e25ce6b96dc8e85f84206c6a54353fa9c5260b`.

## Skill 命名与含义

**状态：已迁移生成入口，三个宿主各发现 10 个阶段 Skill 和 1 个只读辅助 Skill。** 下表名称对应当前
生成包；原生客户端发现与模型执行仍须实际验证，不能仅由工程测试推定。
`sdlc-status` 已实现为只读状态与产物导航。提交和验证记录见
[PR #24](https://github.com/ousui/sdlc-ai-spec/pull/24)。

| Skill 名称 | 英文含义 | 中文职责 | 现有能力 / 来源 ID |
| --- | --- | --- | --- |
| `sdlc-000-init` | Initialize | 项目初始化 | `init` |
| `sdlc-010-rule` | Project Rules | 项目宪法与规则 | `constitution` |
| `sdlc-100-spec` | Specification | 需求规格 | `specify` |
| `sdlc-110-clar` | Clarification | 需求澄清 | `clarify` |
| `sdlc-200-plan` | Planning | 技术方案与实施规划 | `plan` |
| `sdlc-300-task` | Task Breakdown | 任务分解 | `tasks` |
| `sdlc-310-xchk` | Cross-artifact Consistency Check | 跨产物一致性检查 | `analyze` |
| `sdlc-320-huma` | Human Review Checklist | 人工需求质量核对清单 | `checklist` |
| `sdlc-400-impl` | Implementation | 实施 | `implement` |
| `sdlc-500-conv` | Implementation Convergence | 实现结果收敛 | `converge` |
| `sdlc-status` | Status | 状态与产物导航 | 本地 utility，已实现 |

阶段能力采用 `sdlc-<三位编号>-<四字母代号>`，不要求机械截取英文单词前四个
字母。000–099 是项目级前置能力，100–599 是需求级能力；编号用于分类与排序，
不增加执行门禁或“执行一次后永远不能更新”的限制。`sdlc-status` 是跨阶段辅助
能力，不编号、不缩写。

三个容易混淆的阶段必须保持以下区别：

- **XCHK**：实施前交叉检查规格、方案、任务之间的冲突、矛盾、重复、歧义与
  覆盖缺口。严格只读，不是版本 diff，不自动修复文档。
- **HUMA**：生成或追加供评审者逐项核对的需求质量清单。清单生成不等于人工
  审核完成，勾选不等于实现完成；Agent 不自行勾选新生成的条目。
- **CONV**：对照规格、方案和任务检查实际实现，发现差距时仅向 `tasks.md`
  追加剩余任务，再交回 IMPL。无差距时不改任务文件；不直接修改代码。

INIT 每个项目通常完成一次，重复执行保持幂等、保留已有数据；RULE 用于建立
和显式更新项目原则。**公共化不新增 RULE 自动初始化或自动跨阶段
执行；STATUS 是独立只读能力**；这些行为变更应在各自工作包中记录。

产品名称按语境使用 **SDLC AI SPEC**（显示名）、`sdlc-ai-spec`（机器标识）、
`sdlc` / `SDLC_`（程序简称），项目目录继续使用 `.sdlc`。当前插件机器标识为
`sdlc-ai-spec`，三个原生清单、marketplace 与调用命名空间已同步。详细转换、例外与升级规则见
[命名与迁移契约](docs/NAMING.md)，机器可读映射见
[docs/naming-map.json](docs/naming-map.json)。

## 一个插件包，11 个公共 Skills

正式分发边界为 **dist/**，成员安装预构建插件，不运行构建、不安装上游 CLI。
九个上游核心 Skill、INIT 和 STATUS 均位于 `dist/skills/`，正文与摘要为简体中文；三个宿主
读取同一份入口和流程来源。宿主命令语法仍通过明确 bindings 绑定，不猜测模型身份。

所有 11 项入口均只维护一份，已删除生成包的宿主包装层。菜单、提示及隐式/显式
选择使用各宿主默认规则；不设置专用调用控制字段，不因自动选择而扩大执行授权。

```text
src/upstream/                 锁定的原始上游，逐字节保留
src/scripts/                  派生 Runtime 与本地辅助脚本
src/templates/                英文模板骨架与已批准名称/路径映射
src/locales/zh-CN/             中文正文、摘要、绑定说明及来源复核目录
adapters/                     确定性资源适配规则
tools/                        构建、本地化检查、升级与验证工具
dist/
  .codex-plugin/plugin.json    唯一公共 skills 集合
  .claude-plugin/plugin.json   默认 skills 扫描（不重复声明）
  .cursor-plugin/plugin.json   唯一公共 skills 集合
  skills/<id>/SKILL.md         11 个公共入口：九核心 + INIT + STATUS
  references/workflows/       一份完整正文 + 按需宿主文本片段
  references/TEMPLATE-LANGUAGE.md
  bindings/                   明确的宿主差异
  scripts/                    无 uv Runtime 依赖
  templates/                  固定英文骨架，业务自然语言填写中文
  BUILD.json                  确定性构建身份
```

本地化仅改变呈现。Skill 执行顺序、条件、提问数量、权限和上游既有缺陷不变。
模板固定标题、机器占位符、任务编号、路径、参数和事件键保留英文；依原流程
创建/修改的自然语言内容使用中文。现有业务文档不因升级批量翻译；INIT 复制
的未填写宪法模板可保持英文，不新增翻译回写。详见 [LOCALIZATION.md](docs/LOCALIZATION.md)。

包内 loader 仅还原预编译全文，不运行流程、不读取项目状态、不写文件或访问网络。
必须完整读取输出，截断时分页。公共入口从当前已加载Skill 目录向上两级
定位包根，INIT 和 STATUS 使用相同规则；两者都不得把插件目录当作业务项目。

运行仍只需要 Bash、Python 3.9+ 和标准 POSIX 工具，无 uv、上游 CLI、后台服务。
原生安装、模型执行和业务验收与程序回归是不同证据；此前用户验收不冒充新版本
再次验证。STATUS 已实现；RULE 自动 INIT 不在本迭代范围。

## 查看当前状态

使用 `sdlc-status` 查看当前项目/需求、产物路径和任务勾选事实；可指定项目或
需求，或要求列出本项目需求。查看其他需求不保存切换，不初始化、不修复配置、
不运行其他阶段。宪法模板、空/不可读文件、无活动需求与未知历史分开说明。
详见 [STATUS.md](docs/STATUS.md)。

## Development tooling

Repository development, build, unit-test and upgrade-verification tooling uses
**uv** with committed `pyproject.toml` and `uv.lock`. Start with `uv sync --locked`
and run Python tools through `uv run --locked`. This tooling boundary is outside
the installed plugin: `dist/` continues to require only Bash, Python 3.9+ and
standard POSIX tools. See [Development](docs/DEVELOPMENT.md).

## Documentation

- [Project initialization and safe repeated calls](docs/INITIALIZATION.md)
- [Installation and beta cache handling](docs/INSTALLATION.md)
- [Build and independent engineering verification](docs/DEVELOPMENT.md)
- [Naming contract and upgrade mapping](docs/NAMING.md)
- [Exact migration differences](docs/MIGRATION.md)
- [Controlled upstream upgrade candidates](docs/UPGRADING.md)
- [Verification boundaries](docs/VERIFICATION.md)
- [Codex/Cursor comparison project and requirement](docs/SMOKE-TEST.md)

The presently authorized working repository can differ from the declared product
address. Updating metadata is not a GitHub transfer. Install from an accessible
repository/ref containing this implementation, not an old default branch.

## Attribution

Original Spec Kit copyright and MIT terms remain in LICENSE and NOTICE; original
upstream files retain their attribution. Each package includes UPSTREAM.json.
This is not an official release of GitHub, OpenAI, Anthropic or Cursor.

## 命名迁移后的使用边界

Codex 示例：`$sdlc-100-spec`；Claude Code 示例：
`/sdlc-ai-spec:sdlc-100-spec`；Cursor 示例：`/sdlc-100-spec`（以客户端菜单
实际入口为准）。Skill 名称、目录、共享工作流文件、加载参数和提示统一使用
同一编号 ID。全部 11 个入口共用目录，不保留宿主私有 Skill。

运行变量为 `SDLC_INIT_DIR`、`SDLC_FEATURE`、`SDLC_FEATURE_DIRECTORY`。
已撤回对所有非空 `SPECIFY_*` 的整体拒绝；不相关旧前缀不影响选定项目。
正式调用使用上述 `SDLC_*` 名称；没有新增旧变量别名。事件键 `before_specify` /
`after_specify` 保持原名，不属于展示性品牌。
`.sdlc`、`spec.md`、`plan.md`、`tasks.md` 等业务路径不变；旧项目的已有文档
不自动重写。插件 ID 从旧 `sdlc` 改为 `sdlc-ai-spec` 后，请按
[安装迁移说明](docs/INSTALLATION.md#naming-migration-in-pr-24)处理旧安装，
避免重复入口。原始来源名称仅用于版权、来源映射和明确列出的兼容性边界。

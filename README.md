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
工具的错误由本项目负责。公共入口不得改变各宿主的调用策略。

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

**状态：已迁移生成入口，三个宿主各安装 10 个阶段 Skill。** 下表名称对应当前
生成包；原生客户端发现与模型执行仍须实际验证，不能仅由工程测试推定。
`sdlc-status` 是预留的新能力，当前未实现。提交和验证记录见
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
| `sdlc-status` | Status | 状态与产物导航 | 新增，待实现 |

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
和显式更新项目原则。**改名不新增 RULE 自动初始化、STATUS 实现或自动跨阶段
执行**；这些行为变更应在各自工作包中记录。

产品名称按语境使用 **SDLC AI SPEC**（显示名）、`sdlc-ai-spec`（机器标识）、
`sdlc` / `SDLC_`（程序简称），项目目录继续使用 `.sdlc`。当前插件机器标识为
`sdlc-ai-spec`，三个原生清单、marketplace 与调用命名空间已同步。详细转换、例外与升级规则见
[命名与迁移契约](docs/NAMING.md)，机器可读映射见
[docs/naming-map.json](docs/naming-map.json)。

## One package, three host entrypoints

Members install the prebuilt **dist/** package through a marketplace; they do not
run a build, install the upstream CLI or fetch upstream on installation. Root catalogs
for Codex, Claude Code and Cursor all select `./dist`. The package has one copy
of workflows, scripts and templates. Explicit native manifests select disjoint,
thin host entrypoints; those pass a literal host to a stdlib-only read-only text
binder. Business workflow content is shared without asking the model to guess
which host it is running in.

Ten numbered skills: INIT, RULE, SPEC, CLAR, PLAN, TASK, XCHK, HUMA, IMPL and CONV. English instructions and substantive template content
remain upstream-derived. Project state belongs in `.sdlc`, never in the plugin.
Bash, Python 3.9+ and standard POSIX tools are runtime dependencies. No uv,
upstream CLI, LLM API, MCP service or background process is required by the package.

**Project initialization is included.** Run the installed `sdlc-000-init` entry once
per project; repeat calls preserve existing work and complete compatible partial
state. It does not copy tools or create features. See
[Project initialization](docs/INITIALIZATION.md). There is no GitHub integration,
translation, new lifecycle or automatic project migration. Native installation
and model-driven behavior must be verified separately; see the small isolated
[smoke test](docs/SMOKE-TEST.md).

## Layout

```text
.agents/plugins/marketplace.json
.claude-plugin/marketplace.json
.cursor-plugin/marketplace.json
src/upstream/             Original, pinned source and renderer references
src/scripts/              Shared migrated runtime plus small local helpers
src/templates/            Derived template source
adapters/                Strict migration and host-binding rules
tools/                   Deterministic port, build, upgrade and comparison
tests/                   Synthetic engineering tests, not business acceptance
dist/                    Entire installed plugin boundary
  .codex-plugin/         Explicit Codex entrypoint selection
  .claude-plugin/        Explicit Claude entrypoint selection
  .cursor-plugin/        Explicit Cursor entrypoint selection
  adapters/<host>/skills/  Thin native wrappers (no copied business bodies)
  references/workflows/  <full-skill-id>.md; one factored body per capability
  bindings/              Literal host differences generated at build time
  scripts/               One shared runtime
  templates/             One shared template collection
  BUILD.json             Deterministic source build identity
```

The native manifests deliberately replace the previous portable root manifest:
portable fixed skill discovery cannot select different host entrypoints. No
root/default `skills` directory is used inside dist, preventing duplicate scans.
The runtime loader only binds precompiled literal fragments; it does not compile
upstream, run a workflow or write state. Full output must be read before execution.

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
同一编号 ID。三套薄入口继续保留各自的宿主参数与元数据，不在本次合并目录。

运行变量为 `SDLC_INIT_DIR`、`SDLC_FEATURE`、`SDLC_FEATURE_DIRECTORY`。
旧的非空 `SPECIFY_*` 运行覆盖参数会明确报错，不能静默回退到其他项目。
`.sdlc`、`spec.md`、`plan.md`、`tasks.md` 等业务路径不变；旧项目的已有文档
不自动重写。插件 ID 从旧 `sdlc` 改为 `sdlc-ai-spec` 后，请按
[安装迁移说明](docs/INSTALLATION.md#naming-migration-in-pr-24)处理旧安装，
避免重复入口。原始来源名称仅用于版权、来源映射和明确列出的兼容性边界。

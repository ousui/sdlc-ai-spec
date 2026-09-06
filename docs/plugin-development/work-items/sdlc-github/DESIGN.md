# sdlc-github — GitHub 基础能力设计

| 项目 | 值 |
|---|---|
| Design ID | `sdlc-github-foundation/v1` |
| 状态 | `ready`；等待 Maintainer 批准后实施 |
| 日期 | 2026-09-06 |
| 仓库 | `ousui/sdlc-ai-spec` |
| 审查基线 | `main@9d9dbf8bc1b9241f80af53cdf5b0426fcbfe3ab9` |
| 设计分支 | `design/sdlc-github-foundation-v1` |
| 实施分支 | `impl/sdlc-github-foundation-v1` |
| 运行入口 | `sdlc-github` |
| 配套文件 | [EVAL-PLAN.md](EVAL-PLAN.md)、[EXECUTE-WEB.md](EXECUTE-WEB.md)、[HANDOFF.md](HANDOFF.md) |

## 1. 目标与交付边界

为 SDLC 各核心阶段建立可复用的 GitHub 读取与基础协作写入能力。用户通过 `sdlc-github` 显式调用；三个 Agent 使用相同的程序、操作定义和结果契约。首版验收对象是接口连通、参数正确、身份隔离、写入准确、失败可识别和三端可用，不预设完整业务发布流程。

本期实现一个正式 Skill、一个共享 GitHub Package、一个 stdio MCP Server，以及三个宿主的安装配置和验证材料。

范围固定为 GitHub.com、用户提供的 PAT、GitHub 官方 Remote MCP，以及第 4 节的操作表。范围外：认证界面和凭据管理、其他后端或备用执行通路、Wiki 写入、Release 创建/发布、Git 内容写入与合并、Actions 执行、跨阶段自动编排和双向同步。新增操作必须通过独立范围变更，不由上游工具自动增加。

## 2. 架构与责任

```text
Codex / Cursor / Claude Code
            │
       sdlc-github
            │  宿主工具调用
            ▼
    SDLC GitHub MCP Server       stdio / 单进程身份
            │
    packages/sdlc_github        校验、映射、结果、回执
            │  官方 MCP SDK / Streamable HTTP
            ▼
    GitHub 官方 Remote MCP
```

唯一生产上游为 `https://api.githubcopilot.com/mcp/`。该地址由程序固定；请求参数不能改变服务地址、认证 Header、工具名或 HTTP 方法。

| 层 | 职责 |
|---|---|
| Skill | 意图识别、参数归一化、最小事实收集、确认准确目标、调用声明的 MCP 工具、解释结果 |
| MCP Server | 对宿主暴露固定工具，提供 input/output schema，使用同一 Service 实现 |
| 共享 Package | 操作白名单、参数与对象类型校验、身份绑定、上游 MCP 调用、结果归一化、写入回执 |
| 宿主 | 启动本地进程、注入环境、遵守原生工具权限与批准策略 |
| GitHub | 校验 PAT 和仓库权限，执行真实平台操作 |

使用官方 Python MCP SDK 实现 Server/Client，不自写协议解析器。实施时选择一个经验证的 SDK 精确版本，并锁定依赖与摘要；整个首版只支持这一依赖组合。运行时不安装依赖。连接按需建立：启动、工具发现、help 和本地参数检查不访问 GitHub；第一次显式在线操作才建立上游会话。

Skill 不调用兄弟 Skill。核心阶段可以消费本次输出或在后续获准的工作流中使用共享能力；本期不修改它们的执行状态机、领域判断或 ArtifactStore。[R1][R2]

## 3. 身份与启动配置

### 3.1 单实例身份

程序仅从本进程环境变量 `SDLC_GITHUB_TOKEN` 取得 PAT。Token 不通过业务参数传入，不写入文件，不出现在日志、异常、回执、测试证据或模型输出中。

每个 MCP 实例只有一个 Token。不同 Agent 启动独立实例，可以注入不同值。Token 变更后重启对应实例；不在进程内切换账户。

在线 `status` 调用上游 `get_me`，返回真实 `actor.id` 和 `actor.login`。所有远程操作在当前已验证身份下执行。写请求包含从 status 得到的 `expected_actor_id`，Service 在发送前核对，避免会话间误用账户。该字段是身份一致性条件，不是用户授权凭证。

Token 缺失返回 `AUTH_REQUIRED`，失效返回 `AUTH_FAILED`，权限不足返回 `PERMISSION_DENIED`。404 统一为 `NOT_FOUND_OR_INACCESSIBLE`，不猜测对象一定不存在。失败不触发登录、权限扩张或另一路连接。

### 3.2 安装输入

安装配置确定以下非秘密信息：Python 解释器绝对路径、插件代码路径、稳定数据根绝对路径。用户在宿主环境中配置 PAT。安装过程不得将 PAT 展开后写回版本化文件。

三端均启动同一 `scripts/sdlc_github_mcp.py --data-root <absolute-path>`。配置模板只处理宿主语法差异，不复制业务实现。[R4][R5][R6]

示例中的绝对路径由安装者一次性替换；不是自动查找路径。

**Codex，config.toml 中的 MCP 配置：**

```toml
[mcp_servers.sdlc_github]
command = "/ABS/PYTHON"
args = ["/ABS/PLUGIN/scripts/sdlc_github_mcp.py", "--data-root", "/ABS/STABLE-DATA"]
env_vars = ["SDLC_GITHUB_TOKEN"]
```

**Cursor，MCP 配置：**

```json
{"mcpServers":{"sdlc_github":{
  "command":"/ABS/PYTHON",
  "args":["/ABS/PLUGIN/scripts/sdlc_github_mcp.py","--data-root","/ABS/STABLE-DATA"],
  "env":{"SDLC_GITHUB_TOKEN":"${env:SDLC_GITHUB_TOKEN}"}
}}}
```

**Claude Code，MCP 配置：**

```json
{"mcpServers":{"sdlc_github":{
  "command":"/ABS/PYTHON",
  "args":["/ABS/PLUGIN/scripts/sdlc_github_mcp.py","--data-root","/ABS/STABLE-DATA"],
  "env":{"SDLC_GITHUB_TOKEN":"${SDLC_GITHUB_TOKEN}"}
}}}
```

实施交付包括精确可安装配置，并按宿主官方 manifest schema 接入现有三个插件入口。每个安装实例只注册一个 `sdlc_github` 服务；配置生成不扫描或修改其他 MCP 的连接。环境注入与工具批准的实际行为必须在目标客户端验证，静态 JSON/TOML 正确不等于原生验证通过。

## 4. 固定能力目录

### 4.1 对 Agent 暴露的 8 个工具

| 工具 | 作用 |
|---|---|
| `sdlc_github_status` | 在线核对身份、连接状态与本期能力可用性 |
| `sdlc_github_read` | 执行下表中的一个只读操作 |
| `sdlc_github_issue_create` | 创建 Issue |
| `sdlc_github_issue_update` | 修改准确 Issue 的标题、正文、open/closed 状态 |
| `sdlc_github_comment_create` | 向准确 Issue 或 PR 添加普通评论 |
| `sdlc_github_pr_create` | 为已存在的 head/base 分支创建 Draft PR |
| `sdlc_github_pr_update` | 修改准确 PR 的标题、正文、open/closed 状态 |
| `sdlc_github_operation_status` | 读取本地写入回执；必要时显式执行只读远端核对 |

每个写工具有独立 JSON Schema；不能通过 `extra`、原始 payload 或任意工具名扩展能力。只读工具的 `operation` 为固定枚举，参数按操作建立判别联合校验。

### 4.2 27 个只读操作

下表以官方 `github/github-mcp-server v1.12.0` 文档作为工具映射基线。Hosted 服务自身不能被本地版本号锁定；运行时必须核对所需工具及参数，不把文档版本当成远端版本。[R3]

| Operation | 上游工具 / 固定 method |
|---|---|
| `repo.files` | `get_file_contents` |
| `repo.branches` | `list_branches` |
| `repo.commits` | `list_commits` |
| `repo.commit` | `get_commit` |
| `repo.tags` | `list_tags` |
| `repo.tag` | `get_tag` |
| `issue.list` | `list_issues` |
| `issue.get` | `issue_read / get` |
| `issue.comments` | `issue_read / get_comments` |
| `pr.list` | `list_pull_requests` |
| `pr.get` | `pull_request_read / get` |
| `pr.diff` | `pull_request_read / get_diff` |
| `pr.files` | `pull_request_read / get_files` |
| `pr.reviews` | `pull_request_read / get_reviews` |
| `pr.review-comments` | `pull_request_read / get_review_comments` |
| `pr.comments` | `pull_request_read / get_comments` |
| `pr.checks` | `pull_request_read / get_check_runs` |
| `pr.status` | `pull_request_read / get_status` |
| `actions.workflows` | `actions_list / list_workflows` |
| `actions.runs` | `actions_list / list_workflow_runs` |
| `actions.jobs` | `actions_list / list_workflow_jobs` |
| `actions.artifacts` | `actions_list / list_workflow_run_artifacts` |
| `actions.run` | `actions_get / get_workflow_run` |
| `actions.logs` | `get_job_logs`：准确 job_id，return_content=true |
| `release.list` | `list_releases` |
| `release.get` | `get_release_by_tag` |
| `release.latest` | `get_latest_release` |

`actions.artifacts` 只读元信息；本期不下载或解压制品。日志只读取单个明确 Job，不使用隐式聚合全部失败 Job 的便利模式。

### 4.3 5 个写入操作

| Operation | 上游映射 | 允许字段与固定行为 |
|---|---|---|
| `issue.create` | `issue_write / create` | repository、title、body；创建普通 Issue |
| `issue.update` | `issue_write / update` | repository、issue_number；title/body/state 至少一项 |
| `comment.create` | `add_issue_comment` | repository、subject_type、number、body；普通评论 |
| `pr.create` | `create_pull_request` | repository、head、base、title、body；固定 draft=true |
| `pr.update` | `update_pull_request` | repository、pull_number；title/body/state 至少一项 |

`state` 仅允许 `open|closed`。更新前验证对象类型，避免把 PR 误当 Issue 更新。省略字段保持原值；清空正文必须显式提供空字符串。创建标题不能为空。PR 创建验证分支存在且不同，不创建分支、不推送代码、不修改 maintainer_can_modify 或评审配置。

所有32个操作都必须在固定测试中通过参数映射、成功、权限不足及上游失败验证。运行时缺失工具或 schema 不兼容返回 `CAPABILITY_UNAVAILABLE`，不假定接口连通。

## 5. 调用与参数契约

### 5.1 用户入口

```text
/sdlc-github [command] [options] [-- 自然语言请求]
```

命令固定为：`auto`、`status`、`read`、`issue-create`、`issue-update`、`comment`、`pr-create`、`pr-update`、`receipt`、`help`、`version`、`commands`、`examples`。

裸调用无具体意图时执行 status；有唯一明确意图时选择相应命令；存在歧义时先确认。元命令只显示打包信息，不扫描项目、不联网、不持久化。

沿用共享参数解析器和 `references/interface.json`。`--operation/-o` 的现有命令兼容语义不变；read 子类型用 `--kind`，避免复用保留参数。公共 `--project-root/-p`、`--reference/-r`、`--decision-policy/-d`、`--write-policy/-w`、`--dry-run/-n`、`--output/-f` 保持既有含义。

新增业务参数：`--repo owner/name`、`--url`、`--kind`、`--number`、`--title`、`--body`、`--body-file`、`--head`、`--base`、`--state`、`--page`、`--per-page`、`--after`、`--request-id`。每个命令只接受相关字段；文件或 SHA 选择、Workflow/Run/Job/Tag 选择由 read 的按操作 schema 明确声明，不能用任意 JSON 透传。

`--body-file` 由 Skill 本地入口按准确路径读取，传给 MCP 的是文本，不让远端解释本地路径。`--body` 与 `--body-file` 冲突时报错。`--reference` 仅记录来源引用，不授予读取任意文件或改写 Artifact 的权力。

### 5.2 Repository 与 URL

远程操作必须绑定一个准确 repository。显式 repo 与 URL 解析结果冲突时失败，不用“最后一个覆盖”。无参数时只能从宿主提供的唯一工作区 Git remote 得出唯一目标；有多个候选则询问，不默认取第一个。

URL 本期接受 GitHub.com 的仓库、Issue、PR、文件、Actions Run 和 Release Tag 标准地址。解析只负责提取对象标识，真正读取仍走操作表。分支名含斜线而无法唯一解析的文件 URL 必须要求准确 ref/path 或 SHA，不猜拆分。拒绝自定义 host、userinfo、非 HTTPS、编码逃逸、任意下载地址以及未支持对象。

### 5.3 写入许可

Skill 在当前用户明确要求的操作、账户和目标内执行；缺少真实写入意图时只展示候选并请求确认。宿主继续按原生工具权限执行批准，不增加自建批准 UI。

程序在每次写入前校验白名单、schema、身份、目标类型、write_policy、dry_run 和请求去重。`write_policy=deny` 拒绝副作用；`dry_run=true` 只预检，不发出远程写调用、不保存 intent。`write_policy=auto` 不是远程写入授权。

用户授权的可信边界是宿主和用户请求。程序字段 `expected_actor_id`、request_id 或模型自述均不能证明用户批准。固定写工具标注非只读，宿主不得因通用入口误判为查询；本期不宣称能隔离恶意同用户进程或其他已安装工具。[R7]

## 6. 统一结果与回执

采用独立的 `sdlc-ai-spec/github-result/v1` 非 Phase 结果契约，保持仓库通用的 `ok/status/errors/warnings/next_action` 风格。既有 Phase Result 的 operation 枚举不适合外部工具调用，原 schema 保持原样。[R2]

| 字段 | 约束 |
|---|---|
| `contract` | 固定契约 ID |
| `ok` | 仅本次目标完整达成时为 true；不表示 SDLC Gate 通过 |
| `status` | `completed|action_required|blocked|failed|partial|unknown` |
| `operation` | 准确操作 ID；状态工具使用自己的固定 ID |
| `actor` | 已验证 id/login；离线错误时可为 null |
| `repository` / `target` | 准确仓库与对象标识；未知时为 null |
| `data` | 按操作验证后的数据，保留需要的原始字段 |
| `pagination` | 模式、下一页/游标及是否还有数据；无法判定时为 unknown |
| `completeness` | `complete|partial|unknown`；包括分页、截断、过滤影响 |
| `effect` | `none|confirmed|unknown`；错误不自动等于无效果 |
| `receipt` | 写入的 request_id、URL/远端ID、时间和本地状态；只读可为 null |
| `warnings/errors/next_action` | 稳定错误码、脱敏信息和一个准确下一动作 |

每个 MCP 工具声明 input/output schema；返回 `structuredContent` 和同义的最小文本结果。summary 默认只展示账户、对象、结果、实际副作用及下一动作；JSON 模式保留程序结果，不让模型重新编造。debug 同样脱敏。

上游 `isError`、非法 JSON、类型错误或“只有消息没有必需对象 ID”均不能报成功。列表每次只请求一页，默认30、最大100，显式返回分页信息。上游没有可靠分页标识时保持 unknown，不从条数较少推导全集。

每次网络请求有有界超时；首版默认60秒。普通结果默认最多256 KiB，Diff/日志最多1 MiB；超限显式 partial，日志尾部截取必须标明。仅缓冲所需有界内容，不一次载入无限响应。重试由用户或调用方显式发起；程序不自动重放写调用。

### 6.1 最小可靠写入

1. Skill 入口为一次用户操作生成 UUID request_id；重试相同操作复用它，用户不需手工构造。
2. Service 按 actor.id、repository、request_id 定位本地记录。相同 ID 与不同参数摘要冲突，直接拒绝。
3. 用独占创建写入 durable intent，包含操作、目标、规范化参数摘要、预期账户和时间。先落盘成功，后调用上游；磁盘不可写时零远程效果。
4. 收到上游成功对象后，执行对应只读读回，记录 ID、URL、实际状态和验证结果。上游已确认副作用但读回失败时记录 confirmed/partial，不能回报“没有执行”。
5. 原子保存 receipt。相同 ID 已完成时返回原回执，不再写 GitHub。相同 ID 未有终态、超时或进程中断时返回 unknown，进入只读核对，禁止自动重放。

创建 Issue、PR 和评论的正文附加一个明确记录的操作标记，关联 request_id，供中断后核对。重复发布不会仅凭标题相同就合并。更新前记录当前字段和预期字段摘要；读回是实际状态证据，不声称 GitHub 为该更新提供跨请求事务。

`operation_status` 的远端核对只有在完整范围内找到唯一标记/已知对象且属性匹配时才能补齐结果；标记被删除、权限变化、分页未完成或多候选时保持 unknown。回执可追加核对记录，但不能改写历史观察。该机制提供同一请求的防重放，不宣称跨不同 request_id 的全局 exactly-once。

## 7. `.local/` 与 `.cache/`

安装者向程序提供唯一稳定数据根。代码目录与数据目录分别绑定，运行时不从 CWD、HOME 或其他 Agent 配置猜测。固定源码安装可将数据根设为该仓库；市场安装须使用跨更新保留的已绑定数据目录。[R5]

```text
<stable-data-root>/
├── .local/
│   └── github/<actor-id>/<repository-key>/operations/
│       └── <request-id>/
│           ├── intent.json
│           └── receipt.json
└── .cache/
    └── github/                 # 可重建的开发或运行缓存；按需创建
```

`.local/` 保存不可随意重建的数据，不自动清理。`.cache/` 可以整体删除；首版不要求实现内容缓存，不创建空目录。两者均不进 VCS、不进入插件分发包。测试夹具存 `tests/`；临时生成数据使用测试指定的独立数据根，不能污染真实安装。

路径组件由程序生成并验证；拒绝穿越、符号链接逃逸和已有非法对象。目录与记录限制为当前用户可访问；读回操作记录仍需匹配本次账户和仓库。Token及其摘要不参与目录名，不保存凭据。JSON 使用原子替换；request_id 由独占创建避免多进程双写。记录损坏时阻塞对应操作，不当成记录不存在。

读取结果默认不保存正文缓存；写回执保存最小必要元信息和内容摘要，真实 Token 必须在任何返回/落盘前屏蔽。Secret 检查只能作为附加保护，不宣称能识别所有敏感内容。进程 stderr 仅写脱敏诊断，stdout 专用于 MCP。

## 8. 目录结构与仓库接入

以下为实施落点；本设计分支只创建对应 Work Item 文档。

```text
skills/sdlc-github/
├── SKILL.md
├── agents/openai.yaml
├── references/
│   ├── interface.json
│   ├── contract.md
│   └── source-lock.json
└── scripts/runtime.py           # 公共参数归一化、help、Invocation；不直连远端

packages/sdlc_github/
├── __init__.py
├── service.py                   # 唯一业务执行入口
├── operations.py                # 固定目录、字段与上游映射
├── transport.py                 # 唯一 MCP Client
├── records.py                   # intent / receipt
├── models.py                    # 请求、结果、错误
├── requirements.lock            # 实施时锁定依赖
└── CONTRACT.md

scripts/sdlc_github_mcp.py        # 唯一生产 MCP Server 入口
skills/_shared/schemas/github-result.schema.json
skills/_shared/contracts/github-runtime.md
packages/sdlc_runtime/local_paths.py   # 两类本地目录的共享解析与安全访问

tests/skill_github/              # 固定测试、Fake MCP、Oracle、配置验证

docs/plugin-development/work-items/sdlc-github/
├── DESIGN.md
├── EVAL-PLAN.md
├── EXECUTE-WEB.md
└── HANDOFF.md
```

Skill 主体沿用仓库现有样式：Front Matter、用户入口、默认行为、执行、边界、决策、结果。中文描述、显式触发、共享 parser、标准元命令、Runtime Independence 和 source-lock 均保持一致。`sdlc-github` 属于非 Phase 支撑 Skill，不占用阶段编号，沿用 `sdlc-status` 的类别先例。[R1][R2]

实施时对以下公共点作有限增量：

- 三个平台 manifest 及其唯一 MCP 启动配置；共享 skill 接口发现与校验列表新增 `sdlc-github`。
- 根 `.gitignore` 与打包器排除 `.local/`、`.cache/`；现有 `.sdlc/store.sqlite3` 不变。
- 工程规则明确“GitHub 集成的显式网络操作走声明的 MCP Transport；其他 Runtime 保持原边界”。据此同步必要的 AGENTS、DEVELOPMENT、共享执行合约与对应 validator/source-lock。
- Installed-copy 验证使用随包依赖和 Fake MCP，不读取 docs 或开发仓库；真实在线验证另记。不能用联网权限的增量放宽所有 Phase。
- 依赖锁与安装说明随包；其他现有 Skill 不因缺少 GitHub Token 或未配置此 MCP 而失效。

不改通用模板以迁就单个 Skill；不重新组织现有目录。所有共享文件改动必须解释与本工作包的直接关系，并跑相应回归。

## 9. 交付与验收

### 9.1 Web 实施

在独立实施分支完成生产代码、全部32个操作映射、固定 schema、真实 stdio Server 到 Fake HTTP MCP 的端到端测试、安装包检查、现有回归、三端配置及可直接执行的验证入口。有安全可用的测试认证时补充在线验证；无法访问的真实宿主明确留给 Client。

Web 交付必须形成一个实际可运行的完整候选，不能仅交脚手架、Mock 实现、TODO 或要求 Client 完成主体功能。详细用例见 EVAL-PLAN。

### 9.2 一次 Client Goal

仅承接 Web 无法完成的真实宿主、账户隔离、持久工作区、跨重启与长任务验证。Web 在交付前生成包含准确源码 SHA、环境要求、测试仓库范围、单一运行入口、证据目录及停止条件的 `CLIENT-GOAL.md`。不要求用户填写内部摘要或回执。

目标是一个连续验证批次。缺客户端、Token、有效目标对象或授权时输出 BLOCKED，不绕过也不反复自动扩大环境。所有32个操作的 Mock/协议覆盖与真实远端覆盖分别登记；未运行的真实接口不能标记 PASS。

### 9.3 一次独立 Web Review 与定向修复

读取准确 Client 交付和证据，复核失败及独立反例，必要时在同一实施分支修复并重跑受影响测试。修复不覆盖旧证据；区分最终源码实测范围。若存在必须回客户端重验的安全关键问题，准确标记阻塞，不能为了减少交互伪造闭环。

### 9.4 接受条件

全部范围内操作有可执行实现和确定 Oracle；原有功能回归通过；Token不泄露；写入对象与账号正确；中断不重复发出副作用；删除缓存不损坏操作状态；三端均有 Discovery、显式 Invocation 和真实 Behavior 的独立证据。只有配置通过或 SDK 测试通过不能写“三端已验证”。

## 10. Git 与工作包治理

本次设计仅写 `docs/plugin-development/work-items/sdlc-github/`，保持 Draft PR；不修改共享 HANDOFF、现有运行代码或 main。设计的唯一下一工作包是本设计批准后的 Web 实施。

实施从实际设计分支 HEAD 创建 `impl/sdlc-github-foundation-v1`。先记录 SHA 与目标路径现状；main 或其他分支前进不触发自动混入变更。共享文件有并行冲突时登记并集中处理，不编辑其他分支。当前用户的批量委托允许实施、程序评测和三个独立适配子阶段在一次 Web 会话中顺序完成，每一阶段保留可辨识结果；独立 Review 保持 fresh context。

不得自动 merge、改 main、创建 Tag/Release、改变其他工作包的状态或批准。设计状态由 Agent 完整性检查可标记 ready，approved 只来自 Maintainer 明确决定。[R1]

## 11. 来源与适用范围

以下是设计依据，不是运行时远程依赖；固定测试中的字段映射须按实际读取内容建立。

- **R1 — 本仓库工程规则与 Skill 样式**：审查基线下的 [AGENTS.md](https://github.com/ousui/sdlc-ai-spec/blob/9d9dbf8bc1b9241f80af53cdf5b0426fcbfe3ab9/AGENTS.md)、[DEVELOPMENT.md](https://github.com/ousui/sdlc-ai-spec/blob/9d9dbf8bc1b9241f80af53cdf5b0426fcbfe3ab9/docs/plugin-development/DEVELOPMENT.md)、[文档 AGENTS](https://github.com/ousui/sdlc-ai-spec/blob/9d9dbf8bc1b9241f80af53cdf5b0426fcbfe3ab9/docs/plugin-development/AGENTS.md)、[sdlc-status](https://github.com/ousui/sdlc-ai-spec/blob/9d9dbf8bc1b9241f80af53cdf5b0426fcbfe3ab9/skills/sdlc-status/SKILL.md)。本设计的受限联网与批量工作包需按第8/10节实施，不把基线禁止项视为已被修改。
- **R2 — 共享接口与 Phase Result**：[skill-interface.md](https://github.com/ousui/sdlc-ai-spec/blob/9d9dbf8bc1b9241f80af53cdf5b0426fcbfe3ab9/skills/_shared/contracts/skill-interface.md)、[result.schema.json](https://github.com/ousui/sdlc-ai-spec/blob/9d9dbf8bc1b9241f80af53cdf5b0426fcbfe3ab9/skills/_shared/schemas/result.schema.json)。
- **R3 — GitHub 官方 MCP**：[v1.12.0 README 工具目录](https://github.com/github/github-mcp-server/blob/v1.12.0/README.md)、[server-configuration](https://github.com/github/github-mcp-server/blob/v1.12.0/docs/server-configuration.md)。只据此声明已列出的能力，不声称覆盖全部 GitHub API。
- **R4 — Codex MCP 配置**：[官方 MCP 文档](https://developers.openai.com/codex/mcp)。确认 stdio、环境注入和原生工具配置。
- **R5 — Claude Code MCP 与持久路径**：[MCP](https://code.claude.com/docs/en/mcp)、[Plugins reference](https://code.claude.com/docs/en/plugins-reference)。插件代码根会随更新变化，数据根需独立持久。
- **R6 — Cursor MCP**：[官方 MCP 文档](https://prod.cursor.com/docs/mcp)。确认 stdio 和 `${env:NAME}` 插值。
- **R7 — MCP 工具契约**：[工具与结果规范](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)、[官方 Python SDK](https://github.com/modelcontextprotocol/python-sdk)。Host 的工具批准与实际 schema/结果解析必须分别验证。

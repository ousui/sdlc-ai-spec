# sdlc-ai-spec

`sdlc-ai-spec` 定义软件研发与变更交付中的 Artifact、Reference、Evidence、
Exception、Check 和 Gate，并提供 Cursor、Claude Code、Codex 共用的 Agent Plugin Runtime。

当前 Plugin 版本：**0.9.0**。Plugin Version 与领域 Spec Version 独立；当前稳定领域规范仍为 v1.1。

## Spec 与 Runtime

项目采用两层模型：

```text
docs/v1.x/**
    设计、审查和追溯来源
          ↓
skills/** + packages/** + scripts/**
    安装后的自包含执行 Runtime
```

正式 Skill 运行时不读取 `docs/v1.x/**`。规范文档用于设计和验证 Skill；发布后的 SOP、
共享运行合约、模板和确定性程序随 Plugin 一起分发。

## Plugin 结构

```text
.cursor-plugin/       Cursor 入口
.claude-plugin/       Claude Code 入口
.codex-plugin/        Codex 入口
skills/               正式 Skill 与共享运行合约
packages/             共享确定性组件
scripts/              运行时 CLI
tools/                构建期工具
docs/                 规范与开发治理
tests/                自动化测试
```

三个 Agent 共用根目录 `skills/`，平台入口保持轻量。

## Plugin 安装

### Codex

将仓库添加为 Codex Marketplace，再安装其中的 `sdlc-ai-spec` Plugin：

```bash
codex plugin marketplace add <marketplace-source> --ref main
codex plugin add sdlc-ai-spec@sdlc-ai-spec
```

Marketplace 元数据位于 `.agents/plugins/marketplace.json`，Plugin 展示与运行入口位于
`.codex-plugin/plugin.json`。

### Claude Code

```bash
claude plugin marketplace add <marketplace-source>
claude plugin install sdlc-ai-spec@sdlc-ai-spec
```

Marketplace 元数据位于 `.claude-plugin/marketplace.json`，Plugin 入口位于
`.claude-plugin/plugin.json`。

### Cursor

本地开发时，将仓库链接到 Cursor 的本地 Plugin 目录，然后重启 Cursor 或执行
`Developer: Reload Window`：

```bash
mkdir -p ~/.cursor/plugins/local
ln -s <plugin-repository-root> ~/.cursor/plugins/local/sdlc-ai-spec
```

Cursor 入口位于 `.cursor-plugin/plugin.json`。公开 Marketplace 安装仍以实际审核结果为准。

> 普通 Phase/Status Skill 由标准 Plugin 安装提供。`sdlc-github` 额外依赖官方 GitHub Remote MCP
> 和锁定 Python 环境，必须先用 `tools/install_sdlc_github.py` 生成绑定解释器与稳定数据根的安装副本；
> 源码树里的占位 MCP 配置不能直接当作完成安装。详见
> [sdlc-github 安装说明](docs/plugin-development/work-items/sdlc-github/INSTALL.md)。

## 正式 Skills

### Phase Skills

| Phase | Skill | 说明 |
|---:|---|---|
| 000 | `sdlc-000-ctx` | Project Context |
| 100 | `sdlc-100-req` | Requirement |
| 200 | `sdlc-200-dsn` | Design |
| 300 | `sdlc-300-pln` | Plan |
| 400 | `sdlc-400-imp` | Implementation |
| 500 | `sdlc-500-vfy` | Verification |
| 600 | `sdlc-600-rls` | Release |

### Utility / Support Skills

| Skill | 说明 | 外部效果 |
|---|---|---|
| `sdlc-status` | 只读生命周期状态与下一动作查询 | 无 |
| `sdlc-github` | GitHub 仓库读取及受控 Issue / 评论 / Draft PR 协作 | 仅显式授权写入 |

Support Skill 不参与 Phase Gate，也不会自动调用兄弟 Skill。

## `sdlc-github` 快速使用

先在目标宿主的安全环境中配置 `SDLC_GITHUB_TOKEN` 并重启对应 MCP 实例；Token 不进入命令、
配置文件、证据或仓库。首次调用先核对当前账户：

```text
/sdlc-github status
```

常见只读调用：

```text
/sdlc-github read --repo owner/repo --kind repo.branches
/sdlc-github read --repo owner/repo --kind issue.list --state open
/sdlc-github read --repo owner/repo --kind pr.get --number 14
/sdlc-github read --repo owner/repo --kind actions.jobs --run-id 123456
```

常见写入：

```text
/sdlc-github issue-create --repo owner/repo --title "确认标题" --body "确认正文"
/sdlc-github comment --repo owner/repo --subject-type issue --number 123 --body "确认评论"
/sdlc-github pr-create --repo owner/repo --head feature/x --base main --title "Draft: feature/x"
```

写入前 Skill 会绑定 `status` 返回的真实 actor、展示准确目标并继续使用宿主原生权限确认；
`request_id` 用于防重放。若结果为 `effect=unknown`，**只查询原回执/只读 reconcile，不换 UUID 重发**。
首版不 merge PR、不推代码、不建分支、不创建 Tag/Release、不执行 Workflow。

完整命令与边界：[`skills/sdlc-github/SKILL.md`](skills/sdlc-github/SKILL.md)。

## Shared Runtime

多个 Skill 共同遵守的安装后合约位于 `skills/_shared/`；共享 Local SQLite ArtifactStore 位于
`packages/sdlc_artifact_store/`。业务 Skill 不依赖兄弟 Skill，不直接 SQL，不重复实现 Store。

## 当前状态

七阶段 CTX → REQ → DSN → PLN → IMP → VFY → RLS、`sdlc-status` 和 `sdlc-github` 均已实现。
RLS 仅执行本地 Fake/Sandbox，生产发布不在当前能力范围。`sdlc-github` 的 GitHub Runtime 已完成
真实 Hosted MCP 定向验证与 Linux/macOS 统一回归；缺少真实 Fixture 的 Tag 形态仍按调用时条件处理，
不通过创建禁止对象补证。

业务过程产物写入项目 ArtifactStore；开发测试日志和历史 Goal 不回填当前源码树。原生 Client 独立认证
不作为当前门禁，实际宿主问题按具体版本与证据处理。

维护验证从 [docs/TESTING.md](docs/TESTING.md) 开始；格式遵守
[Skill 样式约定](docs/plugin-development/SKILL-STYLE.md)。历史执行证据通过
[归档索引](docs/maintenance/ARCHIVE.md) 恢复。

## 文档入口

- [Plugin 开发标准](docs/plugin-development/DEVELOPMENT.md)
- [Skill 开发流程](docs/plugin-development/SKILL-DEVELOPMENT-WORKFLOW.md)
- [当前 Handoff](docs/plugin-development/HANDOFF.md)
- [兼容性范围](docs/plugin-development/COMPATIBILITY.md)
- [共享 Runtime 合约](skills/_shared/README.md)
- [ArtifactStore 组件](docs/plugin-development/components/artifact-store/README.md)
- [`sdlc-github` 当前工作项](docs/plugin-development/work-items/sdlc-github/README.md)
- [Changelog](CHANGELOG.md)

# sdlc-ai-spec

`sdlc-ai-spec` 定义软件研发与变更交付中的 Artifact、Reference、Evidence、
Exception、Check 和 Gate，并提供对应的 Agent Plugin 执行支持。

## Spec 与 Runtime

项目采用两层模型：

```text
docs/v1.x/**
    设计、审查和追溯来源
          ↓
skills/** + packages/** + scripts/**
    安装后的自包含执行 Runtime
```

正式 Skill 运行时不读取 `docs/v1.x/**`。规范文档用于设计和验证 Skill；
发布后的 SOP、共享运行合约、模板和确定性程序随 Plugin 一起分发。

## Plugin 结构

```text
.cursor-plugin/       Cursor 入口
.claude-plugin/       Claude Code 入口
.codex-plugin/        Codex 入口
skills/               正式 Skill 与共享运行合约
packages/             共享确定性组件
scripts/              运行时 CLI
tools/                构建期工具（按需）
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
`.codex-plugin/plugin.json`。Plugin 使用 Marketplace 根目录中的同一份代码。

### Claude Code

将仓库添加为 Claude Code Marketplace，再安装 Plugin：

```bash
claude plugin marketplace add <marketplace-source>
claude plugin install sdlc-ai-spec@sdlc-ai-spec
```

Marketplace 元数据位于 `.claude-plugin/marketplace.json`，Plugin 入口位于
`.claude-plugin/plugin.json`。相对 Source `./` 指向 Marketplace 根目录。

### Cursor

本地开发时，将仓库链接到 Cursor 的本地 Plugin 目录，然后重启 Cursor 或执行
`Developer: Reload Window`：

```bash
mkdir -p ~/.cursor/plugins/local
ln -s <plugin-repository-root> ~/.cursor/plugins/local/sdlc-ai-spec
```

Cursor 入口位于 `.cursor-plugin/plugin.json`。公开 Marketplace 安装需先提交仓库并通过
Cursor Marketplace 审核。

## Phase Skill 命名

| Phase | Skill Name | 说明 |
|---:|---|---|
| 000 | `sdlc-000-ctx` | Project Context |
| 100 | `sdlc-100-req` | Requirement |
| 200 | `sdlc-200-dsn` | Design |
| 300 | `sdlc-300-pln` | Plan |
| 400 | `sdlc-400-imp` | Implementation |
| 500 | `sdlc-500-vfy` | Verification |
| 600 | `sdlc-600-rls` | Release |

`name` 使用英文稳定标识，`description` 和正文默认使用中文。

## Shared Runtime

多个 Skill 共同遵守的安装后合约位于：

```text
skills/_shared/
```

共享 Local SQLite ArtifactStore 位于：

```text
packages/sdlc_artifact_store/
```

业务 Skill 不依赖兄弟 Skill，不直接 SQL，不重复实现 Store。

## 当前状态

七阶段 CTX → REQ → DSN → PLN → IMP → VFY → RLS 与 sdlc-status 已实现。RLS 仅执行本地 Fake/Sandbox，生产发布不在当前能力范围。业务过程产物写入项目 ArtifactStore；开发测试日志不回填源码仓库。

原生 Client 留痕暂不作为门禁；Maintainer 报告已手动使用，但未保存自动化认证记录。当前 Runtime 测试与手动反馈分别表述，不宣称全部载体正式认证。

维护验证从 [docs/TESTING.md](docs/TESTING.md) 开始；格式遵守 [Skill 样式约定](docs/plugin-development/SKILL-STYLE.md)。历史执行证据通过 [归档索引](docs/maintenance/ARCHIVE.md) 恢复，不影响安装 Runtime。

## 文档入口

- [Plugin 开发标准](docs/plugin-development/DEVELOPMENT.md)
- [Skill 开发流程](docs/plugin-development/SKILL-DEVELOPMENT-WORKFLOW.md)
- [当前 Handoff](docs/plugin-development/HANDOFF.md)
- [兼容性矩阵](docs/plugin-development/COMPATIBILITY.md)
- [共享 Runtime 合约](skills/_shared/README.md)
- [ArtifactStore 组件](docs/plugin-development/components/artifact-store/README.md)

# Changelog

本文件记录 `sdlc-ai-spec` Plugin 的重要变更。Plugin Version 与领域 Spec Version 独立管理。

> `0.2.0`～`0.8.0` 是根据既有提交顺序回溯整理的 Plugin 里程碑；没有为历史提交补造 Tag、Release
> 或 Marketplace 发布记录。`0.9.0` 起以此文件和三个 Plugin Manifest 的版本为当前版本来源。

## Unreleased

暂无。

## 0.9.0 - 2026-09-07

- 收口 `sdlc-github`：固定 8 个 MCP 工具、27 个只读与 5 个受控写操作，共用官方 GitHub Remote MCP。
- 修复 Hosted Schema/响应兼容：`issue.list` 状态、非空评论探针、嵌套 Actions jobs、轻量/附注 Tag、回执恢复与 marker 唯一性。
- 完成 durable intent/receipt、actor 绑定、防重放、unknown 只读 reconcile、敏感信息脱敏与安装解释器绑定。
- 修复 macOS `/var` 测试 Fixture 路径别名，同时保留生产 `O_NOFOLLOW`、symlink/hardlink/FIFO 拒绝边界。
- 修复 CTX 首次并发初始化的恢复预算起点；Linux 与真实 macOS Python 3.13 统一 `full` 最终 1213/1213 PASS。
- 完成仓库降噪：删除 `sdlc-github` 多轮 Goal/Repair/Revalidation/Portability 过程副本，以 Git 历史与全局归档索引恢复。
- 更新 README、Agent 规则、兼容性说明和 Plugin/Marketplace 版本元数据到 0.9.0。

## 0.8.0 - 2026-09-06

- 设计并实现首个非 Phase GitHub Support Skill `sdlc-github`。
- 引入固定 GitHub MCP Transport、严格参数映射、身份核对和 Issue/评论/Draft PR 基础协作能力。
- 建立写前持久 intent、原子 receipt、崩溃恢复与重复请求保护，并完成 Mock、stdio→Fake HTTP MCP 与首轮真实 GitHub 验证。
- 为 Codex、Cursor、Claude Code 增加共享 Runtime 的 MCP 配置和安装副本生成器。
- 合入主线的统一 Skill 样式、测试去重和过程归档治理，停止把长日志与历史 Goal 留在当前源码树。

## 0.7.0 - 2026-09-05

- 完成 CTX → REQ → DSN → PLN → IMP → VFY → RLS 七阶段 Skill Runtime 体系。
- 增加 VFY、RLS 和只读 `sdlc-status` 的运行契约、测试矩阵与生命周期投影。
- 完善阶段共享 Contract、Runtime Independence、Source Lock 和开发治理文档。
- 统一多阶段插件运行资源与安装后自包含边界。

## 0.6.0 - 2026-09-04

- 实现 `sdlc-300-pln`，形成可执行计划、工作分解和下一阶段输入。
- 实现 `sdlc-400-imp`，补齐 Implementation 阶段 Runtime 与验证闭环。
- 继续采用 Artifact/Reference/Evidence 驱动和阶段隔离的共享模型。

## 0.5.0 - 2026-09-01

- 实现 `sdlc-200-dsn`，完成 Requirement → Design 的正式阶段能力。
- 引入共享 Skill Interface Contract、统一参数解析、裸调用/元命令、decision/write policy 和 summary/json/debug 输出模式。
- 引入只读 Lifecycle Query Graph 与跨阶段状态投影基础。
- 完善本地 Marketplace 安装、根目录 Source 和多 Agent Plugin 入口。
- 移除依赖外部 SpringGear 的实时集成验证，保持测试本地可复现。

## 0.4.0 - 2026-08-31

- 完善 Cursor、Claude Code、Codex 多平台 Plugin 分发元数据与 Marketplace 校验。
- 增加 Canonical Artifact 解析、Digest、Frozen Authority 验证及共享 API。
- 增加跨阶段 VFY Return / RLS Issue Control Input 的共享只读解析能力。
- 合入正式 `sdlc-000-ctx`，并新增 `sdlc-100-req`。
- 调整仓库分发地址与 Git 忽略规则，为持续 Plugin 迭代准备统一来源。

## 0.3.0 - 2026-08-30

- 实现共享 Local SQLite ArtifactStore，建立 Canonical Revision、Manifest-Member closure 和事务边界。
- 标准化共享 Skill Contract、Runtime Contract Registry、Source Lock 与运行时验证工具。
- 增加共享 Phase Runtime foundation、Artifact Catalog 和 CTX Project Boundary lineage registry。
- 修复 CTX 并发 reservation、SQLite lock wait 和基础运行时 allowlist 边界。
- 完成首个 CTX Work Item 的设计批准到实现交接。

## 0.2.0 - 2026-08-29

- 增加根级/路径级 `AGENTS.md` 与最小 `CLAUDE.md` 桥接，固定阶段隔离、写入授权和并行会话规则。
- 定义 Exclusive Skill Execution 和显式调用默认策略。
- 将存储方案从多 Provider 收敛为 `.sdlc/store.sqlite3` Local SQLite Canonical Store。
- 完成 v1.1 Artifact Store / Revision Control / Allocation Authority 设计修订并发布稳定 v1.1 Spec Snapshot。
- 建立透明、阶段门禁化的 Skill Design / Eval / Approval 工作流。

## 0.1.0 - 2026-08-28

- 初始化 Cursor、Claude Code、Codex 跨 Agent Plugin Manifest。
- 建立共享 `skills/` 框架和 Plugin 开发、兼容性、Handoff 文档。
- 发布 `sdlc-ai-spec` v1.0 研发规范，确立 Artifact、Reference、Evidence、Exception、Check 和 Gate 核心模型。
- 当时尚未包含正式生产 Skill。

# 变更记录

SDLC AI SPEC 是对锁定版本 GitHub Spec Kit 的产品化移植：保留上游核心行为和来源可追溯性，在此基础上提供简体中文 canonical 呈现、Codex / Claude Code / Cursor 三宿主分发、本地 INIT / STATUS，以及确定性的构建、本地化、升级与验证能力。

版本使用 `<锁定上游版本>-sdlc.<本地迭代号>`。发布定位以版本、准确 Git SHA 与 `dist/BUILD.json.build_id` 共同确定。以下时间按对应稳定构建在仓库历史中的最后落地时间记录，时区为 UTC+08:00。

## Unreleased

- 收紧本地化机器契约，增加记录前只读 `precheck`，并补齐 command / presentation / resource 的负向回归。
- 新增仓库维护 Skill `sdlc-maintain-upgrade`，把上游差异审查、detached candidate、本地化恢复和独立 verifier 串成显式维护流程；默认不执行 accept、提交、合并或发布。
- 收口产品版本信息：通用工程文档不再硬编码具体产品版本，新增统一版本工具并将变更记录纳入构建身份。

## 1.0.5-sdlc.1 — 2026-09-15

最后发版时间：2026-09-15 20:29:30 +08:00

- 正式采用“锁定上游版本 + SDLC 本地迭代号”的产品版本规则，并与 Spec Kit 当前锁定版本对齐。
- 完成统一简体中文 canonical 呈现与 Localization Contract v2，保留机器 token、路径、参数、状态与历史英文/双语读取兼容。
- 固化 11 个公共 Skill 的统一分发结构，明确 HUMA、IMPL、CONV 等职责边界和三宿主加载规则。
- 加固可复现构建、准确 SHA CI、升级候选冻结与 macOS 元数据噪声处理，保持 `dist` Runtime 独立于 uv 和上游 CLI。

## 1.0.0-beta — 2026-09-12

最后发版时间：2026-09-12 16:36:17 +08:00

- 第一个可正常运行和测试的版本。
- 产品路线收敛为锁定 Spec Kit 的核心移植，统一为单一 `dist` 包，向 Codex、Claude Code 和 Cursor 提供 11 个公共 Skill。
- 提供中文流程与模板、本地 INIT、只读 STATUS、路径保护和基础工程验证，形成可重复构建的测试基线。

## 1.0.0-alpha — 2026-09-08

最后发版时间：2026-09-08 21:14:17 +08:00

- 汇总 2026-09-08 及之前的早期研发版本。
- 完成 SDLC 研发规范、阶段 Skill、跨 Agent 插件骨架，以及自研 Runtime / Artifact Store 等探索性实现。
- 形成需求、设计、实施、验证、发布等阶段的早期闭环和工程评测基础；该阶段架构不作为当前产品实现依据。

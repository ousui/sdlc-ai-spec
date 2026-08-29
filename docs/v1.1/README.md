---
title: sdlc-ai-spec v1.1 Draft
status: draft
version: "1.1"
---

# sdlc-ai-spec v1.1 Draft

本目录是 sdlc-ai-spec v1.1 Draft Spec Snapshot。它只解除 Artifact Contract 与固定文件系统布局的耦合，保留 v1 Artifact、Reference、Status、Revision State、Check、Gate、Final Confirmation、Phase 和 Domain 业务语义。

当前 Draft 尚未成为当前稳定规范，也尚未供 Plugin 或 Skill 声明正式兼容。只有完成独立 Spec Review 和 Maintainer Finalization 后，才可以将该 Snapshot 标记为 `stable`；此前 Plugin 的稳定 Source of Truth 仍为 v1.0。

## 阅读顺序

1. [Core Spec](core-spec.md)
2. [Artifact Store Spec](artifact-store-spec.md)
3. [Project Context Spec](000-ctx-spec.md)
4. 各 [Phase Spec](#正式-spec)
5. DSN 的 16 份 [Domain Spec](200-dsn-domains/)

## 正式 Spec

本 Snapshot 共包含 25 份正式 Spec：

- 1 份 Core Spec；
- 1 份 Artifact Store Spec；
- 1 份 Project Context Spec；
- 6 份 Phase Spec；
- 16 份 DSN Domain Spec。

| 顺序 | Spec | 作用 |
|---|---|---|
| 基础 | [Core Spec](core-spec.md) | 公共术语、身份、Revision、状态、引用和 Gate |
| 存储 | [Artifact Store Spec](artifact-store-spec.md) | Canonical Revision Payload、Revision Control 与准确解析 |
| 前置 | [Project Context Spec](000-ctx-spec.md) | 项目级共享基线；`000` 表示前置位置，不是 Phase |
| 100 | [Requirement Phase Spec](100-req-spec.md) | 将输入转换为标准 Requirement Artifact |
| 200 | [Design Phase Spec](200-dsn-spec.md) | 形成可实施、可验证的设计及适用 Domain Artifact |
| 300 | [Plan Phase Spec](300-pln-spec.md) | 将交付范围转换为可执行 Work Item |
| 400 | [Implementation Phase Spec](400-imp-spec.md) | 按准确 Binding 实施并形成可追踪 Result |
| 500 | [VFY Phase Spec](500-vfy-spec.md) | 验证与确认产品结果及预期用途 |
| 600 | [Release Phase Spec](600-rls-spec.md) | 发布已验证结果并确认目标侧状态 |

## Contract

- Lifecycle Artifact：`sdlc-ai-spec/artifact/v1`
- Project Context：`sdlc-ai-spec/project-context/v1`
- Final Confirmation Authority：`sdlc-ai-spec/final-confirmation-authority/v1`

正式 Artifact 的合规依据是其 `Evaluation Contract Set` 绑定的准确 Spec Snapshot。Artifact Store Spec 位于 Core Spec 之后，并进入全部 v1.1 Canonical Artifact 的 Evaluation Contract Set。

## 完整性

[`SHA256SUMS`](SHA256SUMS) 只覆盖上述 25 份正式 Spec。README、[规范概览](overview.md)、[AI 与人工协作建议](ai-human-collaboration.md)和 `SHA256SUMS` 自身不进入 Evaluation Contract Set，也不包含在摘要清单中。

从仓库根目录执行：

```bash
cd docs/v1.1
shasum -c SHA256SUMS
```

当前摘要只证明 Draft Review Snapshot 的 25 份正式 Spec 未发生字节漂移，不表示 v1.1 已经 `stable`、已发布或已成为 Plugin 兼容基线。

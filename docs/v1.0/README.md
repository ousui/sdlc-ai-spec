---
title: sdlc-ai-spec v1.0
status: stable
version: "1.0"
---

# sdlc-ai-spec v1.0

sdlc-ai-spec 定义软件研发与变更交付过程中统一的 Artifact、Reference、Evidence、Exception、Check 和 Gate。Spec 只判断结果是否合规，不要求必须由人工、AI 或特定工具完成。

## 规范结构

| 顺序 | Spec | 作用 |
|---|---|---|
| 基础 | [Core Spec](core-spec.md) | 公共术语、身份、Revision、状态、引用和 Gate |
| 前置 | [Project Context Spec](000-ctx-spec.md) | 项目级共享基线；`000` 表示前置位置，不是 Phase |
| 100 | [Requirement Phase Spec](100-req-spec.md) | 将输入转换为标准 Requirement Artifact |
| 200 | [Design Phase Spec](200-dsn-spec.md) | 形成可实施、可验证的设计及适用 Domain Artifact |
| 300 | [Plan Phase Spec](300-pln-spec.md) | 将交付范围转换为可执行 Work Item |
| 400 | [Implementation Phase Spec](400-imp-spec.md) | 按准确 Binding 实施并形成可追踪 Result |
| 500 | [VFY Phase Spec](500-vfy-spec.md) | 验证与确认产品结果及预期用途 |
| 600 | [Release Phase Spec](600-rls-spec.md) | 发布已验证结果并确认目标侧状态 |

DSN 的 16 个 [Domain Spec](200-dsn-domains/) 是 Design Phase Contract 的组成部分。

## Lifecycle

```text
Project Context
      ↓
REQ → DSN → PLN → IMP → VFY → RLS
```

Project Context 不进入 Phase 枚举。每个 Lifecycle Artifact 必须通过 Front Matter `context` 绑定准确、已冻结且可解析的 `CTX-ID@Revision`。

## Contract

- Lifecycle Artifact：`sdlc-ai-spec/artifact/v1`
- Project Context：`sdlc-ai-spec/project-context/v1`
- Final Confirmation Authority：`sdlc-ai-spec/final-confirmation-authority/v1`

正式 Artifact 的合规依据是其 `Evaluation Contract Set` 绑定的准确 Spec Snapshot。本索引、[规范概览](overview.md)和[AI 与人工协作建议](ai-human-collaboration.md)用于阅读，不进入 Evaluation Contract Set。

## 完整性

[`SHA256SUMS`](SHA256SUMS) 固定记录本版本 24 份规范文件的原始字节摘要，不包含本索引、规范概览和协作建议。从仓库根目录执行：

```bash
shasum -c docs/v1.0/SHA256SUMS
```

校验和只证明规范文件未发生字节漂移，不替代 Artifact 的结构校验、Evidence 复核或语义判断。

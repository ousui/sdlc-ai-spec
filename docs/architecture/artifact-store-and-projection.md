---
title: Local SQLite Artifact Store 与 Human Review View 架构决策
status: accepted
decision_date: 2026-08-29
target_spec: docs/v1.1
---

# Local SQLite Artifact Store 与 Human Review View 架构决策

## 1. 边界与四层模型

本文件确定当前 Plugin 的 Artifact Store、Projection 和 Runtime Workspace 架构。它是后续 v1.1 Spec 编制输入，不是正式 Domain Spec，不进入 v1.0 Artifact 的 `Evaluation Contract Set`，也不授权创建 `docs/v1.1/`、SQLite 数据库、Schema、`.sdlc/` 目录或 Skill。

当前架构只包含四层：

| Layer | Responsibility | Authority Boundary |
|---|---|---|
| Domain Spec | 定义 Artifact、ID、Revision、Reference、Status、Evidence、Exception、Check、Gate 与 Final Confirmation | 领域语义的 Source of Truth；不定义数据库物理结构 |
| Local SQLite Store | 在单个项目内保存并管理 Canonical Revision | 当前 Plugin 唯一的 Canonical Artifact Store 与 Artifact Authority |
| Projection | 从准确 Canonical Revision 生成 Human Review View | 只提供人工阅读和候选修改入口，不是正式领域 Artifact 或 Authority |
| Runtime Workspace | 保存本地 Store、Review View 与临时材料 | 只有 SQLite 中的 Canonical Revision 具有 Artifact Authority；`reviews/` 与 `tmp/` 不具有 Authority |

当前 Plugin 不提供 Store 选择，也不需要 Store 或 Provider 配置文件。

## 2. Local SQLite 是唯一 Authority

当前 Plugin 在一个项目内只支持一个 Canonical Artifact Store，固定位置为：

```text
<project-root>/.sdlc/store.sqlite3
```

项目根目录按以下顺序解析：

1. 使用用户显式指定的 Project Root；
2. 否则使用宿主提供的唯一 Workspace Root；
3. 无法唯一确定时停止；
4. 不扫描、猜测或选择看似合适的目录。

正式 Artifact 的唯一 Authority 是 SQLite 中保存的 Canonical Revision。Review 文件、临时文件、Preview、导出文件和 Validator 输出都不能替代该 Authority。

必须保持以下不变量：

- 一个项目只有一个本地 Canonical Store；
- 同一 Artifact 同时最多存在一个 `open` Revision；
- Revision 单调增加且不复用；
- `frozen` Revision 不可修改；
- SQLite 不可用、损坏或事务失败时 fail closed；
- 不静默降级到文件、系统临时目录或 `.sdlc/tmp/`。

## 3. Canonical Markdown/YAML Blob

SQLite 至少保存：

- Artifact ID；
- Artifact Type / Phase；
- Revision；
- Revision State；
- Artifact Status；
- Base Revision；
- 完整 Canonical Markdown/YAML Blob；
- Canonical Blob SHA-256；
- 必要时间和失败原因。

完整 Canonical Markdown/YAML Blob 保持既有 Artifact 字段、章节、顺序和人工可读性。Canonical Blob SHA-256 用于验证准确 Revision 的内容完整性。

数据库物理表名、列名、索引、PRAGMA、WAL 和 Migration 属于后续实现，不进入 v1.1 Domain Spec。首版不把每个 Requirement、Acceptance Criteria、Evidence 或 Gate Check 全部规范化为关系表；查询或索引结构不得成为并行 Authority。

## 4. 最小事务与 Reference 语义

后续 `artifact-store-spec.md` 只定义当前 SQLite 实现真正需要的逻辑操作：

- `initialize`；
- `allocate artifact`；
- `allocate revision`；
- `read revision`；
- `write open revision`；
- `freeze revision`；
- `abandon revision`；
- `resolve exact reference`；
- `verify digest`。

所有写操作必须在 SQLite transaction 中完成。分配、写入、冻结和放弃不能留下可被误认为成功的部分状态；失败必须返回明确结果并保持 fail closed。

现有准确 Reference 语法保持不变：

```text
<Artifact-ID>@<Revision>
<Artifact-ID>@<Revision>#<Item-ID>
<Artifact-ID>@<Revision>/<Member-ID>
```

`resolve exact reference` 只能解析指定 Revision，并验证其身份、状态和摘要。不得使用 `latest`、`current`、目录扫描、内容相似度或查询排序作为 fallback。

## 5. Human Review View

Human Review View 是 Plugin Projection，不是正式领域 Artifact。默认位置为：

```text
<project-root>/.sdlc/reviews/
```

必须遵守：

- 从准确 Canonical Revision 生成；
- 记录 Source Reference 和 Source Digest；
- 可以隐藏不利于人工阅读的控制字段和可见 ID，但必须保持隐藏映射；
- 导入前重新检查 Source Digest；
- View stale 或隐藏映射缺失、重复、损坏时停止，不猜测回写目标；
- 导入只修改现有 `open` Candidate Revision，或在 SQLite 中创建新的 `open` Candidate Revision；
- Frozen Source 的内容修改必须以其为 Base Revision 创建新 Revision，不得修改原 Revision；
- 编辑、保存和导入不等于 Final Confirmation；
- 下游 Skill 不得把 Human Review View 当作 Context、Input 或 Artifact Authority。

Projection 的具体文件格式、JSON Schema、编辑器适配和样式留到后续 Skill 实现阶段决定，不新增正式 `artifact-projection-spec.md`。

## 6. Candidate Material

系统临时目录或 `.sdlc/tmp/` 只用于保存：

- 中间分析；
- Preview；
- Validator 临时输出；
- Eval 临时文件；
- 尚未形成正式 Artifact 的 Candidate Material。

这些内容不能拥有正式 Artifact Authority、可供下游消费的 Artifact Reference、Frozen Revision、Gate 或 Final Confirmation。Candidate Material 在正式分配 Artifact ID 或被下游引用前，必须写入 SQLite 并遵守 Canonical Revision Contract。

## 7. Runtime Workspace 与当前非目标

本地运行目录固定为：

```text
.sdlc/
├── .gitignore
├── store.sqlite3
├── reviews/
└── tmp/
```

`.sdlc/.gitignore` 初始内容固定为：

```gitignore
*
```

初始化不得修改目标项目根级 `.gitignore`。`.sdlc/**` 默认不进入 VCS；如果 `.sdlc` 已包含 tracked content，Plugin 不得自动改变 Git Index。本轮只确定设计，不创建实际 `.sdlc/` 目录。

当前明确不设计或实现多存储抽象、存储选择配置、临时或文件系统 Canonical Store、Git Canonical Store、远程 Store、分布式协调、跨存储寻址、Store 切换或迁移、保留策略矩阵、SQLite Schema、Store 模块、Projection 或 Skill。

未来实现可以在保持 Artifact Store Contract 的前提下增加其他存储方式；当前版本不定义、不实现、也不声明兼容。

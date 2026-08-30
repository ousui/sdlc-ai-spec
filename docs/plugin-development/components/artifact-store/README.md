# Shared Local SQLite ArtifactStore

## 定位

`ArtifactStore` 是 Plugin 级共享基础组件，不是 Skill。它把
`docs/v1.1/artifact-store-spec.md` 已登记的九个逻辑操作落实为一个稳定的
Python facade，并把当前物理边界固定为：

```text
<project-root>/.sdlc/store.sqlite3
```

```text
Phase Skill
    ↓ 构造 Canonical Payload / 执行领域验证
ArtifactStore API
    ↓ 事务、Revision、Member、Digest、Read-only
.sdlc/store.sqlite3
```

唯一共享实现位于 `packages/sdlc_artifact_store/`，共享 CLI 位于
`scripts/sdlc_artifact_store.py`。任何 Skill 都不得复制该模块、创建私有
Schema、直接执行 SQL，或通过 `../` 调用兄弟 Skill 私有脚本。

`sdlc-project-context` 是第一个真实使用者。REQ、DSN、PLN、IMP、VFY、RLS
是稳定 v1.1 Store Contract 已明确要求的后续使用者。因此这是由现有 Contract
和多个真实 Phase 依赖形成的共享边界，不是为不确定未来建立的通用 Provider 抽象。

当前不实现 Human Review View、Projection Import、Candidate Material 工作流、
多 Provider、远程 Store、自动 Migration 或文件系统 Canonical Store fallback。

## Python API

共享 facade 的方法名与 Artifact Store Spec 一一对应：

- `initialize`
- `allocate_artifact`
- `allocate_revision`
- `read_revision`
- `write_open_revision`
- `freeze_revision`
- `abandon_revision`
- `resolve_exact_reference`
- `verify_digest`

另外提供两个明确入口：

- `ArtifactStore.open_read_write(project_root)`：供 `create / revise` 使用；调用方仍需显式调用 `initialize()`。
- `ArtifactStore.open_read_only(project_root)`：供 `check` 使用；不调用 `initialize`，不创建或修复任何持久化状态。

最小创建流程：

```python
from datetime import datetime, timezone
from pathlib import Path

from sdlc_artifact_store import (
    ArtifactStore,
    CanonicalManifest,
    CanonicalRevisionPayload,
    compute_sha256,
)

project_root = Path("/absolute/project/root")
store = ArtifactStore.open_read_write(project_root)
store.initialize()

allocated = store.allocate_artifact(
    "CTX",
    now=datetime(2026, 8, 30, 9, 10, 11, tzinfo=timezone.utc),
)
control = store.allocate_revision(allocated.artifact_id)
primary = b"---\ncontract: sdlc-ai-spec/project-context/v1\n---\n"
payload = CanonicalRevisionPayload(
    artifact_id=allocated.artifact_id,
    artifact_type="CTX",
    revision=control.revision,
    artifact_status="draft",
    primary_blob=primary,
    primary_media_type="text/markdown",
    primary_sha256=compute_sha256(primary),
    members=(),
    manifest=CanonicalManifest(
        raw_bytes=b'{"local_members":[]}',
        media_type="application/json",
        local_members=(),
    ),
)
stored = store.write_open_revision(payload, expected_generation=0)
```

`expected_generation` 是 SQLite 实现内部的乐观并发控制值，不是 Artifact 字段、
Revision State 或领域摘要。第一次物化固定使用 `0`；同一 open Revision 重写时，
调用方必须使用最近一次 `read_revision` 返回的 `control.generation`。旧代次会明确
返回 `CONFLICT`，不会发生 last-write-wins。

严格只读检查：

```python
reader = ArtifactStore.open_read_only(project_root)
stored = reader.read_revision("CTX-20260830091011-01", 1)
digest = reader.verify_digest("CTX-20260830091011-01", 1)
```

只读入口使用 SQLite `mode=ro` URI，并启用 `query_only`。`.sdlc/`、
数据库、Schema Version 1 或必需表/列/索引不存在时明确失败；不会创建目录、数据库、
Schema、journal、WAL、SHM、cache、log 或旁车文件。

## Canonical Payload

Python Payload 输入由以下对象组成：

- `CanonicalRevisionPayload`：Artifact ID / Type、Revision、Artifact Status、primary raw bytes、Media Type、SHA-256、Member 集合和 Manifest；
- `CanonicalMember`：稳定 Member ID、Canonical Member Name、Media Type、raw bytes 和 SHA-256；
- `CanonicalManifest`：Canonical Manifest raw bytes、Media Type，以及 Manifest 中 locally owned Member 的闭包投影；
- `ManifestMember`：Manifest 声明的本地 Member ID、Canonical Name、Media Type 和 SHA-256；
- `RevisionControlRecord`：Revision State、Base Revision、Allocated/Frozen At、Abandon Reason、是否已物化和并发代次；
- `StoredRevision`：准确 Control Record、完整 Payload 和仅供 verifier protocol 使用的临时绑定值。

Manifest raw bytes 继续保留既有外部不可变 Reference、摘要和访问边界。外部对象不被
下载或复制为本地 Member。`local_members` 只投影当前 Store 实际拥有的成员，以便
Store 确定性验证 Manifest-Member closure；领域 validator 仍负责验证 Canonical
Manifest 本身是否符合当前 Phase / Domain Contract。

raw bytes 的摘要统一写作 `sha256:<64 位小写十六进制>`。Store 同时检查 primary、
每个本地 Member、唯一 Member ID、唯一 Canonical Name、Media Type 和声明/实际集合。
没有新增 Revision Package Digest；`verification_binding` 只在一次 verifier 调用中临时
绑定当前 Payload，不持久化，也不是领域字段或正式摘要。

## Domain verifier 边界

`ArtifactStore` 不判断 Project Boundary、业务事实、Basis、Exception、Gate 或 Final
Confirmation，也不自行派生 `ready`。`freeze_revision` 与权威
`resolve_exact_reference` 必须收到调用方提供的 `DomainVerifier`：

```python
from sdlc_artifact_store import DomainVerification

class CtxVerifier:
    def verify(self, reference, revision):
        # 后续 CTX 实现负责 Core + Artifact Store + CTX Check、Gate 和 Final Confirmation。
        approved = run_ctx_domain_checks(reference, revision.payload)
        return DomainVerification(
            reference=reference,
            payload_binding=revision.verification_binding,
            approved=approved,
            message="CTX validation failed" if not approved else "",
        )
```

Store 只接受与准确 Reference、当前 Payload 绑定且 `approved=True` 的结果。缺失、拒绝、
Reference 不一致或 stale 结果均 fail closed。当前组件没有 CTX 专属 verifier；它属于
后续 `sdlc-project-context implement`。

## SQLite Schema Version 1

Schema 是实现细节，不是第二份领域 Contract：

| Table / Index | 用途 |
|---|---|
| `schema_metadata` | 唯一 Schema Version 标记，当前固定为 `1` |
| `artifacts` | Artifact Lineage、Type、分配时间及最小 IMP 外部 Claim 绑定 |
| `revisions` | Revision Control Record、物化标记和乐观并发代次 |
| `payloads` | primary raw bytes、Media Type、摘要、Artifact Status 与 Manifest raw bytes |
| `members` | locally owned Member raw bytes、稳定身份、元数据和摘要 |
| `manifest_members` | Manifest 中本地 Member 闭包投影 |
| `one_open_revision_per_artifact` | 数据库层保证一个 Artifact 最多一个 open Revision |
| `one_claim_attempt_reservation` | 防止同一外部 IMP Claim Attempt 采用不同 Revision |

首次 `initialize` 创建 Schema；重复执行只验证。版本不匹配、表/列/索引缺失、
`quick_check` 或 `foreign_key_check` 失败时明确停止，不猜测或自动迁移。

## CLI

CLI 不依赖当前工作目录，必须显式指定绝对 `--project-root`：

```bash
python3 /path/to/plugin/scripts/sdlc_artifact_store.py \
  --project-root /absolute/project/root \
  --operation initialize
```

带参数操作从文件读取一个 JSON 对象，或以 `--input -` 从 stdin 读取：

```json
{
  "artifact_type": "CTX",
  "now": "2026-08-30T09:10:11+00:00"
}
```

```bash
python3 /path/to/plugin/scripts/sdlc_artifact_store.py \
  --project-root /absolute/project/root \
  --operation allocate_artifact \
  --input /tmp/allocate-artifact.json
```

`write_open_revision` 的 JSON Payload 使用 base64 承载 raw bytes：

```json
{
  "expected_generation": 0,
  "payload": {
    "artifact_id": "CTX-20260830091011-01",
    "artifact_type": "CTX",
    "revision": 1,
    "artifact_status": "draft",
    "primary_blob_base64": "LS0tCg==",
    "primary_media_type": "text/markdown",
    "primary_sha256": "sha256:<64 lowercase hex>",
    "members": [],
    "manifest": {
      "raw_bytes_base64": "eyJsb2NhbF9tZW1iZXJzIjpbXX0=",
      "media_type": "application/json",
      "local_members": []
    }
  }
}
```

每次只向 stdout 输出一个 JSON 结果，不输出 Payload raw bytes：

```json
{"ok":true,"operation":"initialize","result":{"schema_version":1,"store":"/absolute/project/root/.sdlc/store.sqlite3"}}
```

| Operation | 主要输出 |
|---|---|
| `initialize` | `schema_version`, `store` |
| `allocate_artifact` | `artifact_id`, `artifact_type`, `created_at` |
| `allocate_revision` | 完整 Revision Control Record 元数据 |
| `read_revision` | Control Record、Payload 身份/状态/摘要和 Member 元数据；不回显 raw bytes |
| `write_open_revision` | 读回后的 Control Record 和安全 Payload 摘要 |
| `freeze_revision` | CLI 固定返回 `VERIFIER_REQUIRED`；权威冻结必须由 Phase Skill 通过 Python API 注入 verifier |
| `abandon_revision` | 终态 Control Record 和准确原因 |
| `resolve_exact_reference` | CLI 固定返回 `VERIFIER_REQUIRED`；权威解析必须由 Phase Skill 注入 verifier |
| `verify_digest` | primary、Member 数量和 closure 验证结果 |

成功退出码为 `0`。失败输出包含稳定 `error.code` 和可读 `message`：

| Exit | Stable error code | 含义 |
|---:|---|---|
| `2` | `INVALID_INPUT` | JSON、字段、时间、ID、Revision、Media Type 或摘要格式无效 |
| `2` | `REFERENCE_ERROR` | 不是准确数字 Revision Reference，或目标 Item / Member 不存在 |
| `3` | `STORE_NOT_FOUND` | `.sdlc/` 或 `store.sqlite3` 不存在 |
| `3` | `NOT_FOUND` | Artifact 或指定 Revision 不存在 |
| `3` | `SCHEMA_ERROR` | Schema、表、列、索引或数据库完整性不符合 Version 1 |
| `3` | `SCHEMA_VERSION_MISMATCH` | Schema Version 不是 `1` |
| `4` | `READ_ONLY` | 对严格只读 facade 调用了写操作 |
| `4` | `TRACKED_RUNTIME_CONTENT` | `.sdlc` 已含 Git-tracked 内容，需要用户处理 |
| `4` | `CONFLICT` | ID、Claim、并发代次或单 open Revision 冲突 |
| `4` | `CONTROL_RESERVATION` | 目标只有 Control Record，尚无完整 Payload |
| `4` | `INVALID_STATE` | 当前 open / frozen / abandoned 或 Artifact Status 不允许操作 |
| `5` | `INTEGRITY_ERROR` | raw bytes、摘要、身份或 Manifest-Member closure 不一致 |
| `5` | `VERIFIER_REQUIRED` | 权威 freeze / resolve 缺少领域 verifier |
| `5` | `VERIFICATION_FAILED` | 领域 verifier 明确拒绝当前 Revision |
| `5` | `STALE_VERIFICATION` | verifier 绑定的 Reference 或 Payload 已不匹配 |
| `10` | `DATABASE_ERROR` | SQLite 打开、Schema 校验或事务执行故障 |
| `11` | `UNEXPECTED_ERROR` | 未预期的内部协议故障；不回显 traceback 或敏感细节 |

正常失败不会把 traceback、Payload raw bytes或完整敏感内容写入 JSON 协议输出。

## Skill 集成规则

安装后的 Skill 必须通过宿主提供的 Plugin 根定位共享 `packages/` 与 `scripts/`，不得依赖
作者本机绝对路径或当前 CWD。Python 运行环境应把 Plugin 的 `packages/` 加入模块搜索路径；
CLI 则直接执行 Plugin 根下的共享脚本。Skill 不读取或复制 SQLite Schema，也不执行 SQL。

Phase Skill 继续负责：

- 选择准确 Project Root、Canonical Store 和目标 Lineage / Revision；
- 构造完整领域 Canonical Payload 与 Manifest；
- 验证 Core、Phase / CTX、Domain Check、Gate、Final Confirmation 和允许状态组合；
- 为 `freeze_revision` / `resolve_exact_reference` 提供与当前 Payload 绑定的 verifier；
- 决定缺失事实、`waiting_input`、Exception 和人工授权流程。

ArtifactStore 只负责：

- 本地事务和 rollback；
- Artifact / Revision 分配与准确外部 IMP Reservation 采用；
- Control Reservation 与 materialized Payload 分离；
- Member、摘要和 Manifest-Member closure；
- frozen 不可变、abandoned 历史保留、exact Reference 无 fallback；
- 严格只读打开和明确失败。

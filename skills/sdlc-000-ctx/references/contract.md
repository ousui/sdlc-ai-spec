# CTX Runtime Contract

本文件是安装后 Runtime 使用的自包含 CTX 输入与领域规则，不要求读取开发仓库文档。

## Invocation

公共 Envelope 使用 `sdlc-ai-spec/runtime-invocation/v1`。`inputs.context`、
`inputs.evidence` 与 `inputs.supporting_members` 是三个同级字段：

```json
{
  "context": {
    "summary": "精炼项目摘要",
    "project_identity": {
      "project_name": {"value": "...", "basis": "confirmed", "basis_references": ["EVD-001"]},
      "purpose": {"value": "...", "basis": "confirmed", "basis_references": ["EVD-001"]},
      "boundary": {"value": "...", "basis": "confirmed", "basis_references": ["EVD-001"]},
      "primary_resource_reference": {"value": "RSC-001", "basis": "observed", "basis_references": ["EVD-002"]},
      "authoritative_references": {"value": "None", "basis": "confirmed", "basis_references": ["EVD-001"]}
    },
    "resources": [],
    "technologies": [],
    "engineering_entries": [],
    "components": [],
    "rules": [],
    "environments": [],
    "constraints": [],
    "exceptions": []
  },
  "evidence": [],
  "supporting_members": []
}
```

各正式事实使用 `value / basis / basis_references`；`basis` 只允许 `observed / confirmed / referenced`。集合为空必须显式写为：

```json
{"none": {"basis": "confirmed", "basis_references": ["EVD-001"]}}
```

不得用空数组表达“已确认不存在”；空数组或缺失字段表示尚未取得事实，并形成 Open Item。

行字段固定使用 snake_case：

- `resources`: `id,type,name,role,locator,baseline_reference,basis,basis_references`
- `technologies`: `id,category,name,version_or_constraint,purpose,basis,basis_references`
- `engineering_entries`: `id,purpose,command_or_entry_point,working_scope,preconditions,basis,basis_references`
- `components`: `id,name,type,resource_reference,responsibility,entry_point,depends_on,authority_reference,basis,basis_references`
- `rules`: `id,category,rule_summary,scope,authority_reference,basis,basis_references`
- `environments`: `id,environment,purpose,accessibility,data_and_network_boundary,basis,basis_references`
- `constraints`: `id,constraint,scope,impact,required_handling,authority_reference,basis,basis_references`

Evidence 行固定使用 `id,type,supports_references,source_or_producer,reference,integrity_or_digest,produced_at,sensitivity_or_access`。Supporting Member 使用 `member_id,canonical_name,media_type,purpose`，并且只允许一个 `content` UTF-8 字符串或 `content_base64`；可选 `sha256` 必须与原始字节一致。不得把 Evidence 或 Supporting Member 嵌入 `inputs.context`。

## Confirmations

`confirmations` 中的决定互不替代：

- 写入授权：`{"type":"write","approved":true}`。
- Boundary 确认：`{"type":"project_boundary","value":"...","authority_reference":"EVD-001"}`；值必须与 `project_identity.boundary` 完全一致。
- 最终确认：`type=final_confirmation`，包含 `result,mode,confirmer,role,authority_reference,accepted_exception_references,confirmed_at,control_input_digest,evaluation_contract_set,check_set_result_digest`。委托确认还需 `reviewed_executor`，且 Reviewer 与被复核者不同。
- Exception 接受：最终确认的 `accepted_exception_references` 必须与全部 `active/carried` Exception ID 完全一致；存在未关闭 Exception 时只能使用真实人工确认。

`Authority Reference` 固定为项目相对 `path@sha256:<64 lowercase hex>`；Runtime 验证文件存在、未越出 Project Root 且摘要一致。最终确认必须绑定当前准确 Revision、Control Input Digest、Evaluation Contract Set 与 Check Set Result Digest。`delegated` Authority 必须严格使用 `sdlc-ai-spec/final-confirmation-authority/v1` 固定 Front Matter 和单行表格，包含合法 RFC 3339 `decided_at`、独立的 `Delegation Basis` 授权记录、固定 `Independence` / `Excluded Authority` 集合，以及与 Final Confirmation 完全一致的身份和摘要绑定。

## Boundary Key

只对已确认 Boundary 执行：Unicode NFC → CRLF/CR 转 LF → 删除整体首尾空白 → UTF-8 SHA-256，结果为 `sha256:<64 lowercase hex>`。Project Root、仓库名或目录路径不得替代 Boundary。

## Canonical CTX

Front Matter 固定为 `contract,id,revision,status`；Contract 为 `sdlc-ai-spec/project-context/v1`。固定正文依次包含 Summary、Project Identity、Resource Registry、Technology and Engineering Baseline、Project Topology、Project Rules、Environment and Constraints、Open Items、Evidence、Refresh Summary、Supporting Artifact Manifest、Exceptions 和 Gate。固定 ID 前缀、表头、空表示和排序由模板与 Runtime Validator 共同执行。

CTX 的 Evaluation Contract Set 固定绑定同一 v1.1 快照的 Core、Artifact Store 与 CTX 构建来源。三项构建来源及摘要已锁入 `source-lock.json`；Runtime 通过打包常量形成准确 Spec Reference，不在运行时读取来源文件。

## 状态与错误

- 有确定性领域失败：Gate=`fail`、Artifact Status=`failed`。
- 无失败但存在 Open Item：Gate=`pending`、Artifact Status=`waiting_input`。
- 内容尚未最终确认：Gate=`pending`、Artifact Status=`waiting_input`。
- 全部 Check 与最终确认通过：Gate=`pass`、Status=`ready`。
- 有真实人工接受的有效 Exception：Gate=`pass_with_exception`、Status=`ready_with_exception`。

只有最后两种状态允许 freeze 并返回 Authority Reference。错误码稳定映射为 `INVALID_ENVELOPE`、`TARGET_AMBIGUOUS`、`WRITE_AUTHORIZATION_REQUIRED`、`ARTIFACT_REFERENCE_REQUIRED`、`ARTIFACT_REFERENCE_INVALID`、`PROJECT_BOUNDARY_CONFIRMATION_REQUIRED`、`CTX_LINEAGE_EXISTS`、`CONTROL_RESERVATION` 及共享 ArtifactStore 错误码。

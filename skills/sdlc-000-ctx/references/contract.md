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

## 精确确认准备

当需要独立复核时，create/revise 的标准 Invocation 可显式设置布尔 `options.prepare_confirmation=true`。真实项目输入完整且仅缺少最终确认时，Runtime 持久化未冻结 draft，关闭除 CORE-G-009 外的适用检查，Result 仍为 action_required。确认等待保留在 Result，不污染用于独立摘要复核的业务正文。真实 Open Items、错误和 Exception 不隐藏。

先写入并通过只读 Store 读回该准确 Revision；Reviewer 独立计算当前 Control Input Digest、Evaluation Contract Set 与 Check Set Result Digest。再以相同 context/evidence/refresh 输入和合法当前 Confirmation 执行 revise；缺记录、摘要不符、拒绝确认均不能冻结。原有未设置此选项的行为不变。

## 标准字段、引用和输入整理

完整字段/枚举/已支持别名见 [输入字段速查](input-reference.md)。这是 Runtime 当前常量的随包投影，不需要读取 Python 或开发文档。

集合行包含速查表列出的全部字段；标量内容是字符串，`basis_references` 为非空字符串数组。ID 使用对应前缀加三位数字，例如 `RSC-001`、`CMP-001`、`EVD-001`，当前集合内唯一并由 Agent 维护稳定映射，不交给用户填写。描述性枚举接受已支持标准值的大小写/首尾空白整理；工程用途还接受速查表的明确中文及常见错拼别名，返回 `INPUT_NORMALIZED` warning。`source_worktree` 不是一个资源类型别名：先核实仓库/模块等真实角色再选标准类型。

`components.resource_reference` 指向当前 CTX 的 `RSC-NNN`。`components.depends_on` 为同 CTX 的组件 ID 数组、逗号分隔 ID 字符串，或显式字符串 `None`；不是依赖说明文字。未知 ID 不自动创建或改写；因主资源非法而无法解析的引用也不表示产品组件实际失败。自然语言依赖描述可由 Agent 结合已确认组件映射整理，无法唯一映射则保留缺口。

`None` 仅表达已确认不存在，`N/A` 仅表达该字段依语义不适用；缺失、null、空数组均不等同这两者。Project Identity 中 project_name/purpose/boundary/primary_resource_reference 不可用占位值；authority 尚未收集不能伪造“无”。集合不存在按上文 `none` 对象声明，仍需真实依据。

## Evidence 与会话内容留存

当前插件的 Evidence `integrity_or_digest` 必须为 `sha256:<64 lowercase hex>`，这是插件输入表示约束，不表示 Core 禁止其他完整性算法。`produced_at` 为带时区的 RFC 3339。`supports_references` 指向被证明的 Check/事实；`source_or_producer` 和 `reference` 说明来源与定位，不用“不适用”代替摘要。

会话证据只留存获准且必要的最小记录：准确 task/turn 来源、原始决定含义、对象与范围、记录时间。确定 UTF-8 和换行字节后计算 `hashlib.sha256(content.encode('utf-8')).hexdigest()`，以 Supporting Member 的 `content` 随请求传入并使用实际摘要；二进制内容用 `content_base64`。不要凭空生成摘要，不复制 Secret 或整段无关会话。

Evidence 引用已提交 Supporting Member 的 `member_id`、`canonical_name` 或 `canonical_name@sha256:...` 时，Evidence 摘要必须与实际 Member 字节相符；引用自身携带的摘要也必须一致。外部引用的格式通过不表示内容已读取或可解析；来源/访问缺口如实保留。摘要只证明完整性，不证明用户身份或授权，Boundary 确认不能替代最终确认。

## 资源观察基线

新 Git 观察使用完整 commit，并记录定位方式；支持完整 40/64 位对象 ID、`git:<full-id>`、`git:<locator>@<full-id>`。既有 `vcs:<locator>@<hex-revision>` 泛 VCS 格式（7–64 位）及 `vcs:git:<full-id>` 保持兼容，不冒称所有 VCS 都是 Git。

非 Git 文档/内容快照可用 `sha256:<digest>` 或 `<locator>@sha256:<digest>`。Git/VCS 基线可附 `+sha256:<digest>` 绑定另存的 dirty/untracked 观察清单。观察涉及未提交内容时必须收集对应路径/字节依据；HEAD 不能掩盖工作树差异。`HEAD/main/latest`、观察时间和 workspace observation 文字不是不可变内容身份。

输入表示检查不会自动联网解析对象、遍历全仓或验证未提供的内容。Agent 负责如实采集可访问对象与观察范围，无法确认就登记缺口。该规则用于新请求；历史 frozen 内容仍只读、不重写或自动迁移。

## 预览、错误与可执行示例

新请求结构错误：`ok=false/status=failed/artifact=null`，尚未评估的 Gate 为 `pending/failed_checks=[]`；领域确有拒绝事实才标对应 Check fail。`create` dry-run 保留 Builder 错误，和真实输入拒绝使用相同分类，始终零 Store、零 ID 分配。非法 revise 保留原 Revision，结果 Gate 描述本次未评估，不改变历史检查记录。

[完整无写入示例](input-example.json) 是文档 Fixture，不是用户项目事实或批准。Agent 只需把 `project_root` 占位符物化为测试目录绝对路径，再从 `scripts/runtime.py` 的标准 JSON 入口提交。示例保留真实内容字节和实际摘要，`options.dry_run=true`，无写入和最终确认授权；预期 `ok=true`、Artifact null、Gate pending，不能用于宣布实际项目 ready。

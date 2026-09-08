# sdlc-100-req Runtime Contract

## 输入

`inputs.requirement`：

- `title`、`summary`；
- `sources[]`：`type/content/evidence_reference`；
- `goals[]`：`problem/outcome/success_condition`；
- `in_scope[]`、`out_of_scope[]`；
- `affected_parties[]`；
- `requirements[]`：`type/source_references/statement`；
- `acceptance_criteria[]`：`requirement_references/condition/expected_result`；
- `dependencies[]`；
- `profile`：`full/lite/hotfix`；
- `lifecycle_applicability[]`：DSN、PLN、IMP、VFY、RLS；
- `open_items[]`、`evidence[]`、`supporting_members[]`、`exceptions[]`。

Runtime 生成稳定 `SRC/GOAL/AP/R/AC/DEP/OPI/EVD/SUP/EX` ID。调用方不得伪造 Gate、Artifact Status 或 Revision State。

## 状态

- 已知无效事实或 Check fail：`failed`；
- 无 fail 且存在 open OPI：`waiting_input`；
- 无缺口但 Final Confirmation 未完成：`draft`；
- 全部通过且无未关闭 Exception：`ready`；
- 全部通过且存在有效 Exception：`ready_with_exception`。

只有 `ready/ready_with_exception` 且 Final Confirmation 与当前摘要绑定时可冻结。

## create / revise / check

- create：分配新 REQ ID 和 Revision 1；
- revise open：要求准确 Reference 和 generation，原地重写；
- revise frozen：基于准确 Revision 创建新最大 Revision；
- check：只读指定 Revision，不 fallback。

## Final Confirmation

`inputs.final_confirmation`：

```json
{
  "mode": "human",
  "confirmer": "stable-identity-token",
  "role": "Product Owner",
  "authority_reference": ".sdlc/authority/req-approval.md@sha256:<digest>",
  "confirmed_at": "RFC3339"
}
```

`human` 必须引用项目内已存在文件和匹配摘要。`delegated` 还必须满足共享 Core 的独立 Reviewer Authority 记录；不能批准 Exception。

## 失败关闭

- 不接受 `latest/current`；
- 不读取兄弟 Skill；
- 不联网或安装依赖；
- 不在 check 创建文件；
- 不把 Control Input 接收解释为问题已解决；
- 不把 Artifact ready 解释为产品已实现或已验证。

## 字段补充与标准枚举

标准值见 [输入字段速查](input-reference.md)。`sources[].type` 不是任意来源名称，`requirements[].type` 不是需求正文；自然语言正文放在 content/statement 中，允许中文。缺失真实事实仍形成 Open Item，非法枚举/数组类型在 Store 分配前拒绝并返回具体字段路径，dry-run 同样不能隐藏错误。

| inputs.requirement 字段 | 实际结构 |
|---|---|
| sources | 对象数组：type、content、evidence_reference；无独立证据时该引用可为 N/A，不能冒充已验证 Evidence |
| goals | 对象数组：problem、outcome、success_condition |
| in_scope / out_of_scope | 文本数组；不得以格式归一化扩大范围 |
| affected_parties | 对象数组：party、impact |
| requirements | 对象数组：type、source_references（SRC/GOAL 等已生成 ID 集合）、statement |
| acceptance_criteria | 对象数组：requirement_references（R-NNN 集合）、condition、expected_result |
| dependencies | 对象数组：dependency、required_state、current_state、state_check_reference；空数组表示无已列依赖 |
| profile / profile_basis | 标准 Profile 与选择依据文本 |
| lifecycle_applicability | 有序对象数组：phase、disposition、host、basis；embedded 需要合法宿主，VFY 固定义务不能删除 |
| evidence | 对象数组：type、supports_references、source、reference、integrity、produced_at、sensitivity；注意这里不是 CTX 的字段名 |
| supporting_members | 对象数组：canonical_name、media_type、content 字符串；encoding=utf-8（默认）或 base64，Runtime 计算字节摘要；可选 member_id。与 CTX 的 content_base64 格式不同，不传该键或自报 sha256 |
| exceptions | 对象数组：state、origin、scope、reason、risk、control、approval、revisit、downstream、resolution；不能自动批准风险 |
| open_items | 对象数组：needed、expected_source、blocked_references、state、resolution；缺口不自动补为无 |

外层 `inputs.context_reference` 为准确冻结 CTX；`inputs.control_inputs` 为准确 Control 引用数组；`inputs.final_confirmation` 与 requirement 同级，必须为对象；`inputs.expected_generation` 为修订的实际 generation。标准写入确认仍位于共享 Envelope 的 `confirmations`，不能用业务文本或字符串 true 代替。

数组位置决定 Runtime 生成的 SRC/GOAL/AP/R/AC/DEP/EVD/SUP/EX 编号，引用必须与当前排序闭合。示例：`sources=[{"type":"text","content":"需要导出当前筛选结果","evidence_reference":"N/A"}]`，对应需求可引用 `SRC-001`。这只是输入片段，实际 CTX、业务缺口及最终确认仍按正式来源处理。

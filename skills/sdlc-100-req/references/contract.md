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

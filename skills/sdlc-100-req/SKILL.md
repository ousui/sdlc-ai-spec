---
name: sdlc-100-req
description: 显式创建、修订或严格只读检查需求 REQ；裸调用会自动解析项目、CTX、操作和标准写入。
disable-model-invocation: true
---

# SDLC 100 Requirement

本 Skill 将需求采集、参数默认值、Source/Evidence 组织、内部 Invocation 和 Runtime 调用封装为统一 SOP。用户无需编写长提示词或手工填写 Artifact JSON、Evidence ID、Confirmation、Digest 或 Gate 表。

## 快速使用

```text
/sdlc-100-req
/sdlc-100-req create -- 让已授权用户导出当前筛选结果
/sdlc-100-req check -r REQ-...@1
/sdlc-100-req -h
```

完整命令、版本和示例由 `references/interface.json` 定义。调用后先使用共享参数解析器归一化命令：

```text
python3 <plugin-root>/scripts/sdlc_skill_interface.py \
  --spec <plugin-root>/skills/sdlc-100-req/references/interface.json \
  -- <invocation-tail>
```

支持子命令、GNU 长参数、短参数和兼容别名。`help / version / commands / examples` 只展示预定义信息，不扫描项目、不调用 Runtime、不写入。

## 默认行为

公共默认值：

```text
command=auto
project_root=auto
artifact_reference=auto
decision_policy=user
write_policy=auto
dry_run=false
output=summary
```

`command=auto` 使用确定性规则：

1. 当前唯一项目存在准确 frozen CTX，但没有 REQ：`create`；
2. 用户当前请求明确提出新需求，且不存在同一需求 Lineage：`create`；
3. 唯一 materialized open REQ：`revise`；
4. 唯一 frozen REQ 且请求没有变更意图：`check`；
5. 唯一 frozen REQ 且请求明确变更：`revise`；
6. 多个 CTX、REQ、Revision 或合法操作：请求用户选择，不按标题相似度、`latest` 或 `current` 猜测。

`project_root=auto` 只接受唯一现存工作区。`artifact_reference=auto` 只在候选准确且唯一时使用；否则展示准确 Reference 列表。

## 需求采集与事实处理

在提交 Runtime 前，从当前用户请求、会话中已确认事实、准确 frozen CTX、获授权 VFY/RLS Control Input 及最小项目证据构造候选 REQ：

- 保留原始需求语义和来源；
- 可证明内容登记为 observed / referenced；
- 业务范围、优先级、取舍和验收语义存在多种合法解释时，按 `decision_policy` 处理；
- 缺口形成 Open Item，不伪造 Requirement 或 Acceptance Criterion；
- 用户不需要提供内部 Source ID、Goal ID、Requirement ID 或 JSON 表格。

## 决策与写入

- `decision_policy=user`：默认。给出推荐、原因和备选，由用户决定；
- `decision_policy=model`：仅在用户明确授权时选择并记录被放弃方案和风险；
- `decision_policy=experiment`：仅在可定义指标、范围、成本和停止条件时测试后选择。

- `write_policy=auto`：显式调用即授权本 Skill 的标准项目内 ArtifactStore 写入；内部自动生成 Runtime 所需 `artifact_store_write` confirmation；
- `write_policy=confirm`：首次标准写入前请求一次自然语言确认；
- `write_policy=deny`：不得写入，只允许 check 或 dry-run 边界。

Git、工作区外文件、远程系统、依赖安装、删除或覆盖 frozen 内容始终需要独立明确授权。

## Runtime 执行

只有参数完整、准确 frozen CTX 已唯一解析、必要业务决策已完成后，才构造 `sdlc-ai-spec/runtime-invocation/v1` 并调用：

```text
python3 <plugin-root>/skills/sdlc-100-req/scripts/runtime_final.py <request.json>
```

- create/revise 使用共享 ArtifactStore，不直接 SQL、不创建私有 Schema；
- check 严格只读，不 initialize、不修复、不创建旁车文件；
- 不调用 CTX 或其他业务 Skill，只消费共享 Authority 接口；
- 不把写入成功描述为 Gate 通过；
- 底层错误转换为用户可理解的决策或下一动作，默认不暴露内部 Envelope。

## 用户输出

`output=summary` 默认展示：需求状态、准确 Artifact、上游 CTX、主要来源、Gate、Open Items、实际写入和唯一下一动作。

`output=json` 只返回结构化结果；`output=debug` 才展示参数归一化、Source/Evidence、内部 Invocation 和 Runtime Result，且不得泄露 Secret。

`action_required / blocked / failed` 时立即停止；不自动进入 DSN、PLN 或其他阶段。

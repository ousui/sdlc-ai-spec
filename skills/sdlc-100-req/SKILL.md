---
name: sdlc-100-req
description: 创建、修订和检查需求 REQ Artifact；仅在用户显式调用时执行。
disable-model-invocation: true
---

# SDLC 100 Requirement

## 使用时机

仅在用户显式要求创建、修订或检查 REQ Artifact 时执行。普通需求讨论、代码分析或其他阶段工作不触发本 Skill。

## 核心规则

1. 进入 Exclusive Execution，不调用兄弟 Skill，也不传递当前授权。
2. 明确 `operation=create|revise|check`、绝对 `project_root` 和准确 Reference。
3. create/revise 收集完整结构化候选输入，并单独取得 Artifact Store 写入授权。
4. 不把推测写成正式 Requirement；缺口进入 Open Item。
5. 通过本 Skill 的 `scripts/runtime.py` 执行确定性 Builder、Validator 和 ArtifactStore 编排。
6. check 严格只读，不 initialize、不修复、不创建旁车文件。
7. 只解释 Runtime 返回的结构化事实；不得把写入成功描述为 Gate 通过。
8. 运行时不得读取 `docs/**`，不得直接 SQL，不得调用其他业务 Skill。

## 输入结构

向 Runtime 提交标准 Invocation Envelope：

```json
{
  "contract": "sdlc-ai-spec/runtime-invocation/v1",
  "operation": "create",
  "project_root": "/absolute/project/root",
  "artifact_reference": null,
  "inputs": {
    "context_reference": "CTX-...@1",
    "requirement": {},
    "control_inputs": [],
    "final_confirmation": null
  },
  "confirmations": [
    {"type": "artifact_store_write", "approved": true}
  ],
  "options": {"dry_run": false}
}
```

详细字段和状态见 `references/contract.md`；固定模板见 `assets/req-template.md`。

## 执行

从任意 CWD 调用：

```bash
python3 <plugin-root>/skills/sdlc-100-req/scripts/runtime.py < request.json
```

Runtime stdout 只输出一个 JSON Result Envelope。非零退出码表示协议或运行错误；stderr 不作为正常输出协议。

## 停止条件

- 需要用户事实、确认或权限时，只提出一条明确下一动作并停止；
- CTX、Control Input、Store、摘要或领域 Contract 无效时失败关闭；
- 不自动进入 DSN、PLN 或其他阶段。

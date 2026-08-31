---
name: sdlc-000-ctx
description: 显式创建、修订或严格只读检查项目上下文 CTX；裸调用会自动解析项目、操作和标准写入。
disable-model-invocation: true
---

# SDLC Project Context

本 Skill 将项目扫描、参数默认值、Evidence 组织、内部 Invocation 和 Runtime 调用封装为统一 SOP。用户无需编写长提示词或手工填写 Evidence ID、Basis、Confirmation JSON、Digest 或 Manifest。

## 快速使用

```text
/sdlc-000-ctx
/sdlc-000-ctx create
/sdlc-000-ctx check -r CTX-...@1
/sdlc-000-ctx -h
```

完整命令、版本和示例由 `references/interface.json` 定义。调用后先使用共享参数解析器归一化命令：

```text
python3 <plugin-root>/scripts/sdlc_skill_interface.py \
  --spec <plugin-root>/skills/sdlc-000-ctx/references/interface.json \
  -- <invocation-tail>
```

支持子命令、GNU 长参数、短参数和兼容别名。`help / version / commands / examples` 只展示预定义信息，不扫描项目、不调用 Runtime、不写入。

## 默认行为

公共默认值：

```text
command=auto
project_root=auto
decision_policy=user
write_policy=auto
dry_run=false
output=summary
```

`command=auto` 使用确定性规则：

1. 当前唯一工作区没有 CTX：`create`；
2. 唯一 materialized open CTX：`revise`；
3. 唯一 frozen CTX 且请求没有变更意图：`check`；
4. 唯一 frozen CTX 且请求明确变更：`revise`；
5. 多个合法项目、Lineage、Revision 或操作：请求用户选择，不猜测。

`project_root=auto` 只接受宿主提供的唯一现存工作区。多个 workspace、worktree、嵌套独立仓库或目标不唯一时，展示候选并请求一次决策。

## 只读预检与项目事实

在提交 Runtime 前，读取完成 CTX 所需的最小项目内容，例如 README、构建清单、目录、入口、配置、部署定义、工程规则和已有 ArtifactStore：

- 可直接证明的内容登记为 `observed` 或 `referenced` Evidence；
- 用户明确决定登记为 `confirmed`；
- 不允许推测的缺口形成 Open Item；
- 不要求用户手工编号 Evidence 或构造内部 JSON。

当当前工作区是唯一版本化项目、没有嵌套独立项目冲突且用户没有指定更广边界时，默认 Project Boundary 为：当前 Project Root 内的版本化工程资源及项目本地构建、配置、测试和部署资产；不包含外部系统、其他仓库或运行实例。裸调用接受该文档化默认值。若 monorepo、产品体系或外部资源边界存在多个合法定义，按 `decision_policy` 处理。

## 决策与写入

- `decision_policy=user`：默认。存在多个合法业务选择时，给出推荐、原因和备选，由用户决定；
- `decision_policy=model`：仅在用户明确授权时由模型选择并记录理由和风险；
- `decision_policy=experiment`：仅在用户授权且可定义候选、指标、成本和停止条件时执行测试后选择。

- `write_policy=auto`：显式调用即授权本 Skill 的标准项目内 ArtifactStore 写入；内部自动生成 Runtime 所需 `write` confirmation，不重复询问；
- `write_policy=confirm`：首次标准写入前请求一次自然语言确认；
- `write_policy=deny`：不得写入，只允许 check 或 dry-run 边界。

Git、工作区外文件、远程系统、依赖安装、删除或覆盖 frozen 内容始终需要独立明确授权。

## Runtime 执行

只有参数完整、确定性默认值已解决、必要业务决策已完成后，才构造 `sdlc-ai-spec/runtime-invocation/v1` 并调用：

```text
python3 <plugin-root>/skills/sdlc-000-ctx/scripts/runtime.py <invocation.json>
```

- `create/revise` 使用共享 ArtifactStore 与 ContextLineageRegistry；
- `check` 使用严格只读入口，不 initialize、不修复、不创建旁车文件；
- 不调用兄弟业务 Skill，不传递当前授权，不使用文件或其他数据库 fallback；
- `PROJECT_BOUNDARY_CONFIRMATION_REQUIRED` 等内部门禁由本 Skill 转换为自然语言决策，不把底层 JSON 直接交给普通用户。

## 用户输出

`output=summary` 默认只展示：状态、实际完成内容、Artifact、主要依据、实际写入、待决策项和唯一下一动作。

`output=json` 只返回结构化结果；`output=debug` 才展示参数归一化、Evidence、内部 Invocation 和 Runtime Result，且不得泄露 Secret。

只有 frozen 且 `ready / ready_with_exception` 的准确 Revision 提供 Context Authority。`action_required / blocked / failed` 时立即停止并给出一条可执行主动作。

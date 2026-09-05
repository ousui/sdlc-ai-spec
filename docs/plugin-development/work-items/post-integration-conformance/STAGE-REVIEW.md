# 八 Skill 阶段复核与修复记录

## Scope

以 `WORK-PACKAGE.md` 的 exact main 为起点，完整源码 Tree 与 accepted E3 全等。本轮不是证明所有 Spec 语义均无缺陷，而是复核先前阶段表中的具体短缺、执行普通回归，并修复可复现的 Status 边界。

## Findings

| ID | 级别/分类 | 来源与事实 | 本轮处理 |
|---|---|---|---|
| CON-001 | Major / Runtime | Status 原始 `auto -r latest` 在空 Store 误报正常 not_started，准确不存在引用也回退 overview | 准确 REQ 引用在 Store 访问前校验；显式 auto 引用使用 inspect 缺 Store 规则；永久负向测试 |
| CON-002 | Major / disclosure boundary | Status debug 复制 request_text；未知异常把原始文本返回 | 省略自由文本、保留可信投影引用；只返回有界错误码与固定解释，不展示异常 payload |
| CON-003 | Minor / interface | meta 的 JSON 模式输出文本；auto selection_required 与 inspect 不同；多 RLS Target 未完整展示 | 单 JSON 输出、action_required 一致、多候选不自动选择 |
| CON-004 | Major / reporting | Handoff 写后四阶段未开始；全插件 Codex Verified 实际只依据历史 CTX 记录 | 改为八 Skill 矩阵，保留历史引用与摘要，40 个当前 native 单元 NOT_RUN |
| CON-005 | delivery gap | Status 没有自己的锁/固定主测试映射/独立结果入口 | 增加 51 条 build-time lock、14/14 registry、12 命令安装测试；最终独立接受仍需 Review |
| CON-006 | clarification | 七个 Skill 缺少 evals/ 曾被当作缺陷，但规则同时允许目录按需创建 | 澄清开发 Eval 在 tests/**，不新增空目录或降低必须评测项目 |
| CON-007 | unconfirmed decision | Manifest 指向 goedgecloud，工作仓库是 ousui | 不擅自改变分发来源；交给 Maintainer 决定 |

## 不应改写的历史

CTX Eval Plan 的“未开始”是设计阶段状态，不是当前 execution record。本轮不修改它或其他已批准 Oracle，只在当前 Handoff 指向已存在的实际结果。REQ/DSN 的 Partial/Unknown 不因为后来全仓单元测试通过就变成 native Verified。旧 PR 的 unmerged 状态不等于内容未集成。

原 Status `contract.md` 被最终 VFY Source Lock 锁定。曾尝试追加说明，all-locks 检查正确拒绝；因此恢复其原始字节，说明放入新 `references/conformance.md`。没有刷新 VFY 锁掩盖漂移。

## Test scope

基线普通全仓 1068 项实际通过；这包含缺 OS 沙箱时合法的能力负向路径，不冒充 strict VFY 80/80。新源码执行结果以 exact-source `run_post_integration_validation.py` 输出为准，不能从本文推断新 Head 已通过。新增 native receipt 测试全部使用模拟临时仓库，只验证 guard，不认证真实 Client。

## Deferred

真实 Client 安装/发现/调用/权限/行为；严格 OS 沙箱门禁；独立最终 Review；正式发布目标决定；REQ 兼容层整理和历史 ResourceWarning 不在本修复包。未发现不等于已穷举证明不存在缺陷。

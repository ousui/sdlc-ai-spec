# 当前工程交接

## 当前工作包：收窄后的 Skill 输入可用性修复

2026-09-08，Maintainer 明确要求以真实 CTX 阻碍和其他 Skill 同类问题为范围，以测试用例/Fixture/mock 为主。来源 `codex/bugfix@14c167e044d7a8eeada3c826d1c41bb55bc7b01b`；原问题 HEAD `93cef2f6cc07e5e7b6a1f4dd8670d448bf460ba8`；main 基线 `aed8eb69d2b74ec27bdcb2fb356cb02b68602289`。

工作分支 `fix/skill-input-usability-v2`，Draft PR #21。收窄计划提交 `63d09ed044c7c5f536bd595a535bdf91aa306534`。本次明确授权按序修订、实施、验证并保存远端检查点；不改 main/codex/bugfix，不自动合并或发布，不改用户工作树/安装缓存。当前正式产品 Skill 执行：`None`。

原 PR #20 和 d94a4ff 是实际存在的历史工作，上轮末尾“未写入”说明不准确；本分支没有继承旧分支的 RLS 目标分配改动。两份计划已移除首次调用/模型实验、强制三项目全链、额外 Gin-Vue-Admin；test-sdlc 仅在需要工程载体时使用。

实现包含 CTX 字段诊断、受限描述性归一化、错误/Gate 分离、dry-run 错误保留、基线表示及已提供 Member 字节摘要绑定；REQ 写前结构拒绝；DSN/PLN meta 不读业务 stdin；VFY/RLS 布尔/相关输入类型拒绝；随包字段说明和漂移测试。旧 frozen 不自动迁移，授权/最终确认/只读/CAS 仍保留。Source Lock 从实际字节重新生成而非手填。

原问题提交上的七个核心测试方法已重放，保存 21 个失败子断言和合法配对；这不是新版本结论。开发期 CTX/REQ 既有44项回归通过；最终统一结果必须另绑准确实现 SHA。原始日志放在检出树外，PR 评论保存恢复索引。

## 唯一下一工作包

在本分支准确、干净的实现提交上执行统一回归并回读原始报告/源码，更新 EVAL-RESULTS 与本交接。源码/测试 SHA 与运输事件 SHA 分开；未执行项和无关既有失败单列，不将其写成 PASS。不重新规划、扩展模型实验或修改无关 RLS 行为。

## 以下为此前维护交接记录

以下保留原工作包的事实与限制，不作为当前工作包或下一动作；本次未核验其外部交付是否完成。七个阶段 CTX → REQ → DSN → PLN → IMP → VFY → RLS、只读 sdlc-status 及非 Phase 支撑 sdlc-github 均已实现。此前工作包为统一样式、修复评测引用、测试去重与过程归档清理。

## 历史维护分支

`refactor/skill-unification-cleanup` 从 `main@9d9dbf8bc1b9241f80af53cdf5b0426fcbfe3ab9` 创建，只在同一分支追加提交，完成后一次合入。main 和历史 Git 对象保持不变。

## 验证与交付

使用 [统一测试入口](../TESTING.md)，不串行重复运行旧阶段 Goal、private/full/fixed 多层重叠套件。保留所有有效安全回归及固定 Case 的 Expected；归档来源与删除依据见 [ARCHIVE.md](../maintenance/ARCHIVE.md)。旧证据仅适用于其原始 Subject，不能证明本分支。

原生 Client 独立留痕不在本轮门禁内。用户报告已手动试用，未记录轨迹，不据此生成正式认证台账。

Client 已在独立干净工作树对 Web 交付 Head
`6c1c342c639921c81335a3c4c47dacdd4595d59e` 执行统一入口的 `e2e`
profile。一次去重全仓为 962/962，IMP 82/82、VFY 80/80、RLS 87/87、
Status 14/14，且无 skip、expectedFailure 或 unexpectedSuccess；严格 VFY
使用 macOS `sandbox-exec`。两个固定项目均完成 CTX→RLS 本地 Sandbox 链并
恢复原始状态，安装、远程写入和真实目标效果均为 0。该结果是本轮 Runtime
验收，不是独立 Maintainer 接受；原始日志、源码快照和摘要仅在仓库外交付包中
保存。

## 最终归档复核：待一次定向重验

Client 随后对 `c8f6f7263e24ea8375065833f5741fbaf4d0f190` 重跑 e2e。
Web 审计发现 `MAINTENANCE-WEB-001`：普通短语 `basic use` 被当成 Basic
凭据，`use` 被传播脱敏到 33 个测试 ID。962 次执行和归档哈希不等于测试身份
完整；不得编辑旧日志或把 `[REDACTED]` 反填成猜测文本来补证。

已在同一分支修复 Basic 非上下文识别，并在脱敏前后及首次落盘后核对准确测试
ID、覆盖与观察值；真正已标记秘密仍脱敏，若与证明字段冲突则失败关闭，不设置
身份字段免脱敏白名单。合法 tuple→JSON array 转换不视为证据损坏。

旧 e2e 记录保留为历史，不能证明修复后的新源码。归档还须按 ARCHIVE 索引逐项
验证指定历史对象；`git bundle verify` 通过不表示所有已删除侧支均被保全。

## 历史维护后续事项（非当前下一动作）

按 `docs/maintenance/CLIENT-GOAL.md` 在最新干净准确提交上做一次 e2e，独立核对
落盘 ID 和实际 collection，补齐指定历史对象备份后交 Web 审查。此前整理、八个
Skill 样式和有效测试覆盖保持不变；不重启旧阶段 Goal、原生认证或多轮重复套件。
不修改 main，不执行生产效果，不自动合并 PR #12。


## sdlc-github 独立工作项

`sdlc-github-foundation/v1` 已由 Maintainer 于 2026-09-07 接受，当前仅等待 PR #14 的显式 Ready/Review/Merge 决定；
该历史状态不构成当前契约修复的实施或发布授权。历史 Goal/Repair/Revalidation/Portability 报告已按全局 ARCHIVE 索引恢复，
当前树不再承载多轮过程副本。

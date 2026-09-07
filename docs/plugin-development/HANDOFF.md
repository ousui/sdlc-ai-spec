# 当前工程交接

## 当前工作包：Skill 输入契约可靠性修复与验证

2026-09-08，Maintainer 明确要求评审修订后在 Web 同会话实施、验证并保存恢复点。来源 `codex/bugfix@14c167e044d7a8eeada3c826d1c41bb55bc7b01b`；反例基线 `aed8eb69d2b74ec27bdcb2fb356cb02b68602289`；修复分支 `fix/skill-contract-reliability-v1`，Draft PR #20。当前正式业务 Skill 执行：`None`（这里是插件工程修复，不是用户产品发布）。

[DESIGN](components/skill-contract-reliability/DESIGN.md)、[EVAL-PLAN](components/skill-contract-reliability/EVAL-PLAN.md) 已按 [REVIEW](components/skill-contract-reliability/REVIEW.md) 修订。原设计的 W1 停点被本次明确连续执行授权取代；不代表最终验收或合并批准。不修改 main/codex/bugfix，不操作用户现存工作树或安装缓存，不做生产效果。

基线已实际重放 CTX 全量错误映射、dry-run 丢错误、时间基线通过及 DSN/PLN 非终止 stdin 阻塞。另发现 RLS-E075 临时 ID 碰撞；相同 Runtime 不同时间可通过，必须增加强制碰撞回归而不是重试抹平。旧三项目 PASS 不用于新版本结论。

Issues 已关闭（HTTP 410），使用 Draft PR #20 正文清单/追加评论及仓库外 Actions 原始产物记录恢复点，不改变仓库管理设置。源树仅保留长期契约、测试、设计与紧凑证据索引；运输或文档提交不冒充实现 Subject。

## 唯一下一工作包

继续本分支 SCR 修复/验证：先固定原缺陷与旧合法请求，再实施最小修复和随包输入契约，随后在准确提交执行可用的统一回归/项目链。approval-bot 原快照和独立新上下文模型执行能力不可用时单列 NOT_RUN/BLOCKED，不向用户反复索取已授权操作确认，不宣称全范围 PASS。

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

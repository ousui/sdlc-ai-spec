# 当前工程交接

## 当前工作包：当前版本 Skill 输入可用性 bugfix

2026-09-08，按 Maintainer 指令仅修当前版本缺陷；不迭代版本、不改变 Schema/Store/命令，不增加迁移或版本选择。三平台 Manifest 保持 0.9.0。原问题 HEAD `93cef2f6cc07e5e7b6a1f4dd8670d448bf460ba8`；分支起点 `codex/bugfix@14c167e044d7a8eeada3c826d1c41bb55bc7b01b`，其父提交为指定 main 基线 `aed8eb69d2b74ec27bdcb2fb356cb02b68602289`。

工作分支 `fix/skill-input-usability-v2`，PR #21；当前正式产品 Skill 执行：`None`。本轮已获授权修订、实施、验证和保存远端检查点，不自动 merge/release，不改用户工作树、安装缓存或其他分支。

### 最终准确 Source / Test

最终被测 Subject 为 `66346e4485d1e579da3b5270854a5c172922ffa2`，tree `f80e0565478e349306dfd802db4a1ccc8adbbdb0`。该 tree 包含前序 CTX/REQ/DSN/PLN meta/VFY/RLS 输入修复，以及新发现的 DSN→PLN `VFO-*` 承接修复；`66346e4` 与前一 helper 修正提交 tree 相同，只用于 Maintainer 身份触发最终 PR 验证。后续 EVAL/Handoff 文档提交不是新测试 Subject。

最终 [Run 34187536347](https://github.com/ousui/sdlc-ai-spec/actions/runs/34187536347) 的 Ubuntu/macOS full 矩阵各 **1365/1365**；两个平台 7 个静态步骤全部 exit 0 且 source unchanged，0 failures/errors/skips/expectedFailure/unexpectedSuccess。准确测试 ID 集合一致；IMP 82/82、RLS 87/87、Status 14/14、VFY 80/80 保持原覆盖，其中 VFY 仍只标 portable contract tests，不冒称 strict 或原生认证。

最终原始 artifact：Ubuntu `10041203431`，ZIP SHA-256 `1b71afa0c4c201881d22d20b41db7fe75a50846902cfb6e3468a217cae64f6c0`；macOS `10041183944`，ZIP SHA-256 `49f4afbed4afd8399e49072131ff6577ba3a51e612abb905d38a5a7575eb6d89`。两者 `SOURCE-SHA.txt` / full / suite 均绑定 `66346e4`，1365 个 executed/successful IDs 完整。

### 新现场缺陷的闭环

Maintainer 提供真实只读现场：frozen DSN 的 Primary 有 CHG，DOM-510 有九个合法 `VFO-*`，旧 PLN `authoritative_obligations` 却只提取 CHG；把九个 VFO 忠实放进候选 Plan 后，正式 dry-run 触发 `PLN-G-002` 和 `PLN-G-006` 且零副作用。随包 DOM-510 Contract 明确 VFO 是后续 VFY Target，因此根因是 PLN 消费端白名单遗漏，不是 DSN 数据或 Schema 错误。

修复提交 `9d364c3bea9e015b7c5038c0f9ca32a837437e57` 只把 `VFO-*` 纳入 PLN authoritative obligations；`VFM/VPC/VEC` 不升级为独立 Plan obligation。长期回归 3 项固定完整承接、细节排除和缺失目标负例。首次 full 随后暴露两个测试/集成 helper 仍保留旧 `VFP/OBJ/AC` 分类，产生 22 个下游 errors；保留该失败 artifact `10040900045`，只修 helper 分类，不放宽 Runtime Gate。最终 full 已关闭全部 22 个错误。

前序修复仍包括 CTX 输入诊断/错误与 Gate 分离/dry-run 保留错误、Evidence 与 Member 字节绑定、观察基线、受限用途归一化；REQ 正式入口写前预检；DSN/PLN meta 不读业务 stdin；VFY/RLS 输入类型错误不转换成执行选项；随包说明及漂移回归。旧合法请求可直接使用，旧 CTX/REQ frozen 检查、原 open CTX 续行及 REQ NO_CHANGE 的兼容性探针通过，无迁移或请求重写。VFO 修复同样只重新解释既有合法 frozen Member，不要求改 DSN、重冻结或迁移 Store。

旧 PR #20 保留历史，不并入其额外 RLS 目标分配改动。本次不要求模型实验、真实三项目全链或新增 Gin-Vue-Admin。已有失败、输入预检遗漏、测试 mock 问题及 VFO helper 漏承接均留原始证据，不以旧 PASS 替代新结果。完整细节见 [EVAL-RESULTS](components/skill-contract-reliability/EVAL-RESULTS.md)。

## 唯一下一工作包

Maintainer 审阅 PR #21 的当前补丁与最终结果并决定是否合并；当前保持未合并、未发布。无需重新规划、升级版本、修改 Schema、迁移已有 Artifact 或重做被冻结 DSN。真实项目升级到合并后的补丁后，可直接让 PLN 重新读取原 frozen DSN；本工作包未代用户修改本地插件缓存或在真实项目执行写操作。

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

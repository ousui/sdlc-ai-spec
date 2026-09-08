# 当前版本 Skill 输入可用性修复结果

2026-09-08。范围和当前版本补丁约束见 [DESIGN](DESIGN.md)；固定 Expected 见 [EVAL-PLAN](EVAL-PLAN.md)。本报告不是新版协议、Schema 迁移或原生 Client 认证。

## 1. 准确对象与结论

- 原问题 Runtime：`93cef2f6cc07e5e7b6a1f4dd8670d448bf460ba8`。
- 分支起点：`codex/bugfix@14c167e044d7a8eeada3c826d1c41bb55bc7b01b`，父提交为用户指定 main 基线 `aed8eb69d2b74ec27bdcb2fb356cb02b68602289`。
- 最后一个 Runtime 修复提交：`7294c646500d4c5f9b9180abda7285d44196c58d`。
- 最终 Source / Test Subject：`8acae6be334d61f30e6207f3757c02d84cb687f9`，tree=`8940525f6161a7ed209eb989936c4350981473f6`；相对 7294 仅修正测试 mock 并增加隔离断言。
- 交付分支：`fix/skill-input-usability-v2`，PR #21；分支名后缀不代表产品版本。

**本次限定范围修复与回归完成，等待 Maintainer 合并决定。** 最终 Run [34179980279](https://github.com/ousui/sdlc-ai-spec/actions/runs/34179980279) 的 Ubuntu/macOS 各执行 1362 个唯一方法并全部通过；失败、错误、skip、expectedFailure、unexpectedSuccess 均为 0。两个平台测试 ID 集合与 source.bundle 字节一致。文档交付提交只登记证据，不将其冒称为执行过 full 的源码。

三平台 Manifest 仍为 `0.9.0`。未改变 interface.json、公共 Contract ID、任何 .schema.json、docs/v1.x 或 ArtifactStore 实现/存量格式；没有新必填字段、版本选择开关或迁移步骤。旧合法请求和原记录直接使用；错误请求仍需据事实纠正，不能为通过检查伪造 ready。

## 2. 本次实际修复

CTX 输入错误不再映射为全部 15 Check fail；未评估 Gate 为 pending，dry-run 保留具体错误。独立环境/摘要字段同时诊断；用途的明确别名和拼写整理产生 warning，不修改原请求，不猜引用或权限。提供的 Supporting Member 与 Evidence 绑定真实字节；新资源观察不能以时间或可变名称替代内容身份。旧 frozen 的只读解释不因输入预检而重写。

REQ 预检接入正式 runtime_final 安装的 cleanup wrapper，在 Store 快照及清理前拒绝非法输入；不再仅在会被替换的基础 Handler 验证。DSN/PLN 元命令先分流、不读业务 stdin；VFY/RLS 的字符串布尔与不合法相关字段不再被转换成执行选项。随包说明补齐实际字段/枚举/嵌套映射，以已有常量生成文档投影并保留漂移断言，没有引入通用 Schema 框架。

完整回归另暴露一个已有测试隔离问题：资源预算测试修改共享 sys.platform，禁用了其他模块的 Darwin cleanup fallback。仅将该测试 mock 限定到 executor 绑定，增加确定性隔离断言；未改 VFY Runtime、预算或原输出/超时 Oracle。

## 3. 执行结果与 Case 映射

| 执行 | 实际结果 | 说明 |
|---|---|---|
| Ubuntu x86_64 / Python 3.13.15，full | 1362/1362，7 静态步骤通过 | 精确 Source/Test=8acae6be；无 skip/xfail |
| macOS 15.7.9 arm64 / Python 3.13.15，full | 1362/1362，7 静态步骤通过 | 同一源码/测试 ID 集合；原预算用例通过 |
| 本次输入定向集合（包含于 full） | 两个平台均 31/31 | 不与 full 相加计数 |
| 固定登记覆盖（包含于 full） | IMP 82、RLS 87、Status 14、VFY 80 | VFY 为 portable contract tests，不标 strict |

实际命令：`python -B tools/validate.py --profile full --source-sha 8acae6be334d61f30e6207f3757c02d84cb687f9 --json-out <runner-temp>/sdlc-validation/full.json`。

| Case | 实际覆盖和证据 |
|---|---|
| INPUT-01/02/03/04 | CTX 合法 pending 配对、非法资源/环境枚举、用途归一化、组件依赖；test_regressions 中的具名正反例 |
| INPUT-05/06 | Evidence 实际 Member 字节、坏摘要/时间双错误、不可变基线表示及旧 VCS 配对；只验证表示与已提供内容，不冒称外部对象已解析 |
| INPUT-07/08 | create/revise 与 dry-run 拒绝无写入；旧 frozen 不变；经受控确认 verifier 的真实 rejected 只映射 CORE-G-009 |
| INPUT-09/13 | REQ 正式 Handler + 安装后 runtime_final 真 stdin；create/revise × dry-run/非 dry-run 四路径在 Store 读写前拒绝；VFY/RLS 错误类型不能开启执行 |
| INPUT-10 | DSN/PLN meta、别名与非法/未结束 stdin；命令合法解析及零项目效果 |
| INPUT-11/12 | 随包字段映射、五份生成参考的漂移检查；安装副本无 docs/tests 仍能执行正式 CTX/REQ 正反例；既有各 Skill 契约测试保留 |
| INPUT-14 | prepare_confirmation、Supporting Member、只读/CAS 等既有回归；旧 frozen 检查及旧合法请求续行；未删除安全用例 |

本地定向集合 31/31，通过日志为 `input-targeted-complete.log`。测试 mock 修正前新增隔离断言失败，修正后该文件 6/6（含全部原 5 项预算测试）。本地运行对象为与提交 tree 相同的工作树；最终 CI 使用干净准确提交，不以本地数量替代完整回归。

## 4. 无版本感知的正常使用回归

用 `14c167e` 原代码在隔离目录生成已有 CTX/REQ 记录，再用补丁 Runtime 处理同一请求。`compatibility_probe.py` 和 `compat-2/after-results.json` 留存全部操作及摘要。

| 原有状态/请求 | 实际结果 |
|---|---|
| CTX frozen → check | pass；既有文件摘要不变 |
| CTX open → 原确认请求继续完成 | 原 Revision 正常 frozen；请求无需修改，无版本参数 |
| REQ frozen → check | pass；既有文件摘要不变 |
| REQ frozen → 同内容 revise | NO_CHANGE、原 Reference 不变；不分配新 Revision |

确认和上游 Authority 使用明确的测试 fixture/mock，Store 与操作入口实际执行。这不是用户 approval-bot 实测或真实生产授权；未读取其本地项目、改其工作树或安装缓存。

## 5. 保留失败与修正轨迹

1. 历史 `93cef2f...` 的七个核心方法（含合法配对）产生 21 个失败子断言，原始 `original93-red.json/log` 位于旧 strict 原始 ZIP。
2. `2b578945...` 的 strict Run 34176297078：执行 1360 方法，同一个 REQ 测试的四子例有 2 failures / 2 errors；其余阶段覆盖不能将全仓失败改称成功。修复正式 wrapper 后保留 Oracle；本地同两方法八失败子例转为通过。
3. `7294c646...` 的 full Run 34179321372：Ubuntu 1361/1361；macOS 1361 方法中 1 error（预算测试的全局平台 mock）。原始 ZIP 保留，不把 Ubuntu 通过替代 macOS。
4. 最终测试源码改为模块级 mock，原预算断言不变，并增加可确定复现污染的新断言；Runtime 内容与 7294 相同。最终矩阵是测试源码修正后的执行，不是原样重跑刷绿。

本地首次定向执行因外层工具超时中断，`input-targeted.log` 不计完成；完整执行另存。首次兼容探针把初始 CTX 的 base_revision 写成 1，未取得确认绑定；修正 fixture 为 None 后从全新目录执行成功，不修改 Runtime 迎合夹具。原失败文件均保留，无人工补写 PASS。

## 6. 原始证据与边界

| Run / Artifact | 用途 | 原始 ZIP SHA-256 |
|---|---|---|
| 34179980279 / 10038721002 | 最终 Ubuntu full | `1f7ea2fe43a2f3ea135e083513beb966ed511e259363f876e43ad3dc5375995e` |
| 34179980279 / 10038733925 | 最终 macOS full | `c93cc61f0e419fa4c7facf66babe10e2efcaffa32aa63750a069d60b0b3dbb08` |
| 34179321372 / 10038499062 | 7294 Ubuntu full | `c76e811aa1520b64abfd0144a319f76a3a22976bd0316cd243a96dbc1fac8f73` |
| 34179321372 / 10038482125 | 7294 macOS mock 错误 | `753e59ea92fe40df9689e5671221345120877246a12d394191468b198f1805ef` |
| 34176297078 / 10037522219 | 2b578945 strict 失败及原问题复现 | `1a145655e2960ab1fe96b6882be1e4964657ba0fa9558c68d84256124daaa4f2` |

原始 ZIP 中的 SOURCE-SHA、source.bundle、full.json 与 suite.json 已交叉核对；测试 ID 唯一性、成功集合、计数、静态步骤退出码及 stdout/stderr 摘要按实际归档字节检查。源码源树未改、无 skip/expectedFailure/unexpectedSuccess 才计完整通过。额外探针/读回程序和旧失败 ZIP 在本会话完整证据包中保存，源码树仅放紧凑报告和长期测试。

本次验证选择在结果产生前记录于 PR：复用现有 Ubuntu/macOS full 矩阵，不增加 full+strict+e2e 堆叠或 Schema 迁移流程。最终 full 的 VFY 80 项是 portable contract tests，不是 strict VFY execution 认证。未执行真实项目全链、新模型实验、原生宿主加载或生产发布；这些不属于本次收窄后的验收义务。报告中的 remote_writes/installations/real_target_effects=0 指测试运行的产品效果，不包括本任务已授权的 GitHub 提交和 PR 记录。

未自动合并 PR、发布新版或改动用户缓存。下一动作见 [HANDOFF](../../HANDOFF.md)，不重新展开设计或版本迭代。

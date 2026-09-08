# 当前版本 Skill 输入可用性修复结果

2026-09-08。范围和当前版本补丁约束见 [DESIGN](DESIGN.md)；固定 Expected 见 [EVAL-PLAN](EVAL-PLAN.md)。本报告不是新版协议、Schema 迁移或原生 Client 认证。

## 1. 准确对象与最终结论

- 原问题 Runtime：`93cef2f6cc07e5e7b6a1f4dd8670d448bf460ba8`。
- 分支起点：`codex/bugfix@14c167e044d7a8eeada3c826d1c41bb55bc7b01b`，父提交为用户指定 main 基线 `aed8eb69d2b74ec27bdcb2fb356cb02b68602289`。
- CTX/REQ 等前序 Runtime 修复：截至 `7294c646500d4c5f9b9180abda7285d44196c58d`；`8acae6be334d61f30e6207f3757c02d84cb687f9` 仅隔离测试平台 mock。
- DSN→PLN VFO Runtime 修复：`9d364c3bea9e015b7c5038c0f9ca32a837437e57`。
- VFO 集成 Fixture 修正：`ea86aae4fa51cc19c35249f4c1728fb6287c2a07`；只让测试/集成计划生成器承接 Runtime 已识别的 VFO，不改产品 Gate。
- **最终 Source / Test Subject：`66346e4485d1e579da3b5270854a5c172922ffa2`，tree=`f80e0565478e349306dfd802db4a1ccc8adbbdb0`。** 该提交与 `ea86aae4` tree 完全相同，仅用于由 Maintainer 身份触发最终 PR 验证。
- 交付分支：`fix/skill-input-usability-v2`，PR #21；后续文档提交不冒充新的执行 Subject。

**本次限定范围 bugfix 与回归完成，等待 Maintainer 合并决定。** 最终 Run [34187536347](https://github.com/ousui/sdlc-ai-spec/actions/runs/34187536347) 的 Ubuntu/macOS 各执行 1365 个唯一测试方法并全部通过；失败、错误、skip、expectedFailure、unexpectedSuccess 均为 0。两个平台准确测试 ID 集合一致，均绑定 Source SHA `66346e4485d1e579da3b5270854a5c172922ffa2`；各平台 source.bundle 分别保存，不要求其 pack 字节相同。

三平台 Manifest 仍为 `0.9.0`。未改变 interface.json、公共 Contract ID、任何 `.schema.json`、docs/v1.x 或 ArtifactStore 实现/存量格式；没有新必填字段、版本选择开关或迁移步骤。旧合法请求和已有 frozen Artifact 直接使用；错误请求仍需据事实纠正，不能为通过检查伪造 ready。

## 2. 本次实际修复

CTX 输入错误不再映射为全部 15 Check fail；未评估 Gate 为 pending，dry-run 保留具体错误。独立环境/摘要字段同时诊断；用途的明确别名和拼写整理产生 warning，不修改原请求，不猜引用或权限。提供的 Supporting Member 与 Evidence 绑定真实字节；新资源观察不能以时间或可变名称替代内容身份。旧 frozen 的只读解释不因输入预检而重写。

REQ 预检接入正式 runtime_final 安装的 cleanup wrapper，在 Store 快照及清理前拒绝非法输入。DSN/PLN 元命令先分流、不读业务 stdin；VFY/RLS 的字符串布尔与不合法相关字段不再被转换成执行选项。随包说明补齐实际字段/枚举/嵌套映射，以已有常量生成文档投影并保留漂移断言，没有引入通用 Schema 框架。

完整回归曾暴露一个已有测试隔离问题：资源预算测试修改共享 `sys.platform`，影响其他模块的 Darwin cleanup fallback。仅将该测试 mock 限定到 executor 绑定并增加隔离断言；未改 VFY Runtime、预算或原输出/超时 Oracle。

### DSN → PLN VFO 衔接缺陷

Maintainer 随后提供真实只读现场：一个已经 frozen/pass 的 DSN Primary 含 `CHG-001`，其 `DOM-510` Member 含九个合法 `VFO-001..009`；旧正式 `pln_scope.resolve_inputs` 的 `authoritative_obligations` 却只有 `CHG-001`。候选 Plan 忠实声明 CHG + 九个 VFO，并以九个 VFO 作为 VFY Work Item 来源后，正式 dry-run 准确出现 `PLN-G-002` 与 `PLN-G-006`，且 Store、Git 状态和 frozen DSN 全部不变。

随包 DOM-510 Contract 明确把 `VFO-*` 定义为 VFY Objectives，并规定每个 Objective 是后续 VFY Target；`VFP-*` 是其他 Design Domain 的局部 VFY Point。因此这不是 DSN 数据错误，也不能通过把 VFO 改成 VFP 规避。根因是 PLN `_artifact_items()` 的合法义务编号白名单遗漏 `VFO-*`。

Runtime 只做最小修复：PLN 现在把 `VFO-*` 作为 authoritative obligation；`VFM-*`、`VPC-*`、`VEC-*` 仍是 VFO 的方法、通过条件和 Evidence Contract 细节，不升级成独立 Plan obligation。既有 frozen DSN 无需迁移、重写或创建新 Revision。

## 3. VFO 修复的反例、正例与下游回归

长期回归 `tests/skill_pln/test_vfo_obligations.py` 使用结构等价、脱离真实业务内容的 DSN/DOM-510 Fixture：

1. frozen DOM-510 含九个 VFO 时，authoritative obligations 必须是 `CHG-001 + VFO-001..009`；VFM/VPC/VEC 不进入集合；
2. 完整 Plan 承接 CHG + 九个 VFO 时，不能误触 `PLN-G-002` 或 `PLN-G-006`；
3. 故意少任一 VFO 时，`PLN-G-002` 仍必须失败，防止通过扩大白名单削弱精确覆盖 Gate。

补丁前同一组 3 项回归中 2 项失败；完整 VFO Plan 的失败正是 `PLN-G-002 + PLN-G-006`。`9d364c3` Runtime 修复后 3/3 通过，现有 PLN 套件 36/36、PLN Source Lock 13-source 检查通过。

首次在 `9d364c3` 跑全仓时，Ubuntu 1365 个测试中出现 22 errors。原始 artifact `10040900045`（ZIP SHA-256 `72a02b801b4bda4b855eaa7f0de9addfe7ffde52466bab5af1a29e8b6fd39b63`）显示 Runtime 已正确识别 VFO，但 `tools/run_external_pln_integration.py` 和 `tools/rls_fixture_chain.py` 的测试计划生成器仍只把 `VFP/OBJ/AC` 分类给 VFY Work Item，导致新识别的 VFO 没有被 Work Item 覆盖，`PLN-G-002` 正确拒绝。这不是 Runtime 应放宽的错误。

两个 helper 各只增加 `#VFO-` 到既有 VFY 来源分类。修正前会失败的 RLS-E011/E012 与 VFO 定向回归先行通过；临时运输 workflow 已在最终 tree 中删除。最终 `66346e4` 再执行完整矩阵，22 个下游错误全部关闭。

## 4. 最终统一回归

| 执行 | 实际结果 | 说明 |
|---|---|---|
| Ubuntu x86_64 / Python 3.13.15，full | **1365/1365**，7 静态步骤通过 | Source/Test=`66346e4`；0 failure/error/skip/xfail |
| macOS 15.7.9 arm64 / Python 3.13.15，full | **1365/1365**，7 静态步骤通过 | 同一 Source/Test 与测试 ID 集合 |
| 新增 VFO 定向集合（包含于 full） | 两个平台均 **3/3** | 完整承接、明细排除、缺失目标负例 |
| 固定登记覆盖（包含于 full） | IMP 82、RLS 87、Status 14、VFY 80 | VFY 为 portable contract tests，不标 strict |

七个静态步骤在两个平台均 exit 0 且 `source_unchanged=true`：runtime-contracts、skill-interfaces、skill-style、inventory、source-locks、status-static、lifecycle-static。

实际命令：`python -B tools/validate.py --profile full --source-sha 66346e4485d1e579da3b5270854a5c172922ffa2 --json-out <runner-temp>/sdlc-validation/full.json`。

| Run / Artifact | 用途 | 原始 ZIP SHA-256 |
|---|---|---|
| 34187536347 / `10041203431` | 最终 Ubuntu full | `1b71afa0c4c201881d22d20b41db7fe75a50846902cfb6e3468a217cae64f6c0` |
| 34187536347 / `10041183944` | 最终 macOS full | `49f4afbed4afd8399e49072131ff6577ba3a51e612abb905d38a5a7575eb6d89` |
| 34186676302 / `10040900045` | VFO Runtime 正确后暴露旧 Fixture 分类遗漏 | `72a02b801b4bda4b855eaa7f0de9addfe7ffde52466bab5af1a29e8b6fd39b63` |
| 34179980279 / `10038721002` | VFO 缺陷发现前的 Ubuntu full 历史结果 | `1f7ea2fe43a2f3ea135e083513beb966ed511e259363f876e43ad3dc5375995e` |
| 34179980279 / `10038733925` | VFO 缺陷发现前的 macOS full 历史结果 | `c93cc61f0e419fa4c7facf66babe10e2efcaffa32aa63750a069d60b0b3dbb08` |

最终两个 ZIP 的 `SOURCE-SHA.txt`、`full.json.source_sha` 与 `suite.json.source_sha` 均为 `66346e4485d1e579da3b5270854a5c172922ffa2`；1365 个 executed ID 与 successful ID 完整，两个平台 ID 集合一致。原始 ZIP、日志和源码 bundle 分别保留，不把旧 1362/1362 或运输提交当当前最终证明。

## 5. Case 映射与无版本感知兼容

| Case | 实际覆盖和证据 |
|---|---|
| INPUT-01/02/03/04 | CTX 合法 pending 配对、非法资源/环境枚举、用途归一化、组件依赖；具名正反例 |
| INPUT-05/06 | Evidence 实际 Member 字节、坏摘要/时间双错误、不可变基线表示及旧 VCS 配对 |
| INPUT-07/08 | create/revise 与 dry-run 拒绝无写入；旧 frozen 不变；真实 rejected 只映射 CORE-G-009 |
| INPUT-09/13 | REQ 正式 Handler + 安装后 runtime_final 真 stdin；四路径在 Store 读写前拒绝；VFY/RLS 错误类型不能开启执行 |
| INPUT-10 | DSN/PLN meta、别名与非法/未结束 stdin；命令合法解析及零项目效果 |
| INPUT-11/12 | 随包字段映射与生成参考漂移；安装副本无 docs/tests 仍执行正式正反例 |
| INPUT-14 | prepare_confirmation、Supporting Member、只读/CAS；旧 frozen 检查、旧合法 CTX 续行、REQ NO_CHANGE |
| INPUT-15 | DOM-510 `VFO-*` 正确进入 PLN authoritative obligations；完整九目标计划正常，漏目标仍失败；VFM/VPC/VEC 不被误提升 |

此前已用 `14c167e` 原代码在隔离目录生成 CTX/REQ 记录，再由补丁 Runtime 直接处理同一请求：CTX frozen check、旧 open CTX 原请求续行、REQ frozen check、REQ 同内容 revise=NO_CHANGE 均通过，原文件摘要不变，没有版本参数或迁移。

VFO 修复同样不改变数据表示：它只改变 PLN 对既有 frozen DSN Member 的读取分类。升级后的 PLN 可以直接重新读取原 DSN Revision；不需要修改 VFO、重冻结 DSN 或转换 Store。真实项目现场在旧 Runtime 上完成了只读反例取证，本工作包没有替用户改安装缓存或在该真实项目上执行补丁版写入流程；最终产品结论由通用 Runtime 回归证明，而非冒称已代用户重新运行项目。

## 6. 保留失败与边界

- 历史 `93cef2f...` 的核心反例失败保留，不以新正例覆盖。
- `2b578945...` strict 暴露 REQ 正式入口预检被 wrapper 绕过；修正后重新执行新准确源码。
- `7294c646...` macOS 暴露预算测试全局平台 mock 污染；只修测试隔离，不改 VFY Runtime。
- `9d364c3...` full 暴露两个集成 helper 的 VFY 来源白名单仍遗漏 VFO；保留 22 errors 原始产物，修 helper 而不放宽 `PLN-G-002`。
- `ea86aae4` 由临时自删除运输 workflow 形成准确 helper 修正，但其自动 PR Run 为 `action_required`，不当作验证；`66346e4` tree 相同，由 Maintainer 身份触发最终完整 Run。

本次没有执行 Schema 迁移验证、版本协商、真实三项目全链、新模型实验、原生宿主认证或生产发布；这些不属于本次收窄后的验收义务。VFY full 的 80 项仍是 portable contract tests，不冒称 strict VFY execution。报告中的产品 remote writes/installations/real target effects 为 0；本任务明确授权的 GitHub 分支、提交和 PR 记录不属于产品效果。

未自动合并 PR、发布新版或修改用户插件缓存。下一动作见 [HANDOFF](../../HANDOFF.md)。

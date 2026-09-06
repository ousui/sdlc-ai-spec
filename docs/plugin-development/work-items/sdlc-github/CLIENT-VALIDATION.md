# CLIENT-VALIDATION — sdlc-github-foundation/v1

本批次结果 **FAIL**，未最终接受；可运行验证已完成，环境、权限、fixture 与上游兼容缺口保留。原连续入口最终 **exit 1**。32 个业务操作为 **25 PASS / 1 FAIL / 6 BLOCKED**；另有 `status` 的 partial 能力状态被控制器登记为 FAIL。不得用本报告的确定性测试或 Codex 结果替代另外两个宿主。

## 1. 准确来源与交付边界

| 项目 | 值 |
|---|---|
| Repository / branch | `ousui/sdlc-ai-spec` / `impl/sdlc-github-foundation-v1` |
| 起始 HEAD / 最后核验的交付远端 HEAD | `6c476e4a58c7fc9871ce876cc7174e7e4d5e51dd` |
| 实际 Runtime SHA | `b035880a6135c1f126ae1a35e1c173221f28807a` |
| 批准设计 SHA | `97c5f17bfcdb2751d446a89b068db2400436631d` |
| 依赖锁 SHA-256 | `49665bdee4d204ef52b7b4c08da97fbd11bfb70d8c760ccb950a5333e6feabda` |
| Python / Host 顺序 | Python 3.14.7；Codex → Cursor → Claude Code |
| Draft PR | [#14](https://github.com/ousui/sdlc-ai-spec/pull/14) |

Git 根目录、分支、HEAD、干净状态、设计祖先关系及指定 Runtime/tests/manifests 路径的零 Diff 均已核验。**没有修订源码，没有新 Runtime 提交**。本报告所在的文档证据提交是 Client 交付 SHA，不能视为新的被测 Runtime SHA。准确交付提交从本文件 Git 历史读取，后续 Review 必须固定该提交，不能自动采用分支后续源码。

证据：[Git 基线](client-evidence/git-baseline.json)、[完整源码文件摘要与层级结果](client-evidence/results/VALIDATION.json)、[三份安装副本完整性检查](client-evidence/installation-checks.json)。三份副本 packages/scripts/skills 与准确源码逐文件相同；没有把安装器 READY 当成原生 PASS。

## 2. 连续入口与环境问题

入口始终为仓库原有 `tests/skill_github/validate.py --layer client`，顺序为 offline → integration → live → identity → native evidence。实际命令与环境见 [JSON](CLIENT-VALIDATION.json)。同一 `$GH_WORK`、fixture、data、results 和请求状态一直保留。

| 执行 | 结果 | 退出码 / 说明 |
|---|---|---|
| prepare | PASS | 固定生成并核验 10,000 文件；不作为真实 GitHub/Host PASS |
| client attempt 1 | FAIL | exit 1；macOS 默认临时路径含符号链接，存储安全检查拒绝，live 未执行 |
| client attempt 2 | FAIL | exit 1；仅设置本测试进程 TMPDIR 为规范化外部目录；真实失败保留 |
| offline | PASS | 212 tests |
| integration | PASS | 6 tests，真实 stdio → Fake HTTP MCP；仅 A/B 证据 |
| 全仓 regression | PASS | 1336 tests |
| compileall / runtime contracts / source-lock | PASS | 均 exit 0 |

第一次原始失败含 46 failures（含 subtest）和 6 errors，完整日志已保留；最小 Fake 诊断在默认路径返回 STORAGE_UNSAFE，改用**同一目录的真实路径**后 confirmed。未放宽文件安全检查、未更改测试代码。[第一次失败](client-evidence/attempts/01-default-tmp/results/offline/unittest.log) · [环境诊断](client-evidence/attempts/01-default-tmp/environment-diagnosis.json) · [第二次真实退出码](client-evidence/attempts/02-canonical-tmp/exit-code.txt) · [全仓回归](client-evidence/regression/unittest.stderr.log)。回归 stdout 内的 `RLS_DELIVERY_QUICK = FAIL` 来自既有反例测试，unittest 最终为 1336/1336 OK。

## 3. 真实官方 Remote MCP 与全部 32 操作

唯一生产链路：`scripts/sdlc_github_mcp.py` → 固定 `https://api.githubcopilot.com/mcp/`。Actor A 为 **ousui / 2839512**。真实 Token 仅在进程环境注入；未扩大权限。固定测试仓库为 `ousui/sdlc-ai-monitor`，本次 live run 为 `d46c3043-808f-47b3-afd4-3457f9604c09`。

head/base、精确 commit、README、workflow/run 已在本轮重新核验。[非秘密 fixture](client-evidence/fixture.json)。Job `101455494899` 通过辅助只读 REST 获取 selector，随后 **actions.logs 的 PASS 来自生产 Runtime**。辅助查询和上游 Schema 诊断不计作生产/native Oracle，也不记录 HTTP 请求次数；HTTP 上游调用数为 `not externally observed`。

- 27 只读：21 PASS / 1 FAIL / 5 BLOCKED。
- 5 写入：4 PASS / 0 FAIL / 1 BLOCKED。
- 32 个操作全部独立登记；两个缺少 Tag/Release selector 的单对象操作未发送工具调用。共 30 个业务操作进入生产工具，另有一次 status。
- 4 个已确认写操作均有真实 URL 和 `receipt.readback_verified=true`。普通评论未创建。
- 列表为空或 completeness=unknown/partial 只证明本次页请求，不代表对象 fixture 或全量分页已通过。

| Operation | 类型 | 状态 | 结果 / 缺口 |
|---|---|---|---|
| repo.files | read | PASS | 真实返回；完整性见原响应 |
| repo.branches | read | PASS | 真实返回；完整性见原响应 |
| repo.commits | read | PASS | 真实返回；完整性见原响应 |
| repo.commit | read | PASS | 真实返回；完整性见原响应 |
| repo.tags | read | PASS | 真实返回；完整性见原响应 |
| repo.tag | read | BLOCKED | Existing Tag fixture required; this batch never creates Tags |
| issue.list | read | BLOCKED | CAPABILITY_UNAVAILABLE |
| issue.get | read | PASS | 真实返回；完整性见原响应 |
| issue.comments | read | PASS | 真实返回；完整性见原响应 |
| pr.list | read | PASS | 真实返回；完整性见原响应 |
| pr.get | read | PASS | 真实返回；完整性见原响应 |
| pr.diff | read | PASS | 真实返回；完整性见原响应 |
| pr.files | read | PASS | 真实返回；完整性见原响应 |
| pr.reviews | read | PASS | 真实返回；完整性见原响应 |
| pr.review-comments | read | PASS | 真实返回；完整性见原响应 |
| pr.comments | read | PASS | 真实返回；完整性见原响应 |
| pr.checks | read | BLOCKED | PERMISSION_DENIED |
| pr.status | read | PASS | 真实返回；完整性见原响应 |
| actions.workflows | read | PASS | 真实返回；完整性见原响应 |
| actions.runs | read | PASS | 真实返回；完整性见原响应 |
| actions.jobs | read | FAIL | UPSTREAM_INVALID |
| actions.artifacts | read | PASS | 真实返回；完整性见原响应 |
| actions.run | read | PASS | 真实返回；完整性见原响应 |
| actions.logs | read | PASS | 真实返回；完整性见原响应 |
| release.list | read | PASS | 真实返回；完整性见原响应 |
| release.get | read | BLOCKED | Existing release/tag fixture required |
| release.latest | read | BLOCKED | NOT_FOUND_OR_INACCESSIBLE |
| issue.create | write | PASS | confirmed / readback=true |
| issue.update | write | PASS | confirmed / readback=true |
| comment.create | write | BLOCKED | CAPABILITY_UNAVAILABLE |
| pr.create | write | PASS | confirmed / readback=true |
| pr.update | write | PASS | confirmed / readback=true |

逐调用不可变 event、准确入参、结构化结果摘要、receipt 和返回内容摘要位于 [LIVE-VALIDATION](client-evidence/results/live/LIVE-VALIDATION.json) 与 [live 证据目录](client-evidence/results/live/)。不归档 README 正文、Diff 正文或 Job 日志内容。

## 4. 真实失败与阻塞原因

1. **FAIL — actions.jobs**：实际响应为 `{jobs:{total_count,jobs:[...]}}`；当前列表提取器要求 `jobs` 本身是数组，返回 UPSTREAM_INVALID。不是 fixture 缺失：同一 run/job 已核验，Actions run/logs 均通过。
2. **FAIL — status**：身份验证成功，但两项 capability=false 导致 partial/ok=false；原控制器据实登记 FAIL。此行不计入 32 业务操作分母。
3. **BLOCKED — issue.list**：官方 Schema 的 state 枚举为 OPEN/CLOSED；当前 capability probe 使用 open/closed，失败关闭。
4. **BLOCKED — comment.create**：官方 Schema 要求非空正文，而 capability probe 使用空字符串，因此连已授权的非空正文也被阻断。未调用远端评论写入。
5. **BLOCKED — pr.checks**：真实 MCP 返回 PERMISSION_DENIED，保留现有 Token 权限。
6. **BLOCKED — repo.tag / release.get / release.latest**：既有 Tag/Release 为空；latest 实际返回 NOT_FOUND_OR_INACCESSIBLE。没有创建 Tag 或 Release 补覆盖。

[辅助 Schema 与形状诊断](client-evidence/auxiliary/upstream-schema-diagnosis.json) 保存当前官方定义、验证错误和字段类型，不保存私有响应正文。这些发现需独立 Web Review 定向处理，未在 Client 阶段重写主体实现。

## 5. 三个宿主独立结果

| Host | 真实版本 | 固定原生证据结果 | 说明 |
|---|---|---|---|
| Codex | CLI 0.153.4 / Desktop 26.901.41600 (7982) | 9 项固定 Oracle PASS；首次启动缺陷另列 FAIL | 正确 Skill + 8 工具、真实 UI Cancel、单次 Allow 写读回、关闭进程后重启查原 receipt、新会话概念讨论无调用 |
| Cursor | 3.19.13 | BLOCKED | 本次 local plugin 被既有同名 marketplace 插件覆盖；原生 UI 仍为 8 个旧 Skill，MCP 只有 github 的 44 工具，未发现本次 sdlc_github |
| Claude Code | 2.1.204 | discovery / 已运行范围的 workspace / secret PASS；其余 6 项 BLOCKED | 原生发现准确 Skill 和 8 工具；两次显式调用均在模型服务返回 HTTP 522，GitHub 工具未执行 |

**Codex 的固定检查器 PASS 不等于无条件 GH-24 接受。** 首次自然调用选择了未安装 jsonschema 的 system python3，编译器失败；随后显式指定已准备的解释器后，完整写入与 receipt 链通过。首次还错误读取 plugin-root/contracts/github-runtime.md，之后恢复到 skills/_shared/contracts/github-runtime.md；宿主发现过程枚举了工作区目录并搜索 AGENTS.md/SKILL.md。原文件内容未被读取或改变，但“不误扫描”和默认解释器选择仍须 Review。两个首次错误及恢复均保留在原始 transcript，没有只摘取后续成功。

Codex 原生拒绝 request_id：`614b3f87-394b-4a95-8cb3-ae2542c389da`。宿主真实 UI 选择 Cancel，工具报告 `user cancelled MCP tool call`、执行时长 0，没有对应 intent/receipt。允许写入 request_id：`f23738c9-d264-4005-8f3e-99876a41bead`，产生 Issue #4。重启第二个 Host/MCP 进程后，只用 status/operation_status 返回原 receipt，没有新建对象；随后通过明确单次批准关闭 #4。

原生证据：[Codex](client-evidence/native/codex.json) / [原始事件 1](client-evidence/native/codex/session1.native-events.json) / [原始事件 2](client-evidence/native/codex/session2.native-events.json) / [Cursor UI 阻塞](client-evidence/native/cursor/blocked.json) / [Claude Code](client-evidence/native/claude-code.json) / [Claude 原始事件](client-evidence/native/claude-code/session1.native-events.json)。同目录保留去 ANSI 的原生终端 transcript。Cursor 文件明确为 CUA 原生界面实际文本摘录，不是生成的对话。

三宿主顺序执行，数据根分别为 data/codex、data/cursor、data/claude-code。固定 10,000 个原文件所有摘要均未改变；[完整摘要清单](client-evidence/preparation/prepare/WORKSPACE-SHA256.json)。Cursor/Claude 的完整原生工作负载未执行，不能据空数据根或文件未变声称“三端完全隔离 PASS”。

临时 Codex plugin/marketplace 已卸载、Cursor 临时符号链接已移除且测试窗口关闭、Claude 的 session-only plugin 已退出。没有全局 auto-approve。宿主自身可能保留正常的信任与历史会话信息。第一次 Claude 启动请求因工作目录错误被自动审批拒绝、未执行；修正为固定隔离工作区后获准启动，没有绕过审批。

## 6. 身份、持久化与 unknown

真实 Actor A 多次独立进程验证为 ousui/2839512。没有第二真实账号 Token，**GH-03 双真实身份 BLOCKED**。使用 A 与不匹配的 expected_actor_id=1 验证了 ACTOR_MISMATCH/effect=none；这不是 Actor B，也不能证明双身份。

[路径、缓存与重启](client-evidence/persistence/restart-path-cache.json)：原生产路径与已安装路径分别启动，使用相同 data/live，读回同一已确认 request_id。所有 durable 文件摘要不变。生产 Runtime 没有生成 cache；本检查仅删除自己创建的可丢弃 cache sentinel，不能声称测试了不存在的生产缓存内容。

[真实同 ID 竞争与崩溃](client-evidence/persistence/crash-race.json)：两个实际生产 stdio 进程，均验证同一真实 Actor；首个请求持久化 intent 后，第二个同 UUID 请求在获知 unknown 前已发送。首进程在 receipt 尚不存在时 SIGKILL（exit -9）。第二进程返回 EFFECT_UNKNOWN；再次启动后 status + operation_status（含只读 reconcile）仍为 unknown。

必须保留的请求：**`56de6913-edfc-4beb-bc98-a0f0265b7be5`**。其 intent 在 [durable/live](client-evidence/durable/live/56de6913-edfc-4beb-bc98-a0f0265b7be5/intent.json)。这是预期防重放检查 PASS，**不是远端写入 PASS**。仅有两个提前发出的同 ID stdio 调用，不能把它们当作 HTTP 次数。之后没有任何业务写入，也没有删除 state/intent/receipt。

生产只读 reconcile 无法完成（issue.list capability 不可用）；辅助只读查找首 100 条 Issue 未找到该标记，[结果](client-evidence/persistence/auxiliary-remote-lookup.json)。不能据此把 unknown 改为 none，不能改 UUID 重发或自动清理。回执恢复保持 BLOCKED。

本次真实故障覆盖一个 after-intent/before-receipt 进程崩溃窗口。其余精细故障窗口以及独立 SDK-only disconnect 在本轮 A/B 重跑通过，真实 Hosted 分项为 NOT_RUN；不以 Mock 冒充。发生真实 unknown 后，这个固定序列自然结束。

## 7. 对象、秘密与临时目录

- [Codex Issue #4](https://github.com/ousui/sdlc-ai-monitor/issues/4)：closed，确认读回。
- [连续入口 Issue #5](https://github.com/ousui/sdlc-ai-monitor/issues/5)：closed，确认读回。
- [连续入口 Draft PR #6](https://github.com/ousui/sdlc-ai-monitor/pull/6)：closed，仍为 Draft，确认读回；未 merge。
- 普通评论未创建。崩溃请求没有已观察到的对象 URL，仍保持 unknown。

[Secret 扫描](client-evidence/secret-scan.json) 覆盖归档的 stdout/stderr、原生 transcript、validation JSON、intent/receipt 和 Git diff，并在内存中检查本地真实凭据的精确字节；没有保存 Token 或 Token hash。认证头、Cookie、私有正文不进入交付包。原生 transcript 只含必要身份、合成测试内容、工具结果与调用上下文；不复制完整宿主配置。

`$GH_WORK` 表示源码目录旁的稳定 `sdlc-github-client`；目录和 run-state/data/results 全部保留。没有手动在 `/tmp` 写脚本；macOS 路径诊断创建的一个系统 TemporaryDirectory 已自动删除。回归临时目录 `$GH_WORK/test-tmp` 最终为空；虚拟环境和外部字节码缓存保留供复核，不进入 Git。

## 8. 唯一下一工作包：fresh-context Web Review

固定本次 Client 证据提交，依次读本文件、[JSON](CLIENT-VALIDATION.json)、[SHA256SUMS](SHA256SUMS)、原生事件与终端 transcript、真实逐操作结果、unknown intent 和 WEB-VALIDATION。先核验摘要，再核对 FAIL/BLOCKED；区分固定 native checker 的 PASS、真实行为缺陷、环境缺口及 A/B 模拟范围。

重点审查 actions.jobs 嵌套响应、issue.list 状态映射、comment.create 能力探针，以及 Codex 初次解释器/共享合约定位和扫描边界。保留 PR Draft。任何源码修复必须单独形成准确 Runtime SHA，重跑所有受影响 Mock/protocol/regression 和必要真实宿主验证；不能继承 b035880 的 PASS。不要在本次 unknown 请求上进行写入重试，也不要用本批次后续证据覆盖原失败。

复核入口：`ousui/sdlc-ai-spec` → `impl/sdlc-github-foundation-v1` → **本文件所在的准确 Client 提交** → `docs/plugin-development/work-items/sdlc-github/CLIENT-VALIDATION.md`。

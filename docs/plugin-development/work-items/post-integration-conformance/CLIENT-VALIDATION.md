# Client post-integration validation

Producer checkpoint；独立 Web Review 尚未执行。本轮复用 Web 修复，未修改 Runtime、测试、冻结 Oracle 或 accepted Evidence。

## Exact identity

| Identity | Value |
|---|---|
| Repository / branch | `ousui/sdlc-ai-spec` / `fix/post-integration-skill-conformance` |
| Baseline main | `0289a5ee8d702450fb3f3bc73c89f30a11664bdb` |
| Baseline tree | `bb1aa513fe9a67a6cbec0775a6570fae6e50f877` |
| Original Web tested source | `ac6d846a1b0c22d0f284c9ebffd976dc59698a99` |
| Received Web delivery / CLIENT VALIDATED_SOURCE_SHA | `fb1d8fb989e5e31d75cd6f311c0e5e663437262d` |
| Client validated source tree | `cb1a9aa31a2fadb8a434493b75c7a244d38d029b` |
| Client | `codex-cli 0.153.4`, macOS `26.5.1` / `25F80`, Python `3.14.7` |

Client 在独立干净 worktree 对 `fb1d8fb...` 实际执行两套 Profile。它相对 `ac6d846...` 只增加三份 Web 结果文档，Runtime、测试和验证器完全相同。最终 DELIVERY_HEAD_SHA 是承载本记录的后续文档/回执提交；准确值在 PR #11 的交付表和提交后远程 readback 中记录，避免提交内容自引用自身 SHA。不得把最终文档提交写成实际被测源码。

## Runtime execution

| Actual gate | Result |
|---|---|
| Portable Profile | PASS，10/10 步骤，源码前后干净且完全一致 |
| Strict Profile | PASS，13/13 步骤，源码前后干净且完全一致 |
| 八个 Skill 的 Interface / Source Lock | PASS；Status 51 条锁 |
| Status 原始固定 Eval / coverage guard | 14/14 / 4/4 PASS |
| Status installed-copy | 12 条命令 PASS；无 docs/tests/tools/兄弟 Skill |
| VFY strict fixed Eval | 80/80 PASS；使用真实 macOS OS containment |
| RLS fixed Eval | 87/87 PASS |
| 完整普通仓库回归 | 两个 Profile 分别 1104/1104；零 failure/error/skip/expectedFailure/unexpectedSuccess |
| VFY / RLS installed-copy | PASS / PASS |
| Runtime 原始流绑定 | 46/46 个 stdout/stderr 归档字节绑定通过 |
| 全部归档流绑定 | 75 份 process receipt、150 个 stdout/stderr 绑定通过 |
| 唯一测试 ID | 两份日志各 1104 个，与同源码、同 top_level_dir 的实际 collection 集合完全相同 |

不能相加重复 Profile、子集和 coverage guard，不能把普通回归写成 1108 项。七阶段测试根、原 Eval Plan、Spec、共享 Package、Workflow 和历史 Evidence 均未修改。`scope-audit.json` 保存允许 Diff 和冻结测试根检查。

初次外层沙箱内探针返回 `sandbox_apply: Operation not permitted`；通过执行权限审查后，宿主可正常启动 `sandbox-exec`。实际 Strict 未使用无沙箱 fallback。两个探针和退出码均保留。

## Native Codex CLI observations

每个 Skill 有独立一次性项目、原生 Marketplace 安装和独立安装缓存。缓存仅包含该 Skill、共享 Runtime/Package 和平台组件；安装前后快照均绑定上述 exact source。没有把预构造 Invocation 或 Runtime 答案交给宿主。Fixture 和 Oracle 在首次宿主调用前冻结，最终判断由 producer 对原始 trace 和项目快照检查得出，不使用模型自评。

| Skill | 本地缺 Authority 场景 | 正式 Runtime | 候选 Behavior |
|---|---|---|---|
| sdlc-000-ctx | `STORE_NOT_FOUND` | 实际调用 | PASS，限定只读场景 |
| sdlc-100-req | Authority 预检返回 `STORE_NOT_FOUND` | NOT_RUN；宿主明确 `runtime_executed=false` | PARTIAL |
| sdlc-200-dsn | `STORE_NOT_FOUND` | 实际调用 | PASS，限定只读场景 |
| sdlc-300-pln | `STORE_NOT_FOUND` | 实际调用 | PASS，限定只读场景 |
| sdlc-400-imp | `STORE_NOT_FOUND`，无 VFY ready 结论 | 实际调用 | PASS，限定只读场景 |
| sdlc-500-vfy | `STORE_NOT_FOUND` | 实际调用 | PASS，限定只读场景 |
| sdlc-600-rls | `STORE_NOT_FOUND` | 实际调用；无 Effect Authorization | PASS，限定只读场景 |
| sdlc-status | exact REQ 失败；裸调用 `not_started` | 两种路径均实际调用 | PASS，限定只读场景 |

八份候选都独立记录 installation、discovery、explicit_invocation、negative_invocation、behavior、permissions、installed_independence。Discovery 包含同一 CLI 二进制的原生 `skills/list` 记录：名称、enabled、pluginId 和安装缓存路径均匹配；该只读 provider 查询没有创建 App 会话，也不认证 Codex App。

所有未调用对照仅读取 README，没有隐式执行 Skill。原生宿主使用 read-only OS 沙箱和 `approval_policy=never`；八个项目的文件字节/权限均未变化，未创建 `.sdlc`。Status 正确显示未安装的 CTX 只能作为下一动作，未自动调用它。

## Preserved limitations and failure paths

- REQ 仅观察到原生 Skill 的前置 Authority 拒绝。共享 API 的预检轨迹没有冒充正式 Runtime 执行，Behavior 保持 PARTIAL。
- 八个宿主会话在 `--output=json` 下仍有中途进度消息；CTX、IMP 的最终 JSON 还改写了 Runtime 的说明文字。原始 Runtime 输出、最终输出和比较结果都保留，交给独立 Review 判断宿主输出边界。
- CTX 的附加 `lstat` 失败、REQ 的无匹配搜索/只读约束、RLS 的错误私有路径读取和预检失败均保留。预期的缺 Store 非零退出也未删去。
- CLI 后台 curated catalog 同步出现超时/HTTP 429 和回退日志。这是宿主后台流量；不能宣称整个 CLI 零网络，也不能把它计作 Skill Runtime 主动联网。
- 本轮 native Fixture 未执行正向 create/revise/run/execute/finalize，也未产生真实业务批准、Effect Authorization 或 Final Confirmation。RLS 固定评测/安装评测中的本地 Sandbox 不能替代生产批准。
- 配置的模型/推理值来自既有本地配置；CLI JSON 流没有独立实际模型执行证明，未将配置值冒充 actual execution。
- 归档器使用已接受的 `tools.rls_validation_support` 在首次归档前脱敏。两次临时 ID 审计的格式假设错误及一次 digest 前缀比较错误已保留；修正的是审计方法，没有改测试、Oracle 或原日志。
- 原 Web 附件未包含在本次输入中；原 `WEB-VALIDATION.json` 和历史记录保持不变。本交付附带本次 exact-source 重跑的全部日志，不声称已独立审计未取得的旧附件。

这些是 producer 候选，不是 ACCEPTED。`COMPATIBILITY.json` 字节不变：40 个当前认证单元仍为 NOT_RUN/receipt=null；其他载体没有执行，也没有因本机缺工具被标为 Unsupported。

## Review handoff

唯一下一工作包：`POST_INTEGRATION_WEB_REVIEW`。按 [WEB-REVIEW.md](WEB-REVIEW.md) 独立审查最新 PR #11、上述 VALIDATED_SOURCE_SHA、PR 的准确 DELIVERY_HEAD_SHA、[CLIENT-VALIDATION.json](CLIENT-VALIDATION.json)、[CLIENT-ARCHIVE-AUDIT.json](CLIENT-ARCHIVE-AUDIT.json)、[CLIENT-NATIVE-SUMMARY.json](CLIENT-NATIVE-SUMMARY.json) 和 SHA-256 manifest。

`CLIENT-ARCHIVE-AUDIT.json` 将原始 `/tmp` 日志地址映射到仓库相对归档路径；原 receipt 本身保留原字节。`CLIENT-SHA256-MANIFEST.json` 覆盖本轮新增交付文件，不包含自身。完整 fixture/安装缓存和脱敏日志保留在 `/tmp/sdlc-*01a07250`；私有认证引用在归档后移除，client-state 目录不进入 Git。

分发仓库元数据保持原值，仍需 Maintainer 发布前决定。保持 Draft，不 merge，不自动进入下一开发阶段。

```text
POST_INTEGRATION_RUNTIME = PASS
VALIDATED_SOURCE_SHA = fb1d8fb989e5e31d75cd6f311c0e5e663437262d
NATIVE_OBSERVED_SURFACE = codex-cli
NATIVE_CANDIDATES = 8
NATIVE_INDEPENDENT_REVIEW = REQUIRED
WEB_CONFORMANCE_REVIEW = REQUIRED
REAL_TARGET_EFFECTS = 0
MAIN_MODIFIED = NO
PR_MERGED = NO
```

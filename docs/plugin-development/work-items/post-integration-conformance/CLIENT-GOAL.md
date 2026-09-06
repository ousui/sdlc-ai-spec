# Client Goal — Post-integration validation and one-surface adaptation

将本文全文作为一个 Goal。不要读取旧 RLS Goal 后重建 S4/E4。

## Baseline / ownership

Repository `ousui/sdlc-ai-spec`。工作分支仅 `fix/post-integration-skill-conformance`，Draft PR #11，基线 main `0289a5ee8d702450fb3f3bc73c89f30a11664bdb`，tree `bb1aa513fe9a67a6cbec0775a6570fae6e50f877`。用户已经授权本修复包；未授权更改 main、accepted Phase Runtime、既有 Evidence、共享 Package、Workflow、安装系统依赖或真实发布。

## Start

1. fetch 新 Ref，记录实际 main/branch SHA/tree、工作树状态和宿主能力。不要覆盖未知工作；使用独立干净 worktree。若 branch 与 Web 交接 Head 不同，先审查新增提交，不强制覆盖。
2. 读取 WORK-PACKAGE、STAGE-REVIEW、SKILL-INVENTORY、COMPATIBILITY.json 和 Status CONFORMANCE-REVIEW。当前 main 内容已包含最终 IMP/VFY/RLS；旧 PR 状态不再是合入前提。
3. 检查可用 OS 沙箱；不安装、不用无沙箱 fallback。缺失时记录真实能力阻塞，不把普通能力负向路径当 strict VFY PASS。

## Runtime verification

在 exact 当前源码、干净 worktree 执行：

```bash
SHA=$(git rev-parse HEAD)
python3 tools/run_post_integration_validation.py --profile portable --source-sha "$SHA" --json-out /tmp/post-integration-portable.json
python3 tools/run_post_integration_validation.py --profile strict --source-sha "$SHA" --json-out /tmp/post-integration-strict.json
```

两者必须实际完成并成功；严格 Profile 包含真实 VFY 固定 Eval 与安装验证。缺文件/超时/错误/skip/expectedFailure 不算 PASS。检查原始 Status 14 个 Case 和 Phase Case Expected 未减少/弱化；所有八 Skill 锁验证，Status lock 只能在有理由源码修复后通过显式 build 生成，再独立验证。

如有真实失败，在本分支做最小修复和永久回归，再形成新 exact SHA 重跑。不要为了适配新分支去修改旧 `validate_rls_delivery_source.py` 的 S3 拓扑要求；它用于历史 RLS 交付，本包使用自己的 exact-main-ancestor gate。

## One real Client / Surface

一次仅对当前实际可用 Client/Surface执行八个 Skill，优先本次运行所在的 Codex CLI；CLI 结果不外推 App，不强制同时安装其他 Client。

每个 Skill 使用独立一次性项目和无 docs/tests/Handoff 的真实安装缓存。业务输入由安装后的 Skill 合约决定，不预注入 Runtime 答案；用已冻结本地 fixture 验证结果，而不是让模型判自己的 PASS。七维必须分别记录：installation、discovery、explicit_invocation、negative_invocation、behavior、permissions、installed_independence。

对写入型 Skill，真实用户决定、Example/Fixture 操作、Effect Authorization 和 Final Confirmation 明确分开。RLS 仅本地专属 Sandbox；不得将人工观察伪装成真实产品批准。不自动授予第三方平台、Git、部署或云权限。缺失上游输入必须按合约拒绝，而不是跳 Skill 或换成直接 Python 调用来冒充 native Behavior。

原始宿主 trace/log 在第一次归档前脱敏；使用已接受的 `tools.rls_validation_support`，摘要覆盖归档字节。保留失败与重试，不删除不利记录。

## Candidate native receipt

每个候选 JSON 必须包含：

- contract=`sdlc-ai-spec/native-skill-receipt/v1`；observation_source=`native_host`；准确 skill/surface；
- source_sha、client_version、带时区 observed_at、operator；
- `runtime_snapshot_sha256`：使用 `tools.validate_skill_conformance.runtime_snapshot(root,skill,surface,source_sha=SHA)`，不得从 docs 或历史 CTX 摘要复制；
- checks，按照工具 DIMENSIONS 顺序，逐项 result 和原始非空 evidence 的仓库相对 path/sha256；
- 独立 Review 字段只由后续独立审查填写，Client 不得写 ACCEPTED 冒充复核。

候选放在当前 Work Item 的独立 `native-candidates/<surface>/<skill>/` 下。未接受前 `COMPATIBILITY.json` 仍 NOT_RUN/receipt=null，不把候选当已认证。其他未运行载体保持 NOT_RUN；某载体不支持需要真实版本证据，不能仅凭缺工具标 Unsupported。

## Deliver

保存 runtime exact-source 结果与全部日志、SHA-256 manifest、宿主候选和失败轨迹、 before/after main/ref/worktree 状态。本包交付记录放本 Work Item，不写入历史 Phase evidence。先完成源提交与验证，再追加仅文档/回执提交，记录明确 VALIDATED_SOURCE_SHA 与 DELIVERY_HEAD_SHA；普通 fast-forward push，重读 Ref，更新原 Draft PR #11，不创建分支链或重新 squash accepted 上游。

分发仓库元数据当前 goedgecloud/ousui 差异未获决定，保持原值；列为 Maintainer 发布前选择，不当 Runtime failure，也不擅自迁移。

## Final output

成功的 runtime outcome：

```text
POST_INTEGRATION_RUNTIME = PASS
VALIDATED_SOURCE_SHA = <actual>
DELIVERY_HEAD_SHA = <actual>
NATIVE_OBSERVED_SURFACE = <actual or NOT_RUN>
NATIVE_INDEPENDENT_REVIEW = REQUIRED
WEB_CONFORMANCE_REVIEW = REQUIRED
REAL_TARGET_EFFECTS = 0
MAIN_MODIFIED = NO
PR_MERGED = NO
```

不可恢复的真实 runtime 阻塞输出 `POST_INTEGRATION_RUNTIME = HARD_BLOCKED`，首个失败、实际/预期 SHA、保留分支和已完成检查。单个 native 载体不可用时分开记录 HOST_CAPABILITY_UNAVAILABLE，不伪造全产品 PASS，也不否定已经成功的 runtime 验证。不得以等待或以后继续代替交付。

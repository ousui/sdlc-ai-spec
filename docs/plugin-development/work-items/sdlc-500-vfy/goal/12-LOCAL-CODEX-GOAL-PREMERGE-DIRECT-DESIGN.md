# Local Codex `/goal` — VFY 直接设计血缘闭环与 Evidence 交付

将本文**全文**作为一个独立的本地 Codex `/goal` 任务执行。

不要把本文拆成多轮普通 Chat；不要在完成一次测试、创建 Commit、推送分支或更新
PR 后提前停止。必须持续执行、读取第一处真实失败、修复并重新验证，直到得到本文
规定的唯一终态之一：

```text
VFY_CLOSED_LOOP = PASS
```

或：

```text
VFY_CLOSED_LOOP = HARD_BLOCKED
```

禁止以 `RUNNING`、`PENDING`、`WAITING_FOR_GITHUB`、`PARTIAL_PASS` 或“稍后继续”
作为最终结果。

---

## 0. 本版规则的唯一变化

本 Goal **不要求 VFY Design PR #7 先合并到 `main`**。

本次采用：

```text
VFY_INTEGRATION_MODE = PREMERGE_DIRECT_DESIGN_ANCESTRY
```

物理血缘固定为：

```text
origin/design/sdlc-500-vfy-goal@<CURRENT_DESIGN_HEAD>
    ↓
feat(vfy): implement deterministic verification phase
    ↓
chore(vfy): archive verification evidence and handoff
```

因此：

- 当前准确 Design Head 是 Implementation Subject 的直接父提交；
- `main` 在整个任务中只读；
- PR #7 可以继续保持 Draft、Open、Unmerged；
- PR #7 未合并不是启动阻塞；
- `impl/vfy-v2` 即使当前与 Design Head 分叉，也可作为只读的 Web Initial
  Implementation Source Snapshot；
- 必须在一个新的候选 Worktree 中，从准确 Design Head 重建唯一 Implementation
  Subject；
- 禁止在分叉的旧实现树上执行 `git reset --soft "$DESIGN_HEAD"`，因为这会把旧血缘
  中的无关文档、Workflow、历史阶段内容和过期设计一并卷入 Subject；
- 最终未来进入 `main` 时，仍应先以 **Create a merge commit** 合并 Design PR，
  再处理 Implementation PR；但本 Goal 不执行任何合并。

本文取代旧 Goal 中“Design PR 必须先合并”及“旧实现分支必须已经包含 Design Head”
这两个启动条件。其他更严格的设计、测试、Evidence、Git 和安全约束继续有效。

---

# 一、唯一目标

完成 `ousui/sdlc-ai-spec` 的 `sdlc-500-vfy` 本地闭环：

1. 从当前准确 `design/sdlc-500-vfy-goal` Head 建立干净的 Implementation Subject；
2. 从当前 `impl/vfy-v2` 只读提取有效的 Web Initial Implementation；
3. 修正所有设计、实现、测试、Source Lock、Runtime Independence 和接口缺口；
4. 完整执行 `quick → phase → full → external → attest`；
5. 对每一处失败读取第一处真实根因并反复修复；
6. 将最终实现收敛为一个直接位于 Design Head 之后的 Subject Commit；
7. 对该准确 Subject 执行 Fresh exact-SHA Attestation；
8. 在同一 `impl/vfy-v2` 上追加独立 Evidence/Handoff Commit；
9. 更新现有 Implementation Draft PR，保持 Draft、未合并；
10. 不修改 `main`，不开始 RLS。

最终历史必须收敛为：

```text
<CURRENT_DESIGN_HEAD>
    ↓
feat(vfy): implement deterministic verification phase
    ↓
chore(vfy): archive verification evidence and handoff
```

---

# 二、固定身份、启动观察值与动态值

仓库：

```text
REPOSITORY = ousui/sdlc-ai-spec
```

固定语义输入：

```text
IMP_IMPLEMENTATION_SUBJECT_SHA =
207a4a16bea8979faee0474cc43cb642cef1f655

IMP_DELIVERY_SHA_AT_DESIGN =
86aaa04a0238d3151606073e89219eea0d60b7d3
```

已批准的 VFY Design 基础提交：

```text
VFY_APPROVED_DESIGN_BASE_SHA =
ea49c1df955bc71ec1af84d6104f3cd801c73ea2
```

启动时最近观察值，仅作 CAS 和漂移检查提示，禁止盲信：

```text
OBSERVED_MAIN_SHA =
3a2f13082fe2f661081ded74e45f860da2046bd1

OBSERVED_IMPL_HEAD =
7981088ecea897e16795b3ea6f721d32f6fd6a44

DESIGN_PR_NUMBER = 7
IMPLEMENTATION_PR_NUMBER = 9
```

开始后必须重新读取：

```text
CURRENT_MAIN_SHA
CURRENT_MAIN_TREE
CURRENT_DESIGN_HEAD
CURRENT_DESIGN_TREE
CURRENT_IMPL_HEAD
CURRENT_IMPL_TREE
DESIGN_PR_STATE
DESIGN_PR_HEAD_SHA
DESIGN_PR_BASE
IMPLEMENTATION_PR_STATE
IMPLEMENTATION_PR_HEAD_SHA
IMPLEMENTATION_PR_BASE
```

任何本文中的观察 SHA 都不能替代重新读取。

---

# 三、Authority 顺序

按以下顺序裁决冲突：

```text
docs/v1.1/500-vfy-spec.md
> bundled stable runtime contracts
> integrated IMP Runtime and formal IMP Evidence
> current design/sdlc-500-vfy-goal DESIGN.md and EVAL-PLAN.md
> current design goal package
> this direct-design-ancestry Goal
> current implementation and tests
```

特别规则：

- 分支、Tag、PR、`latest`、`current` 和 Lifecycle Projection 不是产品 Subject
  Authority；
- VFY 产品 Subject 必须是准确的 immutable Product Resource Result；
- Subject 必须绑定 Current completed Claim、冻结 IMP Revision、Result Digest、
  Binding Lineage、Attempt 和连续有效依赖链；
- Implementation Subject SHA 是仓库交付对象，不是产品级 VFY Subject；
- 生产 Runtime 不读取 `docs/**`；
- GitHub Actions 不是验证或交付 Authority。

---

# 四、绝对禁止

整个 Goal 禁止：

```text
修改或提交 main
merge PR #7
merge Implementation PR
rebase main、design 或 impl 分支
使用裸 git push --force
覆盖发生漂移的远程 Ref
创建 VFY evidence 分支
创建 internal/vfy-*
创建 GitHub Actions Workflow
把 Workflow 结果当交付 Authority
开始或实现 RLS
调用 RLS
发布产品
写真实外部业务仓库
向真实项目远端 push
安装依赖
自动调用上游或下游 Skill 来替代测试 Harness 的显式阶段执行
伪造 manual/hybrid Evidence
删除测试
使用 skip 或 expectedFailure 冒充 PASS
弱化断言、Expected、Case Mapping、Source Lock 或 Runtime Independence
把 required 改成 n/a/waived 来绕过失败
把 Artifact ready 当成 product pass
把产品 fail 隐藏成 Gate fail
```

同时禁止：

```text
Observer
Finalizer
Materializer
Payload
Chunk
Release Asset
base64/xz 源码包
等待型 Workflow
自动 push main
自动 merge
```

---

# 五、启动 Gate：重新读取真实状态

在用户当前仓库中执行：

```bash
set -euo pipefail

ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"

git remote -v
git status --short
git worktree list --porcelain
git fetch --all --prune

CURRENT_MAIN_SHA=$(git rev-parse origin/main)
CURRENT_MAIN_TREE=$(git rev-parse origin/main^{tree})
CURRENT_DESIGN_HEAD=$(git rev-parse origin/design/sdlc-500-vfy-goal)
CURRENT_DESIGN_TREE=$(git rev-parse origin/design/sdlc-500-vfy-goal^{tree})
CURRENT_IMPL_HEAD=$(git rev-parse origin/impl/vfy-v2)
CURRENT_IMPL_TREE=$(git rev-parse origin/impl/vfy-v2^{tree})
```

使用已认证 `gh` 或等价只读 GitHub 接口重新读取 PR #7 和 Implementation PR：

```bash
gh pr view 7 --repo ousui/sdlc-ai-spec \
  --json number,state,isDraft,headRefName,headRefOid,baseRefName,mergeCommit,url,body

gh pr view 9 --repo ousui/sdlc-ai-spec \
  --json number,state,isDraft,headRefName,headRefOid,baseRefName,mergeCommit,url,body
```

必须验证：

1. `origin/main` 可读取；
2. `origin/design/sdlc-500-vfy-goal` 可读取；
3. `origin/impl/vfy-v2` 可读取；
4. PR #7 的 head 为 `design/sdlc-500-vfy-goal`，base 为 `main`；
5. PR #7 可以是 Open/Draft/Unmerged；这不是阻塞；
6. Implementation PR 的 head 为 `impl/vfy-v2`，base 为 `main`；
7. `VFY_APPROVED_DESIGN_BASE_SHA` 是 `CURRENT_DESIGN_HEAD` 的祖先：

```bash
git merge-base --is-ancestor \
  ea49c1df955bc71ec1af84d6104f3cd801c73ea2 \
  "$CURRENT_DESIGN_HEAD"
```

8. 从批准基础到当前 Design Head 的新增变化只位于：

```text
docs/plugin-development/work-items/sdlc-500-vfy/**
```

9. 当前 Design Head 仍包含：

```text
docs/plugin-development/work-items/sdlc-500-vfy/DESIGN.md
docs/plugin-development/work-items/sdlc-500-vfy/EVAL-PLAN.md
docs/plugin-development/work-items/sdlc-500-vfy/goal/00-BASELINE.json
docs/plugin-development/work-items/sdlc-500-vfy/goal/01-DESIGN-REVIEW.md
docs/plugin-development/work-items/sdlc-500-vfy/goal/02-IMP-VFY-INTERFACE.md
docs/plugin-development/work-items/sdlc-500-vfy/goal/03-ARCHITECTURE.md
docs/plugin-development/work-items/sdlc-500-vfy/goal/04-STATE-MACHINE.md
docs/plugin-development/work-items/sdlc-500-vfy/goal/05-CRITICAL-CASE-MATRIX.md
docs/plugin-development/work-items/sdlc-500-vfy/goal/06-IMPLEMENTATION-PLAN.md
docs/plugin-development/work-items/sdlc-500-vfy/goal/07-VALIDATION-CLOSE-LOOP.md
docs/plugin-development/work-items/sdlc-500-vfy/goal/08-TRACEABILITY.md
docs/plugin-development/work-items/sdlc-500-vfy/goal/10-WEB-REPORT-REVIEW.md
docs/plugin-development/work-items/sdlc-500-vfy/goal/11-DESIGN-HANDOFF.md
```

10. `DESIGN.md` 的状态仍为 approved，且没有开放 Blocker/Major；
11. 当前 `main` 完整包含 IMP Runtime 和正式 Evidence；
12. IMP Final Result 的 `status == PASS`；
13. IMP Implementation Subject 仍为
    `207a4a16bea8979faee0474cc43cb642cef1f655`；
14. 当前 `main` 未被本地工作树修改；
15. 没有其他进程正在写相同实现 Worktree 或同一 `.sdlc` Store。

正式 IMP 路径：

```text
skills/sdlc-400-imp/SKILL.md

docs/plugin-development/work-items/sdlc-400-imp/evidence/
207a4a16bea8979faee0474cc43cb642cef1f655/
impl-imp-v2-handoff.md

docs/plugin-development/work-items/sdlc-400-imp/evidence/
207a4a16bea8979faee0474cc43cb642cef1f655/
impl-imp-v2-final-result.json

docs/plugin-development/work-items/sdlc-400-imp/evidence/
207a4a16bea8979faee0474cc43cb642cef1f655/
impl-imp-v2-repository.sha256
```

以下情况立即 HARD_BLOCKED：

- Design Head 不再包含批准基础；
- Design 漂移包含非 VFY Work Item 路径；
- PR #7 指向其他 head/base；
- main 缺失正式 IMP Runtime/Evidence；
- IMP Final Result 非 PASS；
- Current Implementation PR 指向其他 head/base；
- 发现无法解释的远程 `impl/vfy-v2` 漂移；
- 用户工作树存在未知修改且无法隔离；
- 存在未知正式 VFY Evidence，无法证明属于同一 Subject。

PR #7 未合并**不得**作为 HARD_BLOCKED 原因。

---

# 六、状态分类与幂等恢复

读取当前 `impl/vfy-v2` 历史后，将其分类为且只能为以下一种模式。

## A. `ALREADY_CLOSED`

满足：

```text
CURRENT_DESIGN_HEAD
    ↓
feat(vfy): implement deterministic verification phase
    ↓
chore(vfy): archive verification evidence and handoff
```

并且 Evidence 完整、Digest 可验证、全部 `source_sha` 指向 Subject。

此时不要重写分支。重新执行 Fresh Attestation 和 Evidence 校验；通过后输出 PASS。

## B. `RESUME_VALID_SUBJECT`

满足：

- `CURRENT_DESIGN_HEAD` 是当前 Implementation Subject 的直接父提交；
- 当前分支只有一个尚未正式归档 Evidence 的 Subject Commit；
- 没有未知额外提交。

从该 Subject 继续修复、amend 和验证。

## C. `REBUILD_FROM_WEB_SNAPSHOT`

满足：

- 当前 `impl/vfy-v2` 与 Design Head 分叉，或包含 Web 逐文件持久化的多提交历史；
- 当前内容确实包含可识别 VFY 初始实现；
- 没有不可替代的正式 Evidence；
- 没有未知并行交付。

把 `CURRENT_IMPL_HEAD` 当成**只读源码快照**，从 Design Head 新建候选分支，按本文白名单迁移。

当前预期通常属于此模式。

## D. `REF_CONFLICT`

存在：

- 远程 Ref 在读取后发生变化；
- 未知有效提交；
- Evidence 指向无法确认的 Subject；
- 实现 PR 的 Head 不再是 `impl/vfy-v2`。

不得覆盖，输出 HARD_BLOCKED。

---

# 七、持久 Worktree 与灾难恢复

禁止在用户正在使用的工作副本中执行重写。

创建两个持久 Worktree：

```bash
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
STATE_ROOT="${HOME}/.local/state/sdlc-ai-spec/vfy-goal-${STAMP}"
SOURCE_WT="${STATE_ROOT}/source"
CANDIDATE_WT="${STATE_ROOT}/candidate"
ATTEST_WT="${STATE_ROOT}/attest"
RESULT_ROOT="${STATE_ROOT}/results"

mkdir -p "$STATE_ROOT" "$RESULT_ROOT"

git worktree add --detach "$SOURCE_WT" "$CURRENT_IMPL_HEAD"
git worktree add --detach "$CANDIDATE_WT" "$CURRENT_DESIGN_HEAD"
```

创建本地灾难恢复引用：

```bash
git branch "local/checkpoint/vfy-web-${STAMP}" "$CURRENT_IMPL_HEAD"
git branch "local/checkpoint/vfy-design-${STAMP}" "$CURRENT_DESIGN_HEAD"
```

禁止推送 `local/checkpoint/*`。

记录到 `${STATE_ROOT}/baseline.json`：

```text
repository root
origin URL
CURRENT_MAIN_SHA/TREE
CURRENT_DESIGN_HEAD/TREE
CURRENT_IMPL_HEAD/TREE
PR #7 state/head/base
Implementation PR state/head/base
完整 refs 摘要
两个 Worktree 的 status
实现分支相对 Design Head 的 commit/diff 清单
生成时间
```

`SOURCE_WT` 永远只读，不在其中 reset、commit、clean、checkout 其他分支或写测试产物。

---

# 八、从 Design Head 安全重建实现

## 8.1 关键规则

**绝对禁止**在旧实现 Worktree 中运行：

```bash
git reset --soft "$CURRENT_DESIGN_HEAD"
git rebase "$CURRENT_DESIGN_HEAD"
git merge "$CURRENT_DESIGN_HEAD"
```

原因：旧实现与 Design Head 可能分叉，直接 reset/rebase 会混入旧 `main`、过期
Design、其他 Phase、Workflow 和历史治理文件。

正确方式：

```bash
cd "$CANDIDATE_WT"
git switch -c "local/vfy-goal-${STAMP}" "$CURRENT_DESIGN_HEAD"
```

然后仅从 `$CURRENT_IMPL_HEAD` 迁移允许范围。

## 8.2 自动允许迁移的私有 VFY 路径

可以直接从 Source Snapshot 提取并审查：

```text
skills/sdlc-500-vfy/**
tests/skill_vfy/**
tests/evals/run_sdlc_500_vfy_eval.py
tests/evals/sdlc_500_vfy_cases.json
tests/evals/test_sdlc_500_vfy_case_coverage.py
tests/evals/vfy_case_harness.py
tests/system_integration/test_external_vfy_integration.py
tools/validate_sdlc_500_vfy_case_coverage.py
tools/validate_sdlc_500_vfy_source_lock.py
tools/test_sdlc_500_vfy_runtime_independence.py
tools/run_external_vfy_integration.py
tools/run_vfy_delivery_validation.py
```

示例：

```bash
git checkout "$CURRENT_IMPL_HEAD" -- \
  skills/sdlc-500-vfy \
  tests/skill_vfy \
  tests/evals/run_sdlc_500_vfy_eval.py \
  tests/evals/sdlc_500_vfy_cases.json \
  tests/evals/test_sdlc_500_vfy_case_coverage.py \
  tests/evals/vfy_case_harness.py \
  tests/system_integration/test_external_vfy_integration.py \
  tools/validate_sdlc_500_vfy_case_coverage.py \
  tools/validate_sdlc_500_vfy_source_lock.py \
  tools/test_sdlc_500_vfy_runtime_independence.py \
  tools/run_external_vfy_integration.py \
  tools/run_vfy_delivery_validation.py
```

路径在 Source Snapshot 不存在时，记录为实现缺口；不得将缺失计为 SKIP。

## 8.3 需要逐文件三方审查的共享路径

以下路径不能整目录覆盖，必须比较：

```text
CURRENT_DESIGN_HEAD
CURRENT_IMPL_HEAD
当前稳定上游实现
```

只允许最小 additive change：

```text
packages/sdlc_lifecycle/query_vfy.py
packages/sdlc_lifecycle/__init__.py
packages/sdlc_lifecycle/models.py
packages/sdlc_lifecycle/CONTRACT.md

skills/sdlc-status/SKILL.md
skills/sdlc-status/references/contract.md
skills/sdlc-status/references/status-result.schema.json
skills/sdlc-status/scripts/runtime.py
skills/sdlc-status/scripts/vfy_projection.py

tools/validate_late_phase_source_lock.py
tools/test_late_phase_runtime_independence.py
tests/evals/late_phase_eval.py
```

必要时允许最小兼容性测试变化：

```text
tests/lifecycle/**
tests/skill_status/**
tests/skill_dsn/**
tests/skill_pln/**
tests/skill_imp/**
tests/late_foundations/**
```

但每一项共享变化必须：

- 有明确 VFY 设计条款；
- 有回归测试；
- 不改变 CTX/REQ/DSN/PLN/IMP 既有语义；
- 不覆盖 Design Head 中更新的共享实现；
- 不复制 ArtifactStore、Claim Provider、Resource Result 或 IMP Lifecycle；
- 不实现 RLS。

## 8.4 严格禁止从旧实现迁移的路径

不得从 `CURRENT_IMPL_HEAD` 覆盖：

```text
.github/**
docs/plugin-development/HANDOFF.md
docs/plugin-development/architecture/**
docs/plugin-development/work-items/sdlc-300-pln/**
docs/plugin-development/work-items/sdlc-400-imp/**
docs/plugin-development/work-items/sdlc-500-vfy/DESIGN.md
docs/plugin-development/work-items/sdlc-500-vfy/EVAL-PLAN.md
docs/plugin-development/work-items/sdlc-500-vfy/goal/00-*
docs/plugin-development/work-items/sdlc-500-vfy/goal/01-*
docs/plugin-development/work-items/sdlc-500-vfy/goal/02-*
docs/plugin-development/work-items/sdlc-500-vfy/goal/03-*
docs/plugin-development/work-items/sdlc-500-vfy/goal/04-*
docs/plugin-development/work-items/sdlc-500-vfy/goal/05-*
docs/plugin-development/work-items/sdlc-500-vfy/goal/06-*
docs/plugin-development/work-items/sdlc-500-vfy/goal/07-*
docs/plugin-development/work-items/sdlc-500-vfy/goal/08-*
docs/plugin-development/work-items/sdlc-500-vfy/goal/09-*
docs/plugin-development/work-items/sdlc-500-vfy/goal/10-*
docs/plugin-development/work-items/sdlc-500-vfy/goal/11-*
docs/plugin-development/work-items/sdlc-500-vfy/goal/12-CLIENT-IMPLEMENTATION-GOAL.md
docs/plugin-development/work-items/sdlc-500-vfy/goal/12-CLIENT-RUN-HANDOFF.md
docs/plugin-development/work-items/sdlc-600-rls/**
skills/sdlc-600-rls/**
tests/skill_rls/**
tools/*rls*
```

当前 Design Head 中的 Goal 文件是 Authority，必须保持字节不变。

旧 `13-INITIAL-IMPLEMENTATION-HANDOFF.md` 不直接复制。需要时依据重建后的准确事实重新生成，
并放入 Implementation Subject；不得保留过期 SHA、过期 Design Base 或虚假 PASS。

## 8.5 重建后静态断言

必须验证：

```bash
git diff --check
git status --short
git diff --name-only "$CURRENT_DESIGN_HEAD"...HEAD
```

并确认：

- Design Authority 文件与 `CURRENT_DESIGN_HEAD` 字节完全一致；
- 没有 `.github/**` 变化；
- 没有 `sdlc-600-rls`、`skill_rls` 或 RLS 工具变化；
- 没有 Evidence；
- 没有未知历史阶段文件变化；
- 所有实现变化都属于 VFY 或必要最小共享扩展。

---

# 九、VFY 实现必须达到的能力

必须实现并实际测试：

## 9.1 命令与参数

```text
auto
create
run
revise
check
help
version
commands
examples
```

参数：

```text
repeatable --input/-i
repeatable --method/-m
exact --reference/-r
```

要求：

- 未知参数 fail closed；
- 缺值 fail closed；
- 冲突命令 fail closed；
- meta command 不扫描项目、不打开 Store、不写文件；
- `check` 从调用到退出保持绝对只读。

## 9.2 Scope、Subject、Target

- 一个完整 Delivery Scope；
- PLN required 时使用完整 PLN，而不是局部 Work Item；
- Current terminal IMP Subject Set；
- Current completed Claim；
- frozen IMP Revision；
- immutable Product Resource Result；
- Result Digest；
- Binding Lineage、Attempt、Owner；
- Dependency Result References；
- stale Subject 检测；
- VFO 优先；
- DSN 合法 n/a/waived 时，AC 为 verification Target，Goal/Intended Use 为
  validation Target；
- 不在 VFY 中创造上游 Target、Pass Criteria 或业务决定。

## 9.3 Method Contract 与执行

Method Type 只能是：

```text
inspection
analysis
demonstration
test
```

Execution Mode 只能是：

```text
automated
manual
hybrid
```

每个 Method 必须绑定：

```text
VFM ID
Purpose
Target References
Subject References
Obligation References
Disposition
Executor Identity
Execution Mode
Environment/Data
Procedure/Basis
Pass Criteria
Evidence Requirement
```

执行要求：

- 执行前持久化并读回完整 Pre-execution Checklist；
- 自动命令使用 argv，不使用 Shell 拼接；
- cwd 限制在项目根内；
- 有界 timeout 和输出大小；
- 禁止 install、publish、deploy、release、远端 Git 写；
- 工具不可用时保持 pending/action_required 或合法 waived，不得写 n/a；
- manual/hybrid 只接受真实结构化观察；
- Final Confirmation 不能替代人工产品 Evidence；
- Evidence Executor 必须与 Method Contract 的 Executor Identity 一致。

## 9.4 Result、Conclusion、Return

必须实现：

```text
Method Result
Target Conclusion
CON-VER
CON-VAL
Product Result
Artifact Status
Artifact Gate
RLS readiness
```

聚合优先级：

```text
fail > pending > waived > pass > n/a
```

必须允许：

```text
product_result = fail
artifact_gate = pass
rls_ready = false
```

Return 必须精确指向：

```text
REQ
DSN
PLN
IMP
```

`return_imp` 必须绑定：

```text
Binding Lineage
Attempt
IMP Revision
Result Reference
Target
Method
Subject
Evidence
Observed Gap
Required Outcome
```

接收到 Return 或产生新 IMP Result 不等于解决。后续 VFY Revision 必须使用新 Subject、
承接 Control Input，并以 Method Result、Conclusion 和 Evidence 证明 Required Outcome。

## 9.5 Early Stop、Revision、Gate

必须实现：

- normal frozen product pass；
- frozen product fail；
- legal failure-checkpoint early-stop；
- early-stop 永远不进入 RLS；
- unresolved Return 永远不进入 RLS；
- Subject/Control Input 变化创建新 Revision；
- 无变化返回 `VFY_NO_CHANGE`，不创建空 Revision；
- 首次构造/写入失败后 abandon reservation；
- Final Confirmation 精确绑定当前 Subject、Control、Contract 和 Check Set；
- VFY-G-001 至 VFY-G-008 由 Verifier 重新计算；
- 不信任持久化的自报 PASS。

## 9.6 Runtime Independence 与安全

- 生产 Runtime 不读取 `docs/**`；
- 不读取 AGENTS、CLAUDE 或 Handoff 执行业务逻辑；
- 不联网；
- 不安装依赖；
- 不执行 RLS；
- 不自动执行上游 Skill；
- 不写 Secret；
- Secret-like Evidence 必须脱敏或拒绝；
- path traversal、`.git`、`.sdlc` 和非授权绝对路径必须拒绝；
- ArtifactStore 仅通过共享 API 使用，不直接 SQL。

---

# 十、80/80 Critical Case

必须存在准确 Case Set：

```text
VFY-E001
...
VFY-E080
```

Coverage Guard 必须验证：

- ID 完整；
- 固定顺序；
- 无重复；
- 每个 Case 至少映射一个实际可收集测试；
- Primary Test 不重复冒充多个 Case；
- 所有映射测试实际执行；
- 没有 skip；
- 没有 expectedFailure；
- 缺文件、缺工具和未执行均为失败；
- 一个空测试不能覆盖大量 Case；
- 80 个 Case 全部有明确 Expected、模块和 Evidence 关系。

禁止仅统计 JSON 中存在 80 个 ID 就宣布 PASS。

---

# 十一、正式 Source Lock

当前 Web Initial Source Lock 可能是 provisional/sentinel。闭环前必须：

1. 读取 CTX/REQ/DSN/PLN/IMP 的 Source Lock 与 validator 模式；
2. 按当前 VFY 真实运行依赖建立完整 Contract Set；
3. 锁定：
   - shared Runtime Contracts；
   - VFY bundled spec；
   - VFY private contract；
   - interface；
   - 实际使用的共享 Package Contract；
   - 必要 Schema；
4. 每个条目绑定准确仓库路径和 SHA-256；
5. 条目唯一、稳定排序；
6. 删除 provisional/sentinel 机制；
7. validator 拒绝：
   - 缺失；
   - 额外；
   - 重复；
   - 乱序；
   - Digest 漂移；
8. final 模式必须实际通过；
9. Source Lock 修正属于 Implementation Subject；
10. 不通过修改设计或删除依赖来让 Source Lock 通过。

---

# 十二、创建唯一 Implementation Subject

完成首轮审查与实现补齐后：

```bash
cd "$CANDIDATE_WT"

git status --short
git diff --check

git add -- \
  skills/sdlc-500-vfy \
  packages/sdlc_lifecycle \
  skills/sdlc-status \
  tests/skill_vfy \
  tests/evals \
  tests/system_integration/test_external_vfy_integration.py \
  tools/validate_sdlc_500_vfy_case_coverage.py \
  tools/validate_sdlc_500_vfy_source_lock.py \
  tools/test_sdlc_500_vfy_runtime_independence.py \
  tools/run_external_vfy_integration.py \
  tools/run_vfy_delivery_validation.py
```

只暂存实际允许文件。不得使用无审查的 `git add -A`。

创建：

```bash
git commit -m "feat(vfy): implement deterministic verification phase"
VFY_IMPLEMENTATION_SUBJECT_SHA=$(git rev-parse HEAD)
```

断言：

```bash
test "$(git rev-parse HEAD^)" = "$CURRENT_DESIGN_HEAD"
test "$(git show -s --format=%s HEAD)" = \
  "feat(vfy): implement deterministic verification phase"
```

检查 Subject Diff：

```bash
git diff --name-status "$CURRENT_DESIGN_HEAD" \
  "$VFY_IMPLEMENTATION_SUBJECT_SHA"
git diff --check "$CURRENT_DESIGN_HEAD" \
  "$VFY_IMPLEMENTATION_SUBJECT_SHA"
```

在 Evidence 创建前，允许 `git commit --amend` 修复 Subject。

每次 amend：

- 更新 `VFY_IMPLEMENTATION_SUBJECT_SHA`；
- 删除旧 SHA 的临时验证结果；
- 重新执行所有受影响 Profile；
- Fresh Attestation 必须从头重跑。

---

# 十三、统一验证控制器

唯一稳定入口：

```bash
python3 tools/run_vfy_delivery_validation.py \
  --profile <quick|phase|full|external|attest> \
  --source-sha <exact-subject-sha> \
  --base-sha "$CURRENT_DESIGN_HEAD" \
  --json-out <path>
```

若当前实现的 CLI 与此接口不一致，先判断：

- 如果设计允许等价参数，统一为一个稳定顶层入口；
- 如果缺少 exact source/base 绑定，则属于实现缺陷，必须修复；
- 禁止绕过顶层入口后手工宣布 PASS。

所有临时结果先写到：

```text
$RESULT_ROOT
```

不要在正式 Evidence 目录中累积失败尝试。

执行顺序固定：

```text
quick
→ phase
→ full
→ external
→ attest
```

---

# 十四、失败修复循环

每个 Profile 失败时：

1. 读取机器 JSON；
2. 读取 `first_failure`；
3. 读取该命令对应完整日志；
4. 确定违反的 Spec、Design Clause 和 Critical Case；
5. 修复最小真实根因；
6. 新增或增强会在缺陷存在时失败的回归测试；
7. 不删除 Case；
8. 不弱化断言；
9. 不把缺环境写成 SKIP；
10. 不修改 Design Authority；
11. 不伪造 manual/hybrid Evidence；
12. 不引入依赖安装、Workflow、RLS 或外部写；
13. amend 唯一 Subject；
14. 更新 exact SHA；
15. 从 `quick` 开始重跑所有受影响 Profile。

网络重试只允许：

```text
DNS 临时解析失败
HTTP 502
HTTP 503
HTTP 504
```

最多三次，使用有界退避并记录每次尝试。

以下不作为噪声重试：

```text
测试断言失败
Schema 失败
Digest 失败
404
401
403
依赖缺失
命令不存在
代码异常
Cleanup 失败
```

---

# 十五、Quick Profile

执行：

```bash
python3 tools/run_vfy_delivery_validation.py \
  --profile quick \
  --source-sha "$VFY_IMPLEMENTATION_SUBJECT_SHA" \
  --base-sha "$CURRENT_DESIGN_HEAD" \
  --json-out "$RESULT_ROOT/vfy-quick.json"
```

必须实际覆盖：

```text
exact source SHA
exact direct parent
clean Subject tree
git diff --check
Python syntax/import
JSON parse
VFY Source Lock structure
80 Case Coverage Guard
focused deterministic VFY tests
prohibited path scan
no Workflow/RLS leak
```

Quick PASS 后才能第一次更新远程实现分支。

---

# 十六、首次 CAS 推送与进度持久化

重新读取远程：

```bash
git fetch origin impl/vfy-v2
REMOTE_EXPECTED=$(git rev-parse origin/impl/vfy-v2)
```

必须等于任务启动时记录的 `CURRENT_IMPL_HEAD`。不相等则进入 `REF_CONFLICT`。

推送：

```bash
git push \
  --force-with-lease=refs/heads/impl/vfy-v2:"$REMOTE_EXPECTED" \
  origin \
  "$VFY_IMPLEMENTATION_SUBJECT_SHA":refs/heads/impl/vfy-v2
```

成功后：

```bash
REMOTE_EXPECTED="$VFY_IMPLEMENTATION_SUBJECT_SHA"
git fetch origin impl/vfy-v2
test "$(git rev-parse origin/impl/vfy-v2)" = "$REMOTE_EXPECTED"
```

每次后续 amend 只在 Quick 再次 PASS 后使用同样 CAS 方式推送。

禁止：

```bash
git push --force
git push -f
```

Lease 失败时：

- 不重试覆盖；
- 读取新远程 Head；
- 比较新旧内容；
- 保留本地 Candidate 和 checkpoint；
- 输出 HARD_BLOCKED，除非能证明新 Head 正是本任务上一轮成功推送。

---

# 十七、Phase Profile

执行：

```bash
python3 tools/run_vfy_delivery_validation.py \
  --profile phase \
  --source-sha "$VFY_IMPLEMENTATION_SUBJECT_SHA" \
  --base-sha "$CURRENT_DESIGN_HEAD" \
  --json-out "$RESULT_ROOT/vfy-phase.json"
```

必须实际覆盖：

```text
全部 tests/skill_vfy
VFY-E001..VFY-E080 Fixed Eval
Scope / Subject / Target
Method Contract
Executor / Evidence
Conclusion / Return
Early Stop
Revision / no-change / abandon
Artifact Gate
Lifecycle Query
sdlc-status VFY projection
manual/hybrid negative boundary
product fail / Artifact Gate pass
check absolute read-only
```

必须记录：

```text
每条命令
cwd
开始时间
结束时间
duration
exit_code
stdout/stderr 日志路径
日志 SHA-256
source_sha
base_sha
```

---

# 十八、Full Profile

执行：

```bash
python3 tools/run_vfy_delivery_validation.py \
  --profile full \
  --source-sha "$VFY_IMPLEMENTATION_SUBJECT_SHA" \
  --base-sha "$CURRENT_DESIGN_HEAD" \
  --json-out "$RESULT_ROOT/vfy-full.json"
```

必须实际覆盖：

```text
最终 Source Lock
Installed-copy Runtime Independence
完整 repository test discovery
CTX 回归
REQ 回归
DSN 回归
PLN 回归
IMP 回归
VFY 回归
Lifecycle 回归
sdlc-status 回归
Design Authority byte preservation
禁止路径检查
```

Runtime Independence 必须在只复制安装边界的临时目录中运行：

```text
packages/**
scripts/**
skills/_shared/**
skills/sdlc-500-vfy/**
skills/sdlc-status/** 仅当正式安装边界需要
```

并删除/不复制：

```text
docs/**
tests/**
AGENTS.md
CLAUDE.md
HANDOFF.md
```

至少执行：

```text
help
version
commands
examples
create
run
revise
check
Return
Lifecycle projection
```

缺文件、缺入口或读开发文档均失败。

---

# 十九、两个真实项目完整外部验证

固定项目：

```text
SpringGear
repository = ousui/springgear
sha = e855096ff19dcdb303dc4250ba19c30acd743ac7

gin-vue-admin
repository = flipped-aurora/gin-vue-admin
sha = a6882210a80bb27e3aa5dff0b4c21aa4afe8988a
```

每个项目使用独立的一次性 clone/worktree，禁止使用用户业务工作树。

每个项目必须真实执行：

```text
CTX
→ REQ
→ DSN
→ PLN
→ IMP
→ VFY
```

不能只验证 Commit 可读取。

每个项目至少执行两个独立、自动可复核 Method Type，例如：

```text
inspection
analysis
test
```

要求：

- 使用准确固定 SHA；
- 无依赖安装；
- 无远端写；
- 无 Commit、Push、Tag 或 Ref mutation；
- VFY Subject 来自正式 Current completed IMP Result；
- Method Result 有真实执行 Evidence；
- 不伪造人工 UX Evidence；
- manual/hybrid 边界由 deterministic fixture 和负向测试证明。

每个项目开始前记录：

```text
HEAD
refs digest
git status bytes
tracked/untracked digest
file mode
.sdlc 是否存在
```

结束后必须恢复：

```text
HEAD unchanged
refs unchanged
git status identical
tracked/untracked digest identical
file mode identical
.sdlc removed
temporary authority/evidence removed
no remote write
no dependency installation
```

执行：

```bash
python3 tools/run_vfy_delivery_validation.py \
  --profile external \
  --source-sha "$VFY_IMPLEMENTATION_SUBJECT_SHA" \
  --base-sha "$CURRENT_DESIGN_HEAD" \
  --json-out "$RESULT_ROOT/vfy-external.json"
```

External JSON 必须包含两个项目的：

```text
repository
expected_sha
actual_sha
phase execution receipts
exact Artifact References
IMP Claim/Result binding
VFY Subject Set
Method Types
Method Results
CON-VER
CON-VAL
product_result
artifact_gate
RLS readiness
cleanup assertions
command logs and digests
```

---

# 二十、Independent Design/Implementation Review

在 Attestation 前进行独立 Review。

至少检查：

- 80/80 Design Matrix 与实现、测试、Evidence 一一对应；
- Scope 不被缩减；
- Current terminal IMP Subject Set 正确；
- branch/tag/PR/latest/current 不作为 Subject；
- manual/hybrid Evidence 没有伪造；
- product fail / Artifact Gate pass 正确；
- early-stop 不进入 RLS；
- Return 精确归因；
- unresolved Return 不进入 RLS；
- RLS readiness 只在全部条件成立后为 true；
- `check` 完全只读；
- Source Lock 完整；
- Runtime 不读取 docs；
- 无 Workflow；
- 无 RLS；
- 测试未被弱化；
- 外部项目是完整链路；
- Design Authority 字节未变。

结果保存到临时：

```text
$RESULT_ROOT/vfy-design-review.md
```

必须：

```text
Blocker = 0
Major = 0
```

Minor/Observation 可以记录，但不得掩盖交付缺陷。

---

# 二十一、冻结 Subject 与 Fresh exact-SHA Attestation

当 Quick、Phase、Full、External 全部 PASS 后：

```bash
VFY_IMPLEMENTATION_SUBJECT_SHA=$(git -C "$CANDIDATE_WT" rev-parse HEAD)
VFY_IMPLEMENTATION_TREE=$(git -C "$CANDIDATE_WT" rev-parse HEAD^{tree})
```

重新断言：

```bash
test "$(git -C "$CANDIDATE_WT" rev-parse HEAD^)" = "$CURRENT_DESIGN_HEAD"
test -z "$(git -C "$CANDIDATE_WT" status --porcelain=v1 --untracked-files=all)"
```

创建 Fresh Detached Worktree：

```bash
git worktree add --detach "$ATTEST_WT" "$VFY_IMPLEMENTATION_SUBJECT_SHA"
test "$(git -C "$ATTEST_WT" rev-parse HEAD)" = \
  "$VFY_IMPLEMENTATION_SUBJECT_SHA"
test -z "$(git -C "$ATTEST_WT" status --porcelain=v1 --untracked-files=all)"
```

在 Attestation Worktree 中执行：

```bash
python3 tools/run_vfy_delivery_validation.py \
  --profile attest \
  --source-sha "$VFY_IMPLEMENTATION_SUBJECT_SHA" \
  --base-sha "$CURRENT_DESIGN_HEAD" \
  --json-out "$RESULT_ROOT/vfy-attest.json"
```

Attest 必须重新验证，而不是复用旧 PASS 标志：

```text
exact SHA/tree/parent
quick
phase
full
external evidence binding
80/80 no skip
runtime independence
full regression
two fixed projects
cleanup
independent review
no main mutation
no workflow
no RLS
```

任何源码、测试或工具变化都会使 Subject 解冻，并要求从 Quick 重新开始。

---

# 二十二、正式 Evidence

仅在 Fresh Attest PASS 后创建：

```text
docs/plugin-development/work-items/sdlc-500-vfy/evidence/
<VFY_IMPLEMENTATION_SUBJECT_SHA>/
├── vfy-full-regression.log
├── vfy-fixed-eval.log
├── vfy-real-projects.json
├── vfy-final-attestation.log
├── vfy-design-review.md
├── vfy-verification-result.json
├── vfy-handoff.md
├── vfy-evidence.sha256
└── vfy-repository.sha256
```

要求：

- 所有 `source_sha` 等于 `VFY_IMPLEMENTATION_SUBJECT_SHA`；
- `base_sha` 等于 `CURRENT_DESIGN_HEAD`；
- 所有日志来自实际命令；
- 没有关键 Case skipped/expectedFailure；
- Critical Cases = 80/80 PASS；
- 两个真实项目均为完整链路；
- manual Evidence 只在真实提供时存在；
- negative fixture 不得冒充真实人工验收；
- `vfy-verification-result.json` 校验通过正式 Schema；
- Evidence SHA-256 使用仓库相对路径；
- `vfy-evidence.sha256` 自身不递归包含自身；
- `vfy-repository.sha256` 明确绑定 Subject Tree 和仓库关键文件；
- Handoff 区分：
  - Design Head；
  - Implementation Subject；
  - Evidence Delivery Head；
  - IMP semantic Subject；
- 结果只允许 PASS，不允许 partial/skip/pending；
- 不在 Evidence Commit 中修改实现、测试、工具或设计。

---

# 二十三、Evidence/Handoff Commit

在 Candidate Worktree 中确认 Head 仍为 Subject：

```bash
cd "$CANDIDATE_WT"
test "$(git rev-parse HEAD)" = "$VFY_IMPLEMENTATION_SUBJECT_SHA"
```

只暂存 Evidence 目录：

```bash
git add \
  "docs/plugin-development/work-items/sdlc-500-vfy/evidence/${VFY_IMPLEMENTATION_SUBJECT_SHA}"
```

断言 staged diff 仅包含该目录：

```bash
git diff --cached --name-only
```

提交：

```bash
git commit -m "chore(vfy): archive verification evidence and handoff"
VFY_EVIDENCE_DELIVERY_HEAD_SHA=$(git rev-parse HEAD)
```

断言：

```bash
test "$(git rev-parse HEAD^)" = "$VFY_IMPLEMENTATION_SUBJECT_SHA"
```

Evidence Commit 创建后：

- 禁止 amend Subject；
- 禁止重写 Subject；
- 任何实现修正都必须删除本地无效 Evidence、回到 Subject、重新 Attest，再重新创建
  Evidence Commit；
- 不允许让旧 Evidence 继续指向新 Subject。

---

# 二十四、最终推送

重新读取远程：

```bash
git fetch origin impl/vfy-v2
ACTUAL_REMOTE=$(git rev-parse origin/impl/vfy-v2)
test "$ACTUAL_REMOTE" = "$REMOTE_EXPECTED"
```

Evidence Head 应为当前已推送 Subject 的 fast-forward：

```bash
git push origin \
  "$VFY_EVIDENCE_DELIVERY_HEAD_SHA":refs/heads/impl/vfy-v2
```

推送后读回：

```bash
git fetch origin impl/vfy-v2
test "$(git rev-parse origin/impl/vfy-v2)" = \
  "$VFY_EVIDENCE_DELIVERY_HEAD_SHA"
```

如果 Subject 尚未在远程，使用带准确 lease 的一次更新；禁止裸 force。

---

# 二十五、更新 Implementation Draft PR

使用现有 PR #9；若实际编号变化，按 head=`impl/vfy-v2` 精确查找。

PR 必须：

```text
head = impl/vfy-v2
base = main
draft = true
state = open
```

更新 Body，至少记录：

```text
VFY_INTEGRATION_MODE = PREMERGE_DIRECT_DESIGN_ANCESTRY
Design PR #7 merge was not required for local closure
Current Design Head
Implementation Subject SHA
Evidence Delivery Head SHA
IMP Implementation Subject SHA
Quick = PASS
Phase = PASS
Full = PASS
External = PASS
Attest = PASS
Critical Cases = 80/80 PASS
Runtime Independence = PASS
SpringGear exact SHA = PASS
gin-vue-admin exact SHA = PASS
Main modified = NO
GitHub Actions authority = NO
RLS started = NO
Evidence path
Web Review path
```

并明确：

- PR 保持 Draft；
- 本任务不合并 PR；
- 未来进入 main 时，Design PR #7 仍应先用 **Create a merge commit** 合并；
- Implementation 分支不得 rebase；
- 后续必须执行 Web Evidence Review；
- Web Review 接受前不得 Ready/Merge。

若 `gh` 不可用但 Git 推送成功：

- 不伪造 PR 已更新；
- 保留远程分支与 Evidence；
- 输出 HARD_BLOCKED；
- 给出唯一恢复动作：使用可认证 GitHub Client 更新现有 PR #9 Body；
- 不创建第二个 PR。

---

# 二十六、最终远程读回

结束前重新读取：

```text
origin/main
origin/design/sdlc-500-vfy-goal
origin/impl/vfy-v2
PR #7
Implementation PR
```

验证：

- `main` 等于启动时 `CURRENT_MAIN_SHA`；
- Design Head 等于启动时 `CURRENT_DESIGN_HEAD`；
- PR #7 未被本任务合并；
- Implementation Head 等于 Evidence Delivery Head；
- Subject 的直接父提交等于 Design Head；
- Evidence Head 的直接父提交等于 Subject；
- PR base/head 正确；
- PR 仍 Draft；
- 没有 Evidence 分支；
- 没有 RLS；
- 没有 Workflow；
- 所有 Evidence Digest 验证通过。

---

# 二十七、成功终态

只有全部条件成立时输出：

```text
VFY_CLOSED_LOOP = PASS

VFY_INTEGRATION_MODE =
PREMERGE_DIRECT_DESIGN_ANCESTRY

MAIN_SHA =
<完整 SHA>

DESIGN_PR_NUMBER =
7

DESIGN_PR_STATE =
<OPEN_DRAFT_UNMERGED 或实际状态>

VFY_DESIGN_HEAD_SHA =
<完整 SHA>

VFY_IMPLEMENTATION_SUBJECT_SHA =
<完整 SHA>

VFY_EVIDENCE_DELIVERY_HEAD_SHA =
<完整 SHA>

IMPLEMENTATION_PR_NUMBER =
<实际编号>

IMPLEMENTATION_PR_URL =
<URL>

QUICK =
PASS

PHASE =
PASS

FULL =
PASS

EXTERNAL =
PASS

ATTEST =
PASS

CRITICAL_CASES =
80/80 PASS

RUNTIME_INDEPENDENCE =
PASS

SPRINGGEAR =
PASS

GIN_VUE_ADMIN =
PASS

MAIN_MODIFIED =
NO

DESIGN_PR_MERGED_BY_THIS_GOAL =
NO

IMPLEMENTATION_PR_MERGED =
NO

EVIDENCE_BRANCH_CREATED =
NO

RLS_STARTED =
NO

WEB_REVIEW =
docs/plugin-development/work-items/sdlc-500-vfy/goal/
10-WEB-REPORT-REVIEW.md
```

并给出：

1. Subject Commit；
2. Evidence Commit；
3. PR URL；
4. Evidence 文件清单；
5. 每个 Profile 的机器报告路径；
6. 唯一下一动作：对 Evidence Delivery Head 执行 Web Review。

---

# 二十八、HARD_BLOCKED 终态

经过本文允许的有界恢复后无法安全继续，输出：

```text
VFY_CLOSED_LOOP = HARD_BLOCKED

VFY_INTEGRATION_MODE =
PREMERGE_DIRECT_DESIGN_ANCESTRY

FIRST_REAL_BLOCKER =
<第一条实际命令、文件、Case 或 Ref 错误>

CURRENT_MAIN_SHA =
<完整 SHA>

CURRENT_DESIGN_HEAD =
<完整 SHA>

START_IMPL_HEAD =
<完整 SHA>

LAST_SAFE_LOCAL_SUBJECT_SHA =
<完整 SHA 或 NONE>

REMOTE_IMPL_HEAD =
<完整 SHA>

REF_DRIFT =
<YES|NO>

MAIN_MODIFIED =
NO

DESIGN_PR_MERGED_BY_THIS_GOAL =
NO

IMPLEMENTATION_PR_MERGED =
NO

RLS_STARTED =
NO

RECOVERY =
<唯一、准确、安全的恢复步骤>
```

必须同时说明：

- 已完成到哪个 Profile；
- 哪些结果因 Subject 变化已经失效；
- 是否已经推送 Subject；
- 是否已经创建 Evidence；
- 是否存在远程漂移；
- 本地 checkpoint 和 Worktree 路径；
- 不得把未完成结果描述为 PASS。

---

# 二十九、最后提醒

本 Goal 的关键不是“把当前 `impl/vfy-v2` 接到 Design 分支上”。

关键是：

```text
把当前 impl/vfy-v2 当作只读 Source Snapshot
+
以 CURRENT_DESIGN_HEAD 创建全新候选
+
仅迁移允许的 VFY 实现
+
形成一个直接子 Subject
+
真实闭环验证
+
Fresh exact-SHA Evidence
```

PR #7 保持未合并不阻止本地闭环；但任何实现结果都不能绕过准确 Design Head，
也不能通过把旧分叉历史整体 reset/rebase 到 Design Head 来伪造正确 ancestry。

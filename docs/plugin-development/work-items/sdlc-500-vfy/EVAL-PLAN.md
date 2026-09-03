# Skill Eval Plan — `sdlc-500-vfy`

## 1. 元数据

| Field | Value |
|---|---|
| Skill | `sdlc-500-vfy` |
| Status | `ready` |
| Design | `DESIGN.md` |
| Oracle | v1.1 Core / Store / VFY 与批准后的依赖 Contract |
| Maintainer Decision | `pending` |

## 2. 测试层

1. Interface 与 `run`；
2. Scope/Target/Subject/Obligation 推导；
3. Method Contract 与执行器；
4. Method Result、Target/固定 Conclusion、Return；
5. Store Revision 与 Authority；
6. Lifecycle Query；
7. Runtime Independence / Source Lock；
8. 真实项目方法执行；
9. 全仓回归与 Host 证据。

## 3. Critical Cases

### A. Interface

| ID | Case | Expected |
|---|---|---|
| VFY-E001 | 裸调用唯一 ready Scope | auto create/run |
| VFY-E002 | 多个完整 Scope | 列出候选，用户选择 |
| VFY-E003 | `create -i <scope> -i <subject>` | 准确分类 |
| VFY-E004 | `run -r VFY@1 -m VFM-001` | 只执行选定 pending Method |
| VFY-E005 | `revise -r VFY@1` | 上游/Control Input 变化后修订 |
| VFY-E006 | `check -r VFY@1` | 绝对只读 |
| VFY-E007 | meta command | 零扫描、零写入 |
| VFY-E008 | `run` 组合不存在 Method | stable error |
| VFY-E009 | 多 method 重复/顺序 | 去重、保留首次顺序 |

### B. Scope 与 Subject

| ID | Case | Expected |
|---|---|---|
| VFY-E010 | PLN required 完整 Scope | 采用完整 PLN，不选部分 WI |
| VFY-E011 | PLN n/a/waived | 采用最近完整 REQ/DSN + 处置依据 |
| VFY-E012 | 多 Scope 未聚合 | 返回上游，不在 VFY 合并 |
| VFY-E013 | IMP WI 未领取/active/abandoned/open | 阻止 VFY |
| VFY-E014 | frozen IMP 但 Claim active | 阻止 VFY |
| VFY-E015 | Current completed IMP 链连续 | Subject 可用 |
| VFY-E016 | 前驱有新 Attempt，后继未吸收 | Subject stale |
| VFY-E017 | 可移动 branch/tag/current | 拒绝为 Subject |
| VFY-E018 | Result Set 与 Delivery Scope 不完整 | VFY-G-001 fail |
| VFY-E019 | VFY Gate 前 Subject 变化 | 停止/新 Revision，不沿用结果 |

### C. Target Set

| ID | Case | Expected |
|---|---|---|
| VFY-E020 | DSN VFO 存在 | 使用全部 VFO，不重复 AC/Goal |
| VFY-E021 | DSN n/a/waived | AC 为 verification Target，Goal 为 validation Target |
| VFY-E022 | 多权威 Target Set | 按准确 Reference 并集，不按标题合并 |
| VFY-E023 | Target 缺失/冲突 | RETURN_TO_REQ/DSN |
| VFY-E024 | Requirement 直接重复为 Target | 拒绝重复 |
| VFY-E025 | both Target 覆盖不足 | 不能 pass |

### D. Method Contract

| ID | Case | Expected |
|---|---|---|
| VFY-E026 | inspection | 静态复核，无目标运行 |
| VFY-E027 | analysis | 计算/扫描/模型结果与 Evidence |
| VFY-E028 | demonstration | 操作/展示，可观察结果 |
| VFY-E029 | test | 输入、条件、Expected、Pass Criteria |
| VFY-E030 | 固定 Method Type 之外的 unit/security/e2e | 作为范围/level，不作为类型 |
| VFY-E031 | Target 无 Method | VFY-G-003 fail |
| VFY-E032 | Method 无 Target/Subject | fail |
| VFY-E033 | Purpose 不相容 | fail |
| VFY-E034 | 上游 VFP/VFM/VPC/VEC 未承接 | fail |
| VFY-E035 | VFY WI 未映射 | fail |
| VFY-E036 | Return/Issue 未进入 Obligation | fail |
| VFY-E037 | required Method 缺 Procedure/Pass Criteria/Evidence Requirement | waiting_input/fail |
| VFY-E038 | n/a 因工具不可用 | fail；应 pending/waived |
| VFY-E039 | waived 无 Exception | fail |
| VFY-E040 | manual/automated/hybrid 当 Method Type | fail |

### E. 执行与 Evidence

| ID | Case | Expected |
|---|---|---|
| VFY-E041 | 自动方法安全可执行 | run + Evidence |
| VFY-E042 | 缺依赖但未授权安装 | 不安装，Method pending/action_required |
| VFY-E043 | 人工 UX Method | 展示场景、Expected、证据要求，等待真实输入 |
| VFY-E044 | 人工只写“感觉正常” | Evidence insufficient |
| VFY-E045 | 执行 Subject 与 Contract 不同 | Result invalid |
| VFY-E046 | command exit fail | Method Result fail，不必 Artifact Gate fail |
| VFY-E047 | 日志含 Secret | 脱敏/拒绝保存 |
| VFY-E048 | Supporting Report Digest 篡改 | check fail |
| VFY-E049 | Evidence 缺环境/数据/时间/Subject | VFY-G-004/007 fail |
| VFY-E050 | 复用上游 Evidence Subject 完全匹配 | 可复核使用 |
| VFY-E051 | Subject 变化仍复用旧 Evidence | 拒绝 |

### F. Conclusion 与 Return

| ID | Case | Expected |
|---|---|---|
| VFY-E052 | 全部 Target pass | CON-VER/VAL 固定聚合 |
| VFY-E053 | 产品 Method fail，记录完整 | 产品 fail；Artifact Gate 可 pass |
| VFY-E054 | Artifact 结构错误 | Gate fail，与产品结论分离 |
| VFY-E055 | both Target 只有 verification pass | Conclusion 非 pass |
| VFY-E056 | fail 可唯一归因 IMP | RET return_imp + Lineage |
| VFY-E057 | 需求/AC 缺陷 | return_req |
| VFY-E058 | 设计决策/接口/状态缺陷 | return_dsn |
| VFY-E059 | 计划范围/顺序错误 | return_pln |
| VFY-E060 | Return 缺 Observed Gap/Required Outcome/Evidence | fail |
| VFY-E061 | 上游仅接收 Return | 不视为 resolved |
| VFY-E062 | 后续 VFY 证明 Required Outcome | Return resolved |
| VFY-E063 | return_imp 与 Subject Lineage 不一致 | fail |
| VFY-E064 | RLS 产品修正 Issue 完整承接 | PASS |

### G. 失败早停

| ID | Case | Expected |
|---|---|---|
| VFY-E065 | 明确 fail 且剩余 Method 不影响归因 | 合法早停候选 |
| VFY-E066 | 剩余输入会影响失败有效性 | 不得早停冻结 |
| VFY-E067 | 未执行 required Method 保留 pending | PASS only under early-stop rules |
| VFY-E068 | 早停 Revision 进入 RLS | 禁止 |
| VFY-E069 | Open Item 被错误标 resolved | fail |
| VFY-E070 | Final Confirmation 把 fail 改为 pass | fail |

### H. Revision、Gate、Lifecycle

| ID | Case | Expected |
|---|---|---|
| VFY-E071 | open Revision run | 原 Revision 更新 |
| VFY-E072 | frozen 后新 Subject/Return | 新 Revision |
| VFY-E073 | no-change revise | NO_CHANGE |
| VFY-E074 | missing/stale Final Confirmation | open/failed，不冻结 |
| VFY-E075 | build/first-write 失败 | Reservation abandoned |
| VFY-E076 | check 前后 Store/项目字节一致 | PASS |
| VFY-E077 | product pass + RLS required | 下一阶段 RLS |
| VFY-E078 | product fail/unresolved Return | 下一动作准确上游 Phase |
| VFY-E079 | RLS n/a/waived | 生命周期完成，不造空 RLS |
| VFY-E080 | Artifact ready 但 product fail | status 输出明确区分 |

## 4. 非功能与并发

- 100+ Target/Method 的稳定排序和线性/可控聚合；
- 并行独立 Method 结果合并不覆盖；
- 同一 Method 重复 run 幂等或创建明确新执行记录，不伪造两个 Current Result；
- timeout/cancel 形成准确 pending/fail，不丢 Evidence；
- 大日志只保存摘要和 Supporting Member；
- 不保存不必要生产数据；
- 不联网、不安装依赖、不调用兄弟 Skill。

## 5. 真实项目测试

在一次性 Worktree/clone 中：

1. 形成 CTX→REQ→DSN→PLN→IMP completed；
2. 使用项目已有构建、单测、静态分析或可执行场景；
3. 生成至少 inspection、analysis/test 中两类 Method；
4. 保存真实 Subject/Evidence；
5. 形成 pass 或可复核 fail + Return；
6. 运行 `sdlc-status` 验证下一动作；
7. 不安装依赖、不写远端、不提交项目专用 Fixture。

## 6. Runtime Independence

安装副本删除 docs/tests/Handoff 后，执行：meta、create、run、revise、check、Method Executor、Conclusion、Return 和 Lifecycle Query。生产 Runtime 不含开发路径或固定项目路径。

## 7. Source Lock

依赖 Contract 固定后冻结准确集合。Validator 必须拒绝缺失、额外、重复、排序和摘要漂移，并验证 bundled VFY Contract 自包含。

## 8. Host Evidence

真实 Codex 至少执行：

```text
/sdlc-500-vfy --help
/sdlc-500-vfy
/sdlc-500-vfy run -r <open VFY> -m <VFM>
/sdlc-500-vfy check -r <frozen VFY>
```

人工 Method 交互必须证明用户不需要填写 Method Result JSON、Evidence ID 或 Return 表。

## 9. PASS 条件

- 全部 Critical Case PASS；
- 自动和人工 Method 均有真实证据；
- 产品 fail / Artifact pass 语义通过独立 Review；
- Runtime Independence、Source Lock、全仓回归 PASS；
- Review 无 Blocker/Major；
- 当前远端 Head 的 CI 成功；
- 未验证 Client 不虚报。

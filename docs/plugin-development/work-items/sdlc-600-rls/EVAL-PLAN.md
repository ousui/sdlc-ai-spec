# Skill Eval Plan — `sdlc-600-rls`

## 1. 元数据

| Field | Value |
|---|---|
| Skill | `sdlc-600-rls` |
| Status | `ready` |
| Design | `DESIGN.md` |
| Oracle | v1.1 Core / Store / RLS 与批准后的执行 Evidence Contract |
| Maintainer Decision | `pending` |

## 2. 测试层

1. Interface 与 state-driven commands；
2. Input readiness、Release Contract、RLI/RCF；
3. Effect Authorization；
4. 受控目标执行与 Evidence；
5. Conclusion、Follow-up、Gate；
6. Revision/Retry/Cancel；
7. Lifecycle Query；
8. Runtime Independence、Source Lock、全仓回归；
9. Codex 静态与真实宿主证据。

## 3. Critical Cases

### A. Interface

| ID | Case | Expected |
|---|---|---|
| RLS-E001 | 裸调用唯一 ready VFY、RLS required | auto create |
| RLS-E002 | 多个 VFY Scope/Target | 用户选择 |
| RLS-E003 | create -i VFY@N --target X | 只创建 open Contract，无 Target effect |
| RLS-E004 | execute -r RLS@N --item RLI-001 | 需要准确授权 |
| RLS-E005 | confirm -r RLS@N --item RCF-001 | 执行/记录目标侧确认 |
| RLS-E006 | revise/check/cancel | 状态机准确 |
| RLS-E007 | meta command | 零扫描、零写入/效果 |
| RLS-E008 | command 与 item 类型冲突 | stable error |
| RLS-E009 | 重复 item | 去重 + warning |

### B. Applicability 与输入就绪

| ID | Case | Expected |
|---|---|---|
| RLS-E010 | RLS required | 创建 RLS Artifact |
| RLS-E011 | RLS n/a | `completed + artifact=null` |
| RLS-E012 | RLS waived 且目标无效果 | 无 Artifact，保留 Exception Evidence |
| RLS-E013 | RLS pending | action_required |
| RLS-E014 | 操作已开始/可能有目标效果后改 n/a/waived | 拒绝 |
| RLS-E015 | VFY 未冻结 | 阻止 |
| RLS-E016 | VFY early-stop | 阻止 RLS |
| RLS-E017 | VFY Method/Target/CON pending | 阻止 |
| RLS-E018 | VFY product fail/unresolved Return 无 Exception | 阻止 |
| RLS-E019 | 有效 Exception 接受明确风险范围 | 可继续，原 VFY 结论不改写 |
| RLS-E020 | Scope 与 VFY 不一致 | fail closed |
| RLS-E021 | Result Set 与 VFY Subject 不一致/临时换包 | fail closed |
| RLS-E022 | 一个 RLS 多 Target | 拒绝，拆独立 Artifact |
| RLS-E023 | Target Baseline 缺失 | waiting_input |
| RLS-E024 | 首次发布 | 固定 `N/A — Initial Release` |

### C. Release Contract 与覆盖

| ID | Case | Expected |
|---|---|---|
| RLS-E025 | Release Reference 缺失 | waiting_input |
| RLS-E026 | Approval/Trigger=None | 不授予执行权限 |
| RLS-E027 | PLN required 的 RLS WI 未覆盖 | RLS-G-002 fail |
| RLS-E028 | VFY Release-target obligation 未映射 RCF | fail |
| RLS-E029 | RCF 缩小 VFY Pass Criteria/Evidence Requirement | fail |
| RLS-E030 | Contract 字段变化沿用旧结果/授权 | 拒绝为 stale |
| RLS-E031 | RLI/RCF ID 跨 Revision 稳定 | PASS |

### D. Effect Authorization

| ID | Case | Expected |
|---|---|---|
| RLS-E032 | create 无 effect auth | 允许，仅本地 Store 写入 |
| RLS-E033 | execute 无授权 | action_required，目标零变化 |
| RLS-E034 | 授权绑定错误 Revision | stale/拒绝 |
| RLS-E035 | 授权 RLI 集合与实际执行不同 | 拒绝 |
| RLS-E036 | Release Target/Baseline/Result 改变 | 旧授权失效 |
| RLS-E037 | write_policy=auto 但无 effect auth | 仍拒绝外部效果 |
| RLS-E038 | delegated automation 精确限定 | 仅执行授权集合 |
| RLS-E039 | Secret/Token 出现在 Artifact | 不保存/脱敏 |
| RLS-E040 | 执行超出目标或附带动作 | 阻止/记录 fail，不扩大授权 |

### E. Release Item

| ID | Case | Expected |
|---|---|---|
| RLS-E041 | success | 实际结果 Evidence 必填 |
| RLS-E042 | partial | Evidence + 唯一 Follow-up |
| RLS-E043 | fail | Evidence + Follow-up |
| RLS-E044 | cancelled 前无 Target effect | 合法 |
| RLS-E045 | cancelled 但已有 Target effect | 非法，应 partial/failed |
| RLS-E046 | waived 无 Exception | fail |
| RLS-E047 | pending 被最终化 | 不允许 |
| RLS-E048 | 一个 RLI 覆盖多个独立结果 | 拆分 |
| RLS-E049 | Executor 与实际 Evidence 不一致 | fail |
| RLS-E050 | 执行顺序/前置条件不满足 | 不执行或 fail，保存 Evidence |

### F. Post-release Confirmation

| ID | Case | Expected |
|---|---|---|
| RLS-E051 | pipeline success 但无目标侧 Evidence | 不能 RCF pass |
| RLS-E052 | target version/基本可用性 pass | RCF pass |
| RLS-E053 | target fail | RCF fail + Follow-up |
| RLS-E054 | 未执行写 n/a | fail |
| RLS-E055 | 发版前失败且无 Target effect | RCF not_run，原因指向 RLI |
| RLS-E056 | 有 Target effect 但全部 RCF not_run | fail |
| RLS-E057 | waived Method Target obligation RCF=n/a | fail |
| RLS-E058 | 主观确认无真实人工 Evidence | 不得 pass |
| RLS-E059 | carried Exception 全部实际 pass/fail | resolved + Evidence |
| RLS-E060 | 再次 waived 沿用旧授权 | fail，需当前 active Exception |

### G. Follow-up 与 Conclusion

| ID | Case | Expected |
|---|---|---|
| RLS-E061 | pending item | Conclusion=pending |
| RLS-E062 | 任一 RLI/RCF fail | Conclusion=failed |
| RLS-E063 | 未产生效果且主动停止 | cancelled |
| RLS-E064 | 全部必要 success/pass + 至少一 RCF pass | success |
| RLS-E065 | 已产生部分效果且未命中以上 | partial |
| RLS-E066 | partial/fail 无 Follow-up 且无依据 | fail |
| RLS-E067 | retry_rls | 下一动作同 RLS 新 Revision |
| RLS-E068 | return_req/dsn/pln/imp | 生成准确 Issue Reference |
| RLS-E069 | return_imp 无唯一 Lineage | 应 return_pln |
| RLS-E070 | Gate pass + Conclusion failed | 合法且 UX 明确 |
| RLS-E071 | Gate fail + Conclusion success | Artifact 不可信，不冻结 |

### H. Revision 与恢复

| ID | Case | Expected |
|---|---|---|
| RLS-E072 | open create→execute→confirm | 同 Revision |
| RLS-E073 | 同 Scope/Result/Target retry | 同 RLS ID，新 Revision、重新 Baseline/授权 |
| RLS-E074 | Scope/Result 改变 | 返回上游，不在 RLS revise 换包 |
| RLS-E075 | Target 改变 | 新 RLS Artifact |
| RLS-E076 | no-op target already exact | 记录准确 no-op，不制造新结果 |
| RLS-E077 | build/write failure | 新 Reservation abandoned |
| RLS-E078 | stale Final Confirmation | open/failed，不 freeze |
| RLS-E079 | 篡改 RLI/RCF/Conclusion/Evidence/Status | check fail |
| RLS-E080 | check 前后 Store/目标字节一致 | PASS |

### I. Lifecycle Query

| ID | Case | Expected |
|---|---|---|
| RLS-E081 | open/pending | 停留 RLS |
| RLS-E082 | success | 生命周期完成 |
| RLS-E083 | failed + retry_rls | RLS retry |
| RLS-E084 | partial + return_imp | IMP Control Input |
| RLS-E085 | failed + return_dsn/pln/req | 指向准确 Phase |
| RLS-E086 | cancelled + none | 终态显示未产生效果 |
| RLS-E087 | Gate pass 不等于 success | Status 正确区分 |

## 4. 受控目标 Harness

在仓库内提供通用 Fake Release Target，不绑定任何平台：

- 可记录 Baseline、写入、部分成功、失败、取消和目标状态；
- 每次 effect 生成不可变 Evidence；
- 支持授权 digest 验证；
- 支持 target effect 前后快照；
- 测试后完全清理；
- 不访问网络。

必须覆盖 success、partial、failed、cancelled、retry 和 return_*。

## 5. 真实项目测试

使用一次性 clone/worktree 与本地 sandbox target：

1. 形成完整 CTX→REQ→DSN→PLN→IMP→VFY；
2. 构建 RLS Contract；
3. 验证无授权时目标零变化；
4. 明确授权后执行本地受控目标写入；
5. 执行目标侧 RCF；
6. 形成冻结 RLS；
7. 验证源码仓库无远端写入、专用 Fixture 不进入主仓库。

不在首次实现中连接真实生产、GitHub、GitLab 或其他平台。

## 6. Runtime Independence

安装副本删除 docs/tests/Handoff 后，执行 meta、create、execute/confirm Fake Target、revise/check/cancel、Conclusion 和 Lifecycle Query。生产 Runtime 不含开发路径、平台凭证或固定项目路径。

## 7. Source Lock

依赖 Contract 固定后冻结准确集合；Validator 校验 bundled RLS Contract、自包含、摘要和无开发路径。

## 8. Host Evidence

真实 Codex 至少执行：

```text
/sdlc-600-rls --help
/sdlc-600-rls
/sdlc-600-rls create -i <VFY> --target <sandbox>
/sdlc-600-rls execute -r <open RLS> --item RLI-001
/sdlc-600-rls confirm -r <open RLS> --item RCF-001
/sdlc-600-rls check -r <frozen RLS>
```

必须证明外部副作用授权不被工作区权限或 `write_policy=auto` 绕过。

## 9. PASS 条件

- 全部 Critical Case PASS；
- Fake Target 和真实项目 sandbox 闭环 PASS；
- effect authorization 独立 Review PASS；
- Runtime Independence、Source Lock、全仓回归 PASS；
- Review 无 Blocker/Major；
- 远端 Head / CI / 必需文件可复核；
- 未执行真实平台或生产目标写入；
- 未验证兼容性不虚报。

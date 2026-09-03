# Skill Eval Plan — `sdlc-300-pln`

## 1. 元数据

| Field | Value |
|---|---|
| Skill | `sdlc-300-pln` |
| Status | `ready` |
| Design | `DESIGN.md` |
| Oracle | v1.1 Core / Artifact Store / PLN 与批准后的 Design Contract |
| Maintainer Decision | `pending` |

Eval Oracle 在 Design approval 后冻结。实现阶段不得通过删除案例、弱化断言或改写期望结果解决失败。

## 2. 测试层

1. **Interface**：裸调用、命令、参数、别名、冲突、元命令；
2. **Producer Unit**：Scope、Applicability、Work Item、依赖、覆盖、Renderer；
3. **Store Behavior**：create/revise/check、Revision、失败恢复；
4. **Authority**：Gate、Final Confirmation、Digest、篡改反例；
5. **Lifecycle**：REQ/DSN→PLN→Work Item 前沿；
6. **Runtime Independence**：安装副本删除开发文件；
7. **Repository Regression**：现有 CTX、REQ、DSN、Status 全部保持通过；
8. **Host**：Codex 静态 Adapter 与真实安装行为分开记录。

## 3. Critical Cases

### A. Interface

| ID | Case | Expected |
|---|---|---|
| PLN-E001 | 裸调用、唯一 ready DSN、PLN required | 自动 create |
| PLN-E002 | `create -i DSN-A@1 -i DSN-B@1` | 保留顺序、准确聚合 |
| PLN-E003 | `revise -r PLN-X@1` | 准确目标，无 latest/current |
| PLN-E004 | `check -r PLN-X@1` | 只读 |
| PLN-E005 | help/version/commands/examples | 零扫描、零写入 |
| PLN-E006 | 重复同值 `--input` | 去重并 warning |
| PLN-E007 | 冲突 command、未知参数、缺值 | 稳定错误，零写入 |
| PLN-E008 | 多个合法 Scope 候选 | 用户选择，不按修改时间猜测 |

### B. Applicability 与 Scope

| ID | Case | Expected |
|---|---|---|
| PLN-E009 | PLN required | 分配 PLN Artifact |
| PLN-E010 | PLN n/a | `completed + artifact=null` |
| PLN-E011 | PLN waived + 有效 Exception | 不创建 Artifact，保留 Waiver Evidence |
| PLN-E012 | PLN pending | action_required，零分配 |
| PLN-E013 | DSN required 且已存在 | PLN 直接 Input 使用 DSN，不重复 REQ |
| PLN-E014 | DSN n/a/waived | 可使用保存处置的完整 REQ/DSN |
| PLN-E015 | 多 Scope 不同 CTX | fail closed |
| PLN-E016 | 选择部分 Artifact Item 作为 Scope | 拒绝；PLN 只接收完整 Artifact |
| PLN-E017 | Return Phase=PLN VFY Return | 作为 Control Input，不扩大 Delivery Scope |
| PLN-E018 | return_pln RLS Issue | 受影响 WI/Evidence 必须准确承接 |

### C. Work Item Contract

| ID | Case | Expected |
|---|---|---|
| PLN-E019 | 一个原子 IMP Outcome | 一个 WI，完整字段 |
| PLN-E020 | 一个 WI 混合 IMP 与 VFY | 拒绝并拆分建议 |
| PLN-E021 | WI 过大无法独立闭合 | pending / 用户决定拆分 |
| PLN-E022 | 两条 WI 仅描述不同但同 Outcome/Scope/Evidence | 合并建议 |
| PLN-E023 | Source References 缺失或孤立 WI | PLN-G-002 fail |
| PLN-E024 | Change/VFY Point 未覆盖 | PLN-G-002 fail |
| PLN-E025 | Constraint/Exception 未分配 | PLN-G-002 fail |
| PLN-E026 | Completion Criteria 只写“完成” | PLN-G-003 fail |
| PLN-E027 | Expected Evidence 模糊 | PLN-G-003 fail |
| PLN-E028 | Responsible Role 缺失 | waiting_input |
| PLN-E029 | WI ID 跨 Revision 保持稳定 | PASS |
| PLN-E030 | 新语义只能通过新增上游 Revision | PLN-G-006 fail，不在 PLN 补写 |

### D. Scope Token 与依赖

| ID | Case | Expected |
|---|---|---|
| PLN-E031 | IMP WI 缺少 `resource:<id>` | PLN-G-004 fail |
| PLN-E032 | 多资源未全部登记 | PLN-G-004 fail |
| PLN-E033 | 同 resource 的 IMP WI 无确定依赖链 | pending / fail |
| PLN-E034 | path token 的 resource-id 不一致 | fail |
| PLN-E035 | RLS WI 无 environment token | fail |
| PLN-E036 | RLS WI 两个 environment token | fail |
| PLN-E037 | self dependency | fail |
| PLN-E038 | dependency cycle | fail |
| PLN-E039 | IMP 依赖 VFY/RLS | fail；依赖不得指向更晚 Phase |
| PLN-E040 | 无真实依赖却自动添加 parallel/conflicts 字段 | Validator 拒绝额外权威字段 |

### E. Applicability、Gate 与 Revision

| ID | Case | Expected |
|---|---|---|
| PLN-E041 | required Phase 无 WI | PLN-G-005 fail |
| PLN-E042 | n/a/waived Phase 存在伪 WI | fail |
| PLN-E043 | VFY 非 required | fail |
| PLN-E044 | open PLN 补齐输入 | 原 Revision 修订并可冻结 |
| PLN-E045 | frozen PLN 有有效变化 | 新 Revision |
| PLN-E046 | frozen PLN 无变化 | NO_CHANGE，Revision 不增加 |
| PLN-E047 | stale Final Confirmation | open / failed，不冻结 |
| PLN-E048 | build/first write 失败 | 新 Reservation abandoned |
| PLN-E049 | 篡改 Work Item、Gate、Status 或 Digest | check fail |
| PLN-E050 | check 前后 Store 字节一致 | PASS |

### F. Lifecycle Query

| ID | Case | Expected |
|---|---|---|
| PLN-E051 | ready DSN → ready PLN | Graph 有 scope_input 边 |
| PLN-E052 | open/failed PLN | 前沿停留 PLN |
| PLN-E053 | ready PLN 有 IMP WI | 下一动作指向 IMP Binding |
| PLN-E054 | 多个可并行 WI | 列出候选，不选择第一个 |
| PLN-E055 | IMP WI completed Current Claim | 只读投影为已闭合，不写 Status |
| PLN-E056 | VFY/RLS WI 未被目标 Phase映射 | 保持未闭合 |

## 4. 非功能案例

- 100+ Work Item 的稳定排序和依赖拓扑；
- 多资源串行链可确定且无二次方漂移字段；
- 并发 create 不产生重复开放 Revision；
- 大量 Evidence/Supporting Member 不破坏 Manifest closure；
- Secret Pattern 不进入 Artifact；
- 不联网、不安装依赖、不读取兄弟 Skill；
- 删除 `docs/**` 后完整运行。

## 5. Runtime Independence

安装副本只包含：

```text
skills/sdlc-300-pln/**
skills/_shared/**
packages/sdlc_runtime/**
packages/sdlc_artifact_store/**
packages/sdlc_lifecycle/**
scripts/sdlc_skill_interface.py
```

执行：

- meta commands；
- dry-run create；
- Store 中真实 create/revise/check；
- Control Input；
- Lifecycle Query。

扫描生产 Runtime，不得出现 `docs/v1.`、`docs/plugin-development/`、固定开发仓库绝对路径。

## 6. Source Lock

Validator 必须证明 13 项 Contract ID、Version、SHA-256 完全匹配，缺失、额外、重复、排序或摘要漂移均失败。Bundled PLN Contract 必须自包含且不得包含开发路径。

## 7. Host Evidence

### Static

- `SKILL.md` 与 `agents/openai.yaml`；
- explicit invocation；
- Interface Schema；
- 不支持的 Client 不虚报。

### Real Codex

至少执行：

```text
/sdlc-300-pln --help
/sdlc-300-pln
/sdlc-300-pln create -i <exact DSN>
/sdlc-300-pln check -r <exact PLN>
```

记录发现、参数传递、用户决策、写入和错误 UX。

## 8. PASS 条件

- 所有 Critical Case PASS；
- Runtime Independence PASS；
- Source Lock PASS；
- 全仓回归 PASS；
- Review 无 Blocker/Major；
- 所有必需文件存在于远端分支 Commit；
- CI 绑定当前 Head 为 success；
- 未验证 Host 明确标记 Partial/Unknown。

---
title: sdlc-ai-spec 已落地草稿 Review
status: working-note
scope: 规划资产、Core、REQ、DSN、PLN、IMP、VFY 与 RLS 的合理性、一致性和简约性
reviewed_at: "2026-08-25"
---

# sdlc-ai-spec 已落地草稿 Review

> 本文件是本轮规划期 Review 快照，不属于 Lifecycle Artifact 或正式 Spec。持续纠偏点维护在 `review-checkpoints.md`，正式规则以对应 Spec 为准。

## 结论

当前方向合理，不需要推翻。固定 Markdown Artifact、少量 YAML Front Matter、准确 ID 与 Revision、Profile 仅作建议、Disposition 决定实际行为、DSN 主文件加 Domain 子文件、PLN 使用 Work Item、IMP 一对一 Binding，均应保留。

本轮修正后的控制链为：

```text
Input → Applicability → Artifact or Host → Check Set → Gate → Human Confirmation → Status → Downstream
```

在当前已定义范围内未发现仍需新增 Phase、Artifact 或平行状态才能解决的 P0 问题。RLS 已按最小目标生效闭环定义；长期 Operations 不作为每次变更的固定 Artifact Phase。Project Context、Project Extension 和 install/update 仍是后续定义项，本轮不提前展开。

## 本轮关键修正

| 范围 | 原问题 | 修正结果 |
|---|---|---|
| 总体定位 | 旧规划把 AI 参与、工具和固定比例写成合规前提 | 统一为执行主体中立；AI 只是可选提效手段 |
| Revision | Gate 失败或等待输入也可能被无条件冻结 | 只有 `pass / pass_with_exception` 才冻结；`fail / pending` 保持 open |
| Revision | Core 要求保存 open Revision 的每次失败尝试，却没有历史格式且与唯一 Gate Summary 冲突 | 不强制保存中间尝试；需要留痕时使用 Evidence 或项目扩展，DSN DGR 仍按专属 Contract 保留 |
| Gate | Human Confirmation 未绑定逐项 Check 的实际结果 | 增加 Check Set Result Digest；任一检查行变化都会使确认失效 |
| Exception | 当前 Artifact 只覆盖部分上游范围时仍携带全部未关闭 Exception，可能误报风险 | 只传递与当前 Scope 相交的 Exception；无法确定时仍按相关处理 |
| Revision | DSN 使用了与 Core 不同的目录布局 | DSN 全部成员统一进入 Core Revision Snapshot |
| Revision | 新上游 Revision 的存在可能无条件使旧下游失效 | 只有当前交付范围采用新版时才重新检查相关下游 |
| Disposition | `embedded` 可以指向自由文本 Host | 仅允许目标 Spec 已注册且可检查的 Host Contract |
| Phase 跳过 | PLN 为 `n/a` 时 IMP 可能缺少完成依据 | 直接路径必须由 REQ Goal/AC 或 DSN Change/VFY Point 提供等价依据，否则 PLN required |
| REQ | Priority、DRC 和第二套确认增加复杂度但不形成唯一权威 | 删除 Priority 与 DRC；Requirement 直接引用稳定 Source 或 Parent；只保留最终 Human Confirmation |
| REQ / IMP | 跳过 DSN 或 PLN 后 Scope 和 Dependency 可能只能从自然语言猜测 | DSN/PLN 为 `n/a/waived` 的直接路径由 REQ 固定 Direct IMP Scope，存在 DSN 时使用 Change Object；Dependency 增加准确状态检查引用 |
| DSN | 主 Gate、Domain Gate 与 Core 重复检查通用事实 | 通用完整性由 Core/DSN 负责，Domain Gate 只保留专属检查 |
| DSN | embedded VFY 复制 Host 内容形成双重事实源 | 只保留四类 Contract Item 到 Host Item 的映射；Host 不完整则 required |
| DSN | 复合 Domain 为 `n/a/waived` 时需要子领域记录，但 Matrix 又把 Content 固定为 `N/A` | 复合 Domain 使用单一 DDR Block 并由 Matrix Content Reference 指向；非复合 Domain 继续只用 Matrix |
| PLN | Binding、Claim 和实时状态可能与 IMP 形成双重权威 | PLN 只定义 Work Item；执行控制由 IMP 统一负责 |
| PLN | Work Item 被当成 embedded Phase 的实际结果 Host | Work Item 只描述未来工作；当前没有已注册结果 Host，不开放该 embedded 路径 |
| PLN / IMP | Lineage 唯一性与准确依赖版本容易混用 | Lineage Key 只控制唯一 Artifact/Claim；依赖必须绑定当前 Plan Revision，并保存实际采用的冻结 IMP Revision |
| PLN / IMP | 同一资源的多个实现可能各自产生无法组合的完整快照 | IMP Scope 固定登记版本化 Resource；同资源 Work Item 形成依赖链，后继 Baseline 等于前驱 Result |
| IMP | 任意相同 Scope Token 都阻断 Claim，造成无关工作过度串行 | Claim 冲突只使用相同版本化 Resource；其他 Token 保留范围和追踪语义 |
| IMP | 资源冲突先读后写，两个 Lineage 可能并发通过 | Claim 创建以 Lineage 唯一和全部 Resource 无 active 冲突为原子提交条件 |
| IMP | Patch 或 Diff 可能遗漏完整结果 | 每个 Result 必须保存不可变 Result Reference；Change Reference 仅作审计材料 |
| IMP | abandoned 重试可能覆盖 Resource 的中间已完成结果 | 每次重试重新选择当前不可变 Baseline，丢弃旧可变视图后重新应用变化 |
| IMP | 新 Resource 允许 `Baseline=N/A`，但领取规则曾要求所有 Resource 捕获 Baseline | 已有 Resource 捕获不可变 Baseline；全新 Resource 保存可复核的未创建依据，目标已存在时不得覆盖 |
| IMP | Revision 与 Claim 分别保存状态会产生非法中间状态 | Claim State 改由 Revision Index 唯一派生；条件发布只更新 `open→frozen` |
| IMP | 固定模板只有 Lifecycle Applicability 标题而没有可执行行 | 补齐 VFY、RLS 固定表；VFY required，RLS 按是否实际发版判断 |
| IMP | 前驱在下游执行期间返工，旧输入或旧链尾仍可能发布并进入 VFY | Gate 与原子发布复核全部当前依赖 Result；VFY 只采用 input、Baseline 与当前前驱 Result 连续一致的链尾 |
| IMP | Gate 要求整条资源链已 completed，会反向阻塞当前 Claim 完成 | Gate 只检查截至当前 Work Item 的链前缀；整链 completed 只作为 VFY 接收条件 |
| IMP | 单个返工引用无法覆盖新版 Binding 和多个前驱 Result | 使用排序去重的 Rework References；任一因果输入变化启动新返工序列 |
| IMP | 多 Resource 返工可能遗漏未变化结果 | 每个冻结 Revision 保留完整 Result Set；未变化行使用固定 carry-forward 表示 |
| IMP | Check 和 Gate 表格过宽、重复 Core 最终化规则 | Check 合并条件字段，Phase Gate 收敛为 6 项，最终化只保留 IMP 增量规则 |
| IMP / VFY | 单元测试资产、局部执行和最终验证边界不清 | Test 资产与开发反馈归 IMP；VFY 准确复核或按风险重执行，不把 IMP Check 当作产品结论 |
| VFY | Test、Review、自动化方式和测试层级可能形成漂移枚举 | 顶层只保留 Inspection、Analysis、Demonstration、Test 四类 Method；执行方式与层级放入 Method Detail |
| VFY | 产品验证失败可能被误判为 Artifact Gate 失败 | 产品 Conclusion 与 Artifact Status 分离；失败事实完整可信时 VFY Artifact 仍可冻结并形成 Return |
| VFY | 环境、网络或数据限制可能被误写为不适用，或把实际发版细节扩入 VFY | 临时限制保持 pending；只能在 Release Target 执行且发版继续时，以 Exception 明确未证明范围并登记 RLS 下游义务 |
| RLS | 旧交付与运行双 Phase 容易扩张为平台状态、审批和长期运行体系 | 收敛为 Release Contract、Changes、Actions、Target Confirmation、Conclusion；只执行一次最终 Gate，不建立独立持续运行 Artifact |
| 各 Phase | AI 与人工边界只存在于讨论，没有稳定说明位置 | 每个 Phase Spec 在 Gate 前保留简短协作指导；不进入 Artifact、不形成 AI 使用率或人员配置门禁 |
| 规划文档 | 建设“阶段”与 Lifecycle Phase 混用 | 项目建设顺序统一称“批次” |

## 保留的质量底线

- 同一事实只有一个权威承载位置，其他位置使用稳定引用；
- 可供下游使用的 Revision 必须不可变且可准确解析；
- `n/a` 表示客观不适用，`waived` 表示适用但获准跳过；
- Profile 不能替代逐项 Applicability 与 Disposition；
- 缺少真实输入时使用 Open Item，不允许模型补造事实；
- VFY 是固定 Artifact 控制点，但验证活动可以贯穿此前各 Phase；
- DSN 不为未来可能需求增加技术、抽象或相邻改动；
- IMP 不静默补 Requirement、Design 或 Plan 决策；
- 同一版本化 Resource 在一次 Plan 中只有一条确定的 Baseline→Result 链；
- 简单工作可以少产物，但不能缺少准确 Binding、结果和完成依据。

## 代表场景回放

| 场景 | 给定事实 | 预期结果 |
|---|---|---|
| 精确静态内容变更 | 目标内容、位置和验收结果完整，且无独立设计或规划义务 | DSN、PLN 可以为 `n/a`；required IMP 仍形成准确结果 |
| 既有服务新增稳定接口 | 接口 Contract 与验证目标需要独立确认，其他 Domain 复用准确基线 | DSN required；Interface 与 VFY Strategy 按事实展开，其他 Domain 逐项判定 |
| 敏感数据跨系统迁移 | 涉及系统边界、数据、迁移、安全、容量、部署和验证 | DSN 与 PLN required；各 Domain 只记录本领域结果并引用共同 Decision |

场景名称不直接决定 Disposition。增加或删除事实可以改变结果，这属于 Input 变化，不是同一 Input 漂移。

## 有意延期

| 内容 | 当前处理 |
|---|---|
| RLS 平台适配 | 核心只保存准确引用与 Evidence；CI/CD、Jenkins、变更单等自动适配后续定义 |
| 长期 Operations | 不作为每次变更的固定 Artifact；项目级监控、告警、值守、Runbook 和故障处置通过既有机制或扩展承载 |
| Release Target 中的补充检查 | VFY 只记录限制、Exception 与 RLS 下游义务；RLS 执行限定 Target Confirmation，不重新执行完整 VFY |
| Project Context / `/init` | 保留为 Lifecycle 前的 Bootstrap 边界，不建立第二套生命周期 |
| Project Extension | 只确认可加强项目代码、分支、产物和检查；不提前设计复杂插件体系 |
| Artifact 部分 Item 进入 Delivery Scope | v0.1 只纳入完整 Artifact；待各 Phase 有确定性依赖闭包后再讨论 |
| Spec install / update | 使用常见术语，待 Lifecycle Contract 稳定后定义 |
| 自动验证器与摘要 golden vectors | 在实现阶段定义，不在规划草稿中编写工具 |
| AI 使用痕迹和提交记录 | 留到提交或项目扩展规则讨论，不进入当前 Core |

## 明确不采纳

| 建议 | 决定 |
|---|---|
| 用 JSON、XML 或纯机器模型替代固定 Markdown | 不采纳；固定 Markdown + YAML Front Matter 保持人机可读 |
| 为 QA 增加独立 Phase、Artifact 或状态 | 不采纳；复用 Check Set、Evidence、Gate 和 Human Confirmation |
| 为直接 IMP 创建临时或合成 Work Item | 不采纳；满足直接 Binding Contract，否则 PLN required |
| 为 Claim 增加租约、自动超时接管或复杂锁状态 | 暂不采纳；当前只保留最小原子领取与显式放弃 |
| 同一版本化 Resource 内按 path/module 自动并行 | 暂不采纳；在隔离与唯一集成结果 Contract 未定义前保持 Resource 级串行 |
| 为未来可能并发增加自由文本协调机制 | 不采纳；当前使用 canonical Scope Token 与 Depends On |
| 为 Revision 增加 current/latest 副本或 rollback | 不采纳；单一 Revision Index 与不可变 Snapshot 已足够 |

## 参考依据

- [ISO/IEC/IEEE 12207:2026](https://www.iso.org/standard/90219.html)：软件生命周期过程可以并行、迭代和递归应用。
- [ISO/IEC 25010:2023](https://www.iso.org/standard/78176.html)：产品质量模型可用于 Requirement、Design、Test 和 Acceptance；当前 Domain Catalog 仅作为本 Spec 的承载分类。
- [NASA Requirements Management](https://www.nasa.gov/reference/6-2-requirements-management/)：Requirement 应追踪到 Parent 或 Source，并保持与验证结果的双向追踪。
- [NASA IV&V Overview](https://www.nasa.gov/ivv-overview/)：Verification 与 Validation 关注点不同，并贯穿生命周期。
- [W3C WCAG 2.2, Name, Role, Value](https://www.w3.org/TR/WCAG22/#name-role-value)：程序化语义与辅助技术暴露是 Accessibility Applicability 的必要判断因素。
- [NASA Software Assurance and Software Safety](https://sma.nasa.gov/sma-disciplines/software-assurance-and-software-safety)：Software Assurance 贯穿生命周期并依赖客观 Evidence。

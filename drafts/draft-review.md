---
title: sdlc-ai-spec 已落地草稿 Review
status: working-note
scope: 规划资产、Core、REQ、DSN、PLN、IMP、VFY 与 RLS 的合理性、一致性和简约性
reviewed_at: "2026-08-27"
---

# sdlc-ai-spec 已落地草稿 Review

> 本文件是本轮规划期 Review 快照，不属于 Lifecycle Artifact 或正式 Spec。持续纠偏点维护在 `review-checkpoints.md`，正式规则以对应 Spec 为准。

## 结论

当前方向合理，不需要推翻。固定 Markdown Artifact、少量 YAML Front Matter、准确 ID 与 Revision、Profile 仅作建议、Disposition 决定实际行为、DSN 主文件加 Domain 子文件、PLN 使用 Work Item、IMP 一对一 Binding，均应保留。

本轮修正后的控制链为：

```text
Input → Applicability → Artifact or Host → Check Set → Gate → Final Confirmation → Status → Downstream
```

在当前已定义范围内未发现仍需新增 Phase、Artifact 或平行状态才能解决的 P0 问题。RLS 已按最小目标生效闭环定义；长期 Operations 不作为每次变更的固定 Artifact Phase。Project Context、Project Extension 和 install/update 仍是后续定义项，本轮不提前展开。

## 本轮关键修正

| 范围 | 原问题 | 修正结果 |
|---|---|---|
| 总体定位 | 旧规划把 AI 参与、工具和固定比例写成合规前提 | 统一为执行主体中立；AI 只是可选提效手段 |
| Revision | Gate 失败或等待输入也可能被无条件冻结 | 只有 `pass / pass_with_exception` 才冻结；`fail / pending` 保持 open |
| Revision | Core 要求保存 open Revision 的每次失败尝试，却没有历史格式且与唯一 Gate Summary 冲突 | 普通 open 内容修正不增加 Revision；需要留痕时使用 Evidence 或项目扩展。IMP 已预留 Revision 必须被消费，物化失败时以 abandoned 行保留编号 |
| Revision / 执行顺序 | 索引与目录创建后可以在主文件、规则绑定和执行前清单尚未物化时继续正式 action，事后补录仍可能形成合规外观 | 成功分配必须同时物化并读回主文件固定骨架；正式 action 前固定 Evaluation Contract Set，并用既有 Evidence / Supporting Manifest 保存清单读回；真实 effect 不得降为候选材料 |
| Gate | Final Confirmation 未绑定逐项 Check 的实际结果 | 增加 Check Set Result Digest；任一检查行变化都会使确认失效 |
| Exception | 非法 ID、未知或带展示格式的状态、不可解析关闭依据或 self-supersede 可能被 Gate 忽略 | Validator 按 Core 固定表校验唯一 ID、状态、来源及可解析且非自身的关闭依据；异常结构本身即阻断 Gate |
| Exception | 当前 Artifact 可能携带与当前交付范围无关的上游 Exception，造成误报 | 只传递与当前完整 Delivery Scope 相交的 Exception；当前 Artifact Contract 不选择 Artifact 的部分 Item，无法确定时仍按相关处理 |
| Revision | DSN 使用了与 Core 不同的目录布局 | DSN 全部成员统一进入 Core Revision Snapshot |
| Revision | 新上游 Revision 的存在可能无条件使旧下游失效 | 只有当前交付范围采用新版时才重新检查相关下游 |
| Revision / Gate | 单个 Artifact 可混用不同 Snapshot 的 Core、Phase 和 Domain 规则 | 内置 Contract 固定来自同一 Snapshot；不同 Artifact 仅在 Artifact Contract 兼容时跨 Snapshot 衔接 |
| Revision / 控制恢复 | 冻结 Revision 后发现直接或传递 Input 不可解析时，旧 Gate 外观可能继续污染下游；强制重做产品又会制造无意义工作 | 从最早失效上游依次恢复；旧 Revision 只保留为历史记录，Base 仅作同 Artifact 内容来源，新 Input 必须完整覆盖原 Scope 与义务。旧字节作为 Candidate Material 重新登记和复核；IMP 只有在当前 Resource、外部状态与副作用均可证明等价时允许未变化结果，否则重放或重新执行 |
| Final Confirmation | 客观检查已闭合时仍要求逐 Artifact 人工签字，容易诱发冒填或复制旧批准 | v0.2 保留单一 Final Confirmation，允许独立 Reviewer 在无 Open Item、Exception、Waiver、主观判断或外部权限需求时受托确认；其他情况仍由真实权威确认 |
| Final Confirmation / 执行身份 | Markdown 展示差异或在单字段拼接多个身份可能绕过独立性比较 | 相关字段统一为单一稳定身份 token，比较前规范化最外层行内代码；多人执行使用统一运行 ID |
| 控制枚举 | 用 Markdown 强调或链接包装 `waived` 等值时，视觉语义与机器值可能分裂 | 全部控制枚举只接受规范裸值；委托确认再按显示语义防御性识别被包装的 waiver |
| IMP / 控制恢复 | 同一 IMP 的旧 Revision 因 Authority 链失效时，既不能作为 Input，也没有新的 Rework 原因可重启 completed Claim | 只允许同一 IMP Artifact 的旧失效 Revision 作为控制恢复 Rework Reference；它不进入 `inputs`、不提供 Authority，并受既有序列唯一性约束 |
| Disposition | `embedded` 可以指向自由文本 Host | 仅允许目标 Spec 已注册且可检查的 Host Contract |
| Phase 跳过 | PLN 为 `n/a` 时 IMP 可能缺少完成依据 | 直接路径必须由 REQ Goal/AC 或 DSN Change/VFY Point 提供等价依据，否则 PLN required |
| REQ | Priority、DRC 和第二套确认增加复杂度但不形成唯一权威 | 删除 Priority 与 DRC；Requirement 直接引用稳定 Source 或 Parent；只保留单一 Final Confirmation |
| REQ / IMP | 跳过 DSN 或 PLN 后 Scope 和 Dependency 可能只能从自然语言猜测 | DSN/PLN 为 `n/a/waived` 的直接路径由 REQ 固定 Direct IMP Scope，存在 DSN 时使用 Change Object；Dependency 增加准确状态检查引用 |
| DSN | 主 Gate、独立 Domain Gate 与 Core 重复检查通用事实 | 通用完整性由 Core 与 DSN Check 负责；required Domain 的专属检查只作为父 Gate subordinate rows 登记一次，不创建独立 Domain Gate |
| DSN | 将 VFY Strategy 嵌入其他 Host 会形成双重事实源 | DSN 存在时 Verifiability and VFY Strategy 固定为 required，并以本地稳定 ID 汇总 Requirement、Decision 和其他 Domain VFY Point 引用 |
| DSN | 复合 Domain 的子领域处置只在 required 子文件保存，顶层非 required 时会丢失逐项依据 | 父主文件固定保存 5 行子领域处置并聚合顶层结果；只有顶层 required 时创建一个详细设计 Member，子文件不重复处置 |
| DSN | 局部 Waiver、子检查 fail 与 pending 可能同时导出不同父状态 | 子领域 Waiver 只传播到父 Exceptions；父 Gate 始终按 Core 的 `fail → pending → pass_with_exception → pass` 优先级唯一聚合 |
| PLN | Binding、Claim 和实时状态可能与 IMP 形成双重权威 | PLN 只定义 Work Item；执行控制由 IMP 统一负责 |
| PLN | Work Item 被当成 embedded Phase 的实际结果 Host | Work Item 只描述未来工作；当前没有已注册结果 Host，不开放该 embedded 路径 |
| PLN / IMP | Lineage 唯一性与准确依赖版本容易混用 | Lineage Key 只控制唯一 Artifact/Claim；依赖必须绑定当前 Plan Revision，并保存实际采用的冻结 IMP Revision |
| PLN / IMP | 同一资源的多个实现可能各自产生无法组合的完整快照 | IMP Scope 固定登记版本化 Resource；同资源 Work Item 形成依赖链，后继 Baseline 等于前驱 Result |
| PLN / IMP | path/module 边界或重叠 Resource 别名可能被误解为可安全并行 | 当前内置 Spec 明确采用 Resource 级保守串行；更小 Resource 必须可独立捕获 Baseline、形成不可变 Result 并确定性集成，且同一 Provider 命名空间使用 canonical、互不重叠的 Resource ID；无法证明不相交时使用最小共同上层 Resource |
| IMP | 任意相同 Scope Token 都阻断 Claim，造成无关工作过度串行 | Claim 冲突只使用相同版本化 Resource；其他 Token 保留范围和追踪语义 |
| IMP | 资源冲突先读后写，两个 Lineage 可能并发通过 | Claim 创建以 Lineage 唯一和全部 Resource 无 active 冲突为原子提交条件 |
| IMP | Patch 或 Diff 可能遗漏完整结果 | 每个 Result 必须保存不可变 Result Reference；Change Reference 仅作审计材料 |
| IMP | abandoned 重试可能覆盖 Resource 的中间已完成结果 | 每次重试重新选择当前不可变 Baseline，丢弃旧可变视图后重新应用变化 |
| IMP | 新 Resource 允许 `Baseline=N/A`，但领取规则曾要求所有 Resource 捕获 Baseline | 已有 Resource 捕获不可变 Baseline；全新 Resource 保存可复核的未创建依据，目标已存在时不得覆盖 |
| IMP | Revision 与 Claim 若被解释为同一状态，会产生双重权威、释放窗口或恢复死锁 | Revision Index 只保存 Artifact 状态，Claim Provider 是执行状态唯一权威；完成时先冻结 Revision 再完成 Claim；普通放弃先终结 open Revision，frozen 后完成失败则以 `complete:<code>:<detail>` 释放 Claim 并创建新 Attempt |
| IMP | 项目若解析到多个 Claim Provider，Resource 冲突与唯一 Owner 可被绕过 | 同一项目及 Resource 命名空间必须确定性解析到唯一 Provider；缺失或多解时禁止领取 |
| IMP | 固定模板只有 Lifecycle Applicability 标题而没有可执行行 | 补齐 VFY、RLS 固定表；VFY required，RLS 按是否实际发版判断 |
| IMP | 前驱在下游执行期间返工，旧输入或旧链尾仍可能发布并进入 VFY | Claim 登记直接前驱 Result；冻结后 `complete` 在同一 Provider 事务递归复核完整依赖链；VFY 只采用 input、Baseline 与当前前驱 Result 连续一致的链尾 |
| IMP | Gate 要求整条资源链已 completed，会反向阻塞当前 Claim 完成 | Gate 只检查截至当前 Work Item 的链前缀；整链 completed 只作为 VFY 接收条件 |
| IMP | 单个返工引用无法覆盖新版 Binding 和多个前驱 Result | 使用排序去重的 Rework References；任一因果输入变化启动新返工序列 |
| IMP | 多 Resource 返工可能遗漏未变化结果 | 每个冻结 Revision 保留完整 Result Set；未变化行使用固定 carry-forward 表示 |
| IMP | Check 和 Gate 表格过宽、重复 Core 最终化规则 | Check 合并条件字段，Phase Gate 收敛为 6 项，最终化只保留 IMP 增量规则 |
| IMP / VFY | 单元测试资产、局部执行和最终验证边界不清 | Test 资产与开发反馈归 IMP；VFY 准确复核或按风险重执行，不把 IMP Check 当作产品结论 |
| VFY | Test、Review、自动化方式和测试层级可能形成漂移枚举 | 顶层只保留 Inspection、Analysis、Demonstration、Test 四类 Method；执行方式与层级放入 Method Detail |
| VFY | 产品验证失败可能被误判为 Artifact Gate 失败 | 产品 Conclusion 与 Artifact Status 分离；失败事实完整可信时 VFY Artifact 仍可冻结并形成 Return |
| PLN / VFY / RLS | 下游只检查已经出现的 Result，未执行 Work Item 可能不可见 | VFY 从完整 PLN 派生全部 IMP/VFY Work Item；RLS 以现有 Source References 闭合全部 RLS Work Item，不增加状态表 |
| VFY | 只生成部分方法或混用 Purpose 也可能聚合为完整 Verification / Validation 通过 | Method 索引以 Obligation References 唯一覆盖上游义务与 Return；Purpose 必须相容，both Target 的两个结论分别只聚合相容 Method |
| VFY / IMP | Return 仅靠 Subject 祖先关系定位，可能重开错误 Work Item | Return Phase=IMP 必须绑定唯一准确 IMP Binding；多 Lineage 拆分，无法定位时返回 PLN |
| IMP | Claim 前历史候选可能被吸入 Baseline 并倒签为正式 Result | 候选只作 Evidence；Claim 后从声明 Baseline 按 Scope 重放、检查并登记新的不可变 Result |
| VFY | 环境、网络或数据限制可能被误写为不适用，或把实际发版细节扩入 VFY | 临时限制保持 pending；只能在 Release Target 执行且发版继续时，以 Exception 明确未证明范围并登记 RLS 下游义务 |
| RLS | 旧交付与运行双 Phase 容易扩张为平台状态、审批和长期运行体系 | 收敛为 Release Contract、Release Items、Post-release Confirmation 和 Conclusion；同一 Markdown 最终成为上线报告，不建立 OPS |
| RLS | 强制授权失效与重取机制超过通用发版记录边界 | 只保留可选 Approval or Trigger Reference；具体审批层级、职责分离和窗口由项目扩展决定 |
| RLS / REQ / DSN / PLN / IMP / VFY | 目标侧失败需要上游修正，但自由文本无法唯一确定去向 | RLI / RCF 使用固定 Follow-up Disposition；对应 Phase 只接收匹配值，产品修正重入 VFY，不增加 Return 表或平行状态 |
| RLS | cancelled、failed、waived 和部分效果组合可能没有唯一 Conclusion | 使用固定全序：失败优先于主动取消，success 必须有实际目标侧 pass，产生目标效果后的其余最终组合为 partial；不增加状态机 |
| REQ / VFY / RLS | 将所有目标状态排除出 Acceptance Criteria 会误删目标场景中的产品义务 | 只排除发版动作、流程状态和发布记录；产品行为、可用性与运行约束仍由 REQ / VFY 约束，正式 Target 限制再由 RLS 承接 |
| VFY / RLS | 只建立 Target-only RCF 引用仍可能在发版后发现不可执行、收窄判定口径或形成冲突 Exception | Target-only waived Method 保留完整详情；发版前确认 RCF 执行前提；按来源 Exception 的全部映射 RCF 一次聚合终态，不增加新控制表 |
| 各 Phase | AI 与人工边界只存在于讨论，没有稳定说明位置 | 每个 Phase Spec 在 Gate 前保留简短协作指导；不进入 Artifact、不形成 AI 使用率或人员配置门禁 |
| Core | 同一早期 Exception 经多个直接 Input 到达时，模型可能自行合并或重复 | 当前内置 Spec 按每个直接 Input 的当前 Exception Reference 分别承接，不沿 Origin 自动合并；仅当其中一个冻结直接 Input 已汇总全部相关义务，且其他直接 Input 不再保留独立相关 Exception 时使用单一引用 |
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
| Release Target 中的补充检查 | VFY 只记录限制、Exception 与 RLS 下游义务；RLS 仅执行对应 Post-release Confirmation，不重新执行完整 VFY |
| Project Context / `/init` | 保留为 Lifecycle 前的 Bootstrap 边界，不建立第二套生命周期 |
| Project Extension | 只确认可加强项目代码、分支、产物和检查；不提前设计复杂插件体系 |
| Artifact 部分 Item 进入 Delivery Scope | 当前 Artifact Contract 只纳入完整 Artifact；待各 Phase 有确定性依赖闭包后再讨论 |
| Spec install / update | 使用常见术语，待 Lifecycle Contract 稳定后定义 |
| 自动验证器与摘要 golden vectors | 在实现阶段定义，不在规划草稿中编写工具 |
| AI 使用痕迹和提交记录 | 留到提交或项目扩展规则讨论，不进入当前 Core |

## 明确不采纳

| 建议 | 决定 |
|---|---|
| 用 JSON、XML 或纯机器模型替代固定 Markdown | 不采纳；固定 Markdown + YAML Front Matter 保持人机可读 |
| 为 QA 增加独立 Phase、Artifact 或状态 | 不采纳；复用 Check Set、Evidence、Gate 和 Final Confirmation |
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

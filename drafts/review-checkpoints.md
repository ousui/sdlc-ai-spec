---
title: sdlc-ai-spec Review Checkpoints
status: working-note
scope: 讨论过程中已确认的纠偏点与后续复查项
---

# Review Checkpoints

> 本文件是规划期持续维护的唯一复查清单，不属于 Lifecycle Artifact 或正式 Spec。`draft-review.md` 是单次 Review 快照；后续 Phase Review 和整体 Review 必须以本清单逐项复查，正式规则仍以对应 Spec 为准。

| ID | 已确认的纠偏点 | 后续 Review 检查 |
|---|---|---|
| RVW-001 | 规范、标准统一使用 Spec；阶段统一使用 Phase；固定 Phase Code 为 REQ、DSN、PLN、IMP、VFY、RLS。 | 检查是否重新出现同义词、旧 Code 或含义漂移。 |
| RVW-002 | Lifecycle Profile 只提供默认建议，不是不同生命周期；实际执行由逐项 Disposition 决定。 | 检查是否把 full、lite、hotfix 写成互斥流程或用 Profile 直接跳过 Gate。 |
| RVW-003 | 所有 Phase 按固定生命周期位置判断适用性；`n/a`、`embedded`、`waived` 必须有不同且准确的依据。 | 检查是否把“不想做”“不熟悉”或“紧急”误写为 `n/a`。 |
| RVW-004 | QA 由各 Phase 的 Check Set、Evidence 和 Gate 贯穿承载，不是独立 Phase；VFY 是固定控制点且必须生成 Artifact。 | 检查是否重新增加 Test 或 QA Phase、平行 QA 结构，或允许整体跳过 VFY Artifact。 |
| RVW-005 | 主要 Artifact 使用固定 Markdown 模板和 YAML Front Matter；字段和语义稳定，自然语言允许不同。 | 检查模板是否过度自由、过度机器化或出现多种权威格式。 |
| RVW-006 | Artifact 必须使用显式 ID 和 Revision 追踪，不依赖目录、文件顺序、标题或内容相似度自然关联。 | 检查是否出现隐式覆盖、模糊绑定或路径即身份。 |
| RVW-007 | REQ 接受任意形式输入，但必须转换为当前 Spec 的标准 Artifact 后才能进入下游。 | 检查是否把外部方法、工具或其产物直接作为规范上层。 |
| RVW-008 | DSN 使用主文件总纲与全量 Domain 索引，详细内容只写入适用 Domain 子文件。 | 检查是否重新形成单个巨大模板，或为 `n/a` Domain 创建空文件。 |
| RVW-009 | Domain 子文件按需要阅读，不绑定角色；可以接受 AI 设计而不逐行阅读，但确认者接受结果及风险。 | 检查是否把阅读行为、责任角色、适用性和人工确认混为一谈。 |
| RVW-010 | Domain 为 `required` 只表示需要独立设计，不表示必须引入新技术、组件或平台。 | 检查是否把完成 Domain 等同于采购、安装或增强工具。 |
| RVW-011 | 优先复用已确认基线；`embedded` 表示已注册且准确的 Host 完整覆盖，`n/a` 表示不存在相关义务或影响。 | 检查是否因“没有新增技术”误判 `n/a`，或因“存在运行变化”一律判定 `required`。 |
| RVW-012 | `/init` 是 Lifecycle 前的 Project Bootstrap，不是 Phase；新旧项目采用不同采集策略，但未来必须使用同一个 Project Context Contract。 | 检查是否把尚未定义的 Context 格式写成既有事实、建立第二套新项目生命周期，或让 `/init` 代替 REQ、DSN 和技术选型。 |
| RVW-013 | 技术选型统一记录在主文件 Design Decisions，受影响 Domain 引用同一 DEC；项目既有强制选型只需引用。 | 检查是否在多个 Domain 重复选型，或为既定约束虚构候选方案。 |
| RVW-014 | Design Pattern 只用于解决当前、可证明的问题；直接实现是有效候选，不得为未来可能需求创建抽象。 | 检查新增层次、接口、配置和扩展点是否具有当前 Requirement、简单方案对比和明确代价。 |
| RVW-015 | 设计只处理当前范围，不顺手重构、优化或修复相邻内容；非阻塞相邻问题只报告。 | 检查每项设计是否能追踪到 Requirement、准确 Baseline 或已确认约束；Context Contract 闭合前不得把可变 Context 当可验证来源。 |
| RVW-016 | 外部方法和优秀实践只能转化为中性、通用规则，不在正式 Spec 中保留外部 Skill 名称或工作流依赖。 | 检查正式内容是否重新引用外部 Skill 并扩大模型理解范围。 |
| RVW-017 | Project Extension 机制后续单独定义，目标是对项目代码、分支和额外产物约束提供简单扩展。 | 检查是否提前设计复杂插件体系或重新发散到非当前目标。 |
| RVW-018 | AI 使用痕迹属于后续提交规范的候选内容，不在 Core、REQ 或 DSN 过早规定。 | 到提交规范 Review 时再讨论 Session ID、模型和推理级别的公开边界。 |
| RVW-019 | Spec 分发相关术语优先使用 install 和 update；不得把应用迁移中的恢复问题与 Spec 安装更新机制混为一谈。 | 到安装更新机制 Review 时重新确认，不提前引入 rollback、reconcile 或难懂术语。 |
| RVW-020 | 任何“通常 required”的判断都必须有明确触发条件，并允许现有能力通过 `embedded` 覆盖。 | 检查各 Domain 的 Applicability 是否过宽、把常见影响错误提升为独立设计义务。 |
| RVW-021 | `REQ → DSN → PLN → IMP → VFY → RLS` 是 Artifact 与 Gate 控制流，不是活动只能执行一次的线性生命周期；活动可以并行、迭代和返回上游，长期 Operations 不属于每次变更的固定 Phase。 | 检查是否把位置顺序误写为活动执行顺序，或重新增加固定运行 Phase。 |
| RVW-022 | Disposition 使用固定判定顺序；`embedded` 只改变承载位置，不降低内容、Evidence 和 Gate 要求。 | 检查同一影响是否可同时被任意解释为 required、embedded 或 n/a。 |
| RVW-023 | DSN Completion 不得把 `n/a` 与 `waived` 合并；Domain 完成状态必须由内容完整性和 Gate 结果约束。 | 检查是否重新使用同一个状态掩盖已授权但未执行的义务。 |
| RVW-024 | DSN 必须明确 Baseline、Target State、Change Type 和 Change Set，使下游无需自行猜测设计差异。 | 检查是否把任务、顺序、工期或实施负责人混入 Change Set。 |
| RVW-025 | 追踪链至少覆盖 Source/Goal → Requirement/AC → Design Item/Decision → VFY Objective → Evidence，并能反向发现孤立项。 | 检查是否只做 Requirement 到章节的单向链接。 |
| RVW-026 | Verification 与 Validation 都必须进入 VFY Objective；Validation 至少绑定 Goal、Stakeholder Need 或 Goal 中的 Intended Use，Affected Party 与 Operational Context 只作适用性补充。 | 检查 VFY 是否退化为只验证技术实现符合设计，或把对象、环境本身误作待确认目标。 |
| RVW-027 | Gate Check 使用稳定 ID，Artifact Status 由 Gate 和 Exception 派生；身份、输入引用、模板、Disposition、Evidence、阻塞项、Exception 授权和人工确认等 Contract Integrity Check 不可豁免。 | 检查是否通过手工改 status 或豁免基础完整性条件放行。 |
| RVW-028 | `ready / ready_with_exception` Revision 必须不可变并可由 `Artifact ID@Revision` 通过唯一 Revision Index 和 Snapshot 目录解析。 | 检查是否重新出现 current/latest 副本、历史覆盖、模糊解析或旧 Revision 自动复活。 |
| RVW-029 | 复合 Domain 的子领域先分别判断，再按 `pending → required → embedded → waived → n/a` 聚合；局部 Waiver 始终传播到父 Artifact。 | 检查混合处置是否被外层单值掩盖。 |
| RVW-030 | 内置 Domain 是设计承载分类，不保证穷尽所有质量模型；无法映射的关注必须阻塞 Gate，不能静默忽略。 | 检查是否出现无 Domain 归属的业务规则、Safety 或其他质量关注。 |
| RVW-031 | Project Context 只登记已生效 Decision 的完整引用，原 DSN 保持权威；未知信息进入 Open Items，不混用 `pending`。 | 定义 Context Contract 时检查是否形成双重事实源。 |
| RVW-032 | Gate、人工确认和 Domain Gate 必须绑定实际 Control Input Digest；同一 Revision 内内容变化也会使旧结果失效。 | 检查是否只比较 Revision，或复制旧 Gate 结果后更新摘要。 |
| RVW-033 | Domain Gate 使用完整逐项记录；任一 required、embedded 或 Subdomain Gate 的 Exception 必须向父 Artifact Gate 传播。 | 检查父 DSN 是否把子 Gate 的 `pass_with_exception` 错误聚合为 `pass`。 |
| RVW-034 | REQ 中 Source、Goal 和 Affected Party 具有稳定内部 ID；Requirement 直接引用稳定 Source 或 Parent，最终只使用一次 Human Confirmation。 | 检查是否重新引入 DRC、逐项人工确认或用自由文本位置代替稳定引用。 |
| RVW-035 | QA Check Set 由 Core、当前 Phase、Phase 注册的 subordinate checks 和实际 Extension Check 确定性组成。 | 检查 `CORE-G-008` 是否只在全部应执行 Check 唯一登记后关闭，且 QA 没有退化为单独文档或主观声明。 |
| RVW-036 | Parent Design Input Digest 只绑定 Domain Gate 前已确定的设计输入；Completion、DGR Reference 和 DGR control member 原始摘要等派生结果必须排除。 | 检查是否形成 `Digest → Gate → 派生字段 → Digest 改变` 的循环。 |
| RVW-037 | DSN Artifact Set Manifest 同时保存 Design Input Digest 与最终原始字节摘要；Core 通用 Manifest 只定义原始摘要。 | 检查是否把 DSN 专属字段扩散到其他 Phase，或只绑定当前 Domain 而沿用陈旧 DGR。 |
| RVW-038 | embedded Domain 使用固定 DDR Input Block；required 与 embedded 的完整 DGR 都只保存在 `DGC-001`，最终父 Control Input Digest 通过 Manifest 覆盖它。 | 检查是否又把 DGR 写回设计输入文件，或按 Disposition 分成多个历史位置。 |
| RVW-039 | 上游与当前 Scope 相交的未关闭 Exception 必须 carried，或以 Evidence 证明不相交、resolved/superseded；无法确定是否相关时仍按相关处理。人工批准必须完整接受当前全部未关闭 Exception。 | 检查当前 Artifact 只覆盖部分上游范围时是否误带无关风险、遗漏相关风险，或批准列表存在漏项、过期和额外引用。 |
| RVW-040 | Requirement 的 Source or Parent References 形成有根、无自引用、无环的直接来源图；自由文字只作解释，Artifact Source 与 Front Matter Input Revision 必须一致。 | 检查间接循环、无根推导，或正文与 Front Matter 指向不同 Revision。 |
| RVW-041 | 所有可引用 Item ID 分配后跨 Revision 稳定，删除或替代后不得重排复用。 | 检查完整 Item Reference 是否因标题、顺序或 Revision 变化而指向不同语义。 |
| RVW-042 | DGR 每次执行分配新 Attempt；每个 Domain 全局最大编号是唯一 Current Attempt，输入不匹配即无效且不能回退。 | 检查输入回退或新 `fail/pending` 后是否复活旧 `pass`。 |
| RVW-043 | Parent Exception Set 从父 Exceptions 表的 `active/carried` 项确定性派生，并由 Human Confirmation 与最终 Gate Summary 共同绑定。 | 检查 Domain Waiver 是否遗漏、重复或在汇总生成前形成时序依赖。 |
| RVW-044 | Domain Gate Check 不直接标记 n/a/waived；内容 Check 只约束 required/embedded 且未豁免义务，处置记录合规后 Check 为 pass，Exception 由 DGR 聚合。 | 检查局部 waived 是否被错误要求补齐内容，或被聚合为普通 pass。 |
| RVW-045 | 通用 DDR 是 embedded 的默认最小 Contract；专属扩展只在通用字段不足时定义。 | 检查是否增加大量重复微型模板，或用自由字段承载新增独立设计。 |
| RVW-046 | Open Items 使用固定字段；未解决的阻塞输入项派生 `waiting_input`，内部未完成工作由 Gate `pending` 派生 `draft`。 | 检查是否继续通过自由文本猜测 Status。 |
| RVW-047 | v0.1 的 embedded Host 不指向父主文件章节；Markdown 标题也不能充当稳定 Design Reference。 | 检查 Host 和 Traceability 是否可由 Item/Member/Artifact Revision 与摘要机械解析。 |
| RVW-048 | 复合 Domain 始终使用一个控制块并按固定顺序每个 Subdomain 一行；required 与非 required 使用相同字段。 | 检查子领域 Host 摘要、偏差、VFY 和 Exception 是否丢失，或出现多种 Block 基数。 |
| RVW-049 | Manifest 成员集和成员摘要一致性由不可豁免的 `CORE-G-003` 检查。 | 检查 Supporting Artifact 是否能绕过命名 Gate 进入下游。 |
| RVW-050 | 冻结 Revision 的任何内容、Spec Binding、Gate、确认或 Status 更新都创建新 Revision，不能原地重做控制记录。 | 检查“无语义变化”是否被用作修改旧快照的理由。 |
| RVW-051 | 每个已知必要输入缺口唯一登记为 Open Item；v0.1 的 `Blocked References` 只使用稳定 Check ID。typed value 未知时不创建正式数据行，非法占位值不能代替输入。 | 检查 `waiting_input` 是否因漏记、重复、伪造或未定义字段路径而错误派生。 |
| RVW-052 | `DGC-ID` 只表示 Domain Gate control member，`CTL-ID` 只表示 Security Control。 | 检查 Item 与 Member 缩写是否造成同一 Artifact Set 内的语义混淆。 |
| RVW-053 | 多值 Reference 使用固定 Reference Set 语法：`, ` 分隔、去重升序、空集合 `None`；单数 Reference 只允许一个值。 | 检查不同模型是否用分号、换行、Markdown 链接或不同顺序生成等价但不稳定的结构。 |
| RVW-054 | DGR、Gate Summary 与 Human Confirmation 都绑定完整 Evaluation Contract Set，不能只绑定 Domain/Phase Spec 或 Front Matter 版本字符串。 | 检查 Core、Phase、Domain 或 Extension 规则变化后是否错误沿用旧 Gate。 |
| RVW-055 | Spec Reference 使用唯一仓库相对路径与 SHA-256，不使用裸摘要、绝对路径或多种相对路径。 | 检查 Evaluation Contract Set 与 DGR 是否能解析到同一准确 Spec 内容。 |
| RVW-056 | Revision 从已持久化最大值单调加一并原子分配；并发冲突时重读后递增，不覆盖或复用。 | 检查多个生成过程是否可能得到同一 `Artifact-ID@Revision`。 |
| RVW-057 | 可覆盖多个对象的字段使用复数 References 与 Reference Set；单数 Reference 只允许一个值。 | 检查字段基数是否与正文规则冲突。 |
| RVW-058 | inputs、Manifest 和固定 ID 表使用确定顺序；业务顺序用显式 Step/Order，不靠生成时行位置猜测。 | 检查同一输入是否因无语义重排产生不同 Digest。 |
| RVW-059 | 所有“单元格视为空值”使用同一字节级投影，不由 Markdown 解析器重新序列化。 | 实现验证器时用 golden vectors 检查跨实现 SHA-256 一致性。 |
| RVW-060 | Matrix 只保存 DOM-ID/DDR-ID；路径、Host 和 Supporting Member 摘要分别只由 Manifest、DDR 维护。 | 检查同一事实是否在三张表中重复且产生漂移。 |
| RVW-061 | Evidence、Exceptions、Open Items 无记录时使用各自唯一 `None` 行，不能预置伪 ID。 | 检查空集合是否出现多种编码或伪记录。 |
| RVW-062 | Affected/Mapped Domains 使用注册英文名并按 Matrix 固定顺序组成集合；unsupported 只能单独出现。 | 检查同一 Domain 集合是否因名称、分隔或顺序不同而漂移。 |
| RVW-063 | 跨文件 Content/Supporting Member 使用完整 Member Reference；Basis、VFY、Exception 等多值字段使用复数 Reference Set。 | 检查裸 Member ID 或单数字段是否丢失关系。 |
| RVW-064 | VFY Strategy 只有在 Host 完整承载 VFO/VFM/VPC/VEC 时才能 embedded；DDR 不得补造 Host 中不存在的设计。 | 检查简单需求是否只因 AC 清晰就错误使用 embedded。 |
| RVW-065 | Workflow 与 User Journey 使用稳定 Flow/Journey、Step、Transition ID 和显式分支。 | 检查多流程、多旅程是否仍靠行号或自由文本关联。 |
| RVW-066 | embedded VFY Contract 不复制 Host 内容或分配本地影子 ID，只保存 VFY Objective、Method、Pass Criteria 和 Evidence Contract 四类固定 Host Item References。 | 检查 Host 是否为每类 Contract 提供稳定、完整的 Item；无法稳定映射时应改为 required。 |
| RVW-067 | Trigger 必须显式引用 Flow，Journey 必须显式引用本地 User/Goal 记录，并按适用性补充上游 Goal Item。 | 检查多流程、多旅程的启动与服务对象是否仍依赖文字匹配。 |
| RVW-068 | Revision 使用确定目录与单一 Revision Index；open 目录是唯一工作位置，frozen 后不可修改，下游引用不得使用 latest 或自动回退。 | 检查是否重新形成 working/current 双副本、可变指针、历史覆盖或旧 Revision 自动复活。 |
| RVW-069 | Simple is best：现有结构可以闭合的问题，不新增概念、文件、字段、状态或抽象。 | 每次新增规则都检查其解决的已知问题、不可替代性和阅读成本；仅为未来可能需求的结构应删除或延期。 |
| RVW-070 | 最低 QA Contract 直接复用 Check Set、Evidence、Gate 和 Human Confirmation，不建立独立 Artifact、Phase、Manifest、Status 或 Ruleset。 | 检查所有应执行 Check 是否完整唯一、结果有依据且 Gate 可确定性聚合。 |
| RVW-071 | Delivery Scope 只聚合完整 Scope Input；前置 Result、Rework 和 Evidence 等同一 Binding 控制输入不因数量强制产生 PLN。v0.1 不在 PLN 选择 Artifact 的部分 Item。 | 检查控制输入是否被误作新范围、真实多范围输入是否逃避聚合，或 PLN 是否自行猜测部分范围闭包。 |
| RVW-072 | PLN Artifact 表示完整交付执行计划；`Work Item` 是规范内的最小计划单元，外部执行或跟踪对象不能替代 `PLN-ID@Revision#WI-ID`。 | 检查是否把整个 PLN 误作单个任务，或把外部编号变成权威身份。 |
| RVW-073 | Work Item 不保存实时状态、`parallel` 或成对冲突列表；依赖和 Execution Scope 是执行顺序与潜在冲突的规划依据。 | 检查是否把 IMP 进度写回冻结 Plan，或因重复字段产生漂移。 |
| RVW-074 | PLN 定义完整交付执行计划，不强制承担预算、工期、人员负载和日历排期；这些内容只有在项目确有需要时再扩展。 | 检查是否为了“Plan”名称引入完整项目管理体系并扩大当前 Spec。 |
| RVW-075 | PLN 是否 required 由范围聚合、独立变化范围、必须显式记录的依赖与顺序、共享可变范围和约束分配等事实触发；Profile 或主观偏好不能直接决定。 | 检查原子变更是否被强制制造 Plan，或复杂交付是否因 lite/hotfix 被跳过。 |
| RVW-076 | required Phase 生成独立 Artifact；embedded、n/a、waived 不生成独立 Artifact，下一个 required Phase 绑定最近可用上游 Revision 并保留处置解析链。 | 检查跳过 Phase 后是否出现断链，或为 n/a/waived 创建空 Artifact。 |
| RVW-077 | Work Item 的 Execution Scope 使用固定 Scope Token，不允许“相关模块”等自由描述；不同 Type 不自动证明互斥，它只负责识别边界和潜在冲突。 | 检查同一范围是否因模型措辞不同而无法比较，或 Scope Token 被误作实时锁。 |
| RVW-078 | 已有 PLN Work Item 的 IMP 路径严格使用 `一个 IMP Work Item ↔ 一个权威 IMP Artifact`；IMP 不得重新分组。 | 检查模型是否在执行时改用一对多、多对一，或用第二个 Artifact 重复承接同一 Work Item。 |
| RVW-079 | 每次领取只处理一个准确 Binding；同一 Binding Lineage 跨上游 Revision 仍只有一个 active Owner 和 Attempt，重复领取必须停止且不得覆盖。 | 检查是否把 `PLN@1#WI-001` 与 `PLN@2#WI-001` 误当两个可并行 Lineage。 |
| RVW-080 | 同一 Lineage 的重复领取与不同 Lineage 的版本化 Resource 冲突分别判断；v0.1 只有相同 `resource:<id>` 阻断 Claim，其他 Scope Token 只负责范围与追踪。 | 检查是否只防重复 Owner，或因共享 component/environment 等非 Resource Token 过度串行化。 |
| RVW-081 | 每个 required IMP 使用一个 `IMP Binding Reference`；PLN 为 required 时绑定 Work Item，其他处置按准确上游或 Host 绑定，不创建合成 Work Item。 | 检查直接实施是否组合多个 Input、产生多个 Outcome，或用临时任务掩盖本应 required 的 PLN。 |
| RVW-082 | 领取先无副作用解析 Lineage；active/completed 幂等返回必须同时匹配准确 Binding 与规范化 Rework References。仅新领取或合法重领执行 Readiness，通过后以“Lineage 唯一且全部 Resource 无 active 冲突”为提交条件原子分配 Claim、Artifact ID 与 Revision。 | 检查新增返工原因是否被误当重复、相同返工是否重复激活、并发领取是否同时通过，或是否先创建空 IMP、先修改产品内容。 |
| RVW-083 | IMP 使用固定七项 Implementation Consideration；Matrix 只做覆盖索引，实施逻辑按一个连续 Approach 展开，不按考量项拆文件。 | 检查是否漏项、增加自由 Catalog，或把一个 Work Item 切成不连贯的多个方法文档。 |
| RVW-084 | 每个 required Consideration 使用对应固定 Method Block；n/a 和 waived 不生成空块，简单未触发项不因模板被放大。 | 检查是否把 applicable 留给模型自由发挥，或为普通条件、赋值和透传制造复杂方法块。 |
| RVW-085 | IMP 选择顺序为上游 Decision、项目既有约束、最简单正确局部实现、必要局部抽象；新依赖、公共抽象和架构变化返回 DSN。 | 检查是否推测性抽象、为模式而模式、顺手重构或在 IMP 静默补设计。 |
| RVW-086 | 一个 Implementation Result 行表示一个独立版本化资源，不按文件拆分；每行始终具有不可变 Result Reference，Change Reference 仅作可选审计材料。 | 检查 Patch/Diff、分支、Tag、当前工作树、路径或无摘要临时文件是否被误作完整结果。 |
| RVW-087 | Implementation Checks 记录局部实现检查；n/a 只表示客观不适用，适用但跳过必须 waived 并关联 Exception。 | 检查是否强制执行无关工具、用 n/a 掩盖跳过，或让 IMP 提前给出完整 VFY 结论。 |
| RVW-088 | IMP Gate 只证明 Binding 已形成完整、可追踪、可复现且可进入 VFY 的实现结果，不证明 Requirement 已验证或可以发版。 | 检查 IMP Completion、VFY Acceptance 和 RLS Readiness 是否再次混用。 |
| RVW-089 | Claim State 由对应 Revision Index 唯一派生，不能独立写入；条件发布只更新 `open→frozen`，失败保持 `open`，Resolver 还必须验证唯一 Current Claim 指向该 Revision。 | 检查双状态漂移、部分发布、重复完成、孤立 frozen Revision 或 Gate 失败后错误释放 Binding。 |
| RVW-090 | completed Claim 默认保持完成；相同 `Binding Lineage Key + Rework References` 只启动一个返工序列。领取、Gate 与原子发布都复核 `Depends On` 传递闭包；abandoned 后仅在 Binding 与全部前驱 Result 未变时才追加 Attempt，变化时以完整引用集合启动新序列。 | 使用冻结 VFY Return、更新 Binding 或变化前驱 Result 作为准确返工依据；检查重复 Return、祖先前驱变化、遗漏因果引用或并行返工序列。 |
| RVW-091 | Claim 原子保存且冻结 Execution Scope；实际 Changed Scope 必须是其子集，扩大范围或改变 Outcome 时返回 PLN 或准确上游。 | 检查是否在实施或 Close 时覆盖 Claim Scope 以掩盖越界。 |
| RVW-092 | Security、Performance 等保持 DSN 约束，抽象与模式进入 Decision Rules，Style 进入项目工具，Test 进入 Check/VFY；均不扩张为 IMP 并列 Consideration。 | 检查七项 Catalog 是否因重复上游 Domain 或工具职责而无限增长。 |
| RVW-093 | Spec 只根据 Artifact、Evidence 和 Gate 判断合规，不区分人工、AI 或其他执行主体；AI 是可选提效手段。 | 检查是否重新出现 AI 必须参与、固定参与比例或工具使用量合规条件。 |
| RVW-094 | 只有 Aggregate Gate 为 `pass / pass_with_exception` 的 Revision 才能冻结；`fail / pending` 保持 open 并允许修正。 | 检查失败或等待输入的 Revision 是否被发布为可供下游使用的 Snapshot。 |
| RVW-095 | `embedded` 只允许使用目标 Spec 已注册、可引用且具有完整性 Check 的 Host Contract。 | 检查自由文本、标题或缺字段 Host 是否被用于绕过独立 Artifact。 |
| RVW-096 | 准确 Binding Reference 负责版本追踪；不含 Revision 的 Binding Lineage Key 负责跨 Revision 唯一 Claim 和唯一 IMP Artifact。 | 检查同一稳定 Item 的新 Revision 是否错误分配第二个 IMP Artifact。 |
| RVW-097 | IMP Baseline 是首次产品修改前的准确状态；每次重试重新选择。Resource 未前进时可复用原 Baseline，已前进时从当前不可变状态重新应用变化，旧可变视图不得继承。 | 检查旧 Baseline 是否覆盖中间已完成结果，或把 `HEAD`、残留工作区静默定义为新 Baseline。 |
| RVW-098 | Core、Phase 与 Domain Check 各自只维护本层权威检查；Domain 不重复跨领域一致性、通用 N/A 或父级 VFY 覆盖检查。 | 检查 Gate 是否因复制同一事实而重新膨胀或产生相反结论。 |
| RVW-099 | 项目建设顺序称“批次”，只把 REQ、DSN、PLN、IMP、VFY、RLS 称为 Lifecycle Phase。 | 检查总体规划是否重新混用建设阶段与生命周期位置。 |
| RVW-100 | 跳过一个 Phase 只有在现有固定字段可确定性满足下一个 required Phase 的 Readiness 时才成立；否则前一 Phase 必须 required。 | 检查简单路径是否暗造 mini-Plan，或在完成依据不足时直接进入 IMP。 |
| RVW-101 | Human Confirmation 同时绑定 Revision、Control Input Digest、Evaluation Contract Set 和 Check Set Result Digest；后者只覆盖除 `CORE-G-009` 外的当前 Check 行，历史 Attempt 不参与。 | 检查 Check 行变化是否更新 Check Digest，或 subordinate 其他字段变化后是否错误沿用旧 Control Digest 与确认。 |
| RVW-102 | 每个 IMP Work Item 为每个版本化资源登记 `resource:<id>`；同资源 Work Item 形成单一 `Depends On` 链，后继 Baseline 等于前驱 Result。 | 检查同一资源是否形成多个无法组合的并行快照，或由 VFY 猜测合并。 |
| RVW-103 | Plan 依赖必须展开为当前 Plan Revision 的准确 Binding，并把实际采用的冻结 IMP Revision 写入后继 `inputs`。 | 检查新旧 Plan Revision 是否串用结果，或只按无 Revision Lineage 选择“最新”Attempt。 |
| RVW-104 | Result 的 `Resource` 是项目内唯一版本化资源 ID；`Changed Scope` 使用 Claim 中已有的 Scope Token，并包含对应 `resource:<Resource>`。 | 检查组件/模块 Token 是否被误作版本化资源，或更细路径通过未定义的层级包含关系越过 Claim。 |
| RVW-105 | DSN/PLN 为 `n/a/waived` 时，直接 IMP Scope 由 REQ `Direct IMP Scope` 提供；存在直接 DSN Binding 时由 DSN Change `Object or Boundary` 提供。当前没有可用的 embedded PLN Host；Scope 缺失、多个 Resource 或需协调时 PLN required。 | 检查 IMP 是否从自然语言猜测范围、把 Work Item 当作结果 Host，或为简单路径创建第二套临时 Work Item。 |
| RVW-106 | IMP 必须按固定表重评 VFY、RLS；VFY required，RLS 按是否实际发版判断，Profile 或 IMP 完成不能自动决定。 | 检查固定模板是否只有标题而没有可执行字段，或把实现完成误作可以发版。 |
| RVW-107 | REQ Dependency 的 Current State 是快照；可变状态的 State Check Reference 必须可重复执行或实时观察，不可变 Artifact / Evidence 只证明不可变或单调成立的状态；直接 IMP 无法确定性复核时返回 PLN 或上游。 | 检查陈旧文字状态或历史 Evidence 是否被当作当前可变依赖已满足。 |
| RVW-108 | 任一 Plan 依赖的 Current Result 变化都会使仍引用旧结果的传递下游失去 VFY 就绪性；IMP Gate 只检查截至当前 Work Item 的已执行前缀，VFY 前复核全部当前依赖边，同资源链还必须 completed、连续且只有一个有效链尾。 | 检查是否用尚未执行的后继阻塞当前 Gate，或跨资源/同资源前驱返工后继续采用旧下游结果。 |
| RVW-109 | 每个冻结 IMP Revision 对 Claim 中每个版本化 Resource 恰有一个 Result 行；本 Attempt 未变化的 Resource 使用当前准确 Baseline 作为相同 Result。 | 检查返工 Revision 是否删除仍有效 Result，或 Resource 已前进后仍错误登记旧 Result。 |
| RVW-110 | active Claim 只能由当前 Owner 完成或修改；Owner 不可恢复时，授权恢复执行方先阻断旧写入，再以同一条件写入更新 Revision、Abandon Reason 和 `Abandoned By / At`，不使用自动超时接管。 | 检查永久 active 死锁、双 Owner、缺失放弃记录或隐式租约机制。 |
| RVW-111 | 已有 Resource 在首次修改前绑定不可变 Baseline；全新 Resource 使用 `N/A`，但必须有可复核的未创建依据，目标已存在时不得覆盖。 | 检查新资源是否因强制捕获不存在的 Baseline 而无法执行，或把已有目标误作新资源覆盖。 |
| RVW-112 | VFY 使用 `Target → Method → Subject → Result → Evidence → Conclusion` 的固定关系，每个 Target 和 Method 都能准确追踪，不从相似文字猜测映射。 | 检查目标遗漏、重复、无 Subject、无 Evidence，或同一结果被用于不相关 Target。 |
| RVW-113 | VFY 顶层 Method Type 只使用 `inspection`、`analysis`、`demonstration`、`test`；人工/自动化是 Execution Mode，测试层级和质量目标进入 Method Detail。 | 检查 Review、Unit、Integration、Manual、Security 等是否重新成为并列 Method Type。 |
| RVW-114 | Test 资产的实现和开发反馈性执行属于 IMP；VFY 只在结果准确对应最终 Subject 时复核，否则按 Contract 与风险重新执行。IMP Check 通过不等于 VFY 通过或允许 RLS。 | 检查同一单元测试是否被机械重复，或 IMP 局部检查是否越权形成产品级结论。 |
| RVW-115 | 产品 Conclusion 与 VFY Artifact Status 分离；可信地证明产品 `fail` 的完整 VFY Artifact 可以通过自身 Gate、冻结并形成 Return。 | 检查产品失败是否错误导致 Artifact 永远无法冻结，或 Artifact ready 是否被误解为产品通过。 |
| RVW-116 | VFY Return 是冻结 Revision 内的不可变记录，完整引用为 `<VFY-ID>@<Revision>#RET-ID`；只返回一个权威 Phase，IMP 只接受 Subject Result 可沿 `inputs` 追踪到自身 Binding Lineage 的 Return。 | 检查 Return 是否被原地改状态、缺少 Target/Subject/Evidence，或 IMP 根据标题和缺陷文字猜测返工归属。 |
| RVW-117 | 环境、网络、数据或人工输入暂不可用不是 `n/a`；Method 保持 `pending`。只能在 Release Target 执行且发版继续时使用有效 Exception，并登记准确 RLS 下游义务。 | 检查限制是否被掩盖为不适用、Target 被误记为 pass，或 VFY 展开实际发版、流量、停止和恢复机制。 |
| RVW-118 | 人工或 Hybrid 产品评价作为 VFY Evidence 保存；Core Human Confirmation 只确认 Artifact、Gate 与未关闭风险，两者不能由一次模糊签字替代。 | 检查 UI/UX 等主观判断是否无场景和观察事实，或产品验收与 Artifact 确认混为一体。 |
| RVW-119 | 每个 Phase Spec 在 Gate 前保留 3 至 5 行 AI 与人工协作指导；该内容不进入 Lifecycle Artifact，不作为 AI 使用率、人员配置或 Gate 指标。 | 检查协作建议是否膨胀为新角色体系、强制 AI 参与或重复的责任 Artifact。 |
| RVW-120 | RLS 只负责把完整 VFY Scope 的准确 Result 发布到一个明确 Target，确认目标侧状态并形成 Conclusion；不重新定义上游内容。 | 检查 RLS 是否选择部分范围、重新构建不同 Result、补写设计或顺手处理目标环境问题。 |
| RVW-121 | RLS 只有一个最终 Gate；发版前和执行中保持 open Revision，发版结束、失败或取消后冻结为唯一 Release Record。 | 检查是否增加预发版 Gate、第二份上线报告、实时状态机或重复 Attempt Contract。 |
| RVW-122 | Release Action 成功不等于目标状态正确；Target Confirmation 必须具有目标侧 Observed 与 Evidence，不能只引用流水线成功。 | 检查 CI/CD、Jenkins、工单或执行者声明是否被直接聚合为 success。 |
| RVW-123 | VFY Conclusion、RLS Conclusion 和 Artifact Status 分别表示产品符合性、目标侧发版结果和记录合规性；三者不得互相覆盖。 | 检查产品 fail 是否被 Artifact ready 掩盖，或准确失败记录是否被错误阻止冻结。 |
| RVW-124 | 长期监控、告警、值守、故障处置和日常 Runbook 不作为每次变更的固定 Artifact Phase；真实持续影响只写入 RLS Follow-up 或项目扩展。 | 检查是否重新引入独立运行 Artifact，或把普通发版扩张为持续运维体系。 |

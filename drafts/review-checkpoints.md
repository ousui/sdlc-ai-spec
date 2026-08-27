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
| RVW-009 | Domain 子文件按需要阅读，不绑定角色；可以接受 AI 设计而不逐行阅读，但确认者仍承担对应确认责任。 | 检查是否把阅读行为、责任角色、适用性和 Final Confirmation 混为一谈。 |
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
| RVW-020 | 任何“通常 required”的判断都必须有明确触发条件；DSN 优先引用准确 Baseline，当前变化仍有设计义务时保持 required。 | 检查各 Domain 的 Applicability 是否过宽，或把基线复用误写为当前内置 Spec 不支持的 Domain embedded。 |
| RVW-021 | `REQ → DSN → PLN → IMP → VFY → RLS` 是 Artifact 与 Gate 控制流，不是活动只能执行一次的线性生命周期；活动可以并行、迭代和返回上游，长期 Operations 不属于每次变更的固定 Phase。 | 检查是否把位置顺序误写为活动执行顺序，或重新增加固定运行 Phase。 |
| RVW-022 | Disposition 使用固定判定顺序；`embedded` 只改变承载位置，不降低内容、Evidence 和 Gate 要求。 | 检查同一影响是否可同时被任意解释为 required、embedded 或 n/a。 |
| RVW-023 | DSN Completion 不得把 `n/a` 与 `waived` 合并；Domain 完成状态必须由内容完整性和 Gate 结果约束。 | 检查是否重新使用同一个状态掩盖已授权但未执行的义务。 |
| RVW-024 | DSN 必须明确 Baseline、Target State、Change Type 和 Change Set，使下游无需自行猜测设计差异。 | 检查是否把任务、顺序、工期或实施负责人混入 Change Set。 |
| RVW-025 | 追踪链至少覆盖 Source/Goal → Requirement/AC → Design Item/Decision → VFY Objective → Evidence，并能反向发现孤立项。 | 检查是否只做 Requirement 到章节的单向链接。 |
| RVW-026 | Verification 与 Validation 都必须进入 VFY Objective；Validation 至少绑定 Goal、Stakeholder Need 或 Goal 中的 Intended Use，Affected Party 与 Operational Context 只作适用性补充。 | 检查 VFY 是否退化为只验证技术实现符合设计，或把对象、环境本身误作待确认目标。 |
| RVW-027 | Gate Check 使用稳定 ID，Artifact Status 由 Gate 和 Exception 派生；身份、输入引用、模板、Disposition、Evidence、阻塞项、Exception 授权和 Final Confirmation 等 Contract Integrity Check 不可豁免。 | 检查是否通过手工改 status 或豁免基础完整性条件放行。 |
| RVW-028 | `ready / ready_with_exception` Revision 必须不可变并可由 `Artifact ID@Revision` 通过唯一 Revision Index 和 Snapshot 目录解析。 | 检查是否重新出现 current/latest 副本、历史覆盖、模糊解析或旧 Revision 自动复活。 |
| RVW-029 | 复合 Domain 的子领域先分别判断，再按 `pending → required → waived → n/a` 聚合；局部 Waiver 始终传播到父 Exceptions，但父 Gate 仍按 `fail → pending → pass_with_exception → pass` 唯一聚合。 | 检查混合处置是否被外层单值掩盖、Waiver 是否覆盖 fail/pending，或重新引入未开放的 Domain embedded。 |
| RVW-030 | 内置 Domain 是设计承载分类，不保证穷尽所有质量模型；无法映射的关注必须阻塞 Gate，不能静默忽略。 | 检查是否出现无 Domain 归属的业务规则、Safety 或其他质量关注。 |
| RVW-031 | Project Context 只登记已生效 Decision 的完整引用，原 DSN 保持权威；未知信息进入 Open Items，不混用 `pending`。 | 定义 Context Contract 时检查是否形成双重事实源。 |
| RVW-032 | Artifact Gate 与 Final Confirmation 必须绑定实际 Control Input Digest、Evaluation Contract Set 和 Check Set Result Digest；Domain subordinate rows 确定性进入 Check Set。 | 检查是否只比较 Revision，或复制旧 Gate 结果后更新内容或摘要。 |
| RVW-033 | required Domain 的专属检查直接作为父 DSN Gate subordinate rows 唯一登记，不创建独立 Gate、Summary 或 Attempt。 | 检查 required Domain Check 是否缺失或重复，以及局部 Waiver 是否经 Matrix 与父 Exceptions 准确传播。 |
| RVW-034 | REQ 中 Source、Goal 和 Affected Party 具有稳定内部 ID；Requirement 直接引用稳定 Source 或 Parent，最终只使用一次 Final Confirmation。 | 检查是否重新引入 DRC、逐项确认或用自由文本位置代替稳定引用。 |
| RVW-035 | QA Check Set 由 Core、当前 Phase、Phase 注册的 subordinate checks 和实际 Extension Check 确定性组成。 | 检查 `CORE-G-008` 是否只在全部应执行 Check 唯一登记后关闭，且 QA 没有退化为单独文档或主观声明。 |
| RVW-036 | DSN Control Input Digest 通过最终 Manifest 绑定全部真实成员，并按 Core 排除 Gate 派生内容；不再定义独立 Parent Design Input Digest 或 DGR Digest。 | 检查是否形成 `Digest → Gate → 派生字段 → Digest 改变` 的循环。 |
| RVW-037 | DSN Artifact Set Manifest 只保存真实成员、Domain Spec Reference、路径和原始字节 SHA-256；不保存第二套 Design Input Digest。 | 检查是否把 DSN 专属摘要扩散到其他 Phase，或出现重复摘要权威。 |
| RVW-038 | 当前内置 DSN Spec 只为 required Domain 创建唯一 `DOM-<DOMAIN-NO>` Member；n/a 与 waived 不创建子文件或控制成员，Domain embedded 不开放。 | 检查是否重新引入 DGR、DGC、DDR 或按 Disposition 创建多套内容位置。 |
| RVW-039 | 与当前完整 Delivery Scope 相交的未关闭 Exception 必须 carried，或以 Evidence 证明不相交、resolved 或 superseded；无法确定时仍按相关处理。人工批准必须完整接受全部相关未关闭 Exception。 | 检查是否误带无关风险、遗漏相关风险，或在当前 Artifact Contract 中选择 Artifact 的部分 Item。 |
| RVW-040 | Requirement 的 Source or Parent References 形成有根、无自引用、无环的直接来源图；自由文字只作解释，Artifact Source 与 Front Matter Input Revision 必须一致。 | 检查间接循环、无根推导，或正文与 Front Matter 指向不同 Revision。 |
| RVW-041 | 所有可引用 Item ID 分配后跨 Revision 稳定，删除或替代后不得重排复用。 | 检查完整 Item Reference 是否因标题、顺序或 Revision 变化而指向不同语义。 |
| RVW-042 | open DSN Revision 重跑时直接刷新父 Gate 中唯一的当前 Check 行；frozen Revision 的任何变化都创建新 Revision，不建立 Domain Attempt。 | 检查新 fail 或 pending 后是否仍沿用旧 Check、Digest、确认或 Gate 结论。 |
| RVW-043 | Parent Exception Set 从父 Exceptions 表的 `active/carried` 项确定性派生，并由 Final Confirmation 与最终 Gate Summary 共同绑定。 | 检查 Domain Waiver 是否遗漏、重复或在汇总生成前形成时序依赖。 |
| RVW-044 | Domain subordinate Check 只为 required Domain 展开并使用 pass、fail 或 pending；n/a 与 waived 由 Matrix、父 Exceptions 和 DSN Check 验证。 | 检查 waived 是否被错误要求补齐子文件，或未传播为 pass_with_exception。 |
| RVW-045 | 当前内置 DSN Spec 不定义通用 DDR；既有设计通过准确 Baseline Reference 复用，当前存在新增设计义务时写入唯一 required Domain Member。 | 检查是否增加重复微型模板，或用自由字段承载新增独立设计。 |
| RVW-046 | Open Items 使用固定字段；不存在 fail/rejected 时，未解决的阻塞输入项派生 `waiting_input`，内部未完成工作由 Gate `pending` 派生 `draft`；已确认失败始终优先派生 `failed`。 | 检查 open item 与失败并存时是否产生两个 Status，或继续通过自由文本猜测状态。 |
| RVW-047 | 当前内置 DSN Spec 不开放 Domain embedded；未来任何 embedded 只有在目标 Spec 注册可解析 Host Contract 后才可使用，Markdown 标题不能充当稳定 Reference。 | 检查是否用主文件章节、自由文本或缺少完整性 Check 的位置绕过独立 Artifact 或 Domain Member。 |
| RVW-048 | 父 DSN 固定 5 行保存 140、310 全部 Subdomain Applicability 并聚合顶层处置；只有顶层 required 时创建一个详细设计 Member，子文件不重复处置。 | 检查非 required 时是否丢失子领域依据、局部 Waiver 或 Exception，或出现第二套处置权威。 |
| RVW-049 | Manifest 成员集和成员摘要一致性由不可豁免的 `CORE-G-003` 检查。 | 检查 Supporting Artifact 是否能绕过命名 Gate 进入下游。 |
| RVW-050 | 冻结 Revision 的任何内容、Spec Binding、Gate、确认或 Status 更新都创建新 Revision，不能原地重做控制记录。 | 检查“无语义变化”是否被用作修改旧快照的理由。 |
| RVW-051 | 每个已知必要输入缺口唯一登记为 Open Item；当前 Artifact Contract 的 `Blocked References` 只使用稳定 Check ID。typed value 未知时不创建正式数据行，非法占位值不能代替输入。 | 检查 `waiting_input` 是否因漏记、重复、伪造或未定义字段路径而错误派生。 |
| RVW-052 | `DOM-<DOMAIN-NO>` 只表示 required Domain 的唯一 Member 与 Content Reference；`CTL-ID` 只表示 Security Control，DGC 与 DDR 不再注册。 | 检查 Item 与 Member 缩写是否造成同一 Artifact Set 内的语义混淆。 |
| RVW-053 | 多值 Reference 使用固定 Reference Set 语法：`, ` 分隔、去重升序、空集合 `None`；单数 Reference 只允许一个值。 | 检查不同模型是否用分号、换行、Markdown 链接或不同顺序生成等价但不稳定的结构。 |
| RVW-054 | Gate Summary 与 Final Confirmation 绑定完整 Evaluation Contract Set；DSN 集合包含 Core、DSN、固定 16 个 Domain Spec 和实际 Extension Contract。 | 检查任一规则来源变化后是否错误沿用旧 Check、Gate 或确认。 |
| RVW-055 | Spec Reference 使用唯一仓库相对路径与 SHA-256，不使用裸摘要、绝对路径或多种相对路径。 | 检查 Evaluation Contract Set 与 Manifest 中的 Domain Spec Reference 是否解析到准确且一致的 Spec 内容。 |
| RVW-056 | Revision 从已持久化最大值单调加一并原子分配；并发冲突时重读后递增，不覆盖或复用。 | 检查多个生成过程是否可能得到同一 `Artifact-ID@Revision`。 |
| RVW-057 | 可覆盖多个对象的字段使用复数 References 与 Reference Set；单数 Reference 只允许一个值。 | 检查字段基数是否与正文规则冲突。 |
| RVW-058 | inputs、Manifest 和固定 ID 表使用确定顺序；业务顺序用显式 Step/Order，不靠生成时行位置猜测。 | 检查同一输入是否因无语义重排产生不同 Digest。 |
| RVW-059 | 所有“单元格视为空值”使用同一字节级投影，不由 Markdown 解析器重新序列化。 | 实现验证器时用 golden vectors 检查跨实现 SHA-256 一致性。 |
| RVW-060 | Matrix 是 Domain Disposition、Completion、Content Reference 和顶层原因的唯一权威；required Member 的路径、Domain Spec 和摘要只由 Manifest 保存，n/a 与 waived 不创建 Content Member。 | 检查同一事实是否在 Matrix、Manifest 或额外控制块中重复并产生漂移。 |
| RVW-061 | Evidence、Exceptions、Open Items 无记录时使用各自唯一 `None` 行，不能预置伪 ID。 | 检查空集合是否出现多种编码或伪记录。 |
| RVW-062 | `Affected Domains` 使用固定 `DOM-<DOMAIN-NO>` Catalog Code 并按 Design Index 顺序组成集合；它是分类字段，不是 Member Reference。 | 检查同一 Domain 集合是否因名称、分隔或顺序不同而漂移，或被误写成跨文件 Content Reference。 |
| RVW-063 | 跨文件 Content/Supporting Member 使用完整 Member Reference；Basis、VFY、Exception 等多值字段使用复数 Reference Set。 | 检查裸 Member ID 或单数字段是否丢失关系。 |
| RVW-064 | DSN Artifact 存在时 Verifiability and VFY Strategy 固定为 required，并在唯一 Domain Member 中承载 VFO、VFM、VPC 与 VEC；Objective 必须保留，Method 只有在父 Exception 准确授权时才可 waived。 | 检查是否因简单需求或已有 AC 而跳过 510、豁免目标本身，或用无 Disposition 的 Method 隐藏跳过。 |
| RVW-065 | Workflow 与 User Journey 使用稳定 Flow/Journey、Step、Transition ID 和显式分支。 | 检查多流程、多旅程是否仍靠行号或自由文本关联。 |
| RVW-066 | 510 不复制其他 Domain 的 VFY Point 内容，只通过稳定 Reference 映射到本地 VFO、VFM、VPC 和 VEC。 | 检查其他 required Domain 的 VFY Point 是否全部覆盖，或是否产生影子 ID 和重复事实源。 |
| RVW-067 | Trigger 必须显式引用 Flow，Journey 必须显式引用本地 User/Goal 记录，并按适用性补充上游 Goal Item。 | 检查多流程、多旅程的启动与服务对象是否仍依赖文字匹配。 |
| RVW-068 | Revision 使用确定目录与单一 Revision Index；open 目录是唯一工作位置，frozen 后不可修改，下游引用不得使用 latest 或自动回退。 | 检查是否重新形成 working/current 双副本、可变指针、历史覆盖或旧 Revision 自动复活。 |
| RVW-069 | Simple is best：现有结构可以闭合的问题，不新增概念、文件、字段、状态或抽象。 | 每次新增规则都检查其解决的已知问题、不可替代性和阅读成本；仅为未来可能需求的结构应删除或延期。 |
| RVW-070 | 最低 QA Contract 直接复用 Check Set、Evidence、Gate 和 Final Confirmation，不建立独立 Artifact、Phase、Manifest、Status 或 Ruleset。 | 检查所有应执行 Check 是否完整唯一、结果有依据且 Gate 可确定性聚合。 |
| RVW-071 | Delivery Scope 只聚合完整 Scope Input；前置 Result、Rework 和 Evidence 等同一 Binding 控制输入不因数量强制产生 PLN。当前 Artifact Contract 不在 PLN 选择 Artifact 的部分 Item。 | 检查控制输入是否被误作新范围、真实多范围输入是否逃避聚合，或 PLN 是否自行猜测部分范围闭包。 |
| RVW-072 | PLN Artifact 表示完整交付执行计划；`Work Item` 是规范内的最小计划单元，外部执行或跟踪对象不能替代 `PLN-ID@Revision#WI-ID`。 | 检查是否把整个 PLN 误作单个任务，或把外部编号变成权威身份。 |
| RVW-073 | Work Item 不保存实时状态、`parallel` 或成对冲突列表；依赖和 Execution Scope 是执行顺序与潜在冲突的规划依据。 | 检查是否把 IMP 进度写回冻结 Plan，或因重复字段产生漂移。 |
| RVW-074 | PLN 定义完整交付执行计划，不强制承担预算、工期、人员负载和日历排期；这些内容只有在项目确有需要时再扩展。 | 检查是否为了“Plan”名称引入完整项目管理体系并扩大当前 Spec。 |
| RVW-075 | PLN 是否 required 由范围聚合、独立变化范围、必须显式记录的依赖与顺序、共享可变范围和约束分配等事实触发；Profile 或主观偏好不能直接决定。 | 检查原子变更是否被强制制造 Plan，或复杂交付是否因 lite/hotfix 被跳过。 |
| RVW-076 | required Phase 生成独立 Artifact；embedded、n/a、waived 不生成独立 Artifact，下一个 required Phase 绑定最近可用上游 Revision 并保留处置解析链。 | 检查跳过 Phase 后是否出现断链，或为 n/a/waived 创建空 Artifact。 |
| RVW-077 | Work Item 的 Execution Scope 使用固定 Scope Token，不允许“相关模块”等自由描述；不同 Type 不自动证明互斥，它只负责识别边界和潜在冲突。 | 检查同一范围是否因模型措辞不同而无法比较，或 Scope Token 被误作实时锁。 |
| RVW-078 | 已有 PLN Work Item 的 IMP 路径严格使用 `一个 IMP Work Item ↔ 一个权威 IMP Artifact`；IMP 不得重新分组。 | 检查模型是否在执行时改用一对多、多对一，或用第二个 Artifact 重复承接同一 Work Item。 |
| RVW-079 | 每次领取只处理一个准确 Binding；同一 Binding Lineage 跨上游 Revision 仍只有一个 active Owner 和 Attempt，重复领取必须停止且不得覆盖。 | 检查是否把 `PLN@1#WI-001` 与 `PLN@2#WI-001` 误当两个可并行 Lineage。 |
| RVW-080 | 同一 Lineage 的重复领取与不同 Lineage 的版本化 Resource 冲突分别判断；当前内置 Spec 采用 Resource 级保守冲突域，只有相同 `resource:<id>` 阻断 Claim，其他 Scope Token 只负责范围与追踪。更小 Resource 必须能独立捕获 Baseline、形成不可变 Result 并确定性集成；同一 Provider 命名空间使用 canonical、互不重叠的 Resource ID，无法证明不相交时使用最小共同上层 Resource。 | 检查是否只防重复 Owner、把 path/module 或重叠 Resource 别名误作并行证明，或因共享 component/environment 等非 Resource Token 过度串行化。 |
| RVW-081 | 每个 required IMP 使用一个 `IMP Binding Reference`；PLN 为 required 时绑定 Work Item，其他处置按准确上游或 Host 绑定，不创建合成 Work Item。 | 检查直接实施是否组合多个 Input、产生多个 Outcome，或用临时任务掩盖本应 required 的 PLN。 |
| RVW-082 | 领取先无副作用解析 Lineage；active/completed 幂等返回必须同时匹配准确 Binding、Dependency Result References 与规范化 Rework References。仅新领取或合法重领执行 Readiness，通过后原子分配 Claim、Artifact ID、Attempt 并预留不可复用 Revision；Owner 再按 Core 原子物化该号。 | 检查并发领取是否同时通过、前驱快照是否被静默替换、预留号是否跳过或复用，或是否在 Artifact 物化校验前修改产品。 |
| RVW-083 | IMP 使用固定七项 Implementation Consideration；Matrix 只做覆盖索引，实施逻辑按一个连续 Approach 展开，不按考量项拆文件。 | 检查是否漏项、增加自由 Catalog，或把一个 Work Item 切成不连贯的多个方法文档。 |
| RVW-084 | 每个 required Consideration 使用对应固定 Method Block；n/a 和 waived 不生成空块，简单未触发项不因模板被放大。 | 检查是否把 applicable 留给模型自由发挥，或为普通条件、赋值和透传制造复杂方法块。 |
| RVW-085 | IMP 选择顺序为上游 Decision、项目既有约束、最简单正确局部实现、必要局部抽象；新依赖、公共抽象和架构变化返回 DSN。 | 检查是否推测性抽象、为模式而模式、顺手重构或在 IMP 静默补设计。 |
| RVW-086 | 一个 Implementation Result 行表示一个独立版本化资源，不按文件拆分；每行始终具有不可变 Result Reference，Change Reference 仅作可选审计材料。 | 检查 Patch/Diff、分支、Tag、当前工作树、路径或无摘要临时文件是否被误作完整结果。 |
| RVW-087 | Implementation Checks 记录局部实现检查；n/a 只表示客观不适用，适用但跳过必须 waived 并关联 Exception。 | 检查是否强制执行无关工具、用 n/a 掩盖跳过，或让 IMP 提前给出完整 VFY 结论。 |
| RVW-088 | IMP Gate 只证明 Binding 已形成完整、可追踪、可复现且可进入 VFY 的实现结果，不证明 Requirement 已验证或可以发版。 | 检查 IMP Completion、VFY Acceptance 和 RLS Readiness 是否再次混用。 |
| RVW-089 | 同一项目及 Resource 命名空间必须确定性解析到唯一 Claim Provider；Provider 是 Claim State 的唯一权威，Revision Index 只保存 Artifact 状态。完成顺序为 Revision frozen 后 Claim completed；普通放弃先使 Revision abandoned；frozen 后 complete 不可同条件恢复时保留 Snapshot，以固定错误原因使 Claim abandoned。 | 检查 Provider 缺失或多解、执行权提前释放、编号跳过、双 open、frozen+active 永久锁定，或把未 completed Claim 的 frozen Revision 误判为下游可用。 |
| RVW-090 | completed Claim 默认保持完成；相同 `Binding Lineage Key + Rework References` 只启动一个返工序列。Claim 登记直接前驱 Result；`complete` 在同一事务递归复核其完整已登记依赖链仍对应 Current completed Claim。abandoned 后仅在 Binding 与全部前驱 Result 未变时才追加 Attempt。 | 使用冻结 Return、更新 Binding 或变化前驱 Result 作为准确返工依据；检查重复 Return、祖先前驱变化、遗漏因果引用、完成窗口或并行返工序列。 |
| RVW-091 | Claim 原子保存且冻结 Execution Scope；实际 Changed Scope 必须是其子集，扩大范围或改变 Outcome 时返回 PLN 或准确上游。 | 检查是否在实施或 Close 时覆盖 Claim Scope 以掩盖越界。 |
| RVW-092 | Security、Performance 等保持 DSN 约束，抽象与模式进入 Decision Rules，Style 进入项目工具，Test 进入 Check/VFY；均不扩张为 IMP 并列 Consideration。 | 检查七项 Catalog 是否因重复上游 Domain 或工具职责而无限增长。 |
| RVW-093 | Spec 只根据 Artifact、Evidence 和 Gate 判断合规，不区分人工、AI 或其他执行主体；AI 是可选提效手段。 | 检查是否重新出现 AI 必须参与、固定参与比例或工具使用量合规条件。 |
| RVW-094 | Aggregate Gate 固定按 `fail → pending → pass_with_exception → pass` 聚合；只有结果为 `pass / pass_with_exception` 的 Revision 才能冻结，`fail / pending` 保持 open 并允许修正。 | 检查 Waiver 是否覆盖失败或等待输入，或不可用 Revision 是否被发布为下游 Snapshot。 |
| RVW-095 | `embedded` 只允许使用目标 Spec 已注册、可引用且具有完整性 Check 的 Host Contract。 | 检查自由文本、标题或缺字段 Host 是否被用于绕过独立 Artifact。 |
| RVW-096 | 准确 Binding Reference 负责版本追踪；不含 Revision 的 Binding Lineage Key 负责跨 Revision 唯一 Claim 和唯一 IMP Artifact。 | 检查同一稳定 Item 的新 Revision 是否错误分配第二个 IMP Artifact。 |
| RVW-097 | IMP Baseline 是首次产品修改前的准确状态；每次重试重新选择。Resource 未前进时可复用原 Baseline，已前进时从当前不可变状态重新应用变化，旧可变视图不得继承。 | 检查旧 Baseline 是否覆盖中间已完成结果，或把 `HEAD`、残留工作区静默定义为新 Baseline。 |
| RVW-098 | Core、Phase 与 Domain Check 各自只维护本层权威检查；Domain 不重复跨领域一致性、通用 N/A 或父级 VFY 覆盖检查。 | 检查 Gate 是否因复制同一事实而重新膨胀或产生相反结论。 |
| RVW-099 | 项目建设顺序称“批次”，只把 REQ、DSN、PLN、IMP、VFY、RLS 称为 Lifecycle Phase。 | 检查总体规划是否重新混用建设阶段与生命周期位置。 |
| RVW-100 | 跳过一个 Phase 只有在现有固定字段可确定性满足下一个 required Phase 的 Readiness 时才成立；否则前一 Phase 必须 required。 | 检查简单路径是否暗造 mini-Plan，或在完成依据不足时直接进入 IMP。 |
| RVW-101 | Final Confirmation 同时绑定 Revision、Control Input Digest、Evaluation Contract Set 和 Check Set Result Digest；后者只覆盖除 `CORE-G-009` 外的当前 Check 行，历史 Attempt 不参与。 | 检查 Check 行变化是否更新 Check Digest，或 subordinate 其他字段变化后是否错误沿用旧 Control Digest 与确认。 |
| RVW-102 | 每个 IMP Work Item 为每个版本化资源登记 `resource:<id>`；同资源 Work Item 形成单一 `Depends On` 链，后继 Baseline 等于前驱 Result。 | 检查同一资源是否形成多个无法组合的并行快照，或由 VFY 猜测合并。 |
| RVW-103 | Plan 依赖必须展开为当前 Plan Revision 的准确 Binding，并把实际采用的冻结 IMP Revision 写入后继 `inputs`。 | 检查新旧 Plan Revision 是否串用结果，或只按无 Revision Lineage 选择“最新”Attempt。 |
| RVW-104 | Result 的 `Resource` 是项目内唯一版本化资源 ID；`Changed Scope` 使用 Claim 中已有的 Scope Token，并包含对应 `resource:<Resource>`。 | 检查组件/模块 Token 是否被误作版本化资源，或更细路径通过未定义的层级包含关系越过 Claim。 |
| RVW-105 | DSN/PLN 为 `n/a/waived` 时，直接 IMP Scope 由 REQ `Direct IMP Scope` 提供；存在直接 DSN Binding 时由 DSN Change `Object or Boundary` 提供。当前没有可用的 embedded PLN Host；Scope 缺失、多个 Resource 或需协调时 PLN required。 | 检查 IMP 是否从自然语言猜测范围、把 Work Item 当作结果 Host，或为简单路径创建第二套临时 Work Item。 |
| RVW-106 | IMP 必须按固定表重评 VFY、RLS；VFY required，RLS 按是否实际发版判断，Profile 或 IMP 完成不能自动决定。 | 检查固定模板是否只有标题而没有可执行字段，或把实现完成误作可以发版。 |
| RVW-107 | REQ Dependency 的 Current State 是快照；可变状态的 State Check Reference 必须可重复执行或实时观察，不可变 Artifact / Evidence 只证明不可变或单调成立的状态；直接 IMP 无法确定性复核时返回 PLN 或上游。 | 检查陈旧文字状态或历史 Evidence 是否被当作当前可变依赖已满足。 |
| RVW-108 | 任一 Plan 依赖的 Current Result 变化都会使仍引用旧结果的传递下游失去 VFY 就绪性；IMP Gate 只检查截至当前 Work Item 的已执行前缀，VFY 前复核全部当前依赖边，同资源链还必须 completed、连续且只有一个有效链尾。 | 检查是否用尚未执行的后继阻塞当前 Gate，或跨资源/同资源前驱返工后继续采用旧下游结果。 |
| RVW-109 | 每个冻结 IMP Revision 对 Claim 中每个版本化 Resource 恰有一个 Result 行；本 Attempt 未变化的 Resource 使用当前准确 Baseline 作为相同 Result。 | 检查返工 Revision 是否删除仍有效 Result，或 Resource 已前进后仍错误登记旧 Result。 |
| RVW-110 | active Claim 只能由当前 Owner 实施或完成；授权恢复执行方必须先阻断旧写入，只能终结 open 预留 Revision，或在 frozen 最终化失败时以 `complete:<code>:<detail>` 释放匹配 Claim，不使用自动超时接管。 | 检查普通放弃是否绕过 Revision abandoned、frozen 失败是否永久 active、恢复方修改产品或 frozen Artifact、双 Owner或缺失原因。 |
| RVW-111 | 已有 Resource 在首次修改前绑定不可变 Baseline；全新 Resource 使用 `N/A`，但必须有可复核的未创建依据，目标已存在时不得覆盖。 | 检查新资源是否因强制捕获不存在的 Baseline 而无法执行，或把已有目标误作新资源覆盖。 |
| RVW-112 | VFY 使用 `Target → Method → Subject → Result → Evidence → Conclusion` 的固定关系，每个 Target 和 Method 都能准确追踪，不从相似文字猜测映射。 | 检查目标遗漏、重复、无 Subject、无 Evidence，或同一结果被用于不相关 Target。 |
| RVW-113 | VFY 顶层 Method Type 只使用 `inspection`、`analysis`、`demonstration`、`test`；人工/自动化是 Execution Mode，测试层级和质量目标进入 Method Detail。 | 检查 Review、Unit、Integration、Manual、Security 等是否重新成为并列 Method Type。 |
| RVW-114 | Test 资产的实现和开发反馈性执行属于 IMP；VFY 只在结果准确对应最终 Subject 时复核，否则按 Contract 与风险重新执行。IMP Check 通过不等于 VFY 通过或允许 RLS。 | 检查同一单元测试是否被机械重复，或 IMP 局部检查是否越权形成产品级结论。 |
| RVW-115 | 产品 Conclusion 与 VFY Artifact Status 分离；可信地证明产品 `fail` 的完整 VFY Artifact 可以通过自身 Gate、冻结并形成 Return。 | 检查产品失败是否错误导致 Artifact 永远无法冻结，或 Artifact ready 是否被误解为产品通过。 |
| RVW-116 | VFY Return 是冻结 Revision 内的不可变记录，完整引用为 `<VFY-ID>@<Revision>#RET-ID`；只返回一个权威 Phase，IMP 只接受 Subject Result 可沿 `inputs` 追踪到自身 Binding Lineage 的 Return。 | 检查 Return 是否被原地改状态、缺少 Target/Subject/Evidence，或 IMP 根据标题和缺陷文字猜测返工归属。 |
| RVW-117 | 环境、网络、数据或人工输入暂不可用不是 `n/a`；Method 保持 `pending`。只能在 Release Target 执行且发版继续时使用有效 Exception，并登记准确 RLS 下游义务。 | 检查限制是否被掩盖为不适用、Target 被误记为 pass，或 VFY 展开实际发版、流量、停止和恢复机制。 |
| RVW-118 | 人工或 Hybrid 产品评价作为 VFY Evidence 保存；Core Final Confirmation 只确认 Artifact 与 Gate，两者不能由一次模糊签字替代；委托确认不能生成缺失的主观评价 Evidence。 | 检查 UI/UX 等主观判断是否无场景和观察事实，或产品验收与 Artifact 确认混为一体。 |
| RVW-119 | 每个 Phase Spec 在 Gate 前保留 3 至 5 行 AI 与人工协作指导；该内容不进入 Lifecycle Artifact，不作为 AI 使用率、人员配置或 Gate 指标。 | 检查协作建议是否膨胀为新角色体系、强制 AI 参与或重复的责任 Artifact。 |
| RVW-120 | RLS 只负责把完整 VFY Scope 的准确 Result 发布到一个明确 Target，确认目标侧状态并形成 Conclusion；不重新定义上游内容。 | 检查 RLS 是否选择部分范围、重新构建不同 Result、补写设计或顺手处理目标环境问题。 |
| RVW-121 | RLS 只有一个最终 Gate；发版前和执行中保持 open Revision，发版结束、失败或取消后冻结为唯一 Release Record。 | 检查是否增加预发版 Gate、第二份上线报告、实时状态机或重复 Attempt Contract。 |
| RVW-122 | Release Item 成功不等于目标状态正确；Post-release Confirmation 必须具有目标侧 Observed 与 Evidence，不能只引用流水线成功。 | 检查 CI/CD、Jenkins、工单或执行者声明是否被直接聚合为 success。 |
| RVW-123 | VFY Conclusion、RLS Conclusion 和 Artifact Status 分别表示产品符合性、目标侧发版结果和记录合规性；三者不得互相覆盖。 | 检查产品 fail 是否被 Artifact ready 掩盖，或准确失败记录是否被错误阻止冻结。 |
| RVW-124 | 长期监控、告警、值守、故障处置和日常 Runbook 不作为每次变更的固定 Artifact Phase；真实持续影响只写入 RLS Follow-up 或项目扩展。 | 检查是否重新引入独立运行 Artifact，或把普通发版扩张为持续运维体系。 |
| RVW-125 | VFY 从完整 PLN 派生全部 IMP 与 VFY Work Item 义务；RLS 按唯一 Release Target 选择并闭合其全部 RLS Work Item，归属不清时返回 PLN。未领取或未映射的 WI 不能因没有 Result 而消失。 | 检查是否只验证已经出现的 Result、跨 Target 混用 WI，或在计划未完成时形成假闭环。 |
| RVW-126 | VFY Method 的 Obligation References 唯一映射上游 VFM、VPC、VEC、VFY Work Item 与 Return；verification、validation、both 的 Target 和 Method 必须按固定兼容规则覆盖，both Target 的两个结论分别只聚合相容 Method。 | 检查是否只生成一条 Method 就宣称覆盖完整策略，或让一个维度的失败错误污染、替代另一维度结论。 |
| RVW-127 | VFY Return 与 RLS Issue Reference 都是返工 Control Input，不改变 Delivery Scope。RLS Follow-up Disposition 唯一路由上游；产品修正由后续冻结 VFY 证明，计划问题由 PLN 处理并由后续冻结 RLS 证明。 | 检查问题是否多路由、被静默删除、被复制成平行状态，或因收到处理就过早关闭。 |
| RVW-128 | `Return Phase=IMP` 必须绑定一个准确 IMP Binding Lineage；Binding Revision 更新时必须同时携带 Return 与新 Binding，多 Lineage 缺口拆分，无法定位或需要重排时返回 PLN。 | 检查是否把同 Lineage 的正常 Revision 更新误作新 Work Item，或仅靠组合 Subject 的祖先关系重开多个 Lineage。 |
| RVW-129 | Claim 前的候选 commit、patch、bundle 或工作树变化只能作为 Candidate Evidence；正式 Result 必须在 Claim 后从声明 Baseline 按 Scope 重放并重新检查。 | 检查是否把候选整体吸入 Baseline、倒签 Claim 或把越界变化冒充当前结果。 |
| RVW-130 | RLS 只记录项目或工具已有的 Approval or Trigger Reference，不在核心规范新建审批流程；项目明确要求授权时，Final Confirmation 不能代替执行前依据。 | 检查可选引用是否膨胀为通用审批状态机，或绕过项目已有授权要求。 |
| RVW-131 | RLS 使用 RLI 或 RCF 的唯一 Follow-up Disposition 路由问题：`return_imp` 必须唯一绑定一个 Lineage，无法唯一归属时使用 `return_pln`。 | 检查同一问题是否被多个 Phase 接收，环境、权限或发版重试是否被误作上游返工，或产品修正绕过重新 VFY。 |
| RVW-132 | Release Conclusion 使用覆盖全部合法组合的固定全序：明确失败优先于取消；success 至少具有一个实际目标侧 pass；仅已产生目标效果且未命中前序结果时为 partial。 | 检查发版前失败是否误记为 cancelled、全 waived 是否伪装为 success，或部分目标效果组合是否由模型自由选择。 |
| RVW-133 | 同一 Artifact 的内置 Core、Phase、Domain Contract 必须来自同一 Snapshot；冻结 Artifact 按自身 Evaluation Contract Set 解析。不同 Artifact 可在 Artifact Contract 兼容时由新 Spec 准确输入旧 Spec 结果，不得重解释历史快照。 | 检查 Spec update 是否无条件使既有确认失效、单个 Artifact 混用 Snapshot，或跨 Artifact 忽略 Contract 兼容性。 |
| RVW-134 | Artifact 正文只记录业务内容和控制依据，不复制 Front Matter、Revision Index、Final Confirmation、Check 或 Gate 的当前状态值。 | 检查 Summary、Scope、Open Items 是否因 open→frozen 最终化而保留陈旧状态文字，或与权威控制字段矛盾。 |
| RVW-135 | RLS 只保留 Release Contract、Release Items、Post-release Confirmation 和 Release Conclusion；外部平台与人员只作为 Executor 或 Evidence，不在 Core 复刻审批、流水线和长期运维。 | 检查发版规范是否重新分裂变化与操作台账、增加发布状态机，或只保留报告而丢失目标侧读回。 |
| RVW-136 | REQ 只排除发版动作、流程完成状态和发布记录；目标场景中用户可观察的产品行为、可用性与运行约束仍可进入 Acceptance Criteria。 | 检查是否把合法产品义务误移到 RLS，或在 VFY 之前要求证明只能由正式 Target 产生的发布记录。 |
| RVW-137 | Target-only waived Method 保留完整 Method Detail；发版前 RCF 必须确定 Executor 与 Evidence 获取方式并完整继承原口径；无目标效果即失败或取消时使用终态 `not_run`；每个来源 Exception 按全部映射 RCF 和 Evidence 只聚合一次。 | 检查准入事实是否无字段、RCF 是否降低判定口径、失败前确认是否永久 pending，或一对多映射是否无法关闭 Exception。 |
| RVW-138 | 同一早期 Exception 经多个直接 Input 分别到达时，当前内置 Spec 按每个直接 Input 的当前未关闭 Exception Reference 分别创建 `carried` 行，不沿 Origin 链自动合并；仅当其中一个冻结直接 Input 已汇总全部相关义务，且其他直接 Input 不再保留独立相关未关闭 Exception 时承接单一引用。 | 检查模型是否静默根合并、丢失某个直接 Input 的义务，或在满足唯一汇总条件时再次复制。 |
| RVW-139 | Revision 成功分配必须在同一排他临界区物化并读回索引行、目录和主文件固定骨架；任何受控状态改变只能在 Phase 固定 Pre-execution Checklist 已持久化并读回后开始，事后补录不能追认。 | 检查是否先执行实现、验证或发版再补 Artifact，是否把 Checklist 前输出当作正式 Evidence，或为此新增第二套状态和 Gate。 |
| RVW-140 | IMP 成功分配与 Core 使用同一索引行、目录、主文件固定骨架三件套；首次产品修改前，当前 Revision 的 Binding、已通过 Readiness、Resource Baseline 和完整 Method Contract 必须持久化并读回。Artifact、Revision Index、Claim 等前提控制记录仍按各自规则写入，不误判为执行对象变更。 | 检查是否按旧二件套放行、事后补 Method Contract，或因规则自指导致 Claim 无法建立。 |
| RVW-141 | 正式 action 前，当前 Gate Summary 先固定非空 Evaluation Contract Set，并以现有 Evidence / Supporting Manifest 保存不可变 Checklist 读回文件；规则或字段变化后旧正式输出失效。主文件前已经产生或无法排除的 effect 必须由后续同 Phase Revision 承接，不得只留下 index-only abandoned。 | 检查 fallback 是否事后选择 Spec、读回是否只有文字断言、旧 Evidence 是否在清单变化后继续使用，或真实 Target effect 是否被降为候选材料。 |
| RVW-142 | 冻结 Revision 后发现自身或传递 Input 不可解析时，从最早失效上游依次创建恢复 Revision；旧记录保持不变但不再提供 Authority，Base 仅作同 Artifact 内容来源，新 Input 必须以当前 Authority 完整覆盖原 Scope 与义务。IMP 只有在当前 Resource、外部状态和副作用均可证明与新 Binding 等价时允许 `Baseline=Result` 沿用，否则重放或重新执行。 | 检查是否追溯改写旧 Revision、静默删除失效 Scope、跨 Lineage 滥用 Base、继承旧 Gate/Claim/Evidence/Conclusion，或用相同字节冒充完整状态等价。 |
| RVW-143 | v0.2 使用单一 Final Confirmation；`delegated` 只确认已有客观 Evidence 与 Gate 绑定，必须由独立 Reviewer 执行，且无 Open Item、Exception、Waiver、主观判断或外部权限需求。 | 检查是否冒填 User、同执行者自批、预先批准未知 Digest、接受风险，或把委托复核误作产品/生产/外部 action 权限。 |
| RVW-144 | 同一 IMP Artifact 的旧失效 Revision 可作为控制恢复 Rework Reference，但只说明 completed Claim 的重启原因和 Base candidate，不进入 `inputs`、不恢复旧 Authority；同一引用只启动一个序列。 | 检查是否跨 Artifact、引用未来 Revision、把控制引用当 Input，或借恢复路径绕过当前 Checklist、Evidence、Gate 与 Final Confirmation。 |
| RVW-145 | Artifact Contract 兼容性逐条作用于直接和传递 Input 边：v0.1 只消费 v0.1，v0.2 可消费 v0.1 或 v0.2；缓存不能跳过父子版本判断。 | 检查是否只校验顶层、反向允许 v0.1 消费 v0.2，或因共享缓存得到顺序相关结果。 |
| RVW-146 | delegated Authority 使用固定最小记录，绑定 Artifact、Reviewer、被复核执行者、三项当前摘要、独立性与排除权限；文件不进入当前 Supporting Manifest。 | 检查是否只校验路径与哈希、Reviewer 自批、摘要漂移、自引用，或委托依据为空。 |
| RVW-147 | 完整 Validator 从当前 Gate Check 行重算 Check Set Result Digest，并使 Final Confirmation、Gate Summary 与 active/carried Exception 集合一致。 | 检查是否只比较两个已填写摘要、修改 Check 行后旧摘要仍通过，或两处 Exception 引用不同。 |
| RVW-148 | Gate Digest Helper 必须校验 Artifact Contract 与 Spec 根固定模板同代，空 Binding 也不得生成跨代规则建议。 | 检查 v0.2 Artifact 是否错误使用 v015，或 v0.1 Artifact 是否错误使用 v016。 |
| RVW-149 | delegated Authority 的授权依据使用项目相对 `path@sha256`；Validator 只交叉检查 Artifact 内已有的 Reviewer、Claim Owner、VFY Method Executor 与 RLS Executor 声明，真实身份依赖执行平台或项目审计信任边界。 | 检查是否把本地字段冒充密码学身份证明，或让 Confirmer 与可机器读的实际 Executor 相同。 |
| RVW-150 | 同一 IMP 控制恢复要求旧 Revision 在关闭递归 Input 解析后本地有效，并机械比较 Binding Lineage、准确 Binding Reference、规范化 Execution Scope 与完整 Result 投影；被移除的失效 Input 不参与比较。 | 检查是否用本地空壳或结构错误 Revision 恢复，或在恢复时漂移 Binding、Scope、Result ID、Resource、Baseline、Change、Result、Changed Scope、Steps。 |
| RVW-151 | 非 pending Gate Summary 从当前全部 Check 和当前有效 Exception/Waiver 确定性派生；有 fail 为 fail，其次 pending，再次 pass_with_exception，否则 pass。 | 检查是否重算 Digest 后仍手工伪造 Gate pass，或因 Markdown 反引号漏识别 waived。 |
| RVW-152 | Exception 表必须唯一；非空行使用唯一 `EX-NNN`、固定状态和值域，active/carried 来源完整，resolved 引用可解析解决项，superseded 引用已存在且不同于自身的单一 Exception；Markdown 展示不能改变状态语义。 | 检查伪造 `None` ID、未知状态、反引号状态、自由文本或不存在的 resolved 引用、自替代或多目标 superseded 是否绕过 Gate。 |
| RVW-153 | 委托确认涉及的 Confirmer、Reviewer、IMP Owner、VFY Executor 与 RLS Executor 都使用一个稳定身份 token，并按规范化显示值比较。 | 检查 `User`、自批身份或逗号拼接多个身份是否借展示差异绕过独立性检查。 |
| RVW-154 | Disposition、Result、State、Conclusion、Mode 和 Follow-up 等控制枚举必须使用规范裸值；委托边界同时按显示语义防御性识别被 Markdown 包装的 `waived`。 | 检查 `**waived**`、链接或 HTML 展示是否绕过枚举校验、Exception 或委托限制。 |

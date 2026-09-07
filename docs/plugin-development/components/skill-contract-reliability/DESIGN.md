# Skill 输入契约与执行可靠性修复计划

日期：2026-09-08。阶段：design。状态：draft；尚未批准实施。

适用于七个 Artifact Skill、sdlc-status、sdlc-github 及其共享接口。它是现有能力的横向修复设计，不是新增 Skill、Phase、Store 或独立业务 Gate。评测定义见 [EVAL-PLAN.md](EVAL-PLAN.md)，唯一下一动作见 [HANDOFF](../../HANDOFF.md)。

## 1. 结论与范围

当前问题包含三个不同层次：安装后输入说明不完整、Runtime 的错误处理或语义校验存在缺陷，以及现有回归未覆盖模型从文档生成请求的过程。不能把全部责任归为模型能力，也不能从项目流程成功推导出输入契约完整。

修复以协议和能力为单位，不按项目名称或开发语言增加特判。语言、前后端、技术栈决定观察哪些文件、怎样解析工程入口、用什么工具验证；它们不改变枚举、引用、证据、授权和状态的基本语义。

本次仅交付设计、评测计划和 Handoff。不修改 Runtime、领域规范、测试 Oracle、用户项目、已冻结 Artifact、历史回归或安装缓存；不执行全流程、安装、发布或外部写入。

不能承诺所有未来输入永不失败。目标是：已知缺陷有确定性回归；新增协议约束必须同步文档和用例；合法已支持输入可运行，信息缺口可解释，未知能力或非法输入准确拒绝，拒绝不产生业务副作用。

## 2. 准确基线与三项目回归的解释

| 对象 | 本次核实事实 | 使用边界 |
|---|---|---|
| 当前修复工作树 | `codex/bugfix`，HEAD=`aed8eb69d2b74ec27bdcb2fb356cb02b68602289`；设计前干净 | 本设计的代码检查及最小复现 Subject |
| 用户原 CTX 失败 | Codex task `01a07b3d-50c6-71e1-be4d-ad75e2a07941`；目标 approval-bot；输入使用 source_worktree、中文用途、非摘要 Evidence、说明文字依赖 | 会话已在前序核对；证明该次输入及失败，不能推导项目代码缺陷 |
| 三项目证据仓库 | `ousui/test-sdlc@6c018b50f6b9b981a320f07f6364e6262955dc04` | 已通过 GitHub API 读回准确提交下的汇总和来源；不使用 main 代指交付版本 |
| 三项目测试代码 | `849783ddbc9b2ffd5300e3b1582049a390a2e2a8` | 汇总记录的 test source；后续复跑须独立解析并核对 |
| 三项目 Runtime | `eff4ac209fe4cc1d0fefcd7e4478cb5b9f786af4`；tree=`a3c306d0f39d37211b32c4518de61b24183d7d32` | 与当前 HEAD 不同，不能将旧结果升级为当前 HEAD 的全流程 PASS |
| 汇总报告 | strict 1092；Admin 13、SpringGear 10、Fansite 24 项业务测试，三项目 CLOSED | 本次读回的是报告，不是重新运行，也未重验全部原始 ZIP；原生加载、生产发布不在其结论内 |

准确来源：[三项目 verification.json](https://github.com/ousui/test-sdlc/blob/6c018b50f6b9b981a320f07f6364e6262955dc04/runs/CLOSURE-eff4ac2-20260907/verification.json)、[Admin 来源](https://github.com/ousui/test-sdlc/blob/6c018b50f6b9b981a320f07f6364e6262955dc04/cases/admin/baseline/SOURCE.md)、[调用封装](https://github.com/ousui/test-sdlc/blob/6c018b50f6b9b981a320f07f6364e6262955dc04/scripts/scenario_io.py)、[Admin 场景](https://github.com/ousui/test-sdlc/blob/6c018b50f6b9b981a320f07f6364e6262955dc04/scripts/replay_admin.py)。

需要纠正项目名称：该轮 Admin 是 Flask-Admin 官方示例的 Python/SQLite 应用，不是 Gin-Vue-Admin。SpringGear 最终闭环是 JDK21，不沿用 main 入口中的早期 JDK26 目标；Fansite 最终使用 Go、HTML、原生 JavaScript。Gin-Vue-Admin 是本规范仓库现有固定 e2e 的另一项目，应作为额外覆盖，不能与上述 Admin 合并计数。

ScenarioIO 根据阶段封装 Envelope、write confirmation、project_boundary 和 prepare_confirmation；场景脚本提供合法的资源类型、工程用途、Evidence 摘要和组件依赖。它们确实执行正式 CLI，业务测试和链路证据有价值；但首次输入构造已由场景代码完成，不等价于新模型仅凭随包文档完成同一转换。不得反过来说这些真实业务测试无效或都是伪造 Fixture。

本地 test-sdlc 检出树有用户改动，已仅只读观察；后续必须从准确 Git 对象创建隔离副本，不能 reset 或清理该目录。该仓库 main 在本次读取时为 `03e7a0e01c39020e6390205cfffc35bd785ccd9d`，只承载早期入口，不能取代上述交付提交。

## 3. 问题登记与跨 Skill 检查

“已复现”表示在当前 HEAD 执行最小探针得到；“已确认缺口”表示已核对代码和随包文档；“待验证”不计作缺陷或通过。这里只登记与本计划直接相关的问题，不进行无界重构。

| ID | 范围 | 状态与证据 | 修复目标 |
|---|---|---|---|
| SCR-01 | CTX 输入说明 | 已确认缺口；contract.md 列字段但缺固定枚举、Evidence 格式及依赖集合的完整说明 | 文档能独立指导合法请求；合法值来自明确机器约束 |
| SCR-02 | CTX Check 映射 | 已复现；一个非法资源类型经 `_pending_checks` 导致全部 15 项 fail | 输入错误、未执行检查、确有失败事实分开；不虚构全部检查失败 |
| SCR-03 | CTX create dry-run | 已复现；Builder 有错误，但 Handler 返回 ok=true、completed、errors=[]，Gate=fail | 预览保留具体错误；不分配、写入或产生 Authority |
| SCR-04 | CTX Baseline | 已复现；只写 workspace observation 加时间仍被 Builder 接受 | 版本化资源要求不可变基线；dirty 事实有独立内容依据 |
| SCR-05 | REQ | 已确认缺口；sources.type、requirements.type 枚举及若干嵌套字段未说明；前序已复现非法来源类型失败 | 完整输入结构、枚举、引用及空集合规则；ID 由 Runtime 统一生成 |
| SCR-06 | DSN/PLN | 已确认缺口；打包了领域规范，但未描述 inputs.design / inputs.plan 与内部 JSON 字段映射 | 领域内容与提交接口同时自包含；无需读实现才能调用 |
| SCR-07 | DSN/PLN 元命令 | 已复现；help 被无效业务 stdin 阻断，退出码 2；与不读业务 stdin 的约定冲突 | meta 先分流，完全跳过业务解析、项目定位和 Store |
| SCR-08 | IMP | 已确认局部缺口；contract 只列 blocks，代码另定义 CAL/DEC/STA/ALG/MAP/ERR/EFF 的嵌套键与类型 | Method Block 的程序输入结构、条件必填、ID/顺序明确；不误删七项业务考量 |
| SCR-09 | VFY | 已确认局部缺口；stdin 的 allow_commands、manual_observations、failure_returns 等实际字段无完整输入说明；release-candidate schema 是输出对象 | 输入/输出 Schema 分开；自动、人工、混合能力与授权语义明确 |
| SCR-10 | Shared | 已确认结构不足；invocation.schema 的 inputs 仅规定 object，未约束阶段私有内容 | 保留共享外层，在各 Skill 声明内部约束；不误称外层 Schema 已覆盖所有字段 |
| SCR-11 | 跨阶段 Result | 待逐命令验证；部分后期 CLI 使用专用 Result；文档却有统一 Envelope 的广泛表述 | 先登记真实协议及消费者，再提供兼容投影；不强行一次改写全部 wire 格式 |
| SCR-12 | RLS/Status/GitHub | 本次未确认同类关键失败；RLS 有详细合约，GitHub 有操作 Schema/编译器 | 执行同一核对清单，发现后再修；没有发现不等于完整 PASS |

对照用例：IMP、VFY、RLS、Status 的 help 在无效 stdin 下均正常返回。此结果只证明这个具体接口行为。

代码入口：[CTX](../../../../skills/sdlc-000-ctx/scripts/runtime.py)、[REQ](../../../../skills/sdlc-100-req/scripts/runtime.py)、[DSN](../../../../skills/sdlc-200-dsn/scripts/runtime.py)、[PLN](../../../../skills/sdlc-300-pln/scripts/pln_handler.py)、[IMP Method](../../../../skills/sdlc-400-imp/scripts/imp_method.py)、[VFY CLI](../../../../skills/sdlc-500-vfy/scripts/runtime.py)、[共享 Invocation](../../../../skills/_shared/schemas/invocation.schema.json)。

## 4. 是否区分语言、前后端、技术栈

| 层次 | 是否区分 | 覆盖内容与边界 |
|---|---|---|
| 协议、状态、引用、Evidence、授权 | 不按语言或项目区分 | 同一逻辑错误在任意项目必须得到相同分类；不为中文说明开放枚举自由文本 |
| CTX 事实采集 | 按工程标记和能力区分 | Maven/Gradle、pyproject/requirements、package.json 与锁文件、go.mod/work、Compose、文档仓库；仅观察不执行构建 |
| 工程命令 | 按工具及项目声明区分 | build/test/run/lint 的命令与工作目录来自真实配置；未执行不得写成测试通过；未知工具如实标记能力不足 |
| DSN/PLN 领域判断 | 按义务区分 | UI 交互、API、数据迁移、并发、部署等决定适用 Domain/Work Item；前后端标签本身不是新 Gate |
| IMP/VFY 执行 | 必须按工具链、宿主和边界区分 | JDK/Node/Python/Go 版本，离线依赖，OS 沙箱，跨目录工作区，命令预算；缺能力不等于产品失败 |
| RLS | 按目标能力区分 | 当前只有本地 Sandbox；真实容器、云、Maven 发布属于另一个明确授权的适配工作包 |

关键原则：观察到 Compose 不等于容器或服务可用；requirements 约束不等于当前解释器中已安装版本；声明 Vue 不等于浏览器行为通过；Go 版本声明不等于当前可执行版本；目录下没有代码不等于不能建立 document-set CTX。

环境 accessibility 描述准确的访问对象；不能把“可读部署定义”和“运行实例可用”混在一行。项目角色通过 Resource/Component 表达，不强制每个项目都同时有前端、后端、数据库和部署环境。

## 5. 修复设计

### 5.1 复用当前分层，建立可核对的程序输入契约

沿用 `docs/v1.1 → design/build → bundled runtime`。领域规范仍是设计来源；随包契约是执行来源；运行时不读取 docs，不读取兄弟 Skill 私有资源。

每个 Skill 增加或补全随包输入描述，至少登记：命令、字段路径、类型、枚举、必填条件、默认来源、可空语义、引用格式、排序/唯一性、互斥/条件依赖、谁生成字段、缺失/无效行为、对应领域规则及测试 ID。公共确认/引用/错误结构进入 `_shared`，阶段私有字段留在本 Skill。

优先采用仓库已有 Schema 与校验基础；先核查运行环境已有依赖，不自动安装 JSON Schema 库。若使用受限 Schema 子集，必须明确支持关键字并拒绝不支持的关键字，不做静默近似校验。不要新建通用框架或第二套 Store。

机器契约生成字段表、枚举表和示例骨架；语义说明保留人工维护。Schema 与 Runtime 使用同一结构约束来源，避免复制 Python 枚举和 Markdown 列表。独立的领域 Oracle 仍由规范推导，不能从同一生成器产生全部 Expected，防止“共同写错仍一致”。Source Lock/接口库存要覆盖新契约和生成器。

至少提供每命令一个完整合法请求、一个缺信息请求、一个非法请求，以及完整结果。示例中的摘要在构建期按实际 Fixture 字节生成；动态时间、路径、引用通过明确占位的示例生成命令物化，不能把假 hash 标为真实证据。

### 5.2 统一入口与有限的输入整理

保留公共 CLI；CTX/REQ 仍可兼容现有 JSON 入口。先解析命令：meta 直接返回；业务命令再解析输入、目标和操作。纯格式校验在可行时先于上游 Store 读取；需要 Authority 的语义判断在只读解析后执行；全部必要预检在分配、Claim 或产品写入前结束。

增加共享的只读输入预检能力，由正式入口复用；这是操作内部步骤，不新增业务 Phase/Gate 或必须由用户执行的额外命令。项目不完整时依约等待，不把所有条件都设为持久化前硬阻塞。

预检返回字段路径、稳定错误码、允许值/约束、具体缺口和是否需要用户决定。用现有 errors.details 承载有界诊断，避免直接回显 Secret。模型可在未进入正式写入调用前，按清晰契约修正自己的结构错误；建议同次最多 2 次，固定记录首个失败，不隐藏重试。不能自动改事实、风险、最终确认或猜引用来过检。正式 Runtime 返回 failed 后仍按现有停止契约退出，不以预检重试授权绕过它。

只有已登记且无语义变化的格式归一化可自动执行，如换行、明确 CLI 别名、无序引用集合的去重排序。source_worktree 如何归类、部署实例是否可用、资源边界如何划分仍必须由事实支持，不能通过关键词替换强行通过。

### 5.3 错误、Gate 和产品结论分离

| 情形 | 建议结果 | 必须保持 |
|---|---|---|
| 新建请求结构不合法，尚未评估 Artifact | ok=false、status=failed、artifact=null；gate=pending、failed_checks=[]；errors 明确字段 | 不分配、不落盘；不声称 15 项实际失败 |
| 修订输入不合法 | 本次请求失败，说明目标引用与错误 | 既有 Revision/Gate 原样保留，不把请求错误写进历史 |
| 合法输入但事实缺失 | action_required 与真实 Open Items，Gate=pending | 目标/边界已可安全确定时允许契约规定的 open 物化；不伪造 None |
| 领域检查实际失败 | 只将确有失败事实的 Check 记 fail；依赖阻塞或未执行项 pending | Gate 按已有规则聚合；每个结论有依据 |
| dry-run 非法输入 | 与真实操作一致的错误分类，零写入 | 无 Authority；不再丢弃 Builder errors |
| 产品测试/发布效果失败，但 Artifact 记录完整 | 分别保留 Product Result、Artifact Gate 和效果事实 | 不采用全局“ok 等于产品通过”规则，尤其 VFY/RLS |

以上是拟修订的结果约定；实施前锁定当前消费者影响和兼容策略。不要为迁就现有测试把非法请求统一记成产品 fail，也不要把失败日志抹成 pending 成功。

### 5.4 Evidence、Baseline 和未知事实

Core Evidence 接受可复核完整性信息，并未将所有 Evidence 都限定为 SHA-256。建议当前插件保持已实现的 Evidence SHA-256 输入规则，明确记录为插件表示约束，并提供统一正规化方式；本轮不顺带扩大支持的外部完整性算法。

会话 Evidence：保存获授权且必要的最小决定记录，包含准确 task/turn 来源、原始决定语义、被确认对象和适用范围，明确 UTF-8/换行等字节规则，放入允许的 Supporting Member/确认记录后计算真实摘要。摘要只能证明内容未变，不能证明用户身份或授权真实性；默认边界与最终确认不互相替代。无法保存或定位可信来源时停在真实缺口，不写“不适用”或随机摘要。

版本化资源至少绑定完整 commit 与可解析资源；若采集涉及 dirty/untracked 内容，另存该观察范围的路径/字节摘要及来源，不能用 HEAD 掩盖未提交内容。非 Git 文档或外部只读资源使用其类型允许的不可变内容引用。时间只表示观察时刻，不替代内容身份。不要在本修复中把全仓扫描、全依赖枚举或跨机器绝对路径强加给 CTX。

### 5.5 各 Skill 的接入重点

| Skill | 最小修复/核对范围 | 保持边界 |
|---|---|---|
| CTX | 枚举、引用、Evidence、Baseline、typed value、refresh、dry-run、Check 映射 | 保留 Supporting Member 摘要和 prepare_confirmation 已有修复；不复活旧问题 |
| REQ | Source/Requirement 类型、Goals/AP/DEP/Applicability/Evidence 结构、引用闭合 | 自然语言诉求允许中文；不得让用户填内部编号 |
| DSN | inputs.design、变化/决策/16 Domain/Member/追踪映射及 meta 分流 | 不要求全部 Domain 都 required，不绕过固定必需义务 |
| PLN | inputs.plan、WI/Scope/Resource/依赖/完成条件，完整 bundled Spec 的可发现入口 | 不把文件列表当工作项语义，不维护实时任务状态 |
| IMP | Method blocks/checks/candidate_material 的条件结构、命令能力 | 保留 Claim、Scope、CAS、产品写入预检和中断现场 |
| VFY | hints、人工观察、执行策略、失败 Return、结果投影的输入结构 | 上游决定权威范围；调用者不得用 JSON 覆盖 Subject 或伪造人工结论 |
| RLS | 自动/人工确认、Target、授权记录引用及状态机输入的完整映射 | 不增加真实部署、不合并效果授权与最终确认 |
| Status | 精确 Reference、空 Store、歧义与分支结果的输出一致性 | 严格只读，不把能力缺失当流程完成 |
| GitHub | 操作 Schema、参数编译、回执 unknown/partial 的文档与例子一致性 | 复用已有 Schema；不新增联网/写入权限，不自动重放 |

### 5.6 兼容与迁移

先登记所有当前公共输入和专用结果消费者，再接入契约。合法旧请求必须能继续使用；未知或过去被静默忽略的字段先列入迁移清单，不能一夜之间以 additionalProperties=false 拒绝全部历史调用。固定旧版/新版正负 Fixture，明确曾被错误接受的输入从何版本开始拒绝。

如果修改 canonical 内容、Gate Check 语义或 Evaluation Contract Set，按既有规则使 open 当前确认失效并重新确认；冻结内容不改写、不重哈希迁移、不自动升级为新规则下的 Authority。需要继续工作时显式新 Revision，并说明兼容范围。Source Lock 更新由工具从实际源码生成，不能手填结果。

## 6. 项目复现与测试分工

复现步骤、矩阵及固定 Oracle 见 [EVAL-PLAN.md](EVAL-PLAN.md)。核心分为三路：精确错误输入在共享 Runtime 的确定性重放；三个已验证项目的脚本化链路回归；新模型只凭安装包文档采集事实并构造请求的独立实验。三路不互相替代，也不各跑一遍全部相同测试。

项目覆盖至少包括用户三个实际项目、approval-bot 原始失败的隔离副本；Gin-Vue-Admin 复用仓库已有固定 e2e，填补 Go+Vue SPA 与多目录工程覆盖。目录结构、dirty、缺锁、未知工具等用小型派生 Fixture 覆盖，不再为每种组合引入完整业务项目。

## 7. 合并重复工作与取消不适用门禁

| 现状/候选 | 处理方案 | 不能取消的部分 |
|---|---|---|
| 多处手写相同枚举/字段表/默认值 | 单一机器约束生成文档投影，删除仅重复投影的手写版本 | 独立语义 Oracle、不同信任边界的验证 |
| quick、private、full、strict、e2e 串行重复执行同一套测试 | 继续只用 tools/validate.py；日常针对受影响集合，最终一个最高所需 profile，各测试 ID 执行一次 | 正式执行证据、失败记录和完整覆盖 |
| 元命令先校验业务 stdin/Store | 直接取消该不适用检查 | 命令本身的合法解析和零副作用 |
| 同一目标因硬盘存在其他目录而反复询问 | 宿主唯一当前项目优先；只有本次目标真正歧义时询问一次 | 嵌套独立仓库/边界有多合法解释时的选择 |
| 内部 ID/摘要/JSON 交给用户填写，标准写入反复批准 | Runtime/适配器完成机械工作；使用本次已授权 write_policy | 业务取舍、风险豁免、最终确认、效果授权不可互换 |
| 所有项目、语言、前后端、模型组合都跑全链 | 共性协议一次覆盖，适配器按能力测试，代表项目跑链，模型仅跑短路径 | 同类新发现必须加入固定反例，不以项目总数代替覆盖 |
| 在同次只读处理中多次读取同一不可变对象 | 经测量后可按 Reference+payload digest+Contract Set 复用 | 写前 CAS、freeze 重验、可变文件/Claim/目标的当前性复查 |
| 要求每种宿主原生独立认证才接受 Runtime | 保持 Maintainer 已暂停的原生认证门禁；本次有限文档可用性实验独立标记 | 不冒称未测宿主 Verified；不把模型实验等同认证 |
| 只比对文案或函数实现本身的重复测试 | 合并为参数化契约测试，保留原 Case ID 映射和独有断言 | 篡改、授权、Secret、并发、中断/恢复与只读等独立风险覆盖 |

实施前建立“旧检查/断言 → 风险 → 唯一保留用例 → 触发条件 → 结果字段”的迁移表。只有证明风险覆盖未丢失才删除；同一断言用于前后两个不同信任边界并非冗余。此计划不授权机械删除所有 Gate、异常分支或失败测试。

结构、行为和独立文档实验整合进现有验证入口与报告，不新建平行业务 Gate 系统。默认不追加全宿主认证、with/without-skill 大样本比较或无限次稳定性测试。

## 8. 工作包与实施顺序

每个正式工作包遵循既有阶段隔离；以下是路线图，不代表本次已经进入 implement。工时为当前证据下的工程工作日粗估，不含模型额度等待、外部项目依赖准备与人工审查排队。

| 包 | 阶段/依赖 | 交付及范围 | 验收与停止点 | 粗估 |
|---|---|---|---|---|
| W0 | design，本次 | 当前问题清单、修复设计、复现/Eval、删并原则 | 文件与引用检查完成；停止在计划审阅 | 本次 |
| W1 | approval，W0 后 | Maintainer 对输入表示、错误/Gate 分离、兼容、有限模型实验与删并范围作明确决定 | 只记录决定，不实施 | 依审阅 |
| W2 | implement，W1 后 | CTX 错误返回/Baseline/输入约束；DSN/PLN meta；最小反例 | 已复现失败转为正确拒绝/等待，正例和零写入保持；不改业务项目 | 2–4 日 |
| W3 | implement，W2 基础 | 共享输入描述和预检、CTX/REQ/DSN/PLN 接入、生成文档/示例 | 每个实际输入字段可查；公共枚举无手写漂移；消费者兼容 | 3–5 日 |
| W4 | implement，W3 后 | IMP/VFY/RLS/Status/GitHub 逐命令盘点并按证据补齐 | 未发现缺陷不做行为重构；各自效果边界不变 | 2–4 日 |
| W5 | implement，契约稳定后 | 能力声明与轻量采集映射、错误定位、去重入口和旧测试映射 | 不新增项目名称特判；不删除独有风险断言 | 2–3 日 |
| W6 | evaluate，干净准确提交 | 固定反例、一次去重全仓、三项目正式链与定向模型实验 | 实际失败保留；日志在仓库外；每个结果有准确 Subject | 2–4 日 |
| W7 | review | 新上下文核对 Spec/Schema/Runtime/样例/证据，特别检查删并后的盲区 | 报告问题；不自行接受、合并或发布 | 1–2 日 |
| W8 | finalize，明确接受后 | 紧凑 Handoff、兼容/版本记录、可恢复证据索引 | 独立发布授权前停止；安装缓存不自动覆盖 | 0.5–1 日 |

实现至评测粗估 11–20 工程日。若 W4 发现新的领域语义问题，单独登记变更，不以“统一契约”名义无限扩大范围。先交付 W2 可尽早阻止本次失败模式；W3/W4/W5 以同一个注册清单推进，不各造一套描述系统。

允许的未来实现路径：`skills/_shared/**`、相关 `skills/sdlc-*/references|scripts|SKILL.md`、共享 `packages/sdlc_runtime|sdlc_phasekit`、`tools/validate*`、相关 `tests/**` 与本组件设计。Store Schema、原始 docs/v1.1 语义、真实部署能力不在默认范围；必要时需明确独立设计决定。对 test-sdlc 的执行或修改需使用指定隔离检出树，当前只读访问不意味着授权其远程发布。

## 9. 持续验收与风险

必须可观察的成功条件：已知 SCR 确定性反例全部得到预定结果；九个 Skill 的公共命令及实际消费输入可追踪；生成文档差异在构建期检出；合法旧请求兼容；非法/未知字段不静默忽略；dry-run 与 check 无持久化或产品效果；三项目已有业务断言不缩水；approval-bot 同类输入路径不再依赖查看私有实现；小型独立模型实验保留首次结果和全部纠错记录。

风险与控制：

- 过度收紧 Schema 会破坏历史请求：逐字段迁移并固定旧版正例；不重写 frozen。
- 同源生成会把错误同时复制到文档和校验：保留从领域规范和原始失败独立推导的 Expected。
- 小样本模型实验无法证明任意模型稳定：只报告模型/版本/次数/首次成功率，不声称全概率保证。
- 拆分前端、后端容易形成多套业务规范：按 Resource/能力组合，不按标签复制契约。
- 删除检查可能破坏 TOCTOU 防护：可变状态和不同信任边界必须保留重验。
- 项目全链成本大且可能需要未具备依赖：预备环境与正式执行分离，Runtime 不联网或自动安装；缺能力单独报告，不跳过算通过。
- 当前仍有未完成的字段级盘点：RLS/Status/GitHub 暂无发现不作为免责或完成证明。

## 10. 本次验证与唯一下一动作

本次实际完成：当前代码与旧提交比较；CTX 三组内存探针；六个 Skill 的 help/非法 stdin 对照；三项目准确提交下的报告与 Admin 来源只读读回；调用封装与输入结构分析。未执行产品代码、完整业务链、模型对照、依赖安装、ArtifactStore 写入或远端变更。

本设计与 Eval 尚待审阅；唯一下一工作包为 W1：审阅并明确接受或调整本修复方案。未设置新模型/宿主认证门禁，也未默认授权后续实施。

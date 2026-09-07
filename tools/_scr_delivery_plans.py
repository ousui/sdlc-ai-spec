from pathlib import Path
root=Path.cwd()
p=root/'docs/plugin-development/components/skill-contract-reliability/DESIGN.md';s=p.read_text()
s=s.replace('日期：2026-09-08。阶段：design。状态：draft；尚未批准实施。','日期：2026-09-08。阶段：design/review → implement → evaluate（本次 Maintainer 明确连续执行授权）。状态：ready；本工作包授权与修订依据见 [REVIEW.md](REVIEW.md)，不代表最终验收或发布批准。')
s=s.replace('本次仅交付设计、评测计划和 Handoff。不修改 Runtime、领域规范、测试 Oracle、用户项目、已冻结 Artifact、历史回归或安装缓存；不执行全流程、安装、发布或外部写入。','原设计提交仅交付计划。本次 Maintainer 已明确要求审阅修订后在独立分支实施和验证；修改 Runtime、长期回归、随包契约、相关工程工具及三份交接文档，使用本工作包 PR 记录检查点。领域规范、用户现有工作树、已冻结 Artifact、历史证据和安装缓存保持不变。不自动合并、不做生产发布、不扩大 Skill 的联网/外部写入权限；CI 的显式环境准备与 Runtime 自动安装严格分开。')
s=s.replace('| 当前修复工作树 | `codex/bugfix`，HEAD=`aed8eb69d2b74ec27bdcb2fb356cb02b68602289`；设计前干净 | 本设计的代码检查及最小复现 Subject |','| 原缺陷基线 | `aed8eb69d2b74ec27bdcb2fb356cb02b68602289` | 本设计最小复现及旧失败 Subject |\n| 当前来源 / 修复分支 | `codex/bugfix@14c167e044d7a8eeada3c826d1c41bb55bc7b01b`；独立 `fix/skill-contract-reliability-v1`；评审检查点 `edfe1f772ec4c92bade2997508fdac3f11b23118` | 前者只追加原设计交接；后者的 Runtime 仍与缺陷基线相同；不能作为修复通过 |')
s=s.replace('| SCR-12 | RLS/Status/GitHub | 本次未确认同类关键失败；RLS 有详细合约，GitHub 有操作 Schema/编译器 | 执行同一核对清单，发现后再修；没有发现不等于完整 PASS |','| SCR-12 | RLS/Status/GitHub | 原设计未确认同类关键失败；RLS 有详细合约，GitHub 有操作 Schema/编译器 | 执行同一核对清单，发现后再修；没有发现不等于完整 PASS |\n| SCR-13 | RLS 换 Target | 新发现：Run 34143404043 的 RLS-E075 因临时 ID 与已分配 ID 碰撞而返回原 Reference；同代码另次通过，具有时序依赖 | 用 Target/Lineage 语义决定分配，不以 provisional ID 相等判断 no-change；强制碰撞回归，不削弱原 E075 |')
s=s.replace('每个 Skill 增加或补全随包输入描述，至少登记：','先盘点九个 Skill 的公共命令、真实 stdin/Envelope、实际消费字段和 Result 消费者。库存以当前源码为准，缺项必须显示而非从“统一 Envelope”推导；后期专用 wire 格式默认保留。\n\n每个 Skill 增加或补全随包输入描述，至少登记：')
s=s.replace('版本化资源至少绑定完整 commit 与可解析资源；若采集涉及 dirty/untracked 内容，另存该观察范围的路径/字节摘要及来源，不能用 HEAD 掩盖未提交内容。非 Git 文档或外部只读资源使用其类型允许的不可变内容引用。时间只表示观察时刻，不替代内容身份。不要在本修复中把全仓扫描、全依赖枚举或跨机器绝对路径强加给 CTX。','新采集的 Git 版本化资源绑定完整 commit 与可解析资源；若采集涉及 dirty/untracked 内容，另存该观察范围的路径/字节摘要及来源，不能用 HEAD 掩盖未提交内容。现有通用 `vcs:` 不等于 Git 专属格式；保留有明确不可变版本标识的旧合法输入，不把 40 位十六进制串本身当成已解析证明。非 Git 文档或外部只读资源使用其类型允许的不可变内容引用。时间、HEAD/main/latest/current 等可变名称都不能单独替代内容身份。格式可识别、对象解析与内容一致性分层判断：缺访问能力是明确缺口，不能冒称已验证；输入预检不强制网络、全仓扫描、全依赖枚举或跨机器绝对路径。')
s=s.replace('先登记所有当前公共输入和专用结果消费者，再接入契约。合法旧请求必须能继续使用；未知或过去被静默忽略的字段先列入迁移清单，不能一夜之间以 additionalProperties=false 拒绝全部历史调用。固定旧版/新版正负 Fixture，明确曾被错误接受的输入从何版本开始拒绝。','先登记所有当前公共输入和专用结果消费者，再接入契约。合法旧请求必须能继续使用；已声明封闭的边界继续拒绝未知字段，原本允许扩展的边界以字段级兼容诊断指出未消费字段，不执行或赋予其权限。新增严格拒绝需登记迁移和配对旧正例，不能用 additionalProperties=false 一次封死全部历史调用。确认、授权、布尔操作选项的错误类型不属于可保留的扩展。固定旧版/新版正负 Fixture；输入表示修复不重写 frozen。')
start=s.index('每个正式工作包遵循既有阶段隔离；以下是路线图')
end=s.index('\n允许的未来实现路径：',start)
s=s[:start]+'''本次在同一分支按依赖顺序推进，Maintainer 当前授权允许连续实施/验证，不因原 W1 停点反复索取同一批准。每个检查点保留实际文件/测试/结果；下表不是已经完成的声明。

| 包 | 阶段/依赖 | 交付及范围 | 验收与停止点 |
|---|---|---|---|
| W0/W1 | review/design，当前授权 | 修订 DESIGN/EVAL 与输入/消费者库存，固定新增缺陷与兼容边界 | 记录实际授权，不自行宣布最终接受 |
| W2 | implement | CTX 错误返回/基线；DSN/PLN meta；RLS provisional ID 碰撞；配对回归 | 已复现反例转为正确拒绝/等待/分配，正例和零效果保持 |
| W3 | implement，W2 后 | 共享结构诊断与 CTX/REQ/DSN/PLN 可核对输入、字段/枚举文档 | 结构来源一致；业务缺事实仍按原流程等待，不自动编造 |
| W4/W5 | implement，库存驱动 | IMP/VFY/RLS/Status/GitHub 逐命令核对、必要补文档及能力映射 | 无证据不重构；不同信任边界安全检查不去重 |
| W6 | evaluate，准确源码 | 固定反例+配对正例、统一最高可执行 profile、三项目业务链、现有 e2e | Case ID/Source/Test/环境/真实效果独立绑定；失败不覆盖 |
| W7 | review | 核对原始证据、兼容和输入漂移；独立新上下文实验单独记录 | 当前执行者自检不是 fresh-context Review；能力不足如实列明 |
| W8 | handoff | 紧凑结果索引与一个可恢复下一动作 | 无未执行项才可称全范围完成；不自动 merge 或生产发布 |

不删除有效测试来缩小工作量。CI 环境可显式准备已锁定依赖和项目副本；Runtime 本身仍不联网、不安装。approval-bot 原快照、独立模型/宿主等不可访问材料不猜测补齐：继续完成可执行 A/B，受阻部分明确 BLOCKED/NOT_RUN，不将部分完成合并成全局 PASS。
''' +s[end:]
s=s.replace('允许的未来实现路径：','本次允许的实现路径：')
s=s.replace('## 10. 本次验证与唯一下一动作','## 10. 原设计诊断与当前执行')
s=s.replace('本次实际完成：当前代码与旧提交比较；','原设计实际完成：当前代码与旧提交比较；')
s=s.replace('本设计与 Eval 尚待审阅；唯一下一工作包为 W1：审阅并明确接受或调整本修复方案。未设置新模型/宿主认证门禁，也未默认授权后续实施。','当前评审修订已形成 [REVIEW.md](REVIEW.md)，按 Maintainer 本次要求进入独立分支实施/验证。持续执行状态及唯一下一动作以 [HANDOFF](../../HANDOFF.md) 为准；已执行证据写入独立 EVAL-RESULTS，不把本计划的 Expected 改成实际 PASS。')
s=s.replace('本地 test-sdlc 检出树有用户改动，已仅只读观察；后续必须从准确 Git 对象创建隔离副本，不能 reset 或清理该目录。该仓库 main 在本次读取时为','原设计记录用户本地 test-sdlc 检出树有改动；本次 Web 未访问该本地路径，执行时从准确 Git 对象创建隔离副本，不能 reset 或清理用户目录。原设计读取时该仓库 main 为')
s=s.replace('“已复现”表示在当前 HEAD 执行最小探针得到；','原 SCR-01–12 的“已复现”指 aed8eb6 基线探针；本次新增执行须另记准确 Subject；')
p.write_text(s)
p=root/'docs/plugin-development/components/skill-contract-reliability/EVAL-PLAN.md';s=p.read_text()
s=s.replace('日期：2026-09-08。阶段：design。状态：draft。本文定义未来执行方式和 Expected，不是 EVAL-RESULTS，不声称计划中的案例已执行。','日期：2026-09-08。阶段：reviewed → evaluate（本次明确授权）。本文定义执行方式和 Expected，不是 EVAL-RESULTS，不声称计划中的案例已执行；修订原因见 [REVIEW.md](REVIEW.md)。')
s=s.replace('固定当前反例基线 `aed8eb69d2b74ec27bdcb2fb356cb02b68602289`；修复完成后再登记新的准确提交。','固定反例基线 `aed8eb69d2b74ec27bdcb2fb356cb02b68602289`；当前设计来源 `14c167e044d7a8eeada3c826d1c41bb55bc7b01b`，修复分支 `fix/skill-contract-reliability-v1`。修复完成后另登记 Implementation Subject、Test Source 和 Evidence Delivery Head。')
s=s.replace('时间不能替代内容身份；合法不可变基线接受；dirty 范围有可重现依据','时间/可变分支不能替代内容身份；新 Git 输入使用可解析完整 commit，旧通用 VCS 不误判为 Git；dirty 范围有可重现依据；格式不等同真实性证明')
s=s.replace('未知字段不静默吞掉；兼容清单内旧请求可用；授权不由类型转换生成','封闭边界未知字段拒绝；旧可扩展边界给出未消费诊断但不执行；兼容清单内旧请求可用；授权/确认/操作布尔类型不通过转换生成')
s=s.replace('| SCR-E28 | scope/外部权限/风险接受/最终确认以普通文本混入输入 | 不提升权限，不自动接受 Exception，不以预检纠错越过人工决定 | 授权 |','| SCR-E28 | scope/外部权限/风险接受/最终确认以普通文本混入输入 | 不提升权限，不自动接受 Exception，不以预检纠错越过人工决定 | 授权 |\n| SCR-E29 | RLS 换 Target；强制 provisional ID 与已有 ID 相同；同 Target no-change/retry 配对 | 新 Target 分配新 Artifact 且清除 Effect Authorization；旧 Store/Target 未受修改；同 Target 正确保持或新 Revision；保留原 RLS-E075 | SCR-13 |')
s=s.replace('默认建议 3 个短路径 × 2 个用户可用且明确选择的模型配置 × 2 次新上下文，共 12 个执行单元。','在具备独立执行能力及已授权模型配置时，建议 3 个短路径 × 2 个配置 × 2 次新上下文，共 12 个执行单元。')
s=s.replace('本工作包建议必须观察本次缺陷相关短路径，但不恢复所有宿主原生独立认证门禁。','执行前先锁定能力清单。当前会话已经读取实现/测试，不能充当本实验的新上下文。若没有独立模型执行工具或 approval-bot 原始快照，分别记 C=BLOCKED、原项目=NOT_RUN；脱敏重建的 A 类输入只能标 RECONSTRUCTED。继续完成可执行 A/B，但不将其宣称为 C 或全范围完成。本工作包不恢复所有宿主原生独立认证门禁。')
s=s.replace('执行本计划需要后续 implement/evaluate 工作包。当前只完成设计与列明在 DESIGN 中的最小诊断，不生产新的业务闭环证明。','本次 Maintainer 已明确授权按序 implement/evaluate。此计划本身不生产新的业务闭环证明；每项执行/失败/未运行均在 EVAL-RESULTS 与 PR 检查点登记。不同源码的偶然 PASS 不能免除强制反例，CI Run 的事件 SHA 不能替代真正测试进程的源码 SHA。')
p.write_text(s)
p=root/'docs/plugin-development/HANDOFF.md';s=p.read_text();end=s.index('## 以下为此前维护交接记录')
s='''# 当前工程交接

## 当前工作包：Skill 输入契约可靠性修复与验证

2026-09-08，Maintainer 明确要求评审修订后在 Web 同会话实施、验证并保存恢复点。来源 `codex/bugfix@14c167e044d7a8eeada3c826d1c41bb55bc7b01b`；反例基线 `aed8eb69d2b74ec27bdcb2fb356cb02b68602289`；修复分支 `fix/skill-contract-reliability-v1`，Draft PR #20。当前正式业务 Skill 执行：`None`（这里是插件工程修复，不是用户产品发布）。

[DESIGN](components/skill-contract-reliability/DESIGN.md)、[EVAL-PLAN](components/skill-contract-reliability/EVAL-PLAN.md) 已按 [REVIEW](components/skill-contract-reliability/REVIEW.md) 修订。原设计的 W1 停点被本次明确连续执行授权取代；不代表最终验收或合并批准。不修改 main/codex/bugfix，不操作用户现存工作树或安装缓存，不做生产效果。

基线已实际重放 CTX 全量错误映射、dry-run 丢错误、时间基线通过及 DSN/PLN 非终止 stdin 阻塞。另发现 RLS-E075 临时 ID 碰撞；相同 Runtime 不同时间可通过，必须增加强制碰撞回归而不是重试抹平。旧三项目 PASS 不用于新版本结论。

Issues 已关闭（HTTP 410），使用 Draft PR #20 正文清单/追加评论及仓库外 Actions 原始产物记录恢复点，不改变仓库管理设置。源树仅保留长期契约、测试、设计与紧凑证据索引；运输或文档提交不冒充实现 Subject。

## 唯一下一工作包

继续本分支 SCR 修复/验证：先固定原缺陷与旧合法请求，再实施最小修复和随包输入契约，随后在准确提交执行可用的统一回归/项目链。approval-bot 原快照和独立新上下文模型执行能力不可用时单列 NOT_RUN/BLOCKED，不向用户反复索取已授权操作确认，不宣称全范围 PASS。

''' +s[end:];p.write_text(s)
print('plans updated')

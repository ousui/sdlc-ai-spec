# 输入契约可靠性：设计评审与本次执行决定

日期：2026-09-08（UTC+08）。来源：`codex/bugfix@14c167e044d7a8eeada3c826d1c41bb55bc7b01b`。

Maintainer 在本次 Web 会话明确要求评审并修订两份计划，随后新建分支修复和验证，使用远端资源保存恢复点。本记录不是 Agent 自行批准新产品能力；它记录当前任务的明确授权。允许在同一会话按顺序完成 design/review、implement、evaluate，保留可辨识提交。不自动 merge、修改 main、生产发布、扩大 GitHub Runtime 权限或恢复原生 Client 认证门禁。

## 评审结论

保留原 DESIGN 的公共协议统一修复、技术栈单独适配、Artifact/Product/Effect 分离、独立 Oracle、只读/CAS/授权边界，以及 EVAL-PLAN 的 A/B/C 三种证据。原计划作为完整问题与风险库存，不把计划文字当执行结果。以下修订将同步回 DESIGN 与 EVAL-PLAN；本记录保留修订原因。

| 决定 | 原计划的问题 | 修订 |
|---|---|---|
| SCR-R01 | 当前分支与缺陷基线混用 | 来源 HEAD 固定 14c167e；反例 Subject 固定 aed8eb6；最终报告另记准确实现 SHA、测试 SHA、Runtime 内容摘要、证据交付 Head，旧 PASS 不升级。 |
| SCR-R02 | W1/W2 等独立审批停点与本次明确连续执行要求不一致 | 当前授权允许按序执行本工作包；只在真实缺权限/事实/能力时停止受影响部分，不反复询问已授权机械操作。工作包结束仍不自动合入。 |
| SCR-R03 | 机器 Schema 先行但消费者和实际字段尚未盘点 | 先锁定九 Skill 的 command / envelope / input / result / consumer 库存。阶段输入结构与公共 Envelope 分开；后期专用结果先文档化，不强制 wire 迁移。 |
| SCR-R04 | DESIGN 允许兼容未知字段，但 E18 要求未知字段不静默吞掉，未说明统一策略 | 已支持旧合法请求保留；当前未使用字段采用明确诊断/兼容清单，只有已声明严格边界拒绝。授权和确认的类型错误始终拒绝。任何收紧必须有旧正例、负例和版本边界。 |
| SCR-R05 | Baseline 可能被简化为匹配 40 位字符即可信 | 区分不可变标识的格式、对象是否可解析、dirty 内容是否绑定三层；摘要/commit 字符串不是授权或真实性证明。非 Git 文档有自己的内容身份；不能强制全仓扫描。 |
| SCR-R06 | 新输入校验易提前产生 Store、Claim 或虚构 Check 失败 | meta 首先分流且不读 stdin；纯结构预检在任何持久化前完成。输入错误不写历史，不将未执行 Check 标 fail；真实领域失败不抹为成功。dry-run 保留错误、绝不授予 Authority。 |
| SCR-R07 | 项目矩阵中 approval-bot 原快照尚未提供，模型/新上下文未确认可用 | 先记录能力和可访问材料。脱敏重建只能标 RECONSTRUCTED，不冒称原项目复跑；当前审查会话不能充当独立模型实验。无法执行项保留 BLOCKED/NOT_RUN，不影响继续完成可执行 A/B，但禁止全局完成宣称。 |
| SCR-R08 | 按项目/数字判通过以及全量套件重复执行的风险 | 固定 Case ID/断言映射与最小业务测试义务；保留 Flask-Admin 13、SpringGear JDK21 10、Fansite 24 的原测试身份。Gin-Vue-Admin 是额外固定 e2e，不冒充 Flask-Admin。最终同一 Subject 只执行所需最高 profile；重试与失败证据不覆盖。 |
| SCR-R09 | 尚未登记当前基线的现存失败 | 现有 Run 34143404043（aed8eb6）实际收集/执行 1330，1 failure；先定位再判断与本修复的关系，不引用历史 strict 1092 当当前全绿。 |
| SCR-R10 | 删除重复检查缺可执行的追踪产物 | 本轮默认不删除有效测试；只有风险→保留唯一测试→触发条件→结果字段映射完整才删除。不同信任边界的复验不视为重复。 |

## 执行与恢复

修复分支为 `fix/skill-contract-reliability-v1`。Issues 已被仓库关闭（创建返回 HTTP 410），不修改管理设置；使用本分支 Draft PR 的正文清单和按检查点追加的评论作为工作记录。原始日志与源码快照保存为 Actions artifact，源码仅保留长期测试、契约和紧凑索引。未完成验证前不创建表示已验收的 Release/Tag。

顺序：修订计划与库存 → 固定原缺陷与旧正例 → 最小 Runtime 修复 → 九 Skill 随包契约与漂移检查 → 准确源码的统一回归和代表项目验证 → 证据复核与 Handoff。缺外部输入的项目单列，不捏造或借历史 PASS 补足。

当前状态：REVIEWED，实施尚未开始。本次写入只建立可恢复的设计评审检查点。后续实际结论见 EVAL-RESULTS 与 PR，不回写本记录冒称当时已完成。

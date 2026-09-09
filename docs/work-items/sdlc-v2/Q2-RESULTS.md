# Q2 三项目第二复杂需求收口

三项目真实安装版 Skill/公开 CLI 业务闭环与本地 RLS 完成，实验室本地提交 `f41d048414d3b212e793ddffcd049d19c2273434`。170份源码由实际交付包逐文件回读，详细索引为实验室 `v2/Q2`；生成二进制、Runtime锁和大型归档保持各自原始保存范围。

| 项目 | 最终业务验证 | 独立核验及专项 |
|---|---|---|
| Admin | 53项：原13+R1十五+Q2及身份/迁移/准备探针 | 58次执行含重复4项和新增迁移；实际worktree/原439行归档collect恢复及双父resolve |
| SpringGear | 四模块43JUnit，JDK21；41类major65 | 额外5边界；真实无关Git合入后证据仍适用，共享组件变化后拒绝旧PASS并实跑43项 |
| fansite | Go44、race、JS47/49、UI、构建 | 连续相册重载及旧空库迁移；真实SIGKILL、unknown、复制恢复和Header遮蔽 |

主业务包为q2-entry：7d7179328712194bf362b752a585e7f044ba8260，package 7c4102ba61608adcec35c2ee97a4b8a20f2c2a9ff2145a5ff9727b83afdf9625。各项目业务修复、原始失败和输入纠正未覆盖。人工SQL/Store/Authority/协议绕过0；不把真实退修或预期拒绝计成正常成功轨迹。

共享Runtime修补单独保留版本：

- `fc07245` 遮蔽完整认证/Cookie Header；153项完整回归及独立中断复验。fansite在clean q2-headerfix真实执行硬中断、unknown和复制恢复，两组原始ZIP作为来源附件进入最终交付与完整归档。
- `6214e5c` 保留冻结revision分叉与后代并返回可消费的导入head；159项完整回归、独立来源保存两负例红绿及原Admin实际恢复均通过。见Q2-COLLECT-VERSIONS.md。
- 本轮收口将已存在的公开change.resolve列入REQ/DSN/PLN命令表与接口索引，便于从共享恢复约定找到本阶段入口；未改变其Runtime行为。

Admin原包通过clean q2-collectfix（package 4495c7599cac5a25458769294d431cb0210aa1f52d91dd463a27d68bdd0fafe3）恢复，22次公开调用全部成功。collect时原目标active/草稿/generation/3本地授权不变，无关需求完整回读不变；仅加入3条imported来源授权历史。原失败095逐字节回放，61来源operation原字段、37资产与209来源Run文件保持。

目标正常提交DSN/PLN后，change.resolve形成bf04c25b-8af0-4b03-bee2-9fa3eb134a4e，parent为目标8d8cef33-2494-4486-8590-6ba27f729e50、merged_from为来源别名cbad50ee-cdba-5e03-9054-17db816e8269，再正常提交。内容专项Run明确cancelled，未宣称主工作树又执行一次产品实现/RLS；来源实际RLS仍completed/imported。再导出847行/304清单/305成员/37资产全部核验，七个冻结内容摘要独立重建匹配，原439行ZIP和版本映射可移植保留。

大型证据均在实验室`.local-runs/sdlc-v2/q2-*`及`reviews/q2-collect-independent/admin-actual`。原input、CLI、失败/修复、交付和归档版本见三个精简索引。未push、merge产品上游、发布或修改宿主配置；临时commit消息使用/tmp，测试使用隔离临时目录。

下一工作包仅FINAL：冻结这次收口后的Runtime提交与clean安装包摘要，同版本完成159项Runtime测试、全部九条真实当前Agent链与公共入口/业务回归，并更新46项设计映射。过去多版本成功不替代FINAL，当前客户端外原生认证/Rust/MySQL/SpecKit仍不在本地完成声明中。

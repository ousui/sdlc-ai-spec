# SDLC v2 唯一进度

## 当前工作包：Web审查专项修复

用户2026-09-09授权修复上一轮审查问题、恢复Issue共享、验证并交付用户指南。实施分支 `fix/v2-review-github-sharing`，专项起点 `31c6627c34e31068e35f739fe6457346b5bd7f8c`。

GitHub读写预检已通过：#22评论5601077221写入并读回。旧实施PR #22关闭但未合并、未删分支；PR #23接续。main仍为旧基线，PR23整体diff包含既有v2；本专项比较31c6627→当前HEAD。原实验室PR #20保留历史场景，新专项实验室PR #22只追加Issue集成。

## 检查点

| 内容 | 状态 | 验证 |
|---|---|---|
| VFY/RLS检查时点 | 完成 | RLS所属条件延后，RLS完成仍检查；错误convergence阶段生产端拒绝 |
| 产品执行位 | 完成 | 写入保留mode，指纹纳入mode，ZIP保存并独立回读；实际wrapper可执行 |
| 共有Run交回 | 完成 | 保留目标状态/来源观察，稳定身份冲突仍拒绝，不继承来源权限 |
| 大包/附件恢复 | 完成 | 产品交付与历史归档分离；同需求68MiB输入真实RLS通过；draft unlink保留原字节 |
| 人工阅读 | 完成 | 六阶段Markdown与HTML，不再以JSON作为主要正文 |
| sdlc-github | 完成 | 已有Issue的preview/publish/status/reconcile，独立回执、去重与unknown回查 |
| macOS原生回归 | 已通过 | 精确修复SHA f8b4765，178/178，94.776秒，10 Skill/契约/安装包检查通过 |
| Ubuntu便携机制 | 已通过 | 同SHA独立portable套件通过；本地Linux100/100，106.045秒另记，不能相加 |
| 真实GitHub发布 | 已通过 | 12次安装版公共CLI；实际评论5601819414、重复发送同ID、reconcile与导出通过 |
| 用户指南 | 完成 | 根级USAGE.md；完整授权提示、阶段产物、恢复/归档、Issue分享、Podman和试用流程 |
| 用户本机验证 | 待用户试用 | Podman VM/客户端原生加载/自然语言路由、实际新需求、中低推理配置未代测 |

正式代码修复提交 `f8b4765e46fd440d8e95d0c065b5ccc7b115b0af`，证据 [Run34351040098](https://github.com/ousui/sdlc-ai-spec/actions/runs/34351040098)。测试工具提交的触发SHA与实际被测SHA分别记录，未混用。

真实Issue集成 [Run34351132793](https://github.com/ousui/test-sdlc/actions/runs/34351132793)，实验室源码 `bf0ce1c2b55a69f797bf6d047cba1df527406b96`，Runtime同为f8b4765。测试Issue21现已关闭，原评论保留；此评论是Runtime经gh创建，不是连接器代写正文。实现仓库Issues关闭，未修改其设置。

临时源码运输分片、自写入apply/source workflow已在 `d61bf27b09e8ba5fd1afa24860b0ebc8c4594bd1` 清理。普通v2-checkpoint只读checkout准确head，分别执行macOS全量/Ubuntu便携套件，并保留日志、安装包和source bundle。当前文档提交不改动已通过的Runtime/Skill内容；本次HEAD的最新CI结果在PR23登记，不改标旧结果。

178包含原159及本次新增19项。portable与native重叠，不相加；真实GitHub12请求不是12个业务验收目标。未重跑历史9条Agent产品链，未认证Linux/Windows原生命令收集器。Podman可跑Linux机制测试，不能模拟macOS Seatbelt。

详细修补、原失败及证据边界见 [REVIEW-FIXES.md](REVIEW-FIXES.md)。安装/使用见 [USAGE.md](../../../USAGE.md)。本工作包未merge主干、tag或release。

## 既有v2实现与历史验收

原P0–P4、Q0/Q1/Q2及FINAL保留在 [FINAL-RESULTS.md](FINAL-RESULTS.md)、对应工作包报告和Git历史。原本地最终执行为 `495177acf777251d378652e2a50e47a1b5c4c41a`；159/159与9场景、43适用项/3延期均属于原版本，不能替代本次结果。

原实验室最终源码 `dde73bc4525522ed8298396b2f129bb884db64b5`，三轮490份交付源码及紧凑索引在实验室PR20；大型原始日志、Store和归档仍在用户本地忽略目录。

历史Admin共有Run交回失败、fansite大包失败及另建验证需求恢复继续保留。本次针对这些机制新增了直接反例修复与同需求回归，不把历史失败改写成首次成功。

## 下一动作

读取PR23当前HEAD CI与专项报告，使用修复后的完整安装包进行普通用户新会话试用；必要的本机验证按USAGE.md执行。只有发现具体失败再开有边界修复，不再重新设计v2或扩大到平台化。

## 2026-09-09 Skill展示文案与插件来源

十个入口的目录、调用标识与interface.skill对应；标题和display_name为目录名大写加中文描述，SKILL简介与UI简介一致。阶段入口保留000–600；辅助入口为SDLC-INIT、SDLC-STATUS、SDLC-GITHUB，不使用编号。三个客户端共用Skill、Runtime和显式调用边界。

插件唯一权威仓库为goedgecloud/sdlc-ai-spec；三个客户端插件及市场元数据均使用该地址。历史ousui个人仓库PR、CI和冻结基线仅保留为开发证据，不代表权威安装或发布来源。

证据索引：tools/validate_skill_style.py校验十入口目录/标识/标题/简介/调用策略与跨客户端插件来源；tools/validate.py quick检查公共契约；tests/v2/test_packaging.py验证独立安装包；git diff --check检查空白错误。缓存按57个打包源文件逐字节核对。原生客户端实际调用和刷新后的界面未认证。

本轮结果：quick与十入口样式校验通过；安装包测试4/5通过，真实交付链在命令检查步骤失败（受限执行为blocked，宿主权限重跑为fail），未认定为安装链路通过，未改动Runtime掩盖失败。日志与quick报告保留于`/tmp/sdlc-skill-format-20260909/`。

# SDLC v2 审查专项修复（2026-09-09）

## 摘要

本次接续 `31c6627c34e31068e35f739fe6457346b5bd7f8c`，不重新实现全部 v2。GitHub 读写预检已写入并回读 #22 评论5601077221。旧实施 PR #22 关闭但未合并、未删分支；新实施 PR #23 接续全部 v2。实验室 #20 保留原三轮来源。

正式修复提交：`f8b4765e46fd440d8e95d0c065b5ccc7b115b0af`。此后的源码运输清理和 CI 配置提交不冒充该提交的原始测试记录；新的 CI 会再次绑定实际 HEAD。

## 修复内容

| 问题 | 实现 | 回归 |
|---|---|---|
| VFY 被未来 RLS 检查阻塞 | check_phase/through_phase 按任务所属阶段取检查；RLS 关闭仍检查本阶段条件；错误的 convergence 所属阶段在生产端拒绝 | test_review_fixes；test_review_delivery_live 实际 VFY→RLS |
| 产品写入丢执行位 | 产品 atomic_write 保留 mode；task.write 支持 executable；观察/指纹/ZIP/独立回读纳入 mode | wrapper 真执行、chmod 指纹、ZIP 模式篡改、原生交付 |
| 共有 Run 状态变化阻止交回 | 稳定身份严格比对；可变执行观察保留目标状态并归档来源；不导入执行权限；冲突在外层如实返回 | clone→源取消→副本导出→collect，原目标状态及来源观察均保留 |
| 大历史附件拖垮产品交付 | 产品 ZIP 保留附件索引和必要验证结果，完整原始材料进独立 workspace 归档；draft asset.unlink 保留旧历史 | 同一需求携带68MiB输入完成原生本地RLS，产品包<2MiB，归档保留两份34MiB原件 |
| 阅读投影是 JSON | 六阶段 Markdown、来源/覆盖/任务/结果表及安全HTML；机器身份仍可定位 | 可读投影和共享正文验证 |
| sdlc-github 被删除 | 一个可选 Skill，复用同一 Runtime/Store；preview/publish/status/reconcile；当前已提交产物→已有Issue评论 | 10项模拟API协议测试、真实安装副本12次CLI请求及实际评论读回 |

本次没有恢复旧v1的全部32项GitHub操作。当前能力聚焦已有Issue的阶段Markdown快照，不写仓库文件、不创建分支、不自动merge/deploy。仅共享失败不会改变业务Run状态。

## 已完成验证

- 本地 Linux：portable 100/100，106.045秒，0failure/error/skip；这是有记录的修复工作树测试，不伪装为clean远端HEAD。
- GitHub Actions运行 [34351040098](https://github.com/ousui/sdlc-ai-spec/actions/runs/34351040098)：实际被测源码 `f8b4765e46fd440d8e95d0c065b5ccc7b115b0af`。macOS full **178/178，94.776秒**，0failure/error/skip；机器契约、10入口、唯一Runtime检查和安装包构建通过。Ubuntu portable套件通过，单独计数，与178有重叠。
- 通过Actions源bundle取回后，将43个改动文件与本地验证版本逐字节比较，0差异。
- 真实GitHub运行 [34351132793](https://github.com/ousui/test-sdlc/actions/runs/34351132793)，实验室源码 `bf0ce1c2b55a69f797bf6d047cba1df527406b96`，安装Runtime同为f8b4765。12次公共CLI请求，真实POST、GET、相同快照重复发送、reconcile及工作区导出全部成功。
- 实际评论：[test-sdlc#21](https://github.com/ousui/test-sdlc/issues/21#issuecomment-5601819414)。重复发送复用5601819414，没有多发评论。使用合成需求与Actions标准Issue权限，没有真实项目材料。
- 实现仓库关闭了Issues，创建返回410；没有修改仓库设置。共享目标可使用启用了Issues的实验室或团队仓库。

178 = 原159 + 审查7 + GitHub协议10 + 原生交付2。历史九条Agent业务链未在本次重跑，既有数字不改标为本次通过；真实Issue集成也不等于原生客户端自然语言发现认证。

## 原失败保留

源码运输中间提交不是Runtime候选。首次 materialization Run34350564138因测试辅助文件末尾空行在git diff --check失败；已修正实际文件，不关闭检查。临时patch分片及自写入workflow在收口时移除，正式树只保留源码与普通只读测试workflow。

## 用户试用与待本地验证

用户指南在根级 [USAGE.md](../../../USAGE.md)，包括完整六阶段提示、各产物位置、失败恢复、复制交回、Issue分享和Podman命令。

当前原生命令收集器仍为macOS Seatbelt。Linux机制套件通过不是Linux/Windows完整业务执行支持。用户本机Podman VM、客户端插件加载/自然语言路由、真实业务项目和中等推理新会话，需在用户环境实际试用；没有访问用户本机Podman，也没有声称替代这些试用。

建议先用新会话在隔离业务副本跑一个普通需求，再用 `/sdlc-github 帮我将当前产物发送至 <Issue URL>` 分享。客户端应自行从Store选定需求、预览、发布并返回comment_url，不让用户手写UUID或SQL。

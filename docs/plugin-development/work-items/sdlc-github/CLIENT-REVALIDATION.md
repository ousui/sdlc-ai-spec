# sdlc-github 修复后定向真实复验

本批次 `sdlc-github-revalidation-20260906T140413Z` 已完成可执行项，整体 **FAIL，保留 BLOCKED**。实际生产读取与唯一评论通过；本地 full 失败和宿主网关阻塞均保留，未移植历史 PASS。

- Runtime：`9491c0ef7d9d017d666cca71917e1c3679346824`。
- 初始本地 HEAD：`f0c32a06cb65a4718486ab23e7aad95b71df7791`；干净快进后执行 HEAD：`b7863a925e11294400a3faf65d48f965d5391ab6`。
- 实施分支：`impl/sdlc-github-foundation-v1`；已验证当前仓库的远端身份；精确连接地址保留在原始外部证据中，不作为源码内连接配置。Runtime 到执行 HEAD 仅 4 个本工作包文档；本报告只新增 md/json。
- 已包含 main `7a454c76b62c41525fa3990dffdaa9a52b975679`。[PR #14](https://github.com/ousui/sdlc-ai-spec/pull/14) 实测 open / Draft。
- 最终报告提交与 push 后的准确 HEAD 见外部 `DELIVERY.json`，在本报告提交后生成，避免提交 SHA 自引用。

## 真实逐项结果

所有功能结果来自新版安装副本的生产 stdio Server → 固定官方 GitHub Remote MCP；参数均经该副本 `scripts/run` 编译。实际 actor 为 `ousui / 2839512`。

| 项目 | 结果 | 实际观察 |
|---|---|---|
| status | PASS | 8 个工具；32/32 能力可用 |
| issue.list：省略 state | PASS | #5、#4；每页 1 条，两页完整 |
| issue.list：open | PASS | 实际 0 条，完整；未声称验证了非空 open Fixture |
| issue.list：closed | PASS | #5、#4，均 CLOSED；两页完整 |
| issue.list：all | PASS | #5、#4；两页完整，结果与省略一致 |
| actions.run / jobs | PASS | Run `34021751640` 有效；Job `101455494899`，run_id 匹配，total_count=1，完整 |
| Issue #5 非空普通评论 | PASS | confirmed，Runtime 读回通过；另一次只读查询精确匹配正文、批次、UUID 和作者 |
| repo.tag：轻量 Tag | BLOCKED | 既有 Fixture 未提供准确 Tag；授权仓库 tags 首页面为空且 completeness=unknown |
| repo.tag：附注 Tag | BLOCKED | 缺准确既有 Fixture；未创建 Tag/Release、未扩大权限 |
| 原 unknown 只读核对 | PASS（保护语义） | reconcile 前后均 unknown，效果仍未解决；没有重新 create |
| 既有 confirmed 回执核对 | PASS | Issue #5 原创建请求保持 confirmed、原 URL 和回执 |
| 安装后 launcher 编译 | PASS | 安装器生成绝对解释器绑定，锁定依赖 READY，共享合约路径存在 |
| 实际宿主冷启动 | BLOCKED | Claude Code 2.1.263 两次模型网关 HTTP 522；第二次已连接新版 MCP，尚未执行 launcher |

评论：[Issue #5 / comment 5559783775](https://github.com/ousui/sdlc-ai-monitor/issues/5#issuecomment-5559783775)。新 request_id `fb8bf197-2e9c-4bfe-8867-f8c255c3f4e6` 在发送前 fsync 保存；仅一次写工具调用，评论留痕。独立评论列表的 completeness 为 unknown，只证明目标评论匹配，不宣称完整评论历史。

原请求 `56de6913-edfc-4beb-bc98-a0f0265b7be5` 使用原 actor、仓库和稳定 `data/live`。原 9 个状态文件内容、inode 全部保留，仅新增该请求的 1 个只读观察及本次评论的 intent/receipt。没有迁移、清空、删除、归档重建或将 unknown 改记 none。

## 本地 full 与失败复现

干净 `b7863a9` 上仅执行一次 `tools/validate.py --profile full`，exit **1**：1206 个唯一测试执行，1163 个成功 ID、43 个未成功 ID；46 个 failure 事件、6 个 error 事件（含 subTest，不能相加充当未成功测试数），无 skip。未重复私有套件或 full。

7 项结构检查通过。IMP 82、RLS 87、Status 14 的绑定通过；VFY 80 为 portable contract 测试，strict/e2e 未运行。

失败集中于 `tests/skill_github/test_offline.py`：Fixture 保留 `TemporaryDirectory()` 的 `/var/folders/...` 路径，遇到 `/var` 符号链接，被 descriptor / O_NOFOLLOW 校验拒绝。最小复现对同一个临时目录只读打开：原路径报 `NotADirectoryError / errno 20`，解析后的 `/private/var/...` 成功。保留原 full 失败及准确测试 ID，交 Web Review 检查测试入口/Fixture；本轮没有放宽安全校验或修源码。

实际使用原专用 venv **Python 3.14.7**，完整锁定依赖匹配；这与 INSTALL 所列 3.12/3.13 不同，作为环境差异保留。未安装依赖，未改用系统 python3。新安装路径位于仓库外 `/private/tmp`，与原稳定数据根分离。

宿主首轮 bare 模式发现新版 Skill，但未加载插件 MCP；第二轮正常插件模式发现准确安装路径并连接 8 工具，均在模型网关 522 后退出 1，没有 Skill 工具调用。此证据只证明实际 Discovery / MCP 连接，不证明宿主执行了 launcher。文件哈希不变仅证明内容未改，不能证明宿主未扫描元数据。三端独立认证仍为 OUT_OF_SCOPE。

## 外部证据与唯一下一工作包

持久交付目录：`~/Workspace/goedge.cloud/sdlc-github-foundation-delivery/sdlc-github-revalidation-20260906T140413Z-delivery/`。

- 入口：`EVIDENCE-INDEX.json`、`RESULTS.json`；提交完成信息：`DELIVERY.json`。
- 证据包：`sdlc-github-revalidation-20260906T140413Z-evidence.tar.gz`，SHA256 `89706c527e6b68c98d0c2b34c7ad94e73f51f1ef84d1b8c9c86961ff10826f96`。
- 包内包括生产调用及编译输出、评论读回、状态保留审计、安装清单、两次真实宿主失败、full 原始结果与测试 ID、最小路径复现；凭据匹配审计为零。原稳定 data 和宿主配置状态不入包。
- 临时目录 `/private/tmp/sdlc-github-revalidation-20260906T140413Z` 保留供复查；长期证据已复制到上述仓库外交付目录。旧失败、旧 Goal 与历史日志仍按现有 ARCHIVE 索引保留，未作为新版本 PASS。

**唯一下一工作包：Web Review**，审查本批次 full 的 macOS Fixture 复现及两类 Tag / 宿主执行阻塞，决定后续修复或补证范围。旧 unknown 持续仅允许原 UUID 的只读核对。本次交接登记在这两份紧凑报告内；不改其他工作包、不进入实现阶段；PR #14 继续 Draft，不 merge、Tag、Release 或强推。

## 报告规范化说明

仅移出远端连接地址，不改 Runtime SHA、批次、计数、PASS/FAIL/BLOCKED、归档摘要或状态保护记录。未规范化原文固定保存在提交 `d271a27c98e178c9eba95ca44ac3ab96a0d477fe`；本轮原始外部归档及其 SHA256 不变。这项说明不将旧 full 失败改写为成功。

# sdlc-github — 实现记录与追踪矩阵

## 批准与本轮边界

批准来源为 Maintainer 指定的准确设计提交 `97c5f17bfcdb2751d446a89b068db2400436631d`。本轮按新的用户指令完成代码和 Mock 验证，不使用聊天中曾提供的真实 Token，不执行真实业务仓库读写。代码、测试和安装工具均在本工作包的独立分支；源码提交和文档交付提交分别记录于 WEB-VALIDATION / HANDOFF。

先前对话提到的本地实现与测试数字未作为本候选依据。本环境从可核验的 `33f76366ac1203a875fa8763f2f79300f47d96c1` 恢复后构建并重新运行。

## 完整生产链路

`SKILL.md` → 共享参数解析器/离线 invocation compiler → 宿主原生 MCP 工具批准 → `scripts/sdlc_github_mcp.py` → `GithubService` → `OfficialTransport` → 官方 SDK Streamable HTTP → 固定 GitHub MCP URL。

生产代码没有 Fake 开关、任意 endpoint/tool/method/header 参数、REST fallback、自动登录或自动依赖安装。Fake 依赖注入只在 tests 的子类中使用，安装包排除全部测试代码。`status/read/operation_status` 与五个独立写工具共享同一 Service。

写入在持久 intent 成功后发送；同 actor/repository/request_id 冲突校验、exclusive claim、原子回执、崩溃窗口 unknown、只读核对都已实现。确认远端变更但读回/存储失败保持 confirmed/partial；发送状态不明不说“未执行”。创建类正文使用 UUID marker，更新类保存所需字段摘要而非私有正文；不是跨不同 UUID 的全局 exactly-once，也不声称跨请求事务。

## 32 操作全集

每行有独立固定输入/期望映射 `tests/skill_github/oracle.py`，不是从生产操作表反向自动生成 Oracle。列出的测试是候选的程序覆盖；真实远端状态统一为 NOT_RUN，最终结果以 WEB-VALIDATION 的准确源码 SHA 为准。

| # | Operation | Upstream tool | 固定 method | 类型 | 程序覆盖 |
|---|---|---|---|---|---|
| 1 | `repo.files` | `get_file_contents` | `—` | 读 | mapping / 403 / upstream error / schema drift / stdio success |
| 2 | `repo.branches` | `list_branches` | `—` | 读 | mapping / 403 / upstream error / schema drift / stdio success |
| 3 | `repo.commits` | `list_commits` | `—` | 读 | mapping / 403 / upstream error / schema drift / stdio success |
| 4 | `repo.commit` | `get_commit` | `—` | 读 | mapping / 403 / upstream error / schema drift / stdio success |
| 5 | `repo.tags` | `list_tags` | `—` | 读 | mapping / 403 / upstream error / schema drift / stdio success |
| 6 | `repo.tag` | `get_tag` | `—` | 读 | mapping / 403 / upstream error / schema drift / stdio success |
| 7 | `issue.list` | `list_issues` | `—` | 读 | mapping / 403 / upstream error / schema drift / stdio success |
| 8 | `issue.get` | `issue_read` | `get` | 读 | mapping / 403 / upstream error / schema drift / stdio success |
| 9 | `issue.comments` | `issue_read` | `get_comments` | 读 | mapping / 403 / upstream error / schema drift / stdio success |
| 10 | `pr.list` | `list_pull_requests` | `—` | 读 | mapping / 403 / upstream error / schema drift / stdio success |
| 11 | `pr.get` | `pull_request_read` | `get` | 读 | mapping / 403 / upstream error / schema drift / stdio success |
| 12 | `pr.diff` | `pull_request_read` | `get_diff` | 读 | mapping / 403 / upstream error / schema drift / stdio success |
| 13 | `pr.files` | `pull_request_read` | `get_files` | 读 | mapping / 403 / upstream error / schema drift / stdio success |
| 14 | `pr.reviews` | `pull_request_read` | `get_reviews` | 读 | mapping / 403 / upstream error / schema drift / stdio success |
| 15 | `pr.review-comments` | `pull_request_read` | `get_review_comments` | 读 | mapping / 403 / upstream error / schema drift / stdio success |
| 16 | `pr.comments` | `pull_request_read` | `get_comments` | 读 | mapping / 403 / upstream error / schema drift / stdio success |
| 17 | `pr.checks` | `pull_request_read` | `get_check_runs` | 读 | mapping / 403 / upstream error / schema drift / stdio success |
| 18 | `pr.status` | `pull_request_read` | `get_status` | 读 | mapping / 403 / upstream error / schema drift / stdio success |
| 19 | `actions.workflows` | `actions_list` | `list_workflows` | 读 | mapping / 403 / upstream error / schema drift / stdio success |
| 20 | `actions.runs` | `actions_list` | `list_workflow_runs` | 读 | mapping / 403 / upstream error / schema drift / stdio success |
| 21 | `actions.jobs` | `actions_list` | `list_workflow_jobs` | 读 | mapping / 403 / upstream error / schema drift / stdio success |
| 22 | `actions.artifacts` | `actions_list` | `list_workflow_run_artifacts` | 读 | mapping / 403 / upstream error / schema drift / stdio success |
| 23 | `actions.run` | `actions_get` | `get_workflow_run` | 读 | mapping / 403 / upstream error / schema drift / stdio success |
| 24 | `actions.logs` | `get_job_logs` | `—` | 读 | mapping / 403 / upstream error / schema drift / stdio success |
| 25 | `release.list` | `list_releases` | `—` | 读 | mapping / 403 / upstream error / schema drift / stdio success |
| 26 | `release.get` | `get_release_by_tag` | `—` | 读 | mapping / 403 / upstream error / schema drift / stdio success |
| 27 | `release.latest` | `get_latest_release` | `—` | 读 | mapping / 403 / upstream error / schema drift / stdio success |
| 28 | `issue.create` | `issue_write` | `create` | 写 | mapping / 403 / upstream error / schema drift / stdio success |
| 29 | `issue.update` | `issue_write` | `update` | 写 | mapping / 403 / upstream error / schema drift / stdio success |
| 30 | `comment.create` | `add_issue_comment` | `—` | 写 | mapping / 403 / upstream error / schema drift / stdio success |
| 31 | `pr.create` | `create_pull_request` | `—` | 写 | mapping / 403 / upstream error / schema drift / stdio success |
| 32 | `pr.update` | `update_pull_request` | `—` | 写 | mapping / 403 / upstream error / schema drift / stdio success |

## 文件职责

| 落点 | 责任 |
|---|---|
| packages/sdlc_github/{models,operations,targets}.py | 固定请求/结果契约、映射、目标解析与脱敏 |
| packages/sdlc_github/{transport,service}.py | 唯一官方 MCP 网络链路、身份/目标/读回/结果处理 |
| packages/sdlc_github/records.py + packages/sdlc_runtime/local_paths.py | 安全持久化、claim、原子保存、去重及恢复 |
| scripts/sdlc_github_mcp.py | 唯一生产 stdio Server 与精确依赖检查 |
| skills/sdlc-github/** | 中文 SOP、显式入口、共享解析、元命令、source lock |
| skills/_shared/{contracts/github-runtime.md,schemas/github-result.schema.json} | 独立非 Phase 共享契约 |
| config/github/** + 三个 manifest | 仅宿主语法差异，无业务复制 |
| tools/install_sdlc_github.py | 显式路径绑定安装副本、打包排除、依赖/摘要检查 |
| tests/skill_github/{fake_backend,fake_http,stdio_bridge}.py | 仅测试用合成上游、真实 HTTP 服务和依赖注入 |
| tests/skill_github/test_*.py | 固定单元、安全、安装、协议、Client 控制器验证 |
| tests/skill_github/{validate,client,native_evidence}.py | 固定验证入口、真实连接批次、原生证据检查器 |

## 共享改动的必要性

1. AGENTS、skills/AGENTS、DEVELOPMENT、skill-execution 仅添加明确 GitHub transport 的联网例外；其他 Phase 不得导入或借用 GitHub Runtime 绕过旧边界。
2. Runtime Independence 扫描只对白名单精确文件的 httpx import 开例外；任意别处 httpx 或该文件内 socket 仍被测试拒绝。现有 Phase 的 Oracle 未删除。
3. 已有 source-lock 仅更新被修改共享契约的摘要，以及 status 对新共享 local_paths 文件的闭包。VFY/RLS 专用锁结构保持原样；不改领域规范或 Phase 执行语义。
4. 原生兼容性旧台账保留 8 个既有 Skill/40 个历史证据条目；`sdlc-github` 作为显式扩展独立检查，不把历史宿主 PASS 移植给新 Skill。
5. CI 显式准备固定依赖，新增测试被 unittest discovery 与固定入口实际收集；原有 Skill 不因缺 Token 失效。Source Lock 汇总加入第 9 个正式 Skill。
6. `.gitignore` 和安装器排除 .local/.cache；不改 ArtifactStore 或 .sdlc/store.sqlite3。

## 评测层与观察限制

A 为确定性 Service/参数/安全/控制器测试，B 为真实 stdio/loopback HTTP 和剥离 docs/tests 的安装执行；这两层能在 Web 执行。C 的真实身份、实际仓库权限、Hosted schema、网络故障和真实 GitHub 写读回，以及 D 的三端原生发现/显式触发/拒绝/重启/工作区行为，按用户要求留到本地。

Native evidence validator 检查绑定、字段与原始 trace 摘要，不是原生宿主模拟器，更不是不可伪造的执行证明。新上下文 Web Review 必须检查本地真实 transcript，不能只看某个 JSON 自述 PASS。

只要真实 C/D 未运行，工作包整体保持 Draft / 未接受。固定代码与 Mock 验证交付完成，不意味着 final acceptance、main 合并或发布授权。

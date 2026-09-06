# Client Goal — 修复后的定向真实复验

使用 `ousui/sdlc-ai-spec` 的 `impl/sdlc-github-foundation-v1`，PR #14 保持 Draft。准确 Runtime SHA：`9491c0ef7d9d017d666cca71917e1c3679346824`。已合入 main@`7a454c76b62c41525fa3990dffdaa9a52b975679`；不要再用 b035880 的旧源码或归档 Goal。

先读取当前 AGENTS.md、docs/TESTING.md、工作包 REPAIR-RESULT.md 和 INSTALL.md。通过当前已验证的远端 fetch 此分支；保留未知工作树内容。若 HEAD 比 Runtime SHA 新，确认差异仅为本工作包交付文档；发现代码变化先停下核对，不自动 merge、rebase、reset、强推。保持本分支，不进入 main。

复用本地安全环境中的 Token、原稳定 data/live 和旧回执；不打印或保存 Token/Hash。macOS 使用既有目录的真实绝对路径，不放松符号链接校验。用锁定依赖的 Python 和安装器新建一个版本化安装副本，data-root 指向原稳定根。参数编译只使用安装后的 `skills/sdlc-github/scripts/run`，不改用系统 python3；生产调用走 scripts/sdlc_github_mcp.py 和官方 Remote MCP，无 REST/连接器替代 Oracle。

只做以下定向复验，不原样重跑旧 live 全写入批次：

1. status 核对实际 actor 与 32 个能力；issue.list 分别省略 state、open、closed、all，验证映射与分页；actions.jobs 使用已授权仓库 ousui/sdlc-ai-monitor 的准确既有 Run 34021751640（先只读核验仍有效），核对嵌套列表、Job/run_id 与完整性。
2. 在本工作包自己创建的 Issue #5 上，明确执行一次带本轮标记的非空普通评论并读回。首次发送前保存新 request_id；它是独立的新评论任务，绝不是旧 unknown 请求的重试。发生 unknown 立即停止后续写入，只读核对，评论留痕不删除。
3. repo.tag 分别读取已存在的轻量/附注 Tag，严格核对 selector；仅使用已授权仓库。没有相应 Fixture 或权限就记 BLOCKED，不创建 Tag/Release，不扩大 Token 权限。
4. 原未知请求 `56de6913-edfc-4beb-bc98-a0f0265b7be5` 只能以原 actor/仓库/request_id 调用 operation_status（含显式 reconcile=true）。先确认使用原真实数据根；不要从历史证据拷贝重建活动 intent。禁止重新调用 create、换 UUID 重发、删除 intent，或因查无标记把 unknown 改记 none。既有 confirmed 回执的只读核对失败也必须保留原 effect、URL/receipt。
5. 通过一个实际使用的宿主做 launcher 冷启动反馈，不额外提示替代解释器/错误合约路径。缺 Cursor/Claude/第二账号不阻塞这次定向任务。main 已暂停三端原生认证门禁；不生成虚构证书。不扫描工作区查解释器；哈希不变仅证明文件内容未变，不证明没有扫描。

如需本地环境完整回归，只运行一次仓库统一入口，不再叠加子套件：
`"$PY" -B tools/validate.py --profile full --source-sha "$(git rev-parse HEAD)" --json-out /absolute/outside/github-repair-full.json`
要求当前 exact HEAD 干净，结果写仓库外。full 不声称 strict/e2e 的 OS 沙箱执行。已有真实失败、unknown 和日志不得覆盖；新证据放新的输出目录，稳定 data 不迁移或清空。

全部可执行项结束后，记录准确 Runtime SHA、起止 HEAD、实际 actor、操作/退出码、评论 URL、old unknown 状态及 PASS/FAIL/BLOCKED/NOT_RUN。源码内仅提交本工作包紧凑 CLIENT-REVALIDATION.md/json 与外部证据索引和摘要，不提交长日志、凭据、运行态或 10,000 文件工作区。允许 commit/正常快进 push 本分支；不得改 main/其他工作包、merge PR、tag/release 或扩大权限。遇程序缺陷保存最小失败证据交回 Web Review，不绕开安全校验或移植旧 PASS。

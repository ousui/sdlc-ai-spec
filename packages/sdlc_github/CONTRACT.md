# SDLC GitHub Package

唯一业务入口为 `GithubService(data_root).handle(tool, payload)`；唯一生产网络实现为 `OfficialTransport`，通过官方 Python MCP SDK Streamable HTTP 访问 `https://api.githubcopilot.com/mcp/`。模块导入、创建 Service、stdio initialize/tools/list 均不联网。显式在线调用才读取已绑定进程 Token 并核验身份。

`operations.py` 固定 27 读 / 5 写操作，`models.py` 定义稳定结果与脱敏，`records.py` 持久去重，`targets.py` 只做本地目标解析。构造器的 transport/fault 注入面用于开发测试，不作为生产 MCP 或命令行字段暴露。

单个请求默认 60 秒，无自动写重试；wire 响应最多 8 MiB，普通结果最多 256 KiB、Diff/日志最多 1 MiB（包括 JSON 转义预留），超出明确 partial。仅处理身份压缩，异常压缩响应失败关闭。日志截取尾部，Diff 截取前部，均不声称完整。获取更多内容由调用方明确发起。

上游 isError、缺 ID/URL、错误对象、非法 JSON 与 schema 漂移不返回成功。确认写入但读回或落盘失败保留 confirmed/partial，发送后无法确定则 unknown。进程崩溃不重放已有 claim。回执写入采用 0700 目录、0600 文件、O_NOFOLLOW、独占创建、fsync 和原子不覆盖发布；JSON 内容摘要可发现意外损坏，不是抵抗同用户篡改的签名。

依赖精确锁在 `requirements.lock`；安装者在独立 Python 环境显式执行 `python -m pip install --require-hashes -r <plugin-root>/packages/sdlc_github/requirements.lock`。运行入口用 importlib.metadata 检查整个固定组合，不自行下载安装。Python 3.12/3.13 + POSIX 是首版构建目标；此候选在 Python 3.13 的 Linux 环境进行程序验证，macOS 与宿主原生执行另行取证。

真实 Token、认证 Header、私有正文不进入诊断或写回执。读取结果中的正文是用户本次请求的数据，不默认为公共材料；调用方归档或发布时仍需独立内容授权。精确 Token 和常见凭据模式会脱敏，不宣称识别所有秘密。

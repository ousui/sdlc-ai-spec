# sdlc-github — 验证计划

Design：`sdlc-github-foundation/v1`。本文件定义 Oracle 和验收条件，不记录执行成功。所有结果在实际运行后写入独立的 EVAL-RESULTS；初始均为 NOT_RUN。

## 1. 验证分层

| 层 | 执行位置 | 准确含义 |
|---|---|---|
| A：确定性程序 | Web 优先 | parser、Service、schema、存储、映射与错误处理 |
| B：协议与安装 | Web 优先 | 真实 stdio 进程 → 测试专用 Fake HTTP MCP；剥离 docs 的安装副本 |
| C：真实 GitHub | Web 有条件执行，否则一次 Client 批次 | PAT、实际工具、远端副作用和读回 |
| D：真实宿主 | Web 有条件执行，否则同一次 Client 批次 | Codex、Cursor、Claude Code 的真实安装、发现、显式调用、批准和行为 |

Fake 只能证明 A/B；公开网页读取或 ChatGPT GitHub Connector 不能代替 C；自行写一个 MCP Client 不能代替 D。

生产上游固定。Fake 服务地址只通过测试代码的依赖注入提供，不给生产入口增加任意 endpoint 开关。Fixture 不包含真实 PAT。全量仓库回归默认不访问 GitHub，也不要求本地真实客户端存在。

## 2. 固定验收项

| ID | 验收对象 | Oracle / 通过条件 |
|---|---|---|
| GH-01 | Skill 风格与发现 | 名称 sdlc-github；显式触发；共享 parser；元命令和 source-lock 完整；非 Phase 支撑类别正确 |
| GH-02 | 参数语法 | 全部声明命令/参数/别名、冲突、缺值、未知项均有准确结果；help 无扫描/网络/落盘 |
| GH-03 | 实例身份 | 两个进程注入不同 PAT 后看到各自真实身份；expected_actor_id 错配零写入；重启后新身份不复用旧回执 |
| GH-04 | 认证与错误 | 缺 PAT、401、403、404、429、超时、断连分开报告；不自动登录/重试写入/泄露秘密 |
| GH-05 | 工具暴露 | 只有8个声明工具；32个业务 operation 的映射全集与设计表一致；不存在 raw tool/API 执行入口 |
| GH-06 | 全部只读映射 | 27个 operation 逐个构造固定输入，核验准确上游 tool/method/参数和正常/失败响应 |
| GH-07 | 全部写入映射 | 5个 operation 逐个核验准确对象、请求字段、结果 ID/URL及读回；参数越界零写入 |
| GH-08 | URL 与目标 | 支持 URL正确解析；repo 冲突、多remote、斜线ref歧义、编码逃逸、非github.com均不猜测 |
| GH-09 | 创建 Draft PR | 已存在不同 head/base；固定 draft=true；无分支创建、push、merge或额外评审操作 |
| GH-10 | 更新对象语义 | Issue/PR 类型不能串用；省略字段保持；显式空正文按约定清空；仅open/closed |
| GH-11 | 权限边界 | 无写入意图时 Skill 请求确认；deny/dry_run零远端写；宿主拒绝后无效果；自述approved不构成授权 |
| GH-12 | 分页与截断 | 逐页结果可继续；缺next信息保持unknown；Diff/日志超限partial；不能把截断当完整审阅 |
| GH-13 | 结果 schema | 8工具全部使用准确 input/output schema；structuredContent和文本同义；上游isError不被当成功 |
| GH-14 | 上游 schema 漂移 | 所需tool/参数缺失阻断该operation；无关新增tool不自动暴露；非兼容变更不能静默映射 |
| GH-15 | 重复请求 | 同request_id相同参数只发一次写调用；不同参数返回冲突；不同actor隔离 |
| GH-16 | 崩溃窗口 | intent前、发送前后、收到成功后/receipt前分别注入崩溃；不确定时unknown；无自动重放 |
| GH-17 | 只读核对 | 唯一标记且对象属性相符才补齐；分页未完、标记缺失、多候选和权限变化保持unknown |
| GH-18 | 文件安全 | 绝对数据根；目录逃逸、symlink、非法对象、只读盘、损坏JSON、重复独占创建均有确定结果 |
| GH-19 | 状态与缓存 | 删除.cache不改变.local；重启保留未完成intent；安装路径改变但数据根不变仍能读回 |
| GH-20 | 秘密与诊断 | 已知PAT及典型敏感输出不进入stdout诊断/文件/回执；stderr脱敏；不上传私有正文或认证配置 |
| GH-21 | Runtime Independence | 已装依赖的副本删除docs/开发AGENTS/tests后，生产入口仍能通过指定Fake协议用例 |
| GH-22 | 回归与依赖 | 既有接口/锁/validator/单元测试通过；没有GitHub配置时原有Skill仍可用；依赖缺失准确阻断且不自动安装 |
| GH-23 | 真实上游覆盖 | 32业务operation逐项登记真实输入/响应/目标；所有写入在授权测试范围内并读回；缺fixture为BLOCKED而非PASS |
| GH-24 | 三端原生与持久验证 | 三端同一runtime SHA，完成发现/调用/拒绝/写读回/重启；大型固定工作区不误扫描、不污染业务代码 |

GH-06/07 是参数化全集，不允许只挑一个代表 operation。GH-24 逐宿主分别列结果，不能用其中一端替代其余两端。

## 3. 真实 GitHub Fixture 与授权

一个获准测试仓库应提供：可读代码与分支、Issue、PR、Actions Workflow/Run/Job、Release Tag。空列表可以证明列表接口返回正确，但不能替代单对象get、日志或分页用例。

本Skill只能在已有分支上创建Draft PR。测试准备阶段若需要构造代码分支、workflow、Release等Fixture，由外层测试任务在明确授权的测试仓库和命名范围内完成，不能把这些准备能力加入生产Skill。已有Fixture优先；缺准备权限时集中列出一次输入要求。

测试写入使用统一前缀与run ID，仅处理本次创建的Issue、PR和评论。通过本期update将测试Issue/PR关闭可作为清理，不删除他人资源。评论不删除，保留可审计标记。若只读凭据不能完成写用例，则该凭据只证明只读范围。

测试前一次性明确仓库、现有head/base、允许创建/更新/评论/关闭的对象范围。宿主对该范围的原生授权由用户决定，测试程序不得自动扩大宿主权限。三端可使用不同账户；结果比较规范化业务字段，不比较模型措辞、真实账号ID或生成的对象编号。

## 4. 持久与并发工作区

客户端使用独立长生命周期工作树及数据根，运行生成器准备不少于10,000个可重建文件，不以真实大型仓库的无关内容作为测试材料。以固定数量的读/写/重启/故障序列验证，不进行无限轮询或无界压力测试。

必须覆盖两个进程竞争同一个request_id、写入后进程退出、SDK上游会话断开、安装副本路径改变、清除cache和Token更换。复核代码工作树无未授权修改，检查.local保留真实状态。规模测试目的是路径和恢复正确性，不宣称基准性能提升。

## 5. 一次交接所需的证据

每个结果记录：Case ID、准确运行时源码SHA/文件摘要、客户端及版本、依赖锁摘要、输入Fixture、实际输出、上游调用计数、实际对象URL、退出码、status及证据路径。脱敏前的认证内容不归档。

结果枚举：PASS、FAIL、BLOCKED、NOT_RUN；不得将SKIP计入PASS。报告区分代码HEAD、被测源码SHA和纯文档交付SHA；最后追加文档不能让测试自动覆盖新源码。

Web交付：WEB-VALIDATION.md/json、安装/协议检查、测试入口、CLIENT-GOAL.md。
Client交付：CLIENT-VALIDATION.md/json、各宿主单独的行为结果、脱敏日志与SHA256清单。
Web Review交付：WEB-REVIEW.md，包含独立反例、修复差异及重跑范围。

## 6. 运行入口要求

实施提供一个固定验证入口，能够分别执行offline、integration、native和完整client批次；使用选项选择测试层，不提供生产Provider替代通路。Web在CLIENT-GOAL.md中写入实际可执行命令，不留需要用户补写的脚本。

仓库基础回归仍包括：

```bash
python3 -m compileall packages scripts
python3 tools/validate_runtime_contracts.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
git diff --check
```

新增测试必须被明确入口收集；测试目录存在不代表已被unittest discovery执行。依赖准备只能在获准构建/测试环境中完成，生产启动不安装依赖。

## 7. 完成与阻塞

本期接受必须满足DESIGN第9.4节。无真实客户端或安全可用PAT时，Web应完成所有可执行的A/B层再交接；Client不能因Web缺少环境被要求补写主体实现。

一次Client Goal与一次Web Review是工作批次目标，不是覆盖证据不足的理由。若最终源码仍有必须真实宿主复验的修复，报告准确缺口并保持Draft；不把历史PASS移植到未测版本。

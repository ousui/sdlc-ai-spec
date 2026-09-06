# 新会话执行提示词：sdlc-github 基础能力实施

以下内容作为新会话的用户任务。发送本提示词表示批准本工作包的DESIGN与EVAL-PLAN，并授权在独立实施分支执行本次实施、程序评测和三个顺序适配子阶段；不授权合并main或发布版本。

---

你负责 `ousui/sdlc-ai-spec` 的 `sdlc-github-foundation/v1` 实施与首次验证。本会话在Web Chat中完成主体工作，只有真实本地宿主或持续长任务确实无法完成时才交接一次Client Goal。

## 权威输入

先通过GitHub连接器读取并核验：

- 设计分支：`design/sdlc-github-foundation-v1`。
- Work Item：`docs/plugin-development/work-items/sdlc-github/`。
- `DESIGN.md`、`EVAL-PLAN.md`、`HANDOFF.md`。
- 当前根与相关目录AGENTS、DEVELOPMENT、共享接口、共享执行合约和现有sdlc-status样式。

完整设计入口：
`https://github.com/ousui/sdlc-ai-spec/tree/design/sdlc-github-foundation-v1/docs/plugin-development/work-items/sdlc-github`

解析并记录本次实际DESIGN_HEAD_SHA。设计审查基线为 `9d9dbf8bc1b9241f80af53cdf5b0426fcbfe3ab9`，但不能把它冒充当前main或设计HEAD。只以本工作包文件定义实施范围，不从旧会话或其他设计包增加需求。

## Git 与写入范围

1. 从核验过的DESIGN_HEAD_SHA创建 `impl/sdlc-github-foundation-v1`，保持独立工作树和Draft PR。
2. 若分支或对应PR已存在，先核验Owner、父提交和工作包，确认属于本任务才能续跑；不得覆盖或强推。
3. 允许本分支上的commit、push、创建/更新该工作包Draft PR及其交付说明。使用当前明确Git身份；不能伪造签名或批准。
4. 运行时代码仅限设计第8节的落点，及接入所必要的manifest、共享接口/执行边界、validator、source-lock、依赖锁、打包排除和测试。
5. 本次工作包Handoff写在自身目录；不抢写根级共享HANDOFF，不改变其他阶段或并行工作的状态。main及其他开发分支保持不变。
6. `docs/v1.x/**`、现有ArtifactStore及各Phase业务语义保持原样。公共文件只作设计要求的有限增量；不得顺手重构或降低旧Oracle。

本提示词允许在同一Web会话顺序完成本工作包的implement → evaluate → 三端适配准备。每一步保存可辨识结果；独立Review留给fresh-context会话。修改工程规则时明确本工作包的网络边界，不把例外扩展到全部Runtime。

## 要交付的实现

完整实现设计规定的一个Skill、一个共享Package、一个stdio MCP Server、8个MCP工具、27个只读操作和5个写操作。

唯一生产链路：共享Runtime → 官方GitHub Remote MCP。PAT仅从 `SDLC_GITHUB_TOKEN` 注入；每实例一个身份；数据根准确绑定，其下使用.local和.cache。

遵守固定目录、接口、参数、结果schema、写入防重放、未知效果核对和三端配置。给现有核心阶段提供可消费的底层结果，不新增业务流程编排。

不能只提交脚手架、空方法、TODO、纯Mock业务实现或一份要求Client实现功能的说明。Fake MCP仅用于测试；生产路径必须真实实现。

## 执行顺序

### A. 基线和可行性核对

核验工具和容器能力、源码、依赖与设计落点。用短的受影响文件清单进入实施，不重新展开架构讨论。外部官方文档用于核对准确schema；Hosted服务变化不能用猜测补齐。

若既定能力存在实际API限制，记录准确操作、来源和阻塞，不静默改变支持范围或启用备用通路。

### B. 一次完成主体代码

先实现操作表/模型/Service与文件回执，再接MCP Server、Skill入口与三端配置。尽早做一条真实stdio → Fake HTTP MCP闭环，再扩展至全部32个操作。

安装配置使用宿主官方方式，任何登录状态、Token获取、权限扩大均由用户环境负责。元命令与原有Skill不得因GitHub不可用而失败。

### C. Web完成所有可运行验证

执行EVAL-PLAN中A/B层、32操作参数化测试、错误/边界/崩溃/并发测试、安装副本剥离docs测试，以及原有回归。

有安全可用的测试PAT和明确测试仓库授权时，可以执行真实MCP验证。不得使用GitHub连接器调用成功来代替自己Runtime的真实MCP证据，也不得从其他工具提取凭据。测试PAT只通过安全环境注入，不要求用户粘贴到聊天。

环境受限时，在Web把代码和可执行测试补齐，并准确记录不能执行的检查。不能把依赖安装失败或网络不可达写成测试PASS。尽量在本阶段修掉可复现问题，避免将简单修复交给Client。

### D. 最多生成一个Client验证包

仅当需要真实本地客户端或长任务时生成一份 `CLIENT-GOAL.md`，绑定实际实现源码SHA和工作树范围，列出：

- 三端配置、精确依赖与启动入口；
- 一个准备检查入口、一个连续验证入口；
- 需要的安全环境变量、测试仓库和已有Fixture，集中一次确认；
- 各Agent独立Token及实例数据根；
- EVAL-PLAN中尚未执行的准确项目；
- 限定的测试写入范围、现有head/base和对象命名前缀；
- 日志/结果/摘要清单路径，失败与停止条件；
- 在同一实施分支提交脱敏结果的方法和随后交回Web Review的提示。

Client任务以执行和诊断为主，不承担主体功能补全。目标是一次连续Goal验证，随后一次Web独立Review和定向修复。缺环境/授权集中返回BLOCKED，不循环扩大权限或伪造完成。若Web已完成全部要求，不人为增加Client交接。

## 权限与安全

本任务的Git仓库写入授权只覆盖该工作包分支和Draft PR，不等于生产GitHub业务操作授权。

没有单独测试范围授权时，真实验证保持只读；五个写接口在Fake中完整验证，并将真实写验证列入Client包。需要准备额外真实Fixture时，说明这是测试准备，不增加生产Skill能力。

不merge、强推、创建Tag/Release、执行生产Workflow、删除他人数据、写Secret或改全局宿主权限。遇到未知远端效果禁止重放。尊重已有代码、历史证据和工作树内容。

## 最终交付

本会话必须返回实际分支、Draft PR、实现SHA、交付SHA，完成的能力与验证层，未验证项，以及需要时唯一CLIENT-GOAL入口。

在Work Item中保存 `WEB-VALIDATION.md/json`、准确测试命令与结果、逐操作实现/测试矩阵、依赖锁与运行时源码摘要。追加文档提交不能冒充重新执行过程序测试。

不能将“配置合法”“协议测试成功”“真实GitHub通过”“三端原生通过”合并成一个笼统PASS。最后的接受状态只按真实证据填写，保持Draft等待独立Review。

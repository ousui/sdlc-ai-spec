# sdlc-github — Web 实施与 Mock 验证结果

**实现源码：`b035880a6135c1f126ae1a35e1c173221f28807a`；A/B 程序验证 PASS。真实 GitHub 和三端原生行为 NOT_RUN，整体尚未接受。**

| 项目 | 结果 |
|---|---|
| 固定离线测试 | 212 / 212 PASS |
| 真实 stdio → loopback Fake HTTP MCP | 6 / 6 PASS；覆盖 32 操作 |
| 全仓 unittest discovery | 1336 / 1336 PASS |
| 基线 validator / source-lock / installed-copy / DSN、PLN eval | 全部退出码 0 |
| 三端顺序安装副本 | Codex、Cursor、Claude Code 配置与剥离执行 PASS；非原生行为证明 |
| 真实 PAT / 官方 Hosted MCP / 原生批准行为 | 按用户指令 NOT_RUN |

运行环境 Python 3.13.5 / Linux，MCP SDK 1.26.0。依赖锁 SHA-256：`49665bdee4d204ef52b7b4c08da97fbd11bfb70d8c760ccb950a5333e6feabda`。

## 源码与交付边界

批准设计提交 `97c5f17bfcdb2751d446a89b068db2400436631d` 未改变。最后复核 PR #13 head 仍与批准 SHA 相同。原设计文件未被重新解释或替换；详见 IMPLEMENTATION.md 和 INSTALL.md。

最后复核远端 PR #14 仍为 Draft，HEAD=`33f76366ac1203a875fa8763f2f79300f47d96c1`。以上实现提交当前在本地 Git/交付 Bundle 中；未将它冒充已推送到远端。此前源码写入被平台安全检查拦截，本轮未改用另一通道绕过。真实业务测试与源码同步也不是同一项授权或证据。

本报告与 Client Goal 是后续纯文档交付提交；Git Bundle HEAD / 包外 DELIVERY-INDEX.json 给出准确交付 SHA。运行时源码未因补充报告而改变；不得把文档 SHA 与实测源码 SHA 混用。

## 覆盖内容

固定操作表、封闭参数、8 工具 input/output schema、身份绑定、Issue/PR 类型、Draft PR、写前持久 intent、原子回执、防重放、实际进程崩溃恢复、分页/大小限制、错误分类、Token 脱敏、安装路径与稳定数据根分离、缓存清除、10,000 文件工作区隔离均有程序案例。

每个操作的独立映射 Oracle 和四类参数化案例见 tests/skill_github/oracle.py / test_offline.py。32 操作协议成功见 test_protocol.py。LiveBatch 真实连接控制器和 native evidence validator 本身由合成输入验证，但没有因此标记任何真实账号/宿主 PASS。

## 精确证据

- `evidence/web/CHECKS.json`：全部命令、源码 SHA、退出码、日志摘要。
- `evidence/web/offline/VALIDATION.json`：212 个案例、源码文件摘要与依赖绑定。
- `evidence/web/integration/VALIDATION.json`：6 个真实协议案例及 per-case transcript。
- `evidence/web/full-regression.log`：全仓实际 discovery 数量和结尾 OK。
- `evidence/web/OPERATIONS.json`：32 操作分层状态矩阵。
- `evidence/web/SOURCE-SHA256.json`：被测源码/测试/构建文件 SHA-256。
- `evidence/web/SHA256SUMS.json`：本目录完整文件摘要（不自哈希）；固定 workspace 只归档摘要，不归档 10,000 个可重建文件。

## 验收组状态

| Case | Web 程序 | 必须保留的边界 |
|---|---|---|
| GH-01 | PASS | Skill/接口/显式触发元数据/source-lock 程序检查通过；原生触发行为留 D。 |
| GH-02 | PASS | 共享 parser、命令/别名/参数、冲突、元命令及 body-file 固定案例。 |
| GH-03 | PASS | Synthetic 双进程身份/错配零写入/重启隔离通过；不同真实账号留 C/D。 |
| GH-04 | PASS | 合成认证、401/403/404/429/5xx、超时/断线分类、秘密处理通过；真实网络留 C。 |
| GH-05 | PASS | 只发现 8 工具；封闭 32 操作，无 raw tool/URL/headers/API 扩展入口。 |
| GH-06 | PASS | 27 个读操作各自 mapping / 403 / upstream error / schema drift 与 stdio 成功。 |
| GH-07 | PASS | 5 个写操作各自 mapping / 403 / upstream error / schema drift、读回与协议成功。 |
| GH-08 | PASS | 准确 repo/URL、冲突、多个 remote、slash-ref 歧义及编码逃逸拒绝。 |
| GH-09 | PASS | 已存在不同 head/base，固定 Draft，不创建分支/推送/merge。 |
| GH-10 | PASS | Issue/PR 类型不可串用，省略与显式空 body 区分，只 open/closed。 |
| GH-11 | PASS | deny/dry-run/actor/schema 边界零写入；真实宿主原生拒绝留 D。 |
| GH-12 | PASS | 显式分页/未知完整性、Diff/日志和 JSON 转义字节限额。 |
| GH-13 | PASS | 8 工具 input/output schema、structuredContent/文本等价；isError 不当成功。 |
| GH-14 | PASS | 每操作所需 schema 漂移 fail-closed；无关工具不暴露。 |
| GH-15 | PASS | 相同 ID 去重、不同参数冲突、多进程竞争一次发送、actor 隔离。 |
| GH-16 | PASS | 固定 6 个故障窗口以及真实 stdio 进程退出的 unknown/reconcile；不宣称断电硬件测试。 |
| GH-17 | PASS | 完整范围唯一标记/属性/actor 匹配才补齐；不确定保持 unknown。 |
| GH-18 | PASS | 显式绝对根、符号链接/硬链接/FIFO/目录逃逸/损坏记录/写入故障检查。 |
| GH-19 | PASS | 重启持久状态、cache 删除与安装路径变化不丢 request 去重。 |
| GH-20 | PASS | 已知 synthetic Token 和典型凭据模式的结果/诊断/落盘边界；本轮未注入真实 PAT。 |
| GH-21 | PASS | 三份剥离 docs/tests/开发指令的安装副本，通过 production Service 的 Fake 协议执行。 |
| GH-22 | PASS | 精确依赖、现有 source-lock/validators/installed copy/evals 及全仓回归；无需 Token。 |
| GH-23 | NOT_RUN | 按用户明确决定未运行真实 32 操作，Client 控制器已完整实现并由 Fake 测试。 |
| GH-24 | PASS | 固定 10,000 文件工作区及安装/恢复模拟通过；三端真正 discovery/invocation/approval/behavior 未运行。 |

## 未验证与唯一下一入口

真实 Hosted schema/权限、32 操作真实读写、不同真实账号、macOS 安全文件行为、三端原生 Discovery/Invocation/批准拒绝/重启/持久工作区，以及 fresh-context 独立 Review 尚未完成。缺失 Tag/Release/Job fixture 不得用空列表代替单对象通过，也不得自行创建禁止的 Tag/Release。

唯一后续入口是本目录 `CLIENT-GOAL.md`；已有程序能够执行 offline、integration、prepare、live、identity、native、client 分层。Client 执行/诊断/留证据，不承担主体功能补写。源码修复后必须更新准确 SHA 并重跑相应检查，不移植历史 PASS。

没有修改 main、其他工作分支、共享/其他工作包 HANDOFF、稳定领域规范或 ArtifactStore。未 merge、创建 Tag、发布 Release，未执行真实业务写入。

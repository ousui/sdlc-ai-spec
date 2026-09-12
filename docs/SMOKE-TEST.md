# 小型可对照的 Codex / Cursor 工作流测试

## 项目：固定来源

使用 **golang/example/helloserver**，这是一个独立 Go 模块，包含两个文件：
`server.go`（简单 HTTP 问候和 `/version`）及 `go.mod`（`go 1.19`）。
它仅导入标准库。将父仓库锁定为：

`7f05d217867b2af52b0a28c6d1c91df97e1b5b39`

来源：

- https://github.com/golang/example/tree/7f05d217867b2af52b0a28c6d1c91df97e1b5b39/helloserver
- https://github.com/golang/example/blob/7f05d217867b2af52b0a28c6d1c91df97e1b5b39/LICENSE

在两个独立目录中使用相同项目、SHA 和需求，不使用两个不同需求，否则会混淆宿主
影响与任务难度。只运行这个隔离模块，不运行完整上游示例仓库。
此人工测试使用一次性副本，需要单独选定目标项目。

## 准备一次性副本

在插件仓库之外获取锁定的示例 checkout：

```sh
git clone https://github.com/golang/example.git /tmp/sdlc-example-source
git -C /tmp/sdlc-example-source checkout --detach 7f05d217867b2af52b0a28c6d1c91df97e1b5b39
```

选择两个不含用户工作的全新目录，将 `helloserver` 文件夹分别复制到其中，并将
来源 LICENSE 和 PATENTS 复制到每份副本。一份在 Codex 打开，另一份在 Cursor 打开。
使用 Go 1.19 或更高版本，记录 `go version`。离线测试使用已安装 Go 工具链，不触发工具链下载。

通过已安装插件入口初始化，不手写脚手架：

- Codex：`$sdlc-000-init`（显式选择一次性 helloserver 目录）。
- Cursor：`/sdlc-000-init`（或插件菜单实际暴露的准确名称）。
- 如测试 Claude：`/sdlc-ai-spec:sdlc-000-init`。

要求报告所选项目和创建/保留的文件。再调用一次：第二次结果必须为 `unchanged`，
文件内容和 mtime 不变。此时不应产生需求/规格或业务变更。若之前使用人工夹具设置
或已经开始需求，重新执行 INIT 补全缺失的兼容数据；不得删除 `.sdlc` 或重置已有需求。
文件契约及失败场景见 [INITIALIZATION.md](INITIALIZATION.md)。
可选：开始前在新的一次性副本中创建本地 Git 仓库；INIT 本身不创建或改变仓库及分支。
不执行远端写入。

## 固定需求：在两个宿主原样粘贴

> 为现有 helloserver 增加健康检查端点。
>
> GET /healthz 必须返回 HTTP 200、Content-Type application/json，响应内容必须
> 准确为 {"status":"ok"}，后接一个换行。该端点不得访问网络服务、数据库、文件或构建信息。
>
> 对准确路径 /healthz，除 GET 外的所有方法必须返回 405，并带 Allow: GET。
> /healthz/ 必须继续使用原有问候行为，不作为健康检查。
> 保留当前 /、/<name>、/version、-g 和 -addr 行为。保留问候中的 HTML 转义。
> 不增加第三方包，不改变 Go 版本。
>
> 使用 net/http/httptest 增加隔离测试，覆盖 GET、POST/HEAD 405、/healthz/ 边界
> 及既有问候的回归检查。测试不得绑定真实 TCP 端口或依赖互联网连接。
> 可以将处理器注册提取为小函数，以便测试路由。
>
> 使用已安装的 SDLC 插件。先仅生成规格并停止，等待审查；在我明确要求实施前不得
> 实施。只在这个一次性项目中工作；不得 commit/push、修改插件、安装依赖或启用其他
> 插件。报告实际检查及未验证项。

## 分阶段执行并检查停止行为

| 步骤 | Codex | Cursor |
| --- | --- | --- |
| 首次初始化项目 | `$sdlc-000-init` | `/sdlc-000-init` |
| 建立最小项目原则 | `$sdlc-010-rule` | `/sdlc-010-rule` |
| 粘贴固定需求 | `$sdlc-100-spec` | `/sdlc-100-spec` |
| 仅澄清有意义的缺口 | `$sdlc-110-clar` | `/sdlc-110-clar` |
| 技术设计（标准库 net/http） | `$sdlc-200-plan` | `/sdlc-200-plan` |
| 生成任务 | `$sdlc-300-task` | `/sdlc-300-task` |
| 跨文档一致性检查 | `$sdlc-310-xchk` | `/sdlc-310-xchk` |
| 需求质量清单（实施前审查） | `$sdlc-320-huma` | `/sdlc-320-huma` |
| 授权实施 | `$sdlc-400-impl` | `/sdlc-400-impl` |
| 评估剩余差距 | `$sdlc-500-conv` | `/sdlc-500-conv` |

宪法应保持 Go 仅用标准库、保留既有行为、要求隔离自动化测试，并禁止敏感凭据和
远端发布。不要虚构额外团队规则。保留上游由评审者拥有清单的语义，不要求实施者
勾选自己的审查门禁。

实施后 `go test ./...` 和 `go vet ./...` 应通过。初始项目可能没有测试，应如实
报告，不虚构基线测试覆盖。无差距的 `converge` 报告不能替代实际测试结果。

## 独立记录结果

记录准确插件提交/build_id、安装缓存路径、客户端版本、模型/推理设置、发现的预期
Skill 数量、薄入口是否加载完整工作流、提问/重复提问、阶段停止行为、.sdlc 文件路径、
实际检查和最终实现 diff。

比较能力和验收结果，不比较文案 SHA 或运行时长。独立比较结束前，不将一个宿主
生成的规格/代码交给另一个宿主。之后可单独测试顺序交接。若 loader 输出截断、
出现错误宿主入口或项目路径指向已安装插件内部，应停止并保留证据。

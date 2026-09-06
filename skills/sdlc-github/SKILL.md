---
name: sdlc-github
description: 显式读取 GitHub 对象或在当前授权范围内操作 Issue、普通评论与 Draft PR，核对身份并保留防重放回执。
disable-model-invocation: true
---

# SDLC GitHub · 仓库协作

## 适用范围

入口 `/sdlc-github [command] [options]`。非 Phase 支撑能力，不判断 Gate 或 Final Confirmation。
生产链路只走当前宿主的 sdlc_github MCP 实例；不会借用其他连接器、REST 或 gh 作为备用执行。

## 约定与边界

保持 exclusive execution，不调用兄弟 Skill、不继承其他会话的写入授权。
仅 8 工具、27 读/5 写；不 merge、推代码、建分支、写 Tag/Release、执行 Workflow 或下载制品。
身份只来自本实例 status；Token 只经宿主环境注入，不粘贴进业务参数或任何证据。
工作区前置发现由宿主自行实施；Skill 不委派全目录搜索、AGENTS/其他 Skill 搜索或无关正文读取。
`decision_policy`/`write_policy` 不代替当前用户意图和宿主原生批准；拒绝后不换通路重试。

## 子命令

| 命令 | 用途 | 写入 |
|---|---|---|
| `auto` | 无意图时检查身份；有意图时先归一化。 | 否 |
| `status` | 核对当前实例的真实身份与能力。 | 否 |
| `read` | 读取一种固定 GitHub 对象。 | 否 |
| `issue-create` | 创建普通 Issue。 | 是，须满足本阶段授权 |
| `issue-update` | 修改准确 Issue。 | 是，须满足本阶段授权 |
| `comment` | 给准确 Issue 或 PR 添加普通评论。 | 是，须满足本阶段授权 |
| `pr-create` | 基于既有分支创建 Draft PR。 | 是，须满足本阶段授权 |
| `pr-update` | 修改准确 PR。 | 是，须满足本阶段授权 |
| `receipt` | 查询本地回执，可显式只读核对。 | 否 |
| `help` | 显示帮助。 | 否 |
| `version` | 显示打包版本。 | 否 |
| `commands` | 列出命令。 | 否 |
| `examples` | 显示调用示例。 | 否 |

## 参数

| 参数 | 短名 | 默认/语义 |
|---|---|---|
| `--command` | `-c` | auto；兼容 --operation/-o，仅表示命令。 |
| `--project-root` | `-p` | 显式项目根；仅用于指定 body-file 的相对路径，不扫描其他工作区。 |
| `--reference` | `-r` | 来源引用，不授予文件读取或外部写入权限。 |
| `--decision-policy` | `-d` | user 为默认；model/experiment 不能扩大外部授权。 |
| `--write-policy` | `-w` | auto/confirm/deny；deny 零写入，仍需当前用户及宿主批准。 |
| `--dry-run` | `-n` | false；只读预检，不写 intent、不产生远端效果。 |
| `--output` | `-f` | summary/json/debug；JSON 不混入进度，均脱敏。 |
| `--repo` | — | 准确 owner/repo；与 URL 必须一致。 |
| `--url` | — | 标准 GitHub HTTPS 对象；不下载任意 URL。 |
| `--kind` | — | 27 个固定 read operation；用 help 查看全集。 |
| `--number` | — | 准确正整数 Issue/PR 编号。 |
| `--title` | — | 新标题；创建不得空白，更新省略表示保持。 |
| `--body` | — | UTF-8 正文；更新显式空值为清空，评论不得空白。 |
| `--body-file` | — | 准确本地文件；与 body 互斥，最大 64 KiB。 |
| `--head` | — | PR 已存在的源分支；同仓库且与 base 不同。 |
| `--base` | — | PR 已存在的目标分支。 |
| `--state` | — | 读取 open/closed/all；更新仅 open/closed。 |
| `--page` | — | 仅页码型读取；默认 1。 |
| `--per-page` | — | 默认 30；最大 100。 |
| `--after` | — | 仅游标型读取；禁止与 page 混用。 |
| `--request-id` | — | 每次新写请求一个 UUIDv4；重试复用，unknown 不重放。 |
| `--path` | — | 准确文件/目录路径；不遍历工作区推断。 |
| `--ref` | — | 准确 ref；与 sha 互斥，斜线分支不猜分段。 |
| `--sha` | — | 准确提交选择器；与 ref 互斥。 |
| `--workflow-id` | — | Actions runs 可选 Workflow 选择器。 |
| `--run-id` | — | Actions jobs/artifacts/run 的准确 Run。 |
| `--job-id` | — | Actions logs 的准确 Job。 |
| `--tag` | — | 既有 Tag/Release；不创建任何 Tag。 |
| `--subject-type` | — | 普通评论目标 issue/pr，先验证类型。 |
| `--expected-actor-id` | — | 从本实例 status 取得；不是批准凭证。 |
| `--reconcile` | — | true/false；receipt 显式只读核对，默认 false。 |

未声明参数拒绝。公共解析采用 `scripts/sdlc_skill_interface.py` 所用的共享 Contract，命令定义在 `references/interface.json`。
内部 Tool Invocation 与用户 CLI 不同，不把所有公共开关直接传给 MCP。

## 执行流程

1. 只读取本 Skill 的 [私有契约](references/contract.md) 和 [GitHub 共享契约](../_shared/contracts/github-runtime.md)。
   共享路径准确为 `<plugin-root>/skills/_shared/contracts/github-runtime.md`，不是 `<plugin-root>/contracts/`。
2. 使用本 Skill 已发现绝对目录下的 `scripts/run` 编译参数，例如 `<skill-root>/scripts/run status --output=json`。
   安装器已绑定准确 Python；不要改成 system python3、寻找另一个解释器或扫描目录猜安装根。
   源码模板未安装时返回 INSTALLATION_REQUIRED；缺依赖时明确阻断，不临时安装。
3. 裸调用编译为 status；自然语言先归一化唯一意图。repo 只取显式参数/URL 或宿主已经提供的唯一 remote。
4. 按编译结果调用当前 MCP；写入先 status 绑定 actor.id、展示准确目标，保持 request_id 并取得当前批准。
5. 验证结构化结果和回执；confirmed/partial 表示已写但本次读回未完全核验；unknown 仅可只读 reconcile。
6. 根据结果输出一次明确摘要或原 JSON 后停止；不生成新的 request_id 重放，也不删除未完成 intent。

元命令只读随包接口，不调用 MCP、不读项目、不联网、不落盘。编译器的 action_required 不是远端执行成功。

## 输出与完成条件

summary 说明账户、目标、完成状态、副作用和下一动作；json 原样返回结构化结果，不混入进度或改写字段；debug 同样脱敏。
`pagination/completeness` 与一页请求成功分开；unknown/partial/资源链接不能用于宣称完整审阅。
闭环以实际调用证据为准；固定测试、真实远端、可选宿主反馈分别记录，原生认证不作为新增门禁。
代码与稳定数据根分离；`.local` 的 intent/receipt 不删除、不跟随代码重装，`.cache` 可重建。

## 资源索引

| 资源 | 何时读取 |
|---|---|
| [接口](references/interface.json) | 编译器解析命令；help/version/commands/examples |
| [私有契约](references/contract.md) | 业务调用前，确认参数域、32 操作与恢复语义 |
| [共享契约](../_shared/contracts/github-runtime.md) | 当前 Skill 执行边界与结果格式 |
| [绑定启动器](scripts/run) | 唯一安装后参数编译入口，不执行远端操作 |
| [编译器](scripts/runtime.py) | 启动器调用；不要用环境默认 Python 直接执行 |

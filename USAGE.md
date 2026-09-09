# SDLC v2 用户使用指南

> 从一个明确需求开始，在现有项目或新项目中，依次完成 REQ → DSN → PLN → IMP → VFY → RLS。人负责明确目标和授权；Agent 完成分析与实现，Runtime 保存结构化事实和检查结果。可选 `sdlc-github` 将可读 Markdown 快照分享至 Issue。

## 1. 首次准备

**先准备业务项目和工具，再让 Agent 开始需求。插件目录与业务目录分开。**

使用完整安装包，包含 `skills/`、`packages/`、`scripts/`、`contracts/` 和宿主 Manifest。不要只复制一个 SKILL.md。安装方式使用客户端提供的本地插件入口；如果客户端尚不能原生加载，可明确让 Agent 读取安装目录下指定 Skill 全文再走公共 CLI，这属于显式 Skill 执行，不代表原生发现认证。

当前 Runtime 要求 Python 3.11+、SQLite 3.37+。实际 `check.run` 和独立 RLS 命令收集器使用 **macOS Seatbelt**；Linux/Windows 上可以运行可移植机制测试，但不能据此声称原生命令收集已支持。Podman 在 macOS 上运行的是 Linux 容器，不会提供 macOS Seatbelt。

业务项目使用自己的 JDK、Go、Node、Maven、数据库与依赖缓存。先准备隔离测试环境；网络安装或生产访问应单独明确授权。插件不自动安装依赖、不修改宿主设置。

在业务项目打开一个新会话，核对工具：

```text
<python3.11> -B <plugin-root>/scripts/sdlc.py --version
<python3.11> -B <plugin-root>/scripts/sdlc.py --contract
```

macOS Framework Python 若命令收集器因启动器 `posix_spawn` 被拒，应使用该已安装 Python 的实际解释器（`sys.base_prefix/Resources/Python.app/Contents/MacOS/Python`，存在时）；不要关闭沙箱或放宽系统调用规则。CI 使用同样的选择方式。

## 2. 一次提示完成一个需求

**你描述业务，不需要填写 UUID、SQL 或操作回执。首次初始化后，项目 CTX 可以复用。**

```text
请在当前业务项目副本中使用已安装的 SDLC v2 完成以下需求。

需求：<目标、当前问题、范围>
验收：<正常行为、异常行为，以及必须保留的既有行为>

未初始化时先使用 sdlc-init、sdlc-000-ctx；已有有效上下文则复用。
然后依次使用 sdlc-100-req → sdlc-200-dsn → sdlc-300-pln →
sdlc-400-imp → sdlc-500-vfy → sdlc-600-rls。

授权在当前隔离项目中修改相关代码和测试、执行已有本地检查、
写入 .sdlc 并交付到 .sdlc/exports/my-feature。
本次不授权生产操作、Git push/merge 或 GitHub 写入。
不需要逐阶段等待我 review。测试失败时在需求范围内修复并复验。
只有缺少必要业务事实、环境或权限时询问最小问题。
继续同一需求并保留失败，不用新需求或直接SQL绕过。
每阶段提供摘要与阅读入口，最后给出实际验证、交付回读和完整归档。
```

单独调用某阶段也支持：只授权 REQ 时完成需求后停止；完整六阶段总授权时由当前 Agent 衔接下一入口。阶段结束不要求反复人工审批。业务范围有歧义时，`run.request_input` 保存问题，用户回答后再继续。

## 3. 六阶段分别做什么

**同一需求贯穿各阶段；内容版本与实际执行记录分别保存。**

| 阶段／Skill | 主要工作 | 你阅读什么 |
|---|---|---|
| INIT／sdlc-init | 初始化或发现、复制已有工作区 | 本地库和资源绑定 |
| CTX／sdlc-000-ctx | 采集项目事实、工具、已确认规则 | 项目画像与约束 |
| REQ／sdlc-100-req | 保留原始输入、需求、验收与来源 | spec.md |
| DSN／sdlc-200-dsn | 明确方案、选择依据和验证目标 | design.md |
| PLN／sdlc-300-pln | 拆解任务，建立覆盖、顺序和条件 | tasks.md |
| IMP／sdlc-400-imp | 按任务写代码与测试，持续自检 | implementation.md |
| VFY／sdlc-500-vfy | 实际验证、发现缺口、退修及复验 | verification.md |
| RLS／sdlc-600-rls | 完成约定的本地包与独立回读 | release.md |

这些文档由 `render` 生成到 `.sdlc/changes/<change-id>/`；`index.html` 是可读总览，`content.md` 是全部阶段投影。阅读视图不是权威数据，也不通过编辑 Markdown 自动改数据库。

当前仅实现本地交付目标。RLS prepared 不是已交付，实际 execute 与回读 succeeded 后才完成。此结果不代表已部署生产或已向上游发布。

## 4. 看进度、换会话和调整需求

**使用 sdlc-status 查询事实，不需要翻数据库。**

可向 Agent 说：“使用 sdlc-status 查看当前需求，生成可读视图，告诉我下一步。”多个需求时明确选一个。换会话后提供同一业务目录及需求标识，让 Agent 从 Store 和原始回执继续；不要重新猜测最新产物。

业务测试失败是正常修复循环：VFY 记录 finding → IMP 修复 → 实际复验 → 用适用新结果关闭 finding。`addressed` 只表示已处理，不等于 `resolved`。

范围或验收变化时使用 `change.revise` 创建新草稿，沿关联复核设计、任务和验证。原始结果仍绑定原版本。代码合入主干的新功能后，HEAD 改变本身不阻塞；实际输入字节、文件模式、环境或检查定义变化时，需要重新验证受影响部分。

文件写入会保留现有执行权限；新脚本需要执行时，Agent 可在 `task.write` 中显式声明 executable。执行位也进入指纹和交付 ZIP。

## 5. 将当前产物分享至 GitHub Issue

**本地研发与远端共享相互独立。先登录 gh，首次给出 Issue 地址，以后同一需求可复用唯一成功目标。**

在自己的终端准备 GitHub CLI 并认证：

```sh
gh --version
gh auth login --hostname github.com
gh auth status --hostname github.com
```

使用现有授权账户，授予目标仓库 Issue 读写权限即可；不要将 Token 粘贴进提示词、Markdown 或 .sdlc。本版只向已有 Issue 追加阶段快照评论，不创建分支、不修改代码、不 merge，也不覆盖用户 Issue 正文。需要新 Issue 时由用户或已明确授权的宿主 GitHub 工具创建。

首次发送示例：

```text
/sdlc-github 帮我将当前已提交的 REQ 产物发送至
https://github.com/<owner>/<repo>/issues/<number>。
允许将本次需求的脱敏 Markdown 摘要写到该 Issue。
```

随后可以说：

```text
/sdlc-github 帮我将当前产物发送至之前的 issue。
/sdlc-github 仅发送当前 DSN 设计，不发送原始日志或附件。
/sdlc-github 查看上次发送是否成功；不确定时只回查，不重复发送。
```

Agent 执行 `github.preview`，固定目标、phase、准确 revision 和 preview_digest，然后依据本次明确意图调用 `github.publish`。默认选择已提交的 active 版本，不会把下一阶段自动创建的空草稿发出去。当前明确请求已经涵盖准确目标和内容时，无需再逐字段确认；敏感内容或目标歧义必须澄清。

只有实际 POST 与 GET 回读核验后才返回 confirmed 和 comment_url。同快照重复发送复用回执；内容更新后生成新快照评论。附件仅发送名称、大小和摘要索引，不上传字节；大文档应按阶段发布。发布正文会脱敏并避免自动触发批量 @ 提及，发送前仍应确认资料适合目标仓库可见范围。

`github.status` 读取本地回执；`github.reconcile` 回查 marker、作者、正文和目标。unknown 或 conflict 时不自动换 ID 重发，也不覆盖远端人工修改。API 不可用不回滚已完成的本地阶段。回执仍在同一 SQLite operations 表，`run_id` 为空，因此不会把共享故障写成产品 Run 失败。

## 6. worktree、分支与归档

**可在一个目录切换分支，也可每个 worktree 使用独立 .sdlc。数据库与真实产品代码分别管理。**

当前目录无 .sdlc 时，sdlc-init 可以发现已有来源，明确选择复制或新建。复制保留项目和历史，创建新工作区身份并绑定本地路径；不直接 cp 正在写入的数据库。

交回使用 workspace.export → workspace.collect。新需求直接合入事实库；同需求内容分叉保留版本并通过 change.resolve 处理。共有 Run/Step/operation 的正常状态演进保留目标现状，并记录来源观察和原包，不让旧副本覆盖新状态。真实身份或冻结内容冲突仍明确失败。collect 外层 conflict 不等于完成。

逻辑交回不合并产品代码，也不继承来源执行权限。产品 Git 合并由单独的明确授权处理。全部 .sdlc 默认不入 VCS。

产品交付包与完整工作区归档不同：

| 文件 | 包含 | 限额 |
|---|---|---|
| local delivery ZIP | 声明范围源码、文件权限、当前内容、适用验证证据、附件索引 | 压缩64MiB／展开256MiB |
| workspace.export ZIP | 原始输入附件、完整关系/历史、Run/日志/回执、补丁和归档来源 | 压缩／展开512MiB |

不要把上一轮完整归档反复作为每个新需求的必需附件。需调整附件集合时，在同一需求创建新草稿，通过 phase.prepare 取得 link_id 和 generation，再 asset.unlink；历史版本与附件字节继续保留。大包预检失败时修订相应范围或附件后在同一需求重试，不另建需求掩盖失败。

## 7. Podman 与跨平台验证

**Podman 可运行 Linux 可移植测试，但不替代 macOS 的完整执行测试。**

仓库提供 `tools/validate_portable.py`，覆盖存储/字段/关系、协议、归档、文件权限、Markdown 与 GitHub 发布回执；真实 GitHub 写入单独在授权环境测试，不在离线套件中发生。

使用本机已有、受信任的 Python3.11+ Linux 镜像（需要 git，权限测试需要 /bin/sh）：

```sh
# image 使用本机已存在的镜像名称；--pull=never 不自动下载。
# 源码只读挂入，临时目录/证据另存，网络关闭。
podman run --rm --pull=never --network=none --read-only \
  --tmpfs /tmp:rw,size=1g \
  -v "$PWD:/src:ro" -w /src \
  <local-python-image> \
  python3 -B tools/validate_portable.py --evidence-dir /tmp/sdlc-portable
```

该命令结束后 `/tmp` 证据随容器删除；要保留，另挂一个专用输出目录至 `/evidence:rw`，并改 evidence-dir。不要把宿主根目录或凭证目录挂入。

macOS 完整回归使用：

```text
<实际Python解释器> -B tools/validate.py --profile full --evidence-dir <仓库外证据目录>
```

Windows 原生收集器与 Linux 原生命令沙箱是后续适配工作。未知宿主的 SANDBOX_UNAVAILABLE 是明确边界，不应通过关闭隔离改成 PASS。

## 8. 问题定位与试用验收

**保存第一次失败，区分业务问题、输入错误、环境限制与 Runtime 缺陷。**

| 现象 | 处理 |
|---|---|
| GENERATION_CONFLICT | 重新 phase.prepare，基于最新草稿合并自己的变化 |
| TASK_BLOCKED | 按返回的具体条件准备或完成先行任务；不要删除条件 |
| unknown | 回查对应 operation 或 GitHub publication；不盲目重放 |
| DELIVERY_SIZE_LIMIT | 产品包与历史归档分开；按预先约定范围修订后同需求重试 |
| IMPORT_CONFLICT | 查看是否已导入行；内容分叉可 resolve，身份冲突保留双方原包 |
| GITHUB_TARGET_REQUIRED | 首次提供准确 Issue URL 或从多个目标中选择 |
| GITHUB_PREVIEW_CHANGED | 重新生成预览，确认新的内容／目标 |
| GITHUB_TRANSPORT_MISSING | 用户准备 gh 与认证；不由 Agent 临时安装或换通路 |
| SANDBOX_UNAVAILABLE | 使用已支持的 macOS 环境；Linux Podman 只跑已声明的可移植验证 |

第一次人工试用选择一个有代表性的中等需求，新会话只给项目、正式插件和需求，不给内部 Handoff 或成功脚本。记录人工纠正次数、协议错误、自主恢复、实际模型配置和最终业务结果。测试失败后自行修复是正常能力；需要用户手工修 ID/SQL/隐藏调用顺序则应报告为产品问题。强模型成功不自动证明低推理档位也成功。

本指南说明实现的操作路径，不承诺任意模型、任意项目和环境都可无条件完成。

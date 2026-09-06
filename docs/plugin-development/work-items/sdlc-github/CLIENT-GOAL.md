# CLIENT-GOAL — sdlc-github 一次本地真实验证

## Goal

你是本工作包的本地验证执行者。只在准确实现上运行真实 GitHub / 两个真实身份 / 三个原生宿主验证，保存可独立复核的证据。主体 Runtime、32 操作实现、固定测试、安装器和连续验证程序已经提供，不要从头设计或补写主体功能。

- 仓库：ousui/sdlc-ai-spec。
- 工作分支：impl/sdlc-github-foundation-v1。
- Draft PR：#14（保持 Draft）。
- 唯一批准设计 SHA：97c5f17bfcdb2751d446a89b068db2400436631d。
- **准确被测实现 SHA：b035880a6135c1f126ae1a35e1c173221f28807a**。
- Runtime / 测试 / tools / manifests / shared contracts 必须与该 SHA 相同；后续纯 Work Item 文档提交允许不同。固定入口会主动核验源码差异，不把新代码当成已测旧版本。
- 本交付的远端分支仍可能只有准备提交；以 Git Bundle 内的实际提交为来源，不能凭 PR 存在认定源码已推送。

## 0. Git 与交付恢复

在独立新工作树或新目录执行。不修改 main、其他分支、根级共享 HANDOFF 或其他工作包。保留任何未知用户变更。

交付包包含完整 Git Bundle。最简单恢复方式：

```bash
git clone /绝对路径/sdlc-github-foundation.bundle sdlc-github-local
cd sdlc-github-local
git switch impl/sdlc-github-foundation-v1
git merge-base --is-ancestor 97c5f17bfcdb2751d446a89b068db2400436631d HEAD
git diff b035880a6135c1f126ae1a35e1c173221f28807a -- packages scripts skills config tools tests .github .codex-plugin .cursor-plugin .claude-plugin AGENTS.md .gitignore
```

最后一条必须无输出；确认 `git status --short` 无未知代码改动。恢复目录可任意命名；不在其他项目目录强行 checkout。不要自动 reset、rebase、merge、force push。远端同步使用已授权的本地 Git 连接，仅允许本分支快进推送；发现远端已前进或内容不一致时记录阻塞，不覆盖。

## 1. 一次性准备与输入核对

只确认下列确实缺失的输入，不重复询问已授权范围：

1. 用户在本地安全环境注入 `SDLC_GITHUB_TOKEN`；只读取是否存在，不打印值、摘要或认证 header。用于双账号用例的 `SDLC_GITHUB_TOKEN_B` 必须属于不同真实 actor；两个同账号 PAT 不能证明身份隔离。没有 B 则该项 BLOCKED，其他可执行项继续。
2. 真实测试仓库已经授权为 `ousui/sdlc-ai-monitor`。只处理本批次新建并带标记的 Issue、PR 和普通评论。保留可审计留痕；可关闭自己新建 Issue/PR，不删除别人资源。
3. 历史准备 Fixture 是 `head=fixture/sdlc-github-20260906`、`base=main`，Workflow ID `351428147`，Run ID `34021751640`，文件 README.md。将其作为候选，运行时核验仍存在且准确，不能把历史值冒充当前证据。Job ID 可从该准确 Run 的列表读取。真实分支若不再适用，集中返回准确缺口，不创建/推送新分支或执行 Workflow。
4. Tag/Release 单对象需要已存在的 fixture。示例里 tag 为 null；缺失时 `repo.tag`/`release.get` 必须 BLOCKED；release.latest 无对象按实际结果登记。允许另指定一个用户明确授权的只读 `tag_repository` 来读取既有 Tag/Release，但不假定 PAT 有权限，不自动创建 Tag/Release，不自动扩大 token 权限。
5. 用户本地已安装并可登录的 Codex、Cursor、Claude Code。记录真实版本。没有某端、不能加载本地插件或无法保留原生证据时，对该端 BLOCKED，而非使用 SDK Client 代替。

建立单一稳定外部工作目录。以下变量都由程序或当前工作树产生，不要求用户填写内部 digest / receipt：

```bash
export SOURCE="$(pwd -P)"
export GH_WORK="$(dirname "$SOURCE")/sdlc-github-client"
export IMPL_SHA="b035880a6135c1f126ae1a35e1c173221f28807a"
mkdir -p "$GH_WORK"
python3 -m venv "$GH_WORK/venv"
export PY="$GH_WORK/venv/bin/python"
"$PY" -m pip install --require-hashes -r "$SOURCE/packages/sdlc_github/requirements.lock"
"$PY" "$SOURCE/scripts/sdlc_github_mcp.py" --check-install
```

若 GH_WORK 已用于本批次，复用其虚拟环境、fixture、run-state 与稳定 data，不删除以制造新开始；已有其他内容先核对所有权。不要覆盖既有运行证据或 unknown 请求。

**唯一准备检查入口：**

```bash
"$PY" tests/skill_github/validate.py --layer prepare \
  --implementation-sha "$IMPL_SHA" --output "$GH_WORK/preparation"
```

它检查准确源码/锁、生成 10,000 文件的固定工作区和未执行的三端证据模板。它不连接 GitHub、不开启真实宿主、不声称权限验证通过。

只在 fixture 文件不存在时复制；随后基于一次性核对修正非秘密 selector：

```bash
test -f "$GH_WORK/fixture.json" || cp tests/skill_github/fixture.example.json "$GH_WORK/fixture.json"
mkdir -p "$GH_WORK/data/live" "$GH_WORK/native"
```

## 2. 三端顺序适配与原生行为验证

按 **Codex → Cursor → Claude Code** 顺序，使用相同源码 SHA，不并行改变共享配置。安装前若目录已存在，核验 INSTALL.json 和文件摘要后复用，不覆盖或删除。首次安装：

```bash
for host in codex cursor claude-code; do
  "$PY" tools/install_sdlc_github.py --host "$host" \
    --destination "$GH_WORK/installed/$host" \
    --data-root "$GH_WORK/data/$host" --python "$PY"
done
```

安装器只创建准确用户选择的代码/数据目录，不注册宿主、不写全局设置。每个宿主的 manifest 与已渲染 MCP 配置都是完整可执行配置；配置路径见 INSTALL.json。

使用该宿主的原生插件加载方式注册**这份**副本，不直接安装远端旧 main，不同时再注册一份独立同名 MCP。Claude Code 可使用 `claude --plugin-dir "$GH_WORK/installed/claude-code"`。Codex/Cursor 按该实际版本提供的本地插件目录或本地 marketplace 导入方式操作；不猜不存在的 CLI 命令。没有可用入口则记录该端安装 BLOCKED。保持宿主默认工具批准，不启用全局 auto-approve 或绕过权限选项。

三个宿主进程分别从本地环境注入各自的 SDLC_GITHUB_TOKEN，彼此不共享进程；数据根分别为 data/codex、data/cursor、data/claude-code。代码与数据不重叠。各端可用同一 actor 做基础行为，但 GH-03 真实跨账号由双身份批次独立验证。

在 `preparation/prepare/workspace` 的固定 10,000 文件工作区中，逐宿主执行以下原生场景。所有 GitHub 写入仍只操作本批次新建对象，使用统一标题前缀 `[sdlc-github-native:<host>:<run-id>]`；请求 UUID 在首次发送前生成并保存在本地验证记录，复试相同操作复用原 UUID。

| 原生检查 | 操作与 Oracle |
|---|---|
| discovery | 启用插件，保留原生 MCP/Skill 发现列表；业务工具名恰好为实现声明的 8 个；Skill 为 sdlc-github（命名空间前缀按宿主记录） |
| explicit_invocation | 用户显式调用 sdlc-github status；实际 actor.id/login 与本宿主注入账户一致，保留调用和结构化结果 |
| approval_denial | 请求创建一个带本批次前缀的测试 Issue，在真实宿主权限提示中拒绝；证明写工具未执行、无远端对象。dry_run/deny 参数不是原生拒绝证据 |
| write_readback | 在新的明确允许操作中创建自己的测试 Issue；结果 effect=confirmed、receipt.readback_verified=true，并只读取回同一对象 |
| restart_receipt | 保存该请求 ID，关闭并重启同宿主 MCP 进程，显式在线 status 后查询该本地回执；不新建重复对象、不改 UUID 重试 |
| no_implicit_invocation | 开新会话只讨论 GitHub 概念，不显式触发 Skill；不得自行调用这 8 个工具 |
| exclusive_execution | 完成本 Skill 请求，不调用兄弟业务 Skill、不触发 Phase/Gate、无额外 workflow/API 副作用 |
| workspace_isolation | 检查 10,000 个既有 fixture 文件摘要完全不变；.local 仅写稳定 data 根，不扫描或写入业务代码 |
| secret_scan | 检查待提交文件/日志，无凭据、认证头、Cookie、私有文件正文或日志内容；原生 trace 中只保留必要身份/对象/状态/回执与内容摘要 |

生成器的模板位于 `preparation/prepare/native-templates/<host>.json`。复制到 `native/<host>.json` 后，**只依据真实运行填值**；不得把 NOT_RUN 批量替换为 PASS。模板本身和检查程序不构成宿主证据。某端根本无法启动或无法取得真实版本时，不把空模板伪装成已执行记录放入 native 目录；在 CLIENT-VALIDATION 中列该端 BLOCKED，检查器对缺少该端记录也返回 BLOCKED。提交缺版本/缺 trace 却自述执行的记录会被判为证据不合格。

证据结构由 `tests/skill_github/native_evidence.py` 明确定义：每个 host record 包含真实 host_version、runtime_sha、dependency_lock_sha256，以及 9 个 checks。每个已执行 check 指向一个本地相对路径 JSON trace 和其 SHA-256；trace 至少有 host、runtime_sha、calls，并包含该 Oracle 所需字段。例如：

```json
{
  "host": "codex",
  "runtime_sha": "b035880a6135c1f126ae1a35e1c173221f28807a",
  "calls": [],
  "host_permission_decision": "denied",
  "remote_effect": "none",
  "write_tool_executed": false
}
```

这只是**格式示例，不是执行结果**。原生界面或工具原始 transcript 的脱敏副本也一起保存，trace 中记录其相对路径，供随后 Web Review 独立核验。SHA-256 用本地程序读取文件计算，不让用户填写、不由模型编造。允许人工进行原生权限拒绝与 UI 操作；明确记录人工步骤。

完成写读回后可在原生宿主显式关闭本批次自己创建的 Issue，记录 URL；普通评论不删除。若操作副作用 unknown，停止所有后续写入，只查询原 request_id 或远端只读核对，不自动清理可能不确定的对象。

## 3. 唯一连续验证入口

原生场景执行后运行一次连续批次（缺少客户端时仍可执行并诚实保留 BLOCKED）：

```bash
"$PY" tests/skill_github/validate.py --layer client \
  --implementation-sha "$IMPL_SHA" \
  --fixture "$GH_WORK/fixture.json" \
  --data-root "$GH_WORK/data/live" \
  --native-evidence "$GH_WORK/native" \
  --allow-test-writes \
  --output "$GH_WORK/results"
```

顺序：offline → integration → live → identity → native evidence validation。live 使用**未修改的生产 stdio 入口**与官方 MCP；不用 GitHub 连接器/REST 验证冒充 Runtime。五个真实写操作只创建/修改/评论/关闭本批次自己的 Issue/PR；PR 始终 Draft，head/base 必须预先存在。所有 27 个只读操作逐项记录，无 fixture 就 BLOCKED。

真实双身份验证用两个生产 stdio 进程核对不同 actor，并在身份不匹配的 dry-run 中验证零写入。它是 C 层实例身份测试，不代替三端原生 D 层。持续性相关场景以固定序列结束，无无限轮询或压力循环。

同一批次重跑必须复用 results/live/run-state.json、数据根和准确 fixture，控制器会复用 UUID。unknown 状态下禁止删除 state、换 ID 或自动重放。只有用户明确确认新独立测试批次，才允许新的前缀/结果目录。

连续入口退出码：0 全部通过；1 存在失败；2 存在阻塞。不能忽略非零、把 BLOCKED/SKIP 计 PASS 或使用历史 PASS 覆盖未测源码。固定 mock 成功与 live/native 行为分别报告。

## 4. 输出与停机

在本 Work Item 内只追加 CLIENT-VALIDATION.md/json、按宿主分开的脱敏证据及 SHA256 清单。复制必要的 results、native 证据，不提交 .local/.cache、Token、完整本地路径配置、私有正文、整个 10,000 文件树或虚拟环境。

每项记录准确代码 SHA/文件摘要、锁摘要、真实 host/version、输入 fixture/实际对象 URL、状态/副作用、退出码和证据路径。HTTP 上游调用次数若没有独立观察依据，写 not externally observed；MCP 客户端计数不是 HTTP 请求计数。输出状态总结须保留这些区别。

源码变动属于返修，不可沿用当前 b035880 的测试证明。发现安全关键或确实需要主体代码修改的问题，保存最小复现和失败证据，停止相关写入，交回独立 Web Review；不要在本批次临时扩大操作表、放开网络后门、更换 SDK 组合或重写设计。

本分支上的本地证据 commit 和正常快进 push 已获授权。提交前确认当前根/分支/HEAD/status，使用本地当前明确 Git 身份；不要替换用户身份。远端来源未配置时使用用户已连接的正确仓库认证，不从其他工具提取凭据。源代码未同步时先快进同步本工作包提交，再提交证据；遇权限/分支冲突保留 bundle/commit 并记录 BLOCKED，不强推。PR 保持 Draft。

停止条件：所有能执行的条目已有真实结果；缺环境/权限/fixture 的一次性输入清单已经返回；所有不确定副作用未被重放。最终只交回下面一个 fresh-context Web Review 包，不另建多份 Goal。

## 5. 交回独立 Web Review 的提示

请独立审查 ousui/sdlc-ai-spec 的 sdlc-github-foundation/v1。唯一批准设计为 97c5f17bfcdb2751d446a89b068db2400436631d，Web 实现为 b035880a6135c1f126ae1a35e1c173221f28807a。先读取本次 Client 交付的准确提交、CLIENT-VALIDATION.md/json、三个原生宿主 transcript 和 SHA256 清单，以及 WEB-VALIDATION。核验实际业务操作、真实 actor/对象、8 工具/32 操作、原生批准拒绝、unknown 防重放、缓存/持久状态、source-lock 与回归。不要用 Mock/SDK/配置合法替代真实宿主证据。只在同一实施分支定向修复，保留旧证据并对修改后的准确源码重跑；需要本地复验的安全关键差异保持 Draft。禁止 main/其他工作包改动、merge/tag/release。最终明确接受或精确阻塞，不把未测试源码当作通过。

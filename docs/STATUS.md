# sdlc-status：只读状态与产物导航

STATUS 是本项目本地 utility，不编号、不加入九项上游核心命令，不是验收器或
流程调度器。入口是 `dist/skills/sdlc-status/SKILL.md`。它不会初始化、修复、
切换当前需求、改任务勾选、执行其他 Skill、构建/测试/应用代码或网络操作。

## 使用方式

在 Agent 中调用 `sdlc-status`，可以查看当前状态、指定项目/需求或列出本项目
的需求。使用当前已加载插件的绝对路径，不把插件路径当作业务 cwd：

```sh
python3 -I -B "$SDLC_PLUGIN_ROOT/scripts/python/project_status.py" --json
python3 -I -B "$SDLC_PLUGIN_ROOT/scripts/python/project_status.py" --project "$PROJECT" --list
python3 -I -B "$SDLC_PLUGIN_ROOT/scripts/python/project_status.py" --project "$PROJECT" --feature .sdlc/specs/001-example --json
```

只需 Python 3.9+ 标准库，不依赖 Bash、uv、Git 或上游 CLI。不带 `--json` 时
直接输出中文 Markdown。没有输出文件、修改或修复参数；路径作为独立参数引用。

| 参数 | 意义 |
|---|---|
| `--project PATH` | 本次项目目录；明确无效目标不会回退到其他项目 |
| `--feature PATH` | 本次需求目录；相对路径基于项目，不自动补 specs 前缀 |
| `--list` | 列出本项目默认 `.sdlc/specs` 下的需求，不扫描其他工作区 |
| `--limit N` | 目录结果展示上限，默认 20，允许 1–200 |
| `--json` | 一个结构化 stdout 对象，不写 status.json |

项目：明确参数 > `SDLC_INIT_DIR` > 业务 cwd 向上最近的 `.sdlc` 标记。
需求：明确参数 > `SDLC_FEATURE_DIRECTORY` > `feature.json.feature_directory`。
`SDLC_FEATURE` 仅标签。不用 Git 分支或修改时间选择需求。无标记报告未初始化；
最近标记损坏时不跳过它。显式未初始化子目录不会改查父项目。查看其他需求不
保存切换。允许合法外部状态/需求路径；业务路径指向插件资源时拒绝读取。

## 文件事实，不是阶段完成度

输出包括上下文、选择来源、包身份、历史初始化版本、产物、任务/清单和提醒。
只读明确的相关文件，不执行项目指令，不输出秘密配置或完整环境。

当前包版本来自 UPSTREAM.json，build_id 来自 BUILD.json；初始化记录不是当前
运行版本或自动升级理由。文件分别标为存在、缺失、空、不可读、编码/类型错误、
断链或过大。可选产物缺失不是业务失败。

宪法单独展示三个互不等价的事实：文件状态、可选生成来源记录，以及占位符观察。
若 `.sdlc/memory/.constitution-template.json` 有效，STATUS 对本次稳定读取到的
`constitution.md` 原始字节计算 SHA-256，并显示 `matches_baseline` 或
`differs_from_baseline`；不使用当前插件模板重新推断历史。来源记录缺失时显示
`missing/unknown`，不会补造；损坏、不可读或读取期间变化时明确诊断并把比较结果
降为 `unknown`。`source` 只作为字符串数据显示，不按其路径读取、执行或联网。

生成内容一致不等于 RULE 未执行或宪法未批准；内容不同也不等于 RULE 已完成。
占位符是否存在只是另一个文件观察项，不能与审批或治理质量合并成阶段结论。

任务仅统计顶层 Markdown 复选框中带 T 和至少三位数字的任务行，勾选支持空格、
x、X。忽略 fenced/indented code、HTML 注释和标为 Examples/示例的章节。
数字只表示识别到的行，不是项目总工作量；重复编号、未知格式和零任务不能
显示为可靠完成度。默认列五项未勾选任务及文件行号。清单按文件独立统计。

文件存在不等于阶段完成，宪法模板不等于 RULE 完成，全部勾选不等于测试通过、
收敛或可发布。CLAR/XCHK/CONV 无持久化证据时为未记录，不推断从未执行。
任务内容仅是数据；建议入口不自动执行，也不授予额外写入/跨阶段权限。

## stdout 契约和退出码

schema_version 为 1。顶层有 status、snapshot、plugin、project、selection、
artifacts、tasks、checklists、features、warnings、suggestions、history。
有状态目录时包含 initialization；请求列表时有 feature_list。宪法 artifact 保持
`assessment: not_verified`，并增加 `generation.record_state`（valid/missing/invalid/
unreadable）、`generation.content_relation`（matches_baseline/differs_from_baseline/
unknown）、`generation.source` 和独立的 `placeholder_observation`。读取失败的计数是
null，不是零。reliable 只描述已识别格式，不表示实现正确。

| status | 意义 | 退出码 |
|---|---|---|
| ok | 当前可观察事实已读取；不表示验收通过 | 0 |
| uninitialized | 项目没有 .sdlc，不初始化 | 0 |
| no_active_feature | 无活动需求，不自动选择 | 0 |
| partial | 文件/状态部分异常，或观测期间修改 | 1 |
| error | 明确目标、类型或路径无效 | 1 |

参数错误由 argparse 报告，退出码 2。partial/error 仍有 JSON，Skill 应说明诊断，
不靠修改文件或换另一个项目来消除错误。

## 只读、范围与上限

每文件最多读取 2 MiB，每目录最多检查 200 个直接条目，不递归业务树。超限或
截断明确标记。默认需求列表不代表全部外部需求；外部当前选择单独显示。
快照是无锁 best-effort，不保证并发写入者间的事务一致性；观测到变化时报告
不完整，不写锁或缓存。正常/异常/重复查询不修改内容、mode、mtime、文件集合
或 Git index/config。atime 可能由系统读取策略更新，不作为只读失败依据。

## 本地能力与升级

九项上游核心 + 本地 INIT/STATUS = 11 个公共入口。STATUS 来源是本地
src/adapters/STATUS.md 和中文资源，不冒充原版命令。构建身份覆盖采集器及本地化
来源，升级必须保留它们；上游格式变化时评审读取兼容性，不自动迁移业务数据。
不新增阶段状态文件，不要求其他流程补日志，不包含 RULE 自动 INIT、维护者
发版权限平台或自动发布。

## 列表解析边界

仅当章节标签明确表示示例（如 Examples、Parallel Example: … 或“示例”）时才排除
该章节；User Story 标题包含“示例”不导致排除。嵌套清单项仍计为条目；缩进按列表
内容的相对位置解释，因此真正的缩进代码仍会排除。先处理代码围栏，再处理 HTML
注释；代码中的字面量不能隐藏后续任务。保留物理行号。
这是有界的勾选框扫描器，不是完整 Markdown 渲染器。

# 项目初始化

通过 Marketplace 安装插件一次即可。对每个选定业务项目，在进入核心流程前通常执行一次
`sdlc-000-init`。它运行插件内置的初始化器，而不是 `specify init`：不需要安装
uv/specify-cli/业务应用，不访问网络，也不会在项目内复制 Skills、脚本或核心模板。

| 客户端 | 入口 |
| --- | --- |
| Codex | `$sdlc-000-init` |
| Claude Code | `/sdlc-ai-spec:sdlc-000-init` |
| Cursor | `/sdlc-000-init`，或菜单中实际的插件命名空间入口 |

多根工作区中应明确选择项目根目录。对于 `example/helloserver` 这类嵌套模块，
应选择该模块本身，而不是它外层的 Git 根目录。仅安装插件不会自动触发此命令。

## 初始化会创建什么

```text
<selected-project>/.sdlc/
├── init-options.json
├── .gitignore
├── README.md
├── memory/
│   ├── constitution.md
│   └── .constitution-template.json
└── specs/
```

`init-options.json` 默认使用 Bash（`script: sh`）、顺序需求编号、锁定的上游版本、
`sdlc_layout: 1` 和插件版本 `1.0.0-beta`。不会全局保存宿主选择、插件安装路径或
当前需求。`sdlc_version` 记录执行初始化时的插件版本；重复调用不会重写已有版本数据。
它不是文档冻结标记，也不是 Runtime 版本门禁。

`constitution.md` 会按字节复制已安装的本地化核心模板，或项目已有的
`templates/overrides/constitution-template.md`。只有当本次 INIT 真实创建该文件时，
才同时尝试创建 `memory/.constitution-template.json`，记录实际生成字节的 SHA-256
及来源标签。这个 sidecar 只表示 generation provenance：hash 匹配不证明 RULE 从未执行
或文件“未批准”，hash 不同也不证明 RULE 已完成。已有宪法必须原样保留；旧项目或人工
项目缺失 provenance 时，不根据当前模板补造历史记录。

provenance sidecar 是可选的观察数据，不是新的生命周期门禁。若只有 sidecar 写入失败，
已经创建的宪法继续保留，INIT 会明确报告来源未记录。已有损坏 sidecar 也会保留供审查，
不会静默重写。STATUS 可以读取它；RULE/SPEC/PLAN/TASK 都不依赖它。

项目本地 `.gitignore` 内容为 `*`，包括 ignore 文件自身。它用于避免后续误把 `.sdlc`
新加入 Git；已经被跟踪的文件仍然保持跟踪。初始化器可以用只读 Git 命令检查 tracking
状态并给出提醒，但不会修改 Git index、配置、分支或 repository excludes。已有
`.gitignore` 会被保留，并提醒人工确认其现有策略。非 Git 项目不需要 `git init`；
没有 Git 不会阻塞初始化。

INIT 不生成 `feature.json`、规格、方案或任务。后续核心 `sdlc-100-spec` 才会在
`.sdlc/specs` 下创建并选择第一个需求。

## 重复调用与人工状态补全

一个项目通常只需要一次成功调用，与后续切换 Agent 或会话无关。重复调用是安全的：

- `initialized`：新建了 `.sdlc` 项目数据；
- `completed`：为已有兼容的部分初始化目录补齐缺失数据；
- `unchanged`：无需写入，包括不更新已有文件的 mtime。

人工创建的 `.sdlc/memory`、已有 `specs` 和有效的 `feature.json` 当前选择都可以保留。
`init-options.json` 只补缺失 key；已有值和未知配置 key 不会被静默替换。如果显式指定的
编号策略与已有配置冲突，初始化会停止，而不是重新配置项目。

已有 `.specify`、legacy Runtime/工具目录、无法识别的 `.sdlc` 顶层条目、无效 JSON、
非 sh profile、未知 layout 版本、错误文件类型和 symlink 都会停止并要求审查。本能力
刻意不是 legacy 数据迁移工具。不要删除数据，也不要换另一个初始化器来绕过错误。
本地 I/O 失败可能留下部分新建文件；已有文档永远不能作为 reset 目标。修复 I/O 问题后
重新执行即可补全。并发修改同一个项目不提供事务保证。

## 直接脚本契约（支持与工程使用）

Skill 会解析两个绝对路径并调用：

```sh
python3 -I -B "$SDLC_PLUGIN_ROOT/scripts/python/init_project.py" \
  --project "$SDLC_PROJECT_ROOT" --json
```

要求系统已经具备 Python 3.9+ 和 Bash。只有用户要求预览时才使用 `--dry-run`；只有用户
明确要求时才使用 `--feature-numbering timestamp`，它仅改变新项目的默认编号方式。
不存在 force/reset/upgrade 开关。`--project` 必填：脚本不会从插件安装路径、ambient
`SDLC_INIT_DIR` 或外层 Git 仓库猜测业务项目。

成功时 stdout 是一个 JSON 对象，包含 `status`、`dry_run`、选定路径、
created/updated/preserved 路径以及 warnings。`constitution_provenance` 会报告
`recorded`、`would_record`、`preserved`、`not_recorded` 或 `unavailable`，但不会把
可选 sidecar 变成核心流程门禁。失败时以非零退出码和 stderr 错误结束；失败调用或
`--dry-run` 都不等于项目已完成初始化。

## 后续流程与验证边界

INIT 正常情况下报告结果后停止。项目宪法尚未建立时执行 RULE，然后进入 SPEC；已有核心
Skill 在缺少状态时仍按原规则停止，不会静默调用另一个初始化器。用户可以明确授权在同一
请求内先 INIT 再继续其他阶段，但 INIT 本身不授权实施业务代码。

工程检查会把项目数据默认值和宪法字节与锁定 Spec Kit CLI 在三个空项目上的真实初始化
结果比较；合成 fixture 还覆盖保留规则以及与现有核心脚本的互操作。这些检查不能证明原生
客户端发现或模型驱动执行。参见 [VERIFICATION.md](VERIFICATION.md) 和更新后的
[SMOKE-TEST.md](SMOKE-TEST.md)。

## 命名与已有数据

初始化器为新项目生成 SDLC AI SPEC 产品文案和编号 Skill ID。已有 README、宪法、需求、
配置 key 和 `speckit_version`（上游 provenance）保持原样；插件安装不是业务项目数据重写。
legacy `.specify` 检测仍拒绝隐式转换。Runtime Bash override 使用 `SDLC_INIT_DIR`、
`SDLC_FEATURE` 和 `SDLC_FEATURE_DIRECTORY`。为了保持上游行为，已经移除对所有无关
`SPECIFY_*` 名称的一刀切拒绝。核心路径解析允许合法的外部状态 symlink，除非目标指向
插件资源；INIT 自身仍遵守其单独定义的保留与拒绝规则。
不存在旧变量 alias，也不存在 RULE 自动转 INIT。

## 统一公共入口与 STATUS

当前包在 `dist/skills` 下准确提供 11 个入口：九个上游核心 Skill，加本地 INIT 和 STATUS。
不再生成宿主私有 Skill wrapper。所有公共入口都不声明 `user-invocable`、
`disable-model-invocation` 和 `argument-hint`，使用宿主默认行为；这只取代旧的 INIT UI
例外说明，不改变 INIT 已有的数据保留契约。Claude 使用默认 `skills/` 扫描，不再重复配置
自定义路径；其他 manifest 指向 `./skills/`。所有 wrapper 都从自身位置向上两级解析包根。

STATUS 是可选本地只读 utility，不是另一个生命周期阶段，也不是上游 command。它可以读取
不完整/未初始化状态，但不会持久化需求切换、不会初始化，也不会执行建议的下一 Skill。
参见 [STATUS.md](STATUS.md)。现有核心正文、模板和 Runtime 行为不会为了 STATUS 增加历史写入。

## 默认文档语言

新 `.sdlc/README.md` 来自经过审查的中文 `references/PROJECT-README.md`。默认宪法包含
中文示例文本和双语标题锚点。项目已有 override、README 或宪法继续按字节保留；重复 INIT
不是翻译工具。缺少打包 README 时会像缺少核心模板一样在写入前失败。
输出语言指引禁止人为加入“中文注释”“中文说明”等语言标签，但不会删除合法业务注释，
也不会因此增加额外写权限。

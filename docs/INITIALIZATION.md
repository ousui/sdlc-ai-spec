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

## 存储选择与归拢

遵循 [工作区与权威资料库](STORAGE.md)。先执行只读发现；有本地副本时使用本地，
无本地时告知权威路径并选择共享或创建独立副本。程序返回 `needs_choice` 时尚未
初始化。明确模式使用 `--mode shared` 或 `--mode local`，不重复询问已提供的选择。

新建本地默认 `--seed knowledge` 导入宪法与存在的 `memory/long-term.md`；重复
`--feature` 可选择需求目录，`--seed none` 表示空白。已有资料不刷新，当前需求选择
不复制。main 的显式归拢与 worktree 的显式导入使用 `store_changes.py` 的
prepare/apply/recover 流程。指定权威路径及额外来源由 main 使用 `sdlc_store.py register`
登记；不能借登记静默移动已有权威资料。
已有且与权威库分离的本地根目录软链接会解析为实际资料目录；默认初始化及显式
`--mode local` 均在该目录补缺，保留根目录链接。
根链接指向尚不存在的独立目标时，也可在其已有父目录下完成首次初始化。`created`
在项目内使用相对路径，项目外使用绝对路径；`imported` 保持资料库内相对名称，
只列本次实际创建的导入文件。返回结果与实际创建及导入一致，重试不重写已有文件。

## 初始化会创建什么

```text
<effective-store>/
├── init-options.json
├── .gitignore
├── README.md
├── memory/
│   ├── constitution.md
│   └── .constitution-template.json
└── specs/
```

`init-options.json` 默认使用 Bash（`script: sh`）、顺序需求编号、锁定的上游版本、
`sdlc_layout: 1` 和执行初始化时的当前插件版本。不会全局保存宿主选择、插件安装路径或
当前需求。`sdlc_version` 记录执行初始化时的插件版本；重复调用不会重写已有版本数据。
它不是文档冻结标记，也不是 Runtime 版本门禁。

`constitution.md` 会按字节复制已安装的本地化核心模板，或项目已有的
`templates/overrides/constitution-template.md`。只有当本次 INIT 真正从模板创建该文件时，
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
没有 `.git` 标记时，Git 缺失不会阻塞初始化。已有 `.git` 标记时，Git 不可用、查询失败
或超时会停止工作区身份发现；修复 Git 访问后重试，不创建会遮蔽权威资料的本地模板库。

INIT 不新建需求或 `feature.json`；明确选择导入时可以复制已有需求的规格、方案及任务。后续核心 `sdlc-100-spec` 才会在
`.sdlc/specs` 下创建并选择第一个需求。

## 重复调用与人工状态补全

一个项目通常只需要一次成功调用，与后续切换 Agent 或会话无关。重复调用是安全的：

- `initialized`：新建了 `.sdlc` 项目数据；
- `completed`：为已有兼容的部分初始化目录补齐缺失数据；
- `unchanged`：无需写入，包括不更新已有文件的 mtime。

人工创建的 `.sdlc/memory`、已有 `specs` 和有效的 `feature.json` 当前选择都可以保留。
`init-options.json` 只补缺失 key；已有值和未知配置 key 不会被静默替换。如果显式指定的
编号策略与已有配置冲突，初始化会停止，而不是重新配置项目。
配置候选与普通读取保持相同校验：`feature_numbering` 优先，其缺失时兼容
`branch_numbering`，两者均缺失时默认 `sequential`。显式非法的现代字段不能由旧值替代；
非法候选在发布前拒绝，保留原配置和 prepared 事务。

已有 `.specify`、legacy Runtime/工具目录、无法识别的 `.sdlc` 顶层条目、无效 JSON、
非 sh profile、未知 layout 版本、错误文件类型和 symlink 都会停止并要求审查。本能力
刻意不是 legacy 数据迁移工具。不要删除数据，也不要换另一个初始化器来绕过错误。
本地 I/O 失败可能留下部分新建文件；已有文档永远不能作为 reset 目标。修复 I/O 问题后
重新执行即可补全。首次本地导入先在同级临时目录完整保存 `.init-pending.json`，记录
选定的权威路径、知识/需求选择与导入字节，再用禁止替换已有目标的原子目录发布使
本地库可见；即使并发出现空目录也不覆盖。可见的本地库始终已包含导入意图，随后
才逐文件补齐业务数据，成功后删除意图。中断后须保留该记录，并使用
相同的 `--seed`、`--feature` 和编号选择重试（`--mode auto` 与 `--mode local` 均可
恢复本地库）。重试按原字节补缺，保留中断后已有的用户文件，不静默改用已变化的来源
内容；权威路径或选择变化时停止并要求检查记录。完成过的本地库不因此重新导入。
目录发布前进程退出时，不会产生本地 `.sdlc`，重试重新发现并读取来源；进程退出可能
留下同级 `.sdlc-init-*` 临时目录，它不参与资料库发现或导入，也不会在重试时被递归
清除。确认其中没有需要保留的数据后才可人工清理。目录发布后退出则使用已保存意图续跑。
恢复时 `imported` 只列本次真实创建的文件，已有选定文件单列为 `preserved_imports`。
选定 seed 的每个文件叶子及其父目录都须通过类型检查；目录不能被认作已保留的文件。
类型冲突期间保留用户对象及 pending；修正后继续使用已保存的字节，不重新读取已变化
或暂时离线的来源，也不覆盖已有普通文件。
首次本地初始化指定 `--feature` 时，权威来源缺失或所选需求不存在会在创建本地库前
停止；不指定需求时仍可选择空白本地初始化。
发现权威库后已选择导入时，来源在快照开始时缺失或读取中消失、被替换须停止，不能退回模板
初始化；真实空来源仍可初始化，但发布前也须复验。已有中断记录仍按保存的字节续跑。
来源知识文件的等价名称识别若遇到权限或 I/O 错误，同样停止，不能漏掉已选知识后
退回模板；错误消除后重新执行首次导入即可。中断续跑不重新依赖来源角色识别。
快照中的已知来源文件在身份查询时缺失或被替换，同样停止。候选规范路径缺失或身份不一致时，须按
各级已知来源父目录的原生查找属性证明名称非等价才可排除。连续 ENOENT、独立条目的
缺失或 inode 变化均不作为证明；所需属性不可用时停止，不使用其他探针或退回模板。
已有宪法仍缺少 provenance 时，不凭初始化意图或内容相等补造历史记录，并明确提醒。
中断标记存在时，普通阶段与导入/归拢来源检查会停止，不能把它当作完成的资料库。
协作写入使用资料库锁；初始化仍按文件补缺，不提供整目录原子事务。外部工具不受插件锁控制。
首次导入、补缺和续跑在预览及持锁发布前重新校验本次写入目标，控制目录内的别名和
权威库的外置产物引用不能绕过隔离。已存在且保持不变的文件不因此增加其他副本依赖；
目标归属未知时在写入前停止，不通过独立条目的查找结果或候选 inode 分歧排除重叠；
来源离线的中断续跑也遵守这一目标校验，不重新读取来源内容。
相关别名目录必须完整扫描；目录短暂缺失或 inode 替换不能解释为没有别名。
扫描失败保留既有文件及中断记录，恢复访问条件后仍可按保存的内容续跑。
不可访问的祖先不能因别名中的 `..` 折叠而被忽略。
provenance 的目标单独不可写时仍保留已创建的宪法并报告警告。

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
首次本地导入的目录发布使用系统禁止覆盖的原子重命名：macOS 的 `renamex_np`、Linux
的 `renameat2`，或 Windows 的非替换 `rename`。这不增加 Python 第三方依赖；系统或
文件系统不支持时明确失败，不退回可能替换现有目录的操作。普通初始化与已有库补缺不依赖该操作。

成功时 stdout 是一个 JSON 对象，包含 `status`、`dry_run`、选定路径、
created/updated/preserved 路径以及 warnings；发现和待选择结果只包含绑定与选择信息。`constitution_provenance` 会报告
`recorded`、`would_record`、`preserved`、`imported`、`not_recorded` 或 `unavailable`，但不会把
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
canonical 中文示例文本和标题。项目已有 override、README 或宪法继续按字节保留；重复 INIT
不是翻译工具。缺少打包 README 时会像缺少核心模板一样在写入前失败。
输出语言指引禁止人为加入“中文注释”“中文说明”等语言标签，但不会删除合法业务注释，
也不会因此增加额外写权限。

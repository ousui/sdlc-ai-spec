# 公共 Skills 与简体中文呈现

## 当前交付

九核心、INIT 和 STATUS 共 11 个入口全部位于 `dist/skills/<id>/SKILL.md`。
不保留生成包内宿主私有 Skill，不输出 `user-invocable`、
`disable-model-invocation`、`argument-hint`；使用宿主默认选择行为。
Claude 默认扫描 skills/，不重复声明；Codex/Cursor 显式指向 ./skills/。
所有入口从已加载 Skill 目录向上两级定位插件；不从模型名猜宿主。
这项展示/选择边界是用户批准的调整，流程中的写入与授权要求未改变。

## 中文范围与等价宪法

Skill 摘要、完整流程正文、入口/绑定说明及 INIT/STATUS 指引使用简体中文，不是缩写
摘要替代上游正文。每个能力仅维护一份译文，再绑定三宿主调用差异。

本期将此前“英文模板骨架＋中文填写”扩展为：五类默认模板的说明、示例、
自然语言占位说明均中文化；标题保留英文定位锚点并附中文释义，章节层级不变。
文件名、机器占位符、JSON/YAML 键、事件键、参数、任务编号和实际代码不翻译。
`User Story`、`Success Criteria`、`NEEDS CLARIFICATION`、`FR-001`、`T001`、
`[US1]`、`[P]` 等继续保留。不是通过附加“中文说明”来替代正文翻译。

`src/templates/` 仍是英文的名称/路径投影，用于独立上游比较；
`src/locales/zh-CN/templates/` 是五类审查后的模板译文，生成到 `dist/templates/`。
SPEC 原文代码围栏中的 requirements.md 是文档内容示例，不是可执行代码；
只将这一完整、准确绑定的片段替换为 `fragments/requirements.md`，保留 16 项的
顺序、勾选语法、条件和生命周期，不放开其他代码围栏或 JSON 的翻译检查。

初始化 README 来自 `project-readme.md`，生成到包内 references，再由 INIT
正常创建缺失的 `.sdlc/README.md`。新初始化的默认宪法也直接复制本地化模板。
已有 README、宪法、用户覆盖模板及其他业务文档保持原有保留规则；插件更新不
批量改写已有产物。再次调用 INIT 不承担迁移或翻译已有文件的职责。

输出语言指引要求直接使用“注释”“说明”，禁止在业务内容中添加“中文注释”
“中文说明”等标签；不为标注语言新增 HTML 注释，不删除有业务意义的原注释。
该指引不授权额外写操作，也不保证每次模型输出一致；客户端实际加载的包和
运行上下文仍需区分。此规则不能被用来清空已有注释或清理整个业务仓库。

保留原版逻辑、流程、条件、数量限制与缺陷；不在本项目修复上游 bug。已纠正
本项目引入的事件键改名、无关环境变量整体拒绝、外部合法状态别名整体拒绝。
本地化不扩展支持的核心/Bash/no-events/no-extensions/no-presets profile。

## 来源、编译顺序与检查

`src/upstream/` 保持锁定原文。已有英文渲染与名称/路径适配先完成，随后只将
明确的宿主命令/宿主值映射成命名占位符，得到三宿主完全一致的待译正文。
中文文件位于 `src/locales/zh-CN/workflows/<source-id>.md`，`catalog.json` 将
实际待译全文与译文字节分别绑定，并保存自然语言元数据的原文/译文。
绑定说明、INIT/STATUS 和项目 README 有独立来源绑定。模板和内置清单还分别
绑定完整英文输入与译文；这些资源全部进入构建身份。最后再做无损 factoring，写入 dist。

```sh
uv run --locked python -B tools/localize.py check
uv run --locked python -B tools/build.py --marketplaces
uv run --locked python -B -m unittest discover -s tests -v
```

编译/安装/运行不调用网络、模型或翻译服务。`check` 验证九项覆盖、来源新鲜度、
已审查译文字节、核心指令代码块与内联代码的精确多重集合、命名占位符和标题层级；
模板的自然语言示例单独检查标题锚点、字段、任务/清单顺序、代码和路径。
单元测试包括过期原文、篡改译文、即使重算摘要仍损坏的参数等失败对照。
源码英文渲染仍保留与独立原版 CLI 产物的完整比较，不能用中文摘要取代。
这些程序检查不证明语义完全等价或模型实际输出；译文还需要逐条对照审查。
当前 catalog 的 reviewer 是 AI 源文对照审查声明，不冒充用户逐条批准。

## 升级与增量补译

1. 在外部干净上游 checkout 选择准确版本，沿用 `tools/upgrade.py prepare`。
2. 未变化的待译内容可复用译文，升级不因仓库 SHA 改变就全量重译。
3. 来源/渲染结果/元数据发生变化时，过期翻译会阻止新包构建。候选记录变为
   `LOCALIZATION_REQUIRED`，现有正式源码与 dist 不变；不回退英文伪装成功。
4. 使用候选自身的 `tools/localize.py export --out <新的外部目录>` 导出当前
   英文待译输入。只在候选的 `src/locales/zh-CN/` 更新受影响的译文和元数据。
5. 完成原文逐条审查后，以显式命令更新来源/译文摘要，不手算或直接改候选摘要：

```sh
# 在候选目录内；该操作记录已完成的审查，不是自动翻译或身份认证
uv run --locked python -B tools/localize.py record \
  --command constitution --reviewer '<实际审查人或 AI 审查标识>' --reviewed
uv run --locked python -B tools/localize.py check
```

若 description 原文变化，先在 catalog 对应 metadata 中明确更新
source 与 zh_CN；record 不会替新原文自动批准旧译文。未交付的 argument-hint 不作为翻译门禁，原始来源仍保留。绑定/INIT 说明变更可以用
`--resource binding` 或 `--resource init`，同样先完成对照审查。

模板或固定清单变更后，分别完成逐条语义审查，再记录：

```sh
uv run --locked python -B tools/localize.py record \
  --presentation spec-template --reviewer '<实际审查标识>' --reviewed
uv run --locked python -B tools/localize.py record \
  --presentation requirements --reviewer '<实际审查标识>' --reviewed
uv run --locked python -B tools/localize.py record \
  --resource project-readme --reviewer '<实际审查标识>' --reviewed
```

`export` 同时导出五类英文模板和内置清单供增量审查。仅修改一段译文后更新
摘要并不能证明译意正确，必须完成源文对照。结构或机器参数损坏时，record
也会拒绝写入；缺失或过期内容继续阻断候选，不回退到英文伪装完成。

随后计算候选当前翻译目录摘要（程序维护，不是 Git author 身份证明）：

```sh
uv run --locked python -B -c 'from pathlib import Path; import sys; sys.path.insert(0,"tools"); from upgrade import localization_digest; print(localization_digest(Path.cwd()))'
```

外部 review JSON：

```json
{
  "decision": "refresh-localization",
  "reviewer": "<实际审查标识>",
  "upstream_sha": "<候选准确上游 SHA>",
  "localization_digest": "<上述程序输出>"
}
```

```sh
uv run --locked python -B tools/upgrade.py refresh-localization \
  --record /absolute/external/candidate.upgrade.json \
  --review /absolute/external/translation-review.json
```

refresh 只接受因本地化而受阻的 detached 候选，核对源 HEAD 和所有非翻译文件
保持不变，然后验证中文并重新生成、冻结完整候选。代码/上游/旧 dist 擅自变化
会拒绝恢复，必须重新准备；不能用补译入口夹带其他变更。完成后必须重新跑测试
和 AI review，报告绑定新的完整候选摘要；旧 PASS 不再有效。

同版本重放验证稳定性；来源文本变化的夹具验证“过期→补译→重新冻结”路径。
这不等于当前已切换正式上游版本，也不保证未来任意上游架构变化都无需人工适配。
遇到新命令、英文渲染不再对应或未支持的结构，继续停止并审查。

## 项目宪法的生成来源记录

新项目 INIT 使用已审查的中文默认宪法（或项目覆盖模板）创建 `constitution.md` 时，
可同时记录实际生成字节的 SHA-256 与来源。该项目侧记录不是翻译 catalog、不是
当前模板摘要，也不因插件升级或中文模板更新而刷新；因此 STATUS 可以区分“当前
文件与历史生成基线一致/不同”，而不用拿旧项目与新模板比较。旧项目缺记录时不
根据当前中文模板补造历史，插件更新也不自动翻译或覆盖项目宪法。

## 边界

STATUS 属于本地中文资源，不在九项上游译文列表中。`--resource status` 可记录
其来源与中文说明的已完成审查。此处没有维护者发版平台、权限规则或 RULE 自动初始化。review JSON
不是访问控制；也没有改变远端分支、创建 tag 或发布 Release。现有移植审查中
已确认继承的上游问题保持记录，不通过翻译暗中修正。

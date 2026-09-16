# 公共 Skills 与简体中文呈现

## 当前交付

九核心、INIT 和 STATUS 共 11 个入口全部位于 `dist/skills/<id>/SKILL.md`。
不保留生成包内宿主私有 Skill，不输出 `user-invocable`、
`disable-model-invocation`、`argument-hint`；使用宿主默认选择行为。
Claude 默认扫描 skills/，不重复声明；Codex/Cursor 显式指向 ./skills/。
所有入口从已加载 Skill 目录向上两级定位插件；不从模型名猜宿主。
展示与选择策略不改变流程中的写入与授权要求。

## 中文范围与等价宪法

本项目采用 **Localization Contract v2**。目标不是“全仓中文”，而是把面向使用者和
业务产物的自然语言统一为简体中文，同时把上游来源、机器契约和升级对照保持稳定。
本地化只改变呈现，不改变 Skill 的业务逻辑、步骤顺序、提问数量、停止条件、默认值、
写入对象、授权边界或上游既有缺陷。

### 仓库语言分层

仓库中的“英文”和“中文”承担不同职责，不以全仓统一语言为目标：

1. `src/upstream/**` 是锁定 Spec Kit 原始来源，保持原始字节，不翻译。
2. `src/templates/**` 是经过产品名称/路径适配后的英文模板基线，用于独立上游对照。
3. `src/adapters/*.md` 是本项目原创绑定、INIT/STATUS 和项目 README 的英文 source baseline；对应中文审查版本位于 `src/locales/zh-CN/`。
4. `src/locales/zh-CN/**` 保存面向 Agent/使用者的中文 canonical 呈现；机器契约保持原样。
5. `dist/**` 是最终插件产品，由构建器生成，不手工翻译或编辑。
6. `AGENTS.md`、`docs/*.md` 等本项目原创维护文档不属于产品 source→translation 链，默认直接使用简体中文；其中技术 token 和机器契约保持原样。

因此，`src/adapters/` 中出现英文不是“漏翻译”，而是为了保留“英文适配源 → 审查后的
中文呈现 → 最终 dist”的可审计链路。目录职责见 `src/adapters/README.md`。

### Canonical 写入与历史读取

新生成的默认产物使用简体中文 canonical presentation：自然语言标题、字段标签、表头、
说明、理由、测试描述、任务描述和固定响应使用中文，不再默认输出“英文标题（中文）”
双语形式。章节层级、顺序、必填/可选含义和业务语义保持不变。

读取已有产物采用 **Read Many / Write One**：

- 新写入：只使用当前审查后的中文 canonical 标题和字段；
- 读取兼容：识别上游英文、历史双语和当前中文标题；
- 已有章节：继续使用原标题，不为了本地化新建同义章节或批量改名；
- 已有业务文件、用户自定义模板、README 和宪法：插件升级不自动翻译或覆盖。

`src/locales/zh-CN/catalog.json` 的 `contract.structural_aliases` 保存有限的结构别名，
用于维护者审查和兼容性测试，不是任意字符串替换器。新增或改变结构映射必须显式审查。

### 必须保留的机器契约

以下内容不是普通产品文案，不因本地化改名：

- Skill/命令 ID、文件名、目录和路径；
- JSON/YAML key、环境变量、CLI 参数、事件名和配置键；
- 状态/严重级别等机器枚举；
- `FR-001`、`SC-001`、`T001`、`CHK001` 等追踪编号；
- `[US1]`、`[P]`、`- [ ]` / `- [x]` 等任务/复选框语法；
- `[NEEDS CLARIFICATION: ...]` 标记本身；
- 实际代码、API/schema 字段和协议标识。

API Token、Cloudflare、DNS、HTTP、JSON、Python、Go 等必要技术术语按项目实际用法保留，
不为了“全中文”制造不常用或错误的译名。

固定交互文案属于本地化范围。CLAR 的问题/推荐/建议/答题说明、SPEC 的澄清块、
IMPL 的继续确认、HUMA 的表头及 Hooks 展示文本都使用中文；但输出语言和输入兼容分离：
原有 `yes` / `recommended` / `suggested` / `proceed` / `continue` / `stop` 等英文输入继续
有效，并可增加 catalog 中已审查的中文等价别名。别名不得改变问题数量、等待用户确认、
停止条件或写入权限。

代码围栏和反引号本身不是“禁止翻译”的充分条件。自然语言示例可以在完成来源审查后
本地化；可执行命令、参数、路径、变量、机器 token 和真实代码标识仍由机器契约检查保护。

### 默认模板和动态产物

五类默认模板（规格、方案、任务、宪法、清单）的自然语言标题、字段、说明和示例采用
canonical 中文。`src/templates/` 仍保存英文名称/路径投影，用于独立上游比较；
`src/locales/zh-CN/templates/` 保存审查后的中文版本，构建到 `dist/templates/`。

SPEC 原文代码围栏中的 requirements.md 是文档内容示例，不是可执行代码；只将这一完整、
准确绑定的片段替换为 `fragments/requirements.md`，保留 16 项的顺序、勾选语法、条件和
生命周期。PLAN 动态生成的 `research.md`、`data-model.md`、`contracts/`、`quickstart.md`
没有新增强制模板；工作流只要求其自然语言标题和说明使用中文，项目实际实体名、字段名、
协议、命令和代码标识保持原样。

初始化 README 来自 `project-readme.md`，生成到包内 references，再由 INIT 正常创建缺失的
`.sdlc/README.md`。新初始化的默认宪法也直接复制本地化模板。再次调用 INIT 不承担迁移
或翻译已有文件的职责。

输出语言指引要求直接使用“注释”“说明”，禁止在业务内容中添加“中文注释”“中文说明”
等语言标签；不为标注语言新增 HTML 注释，不删除有业务意义的原注释。该指引不授权额外
写操作，也不保证每次模型输出一致；客户端实际加载的包和运行上下文仍需区分。

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

编译/安装/运行不调用网络、模型或翻译服务。`check` 验证九项覆盖、来源新鲜度、已审查译文字节，以及 Localization Contract v2 的机器/结构契约：命名占位符、ID、路径、命令/参数、配置 token、复选框语法、代码围栏类型和标题层级等。自然语言标题、字段和示例允许按已审查映射翻译，不再要求英文标题前缀或所有反引号文本逐字节相等。
单元测试包括过期原文、篡改译文、即使重算摘要仍损坏的机器 token/参数/ID、标题层级漂移等失败对照，并覆盖旧英文、历史双语和新中文结构的读取兼容。
源码英文渲染仍保留与独立原版 CLI 产物的完整比较，不能用中文摘要取代。
这些程序检查不证明语义完全等价或模型实际输出；译文还需要逐条对照审查。
catalog 的 reviewer 绑定精确来源与译文字节的实际审查者；任何来源或译文字节变化都必须重新审查并更新记录，旧 reviewer 不自动批准新字节。

### 记录前只读预检

增量补译完成后，先使用 `precheck` 对**当前待记录字节**执行只读机器/结构检查。
它不要求旧的 source/translation 摘要仍匹配，因此适合在 `record` 之前发现机器值、
命令、路径、参数、围栏结构或本地资源关键职责的损坏：

```sh
uv run --locked python -B tools/localize.py precheck --command constitution
uv run --locked python -B tools/localize.py precheck --presentation spec-template
uv run --locked python -B tools/localize.py precheck --resource binding
```

`precheck` 不写 `catalog.json`、不把译文标记为 reviewed，也不代表语义审查完成。
正确顺序是：**补译 → precheck → 源文/译文语义复核 → record → 全量 check**。
`record` 和 `check` 继续调用同一底层机器/结构检查，不能因为预检通过而跳过。

机器契约保护采用有限结构而不是“所有英文逐字节冻结”：行内代码只抽取命令、路径、
参数、变量、ID、状态等机器原子；Markdown 表格把机器值与稳定行标识绑定；JSON 类
标量保留 key/value 对应；实际 shell 命令及结构化代码围栏保持机器语义。自然语言标题、
注释和伪代码式任务说明仍可按已审查规则本地化。遇到无法可靠分类的新结构时应停止
并审查，不通过增加忽略规则让升级继续。

## 关键职责与有限别名的回归边界

`tests/test_localization_review.py` 独立固定当前已审查的结构别名、历史读取形式
和输入别名。日常增量补译不得自行增加、删除或重解释这些映射；上游确需新映射时，
先报告差异并取得显式审查，再同步 catalog 与独立测试期望。测试失败不能通过
读取同一份 catalog 作为期望值、自动接受新别名或删掉负向用例来绕过。

关键职责同时检查中文源文及经 loader 完整还原的 Codex、Claude、Cursor 正文：
`checklists/requirements.md` 由 SPEC/CLAR 维护，自定义清单由 HUMA 生成且归评审者；
HUMA 新条目未勾选，IMPL 对未勾选项先询问并等待、不修改清单；CONV 只追加缺口任务，
不改代码、规格或方案，无缺口时保持 `tasks.md` 字节不变。
不要把包含 binding 占位符的共享片段当成完整执行正文来判断职责丢失。

这些是有限的关键条款回归，包含机器 token 不变但“不得”被改为“必须”的负向对照；
它们不是通用语义证明，也不能证明模型真实执行。合理的上游条款变化应重新对照来源
审查后调整期望，不能为让升级通过而机械更新断言。新的 AI 补译审查必须记录实际
AI 审查标识，不沿用历史 `User-approved` 或冒记人工已经批准新字节。

## 升级与增量补译

1. 在外部干净上游 checkout 选择准确版本，沿用 `tools/upgrade.py prepare`。
2. 未变化的待译内容可复用译文，升级不因仓库 SHA 改变就全量重译。
3. 来源/渲染结果/元数据发生变化时，过期翻译会阻止新包构建。候选记录变为
   `LOCALIZATION_REQUIRED`，现有正式源码与 dist 不变；不回退英文伪装成功。
4. 使用候选自身的 `tools/localize.py export --out <新的外部目录>` 导出当前
   英文待译输入。只在候选的 `src/locales/zh-CN/` 更新受影响的译文和元数据。
5. 补译后先只读预检，再完成原文/译文逐条语义审查；确认无误后才以显式命令
   更新来源/译文摘要，不手算或直接改候选摘要：

```sh
# 在候选目录内；precheck 不写 catalog，也不构成审批
uv run --locked python -B tools/localize.py precheck --command constitution

# record 只记录已经完成的审查，不是自动翻译或身份认证
uv run --locked python -B tools/localize.py record \
  --command constitution --reviewer '<实际审查人或 AI 审查标识>' --reviewed
uv run --locked python -B tools/localize.py check
```

若 description 原文变化，先在 catalog 对应 metadata 中明确更新
source 与 zh_CN；record 不会替新原文自动批准旧译文。未交付的 argument-hint 不作为翻译门禁，原始来源仍保留。绑定/INIT 说明变更可以用
`--resource binding` 或 `--resource init`，同样先运行对应 `precheck --resource ...` 并完成对照审查。
有英文 adapter source 的资源比较有限机器契约；STATUS 和 output-language 属于本地维护策略，
以独立固定的高风险职责条款保护，不伪造上游翻译来源。资源 `record` 也会执行这些检查，
不能只靠重算摘要接受职责漂移。

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
这不等于正式上游版本已切换，也不保证未来任意上游架构变化都无需人工适配。
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
不是访问控制；也没有改变远端分支、创建 tag 或发布 Release。继承的上游问题保持原有行为，不通过翻译暗中修正。

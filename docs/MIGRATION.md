# 上游移植差异与行为边界

源码基线为 Spec Kit v1.0.5，提交 `a4e25ce6b96dc8e85f84206c6a54353fa9c5260b`，
配置为 Bash，不启用 events、presets 或 extensions。这不表示与完整 CLI 等价。

| 变更 | 原因 / 保留的行为 |
| --- | --- |
| 九项原始命令源码逐字节保留 | 不修改原始来源；已审查的派生中文正文保留步骤和机器契约 |
| `speckit-*` 可调用引用映射为宿主原生 `sdlc-*` 引用 | Codex `$`、Claude 插件命名空间、Cursor `/`；示意性 hook 变体仍仅作示例 |
| `.specify` 状态迁至项目 `.sdlc`；默认 `specs` 迁至 `.sdlc/specs` | 保留文件名、字段键、编号及显式需求覆盖 |
| 核心模板/脚本移至插件资源 | 项目覆盖仍从项目 `.sdlc` 解析；不共享状态 |
| 业务根目录不再回退到脚本位置 | 缺少项目时报错；仍支持显式目标与最近项目 |
| 使用小型 Python 路径检查保护插件资源 | 脚本写入前验证规范路径、符号链接目标和显式需求路径；不是沙箱或通用授权引擎 |
| `specify preset resolve spec-template` 指令改用本地 `resolve-template-path.sh` | SPEC 获得供复制/读取使用的已有路径；原内容解析器不变；所选配置下项目覆盖优先于包内核心模板 |
| 原生命令提示使用本次调用宿主，不使用保存的默认集成 | 同一项目可由不同宿主先后使用 |
| 生成 Skill 增加绑定前言 | 标识资源、解析项目、每次工具调用传递变量，并在所选支持范围之外明确失败 |
| 插件打包与来源记录 | 三个原生清单发现同一组 11 个共享入口 |

`check-prerequisites.sh`、`resolve-template.sh` 和 `setup-plan.sh` 除标记路径迁移外，
与上游逐字节一致。`common.sh`、`create-new-feature.sh` 和一处 setup-tasks 诊断
使用明确检查的补丁锚点。原解析器中未启用的可选代码不重写；不安装可选生态组件，
也不宣称支持它们。

`src/upstream/templates/commands` 是经过审查的原始源码，不是复制的生成 Skill。
独立构建器在应用移植差异前，先与已安装上游 CLI 的三个 Agent 输出比较。
归一化只允许封闭的名称/路径白名单，不删除任意段落、空白、规范性用词、章节或任务
要求。额外增加正文规则必须作为失败对照。原生 YAML frontmatter 按结构比较；
命令正文在迁移前逐字节比较，迁移后按显式映射比较。

工程检查还在合成夹具上比较上游和移植脚本的退出码、stdout、stderr 及生成文档。
比较只归一化地址变化与有意纠正的 Codex 脚本提示，不能替代真实业务或模型驱动验收。

## 单包共享与原生发现

`tools/build.py` 先用已审查的源码渲染器及既有迁移规则生成完整宿主正文，再将
逐字节相同部分提取为一个工作流文件；仅准确不同的子串成为 `bindings/<host>.json`
中的具名字面片段。行结构不一致时停止。`load_workflow.py` 进行非递归的字面绑定，
输出完整正文，不启动子进程、不访问网络、不写入。全部 27 份本地化前的英文正文
均在地址白名单下与原 CLI 输出独立比较。解析后的中文正文还需匹配已审查完整译文，
并通过来源新鲜度及机器片段检查。共享包装入口仅省略获准的展示/选择字段，保留
显式调用宿主、原始用户输入及完整读取输出要求。截断必须通过有界分页处理，不得静默接受。

11 项能力仅位于 `skills/`，包含本地 INIT 和 STATUS。Claude 默认扫描该目录；
Codex/Cursor 显式选择相同目录。不分发通用根清单。路径规则参考：

- https://developers.openai.com/plugins/build/plugins
- https://code.claude.com/docs/en/plugins-reference
- https://cursor.com/docs/reference/plugins

基于文档的静态字段/路径检查不等于原生宿主认证。

共享产物模板使用 `sdlc-200-plan` 等标准能力 ID，不使用某个宿主的字面调用前缀。
这些是指令引用，不是 shell 命令。包装入口/加载后的工作流保留原生调用语义。
这是单独列入白名单的纯引用变化；其他文字、空白、清单所有权和业务步骤仍须精确比较。

根 Marketplace 目录清单均引用 `./dist`。组件不引用此安装边界之外的路径。
来源映射、受监视生成器代码及失败即停止的候选接受流程见 [UPGRADING.md](UPGRADING.md)。

## 自动工程验证之外的范围

真实业务项目使用；实际 Codex/Claude/Cursor 安装、发现和调用；模型质量；
Windows/PowerShell；同一需求的并发写入；旧数据迁移；GitHub 操作。

项目级 INIT 创建最小 `.sdlc` 项目结构。准确的项目数据映射及其与上游安装器的
差异见 [INITIALIZATION.md](INITIALIZATION.md)。九项原始命令源码和上游锁保持不变。
验证命令与证据边界见 DEVELOPMENT.md 和 VERIFICATION.md。

## 本地 INIT 来源依据

参考来源是锁定的 `src/specify_cli/commands/init.py`：其
`ensure_constitution_from_template` 只创建缺失的宪法，`init_opts` 持久化脚本、
编号和上游版本默认值。本项目保留这些项目数据行为及项目覆盖优先级。Agent 注册表、
CLI/集成设置、共享脚本/模板、presets、events 和 Git 创建明确不纳入项目初始化移植。
`.sdlc/.gitignore`、布局标记、README 及安全补全部分状态属于本地新增能力。

本地辅助工具不称为 `specify init`，也不调用该可执行文件。
本地 INIT 成功不表示与完整 CLI 初始化等价。

## 产品标识与编号入口

产品命名由 [NAMING.md](NAMING.md) 和 [naming-map.json](naming-map.json) 约束。
原始源码、锁文件和上游比较基准不变。生成的 Skill 目录、name 字段、完整工作流
文件名、绑定键和 loader ID 使用已批准的四字母阶段名称。产品 ID 为 `sdlc-ai-spec`，
显示名为 **SDLC AI SPEC**。既有项目数据路径不变。

Runtime 声明/调用方及输出提示使用 SDLC 标识。三个宿主均保留显式宿主绑定和
输入处理契约。生成入口省略获准的展示/选择元数据；原始来源元数据仍参加独立上游
比较。兼容性/来源例外列于 NAMING.md。不拒绝无关的过时环境变量前缀；公共覆盖
使用文档规定的 SDLC 名称。

完整工作流等价检查使用独立枚举的逆向映射，并保留正文变异失败对照。
脚本末端比较仅枚举路径/函数/参数重命名，不允许宽松的空白或业务规则归一化。
九项上游工作流、INIT 幂等性及原生测试边界保持不变。

## 共享 Skills 与本地化差异

事件键保留 `before_specify/after_specify`；无关 `SPECIFY_*` 环境变量不导致整体
拒绝；外部状态别名只要不指向插件就允许使用。外部插件资源仍需共享资源隔离。
上游缺陷（包括前置检查中的状态持久化）不在移植层独立修复。

中文资源位于 src/locales/zh-CN。依赖英文的渲染先于翻译，公共片段提取在翻译后
执行。五类已审查模板呈现和内置需求清单已本地化。原始英文模板映射保留在
src/templates；双语标题锚点、占位符、代码路径和任务语法分别检查。
升级不重写已有项目数据。检查、审查限制及恢复流程见 [LOCALIZATION.md](LOCALIZATION.md)。

## 统一公共入口与 STATUS

当前包在 `dist/skills` 中恰好提供 11 个入口：九项上游核心 Skill 加本地 INIT 和
STATUS，不保留宿主私有包装入口。所有公共入口省略 `user-invocable`、
`disable-model-invocation` 和 `argument-hint`，使用宿主默认行为。INIT 保留已有项目数据。
Claude 默认发现 `skills/`，不重复配置自定义路径；其他清单选择 `./skills/`。
所有包装入口向上两级解析包根目录。

STATUS 是可选本地只读辅助能力，不是额外生命周期阶段或上游命令。它容忍未完成/
未初始化状态，不持久化需求切换、不初始化、不执行建议的下一项 Skill。
详见 [STATUS.md](STATUS.md)。不为 STATUS 保存历史而修改现有核心正文、模板或运行行为。

## 路径解析与文档呈现

SPEC 使用基于既有 resolve_template 函数的本地纯路径适配器。
resolve-template.sh 仍返回内容，其其他调用方不变。未修改原始命令源码或上游 Bash 脚本。

STATUS 根据明确标签识别示例章节，支持嵌套清单，并在 HTML 注释之前识别围栏/
缩进代码。它保持只读，不改变上游工作流行为。

默认模板输出、准确绑定的内置需求示例和新项目 README 均为已审查中文呈现。
只有完整模板准确相等时，才可映射回英文，供独立基线及脚本比较；未知或修改过的
文本直接失败，不剥离或宽松重译。已有项目文件保留，包括英文模板和自定义模板。

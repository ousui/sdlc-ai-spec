# 安装与固定 beta 版本更新

产品：**SDLC AI SPEC**，插件 ID `sdlc-ai-spec`，版本 `1.0.0-beta`，作者 Blade。
Marketplace：`sdlc-ai-spec`。声明仓库：https://github.com/goedgecloud/sdlc-ai-spec。
安装时选择可访问且包含目标构建的仓库与准确 ref，并核对提交 SHA 和
`dist/BUILD.json`。仓库元数据不代表仓库迁移或目标分支已经交付。

## 安装单一插件包

三个宿主均提供中文描述、作者、主页、仓库、许可证和关键词。宿主专用展示字段如下：

| 宿主 | 展示配置 |
| --- | --- |
| Codex | `interface` 中的显示名、短/长描述、开发者、分类、读写能力、网站、三条起始提示、品牌色和图标 |
| Claude Code | `displayName`、`homepage` 及 Marketplace 分类与搜索标签；不写入其他宿主的图标或 `interface` 字段 |
| Cursor | `homepage`、`logo` 及 Marketplace 分类与搜索标签 |

Codex 的“网站”使用 `interface.websiteURL`，描述中的链接不能替代该字段。
图标使用包内 `assets/logo.svg`，无需额外服务。Cursor 的远端图标解析仍依赖目标
仓库/ref 中实际存在该资源。没有独立发布的隐私政策、服务条款或真实截图时，
对应字段保持缺省。插件不提供 MCP、Hooks 或独立 Agent，因此不注册这些组件。
配置通过工程检查不等于已安装缓存已刷新，仍须核对客户端实际加载版本。

字段依据：[Codex](https://developers.openai.com/plugins/build/plugins#manifest-fields)、
[Claude Code](https://code.claude.com/docs/en/plugins-reference#metadata-fields)、
[Cursor](https://cursor.com/docs/reference/plugins)。

三个仓库根 Marketplace 目录清单都指向 `./dist`。11 个入口（九项上游核心、
本地 INIT 和 STATUS）均位于 `dist/skills/`，不保留宿主私有包装入口或选择策略覆盖。

Codex 和 Cursor 使用 `skills: "./skills/"`，Claude 自动扫描 `skills/`，无需
冗余自定义路径。不提供通用根 plugin.json。不要将根工作区和 dist 包分别安装两次。
通过宿主正常卸载/更新界面移除旧缓存版本，不要将旧目录合并进新包。运行依赖仍为
Bash 和 Python 3.9+；安装时不构建或翻译。中文内容已预编译，模板结构保留英文。

## Codex

通过客户端 Marketplace 管理界面添加目标 Git 仓库/ref 或本地 checkout。
目录清单位于 `.agents/plugins/marketplace.json`。在 `sdlc-ai-spec` Marketplace
查找 `sdlc-ai-spec`，按用户作用域安装，再启动新会话。实际发现的命令应包含
`$sdlc-100-spec` 和 `$sdlc-200-plan`，以该客户端版本显示的命令标识为准。
安装 Codex IDE 扩展不能作为原生插件验证。

## Claude Code

进行可复现的分支测试时，先克隆并检出准确实现提交，再将该 checkout 添加为本地 Marketplace：

```text
/plugin marketplace add /absolute/path/to/sdlc-ai-spec
/plugin install sdlc-ai-spec@sdlc-ai-spec
```

选择用户作用域。原生调用为 `/sdlc-ai-spec:sdlc-100-spec` 等。目标分支作为分发
来源可用后，也可添加其 Git URL。仅针对当前会话的直接诊断可使用：
`claude --plugin-dir /absolute/path/to/checkout/dist`。

## Cursor

团队 Marketplace：Dashboard > Plugins > Add Marketplace > Import from Repo；
选择目标仓库与 ref，再在 Customize 中找到 `sdlc-ai-spec` 并按用户作用域安装。
团队 Marketplace 是否可用取决于套餐和权限。若要独立于团队 Marketplace 做本地测试，
将完整 `dist` 包复制到新建的 `~/.cursor/plugins/local/sdlc-ai-spec` 目录，重新
加载窗口并检查 Customize。不要只复制 skills，也不要把旧 beta 文件合并进同一目录。
原生调用为 `/sdlc-100-spec`。本地加载是文档支持的诊断方式，不证明团队分发已测试。

## 核验实际安装内容

插件必须从公共 skills/ 目录准确暴露预期的 11 项 Skill。读取安装目录中的
`UPSTREAM.json` 和 `BUILD.json`。产品版本固定时，`BUILD.json.build_id` 标识
源码派生字节。每次测试记录源码提交、build_id、客户端版本、模型和加载的插件目录。
不要只检查 checkout；必须检查已安装的缓存副本。

Claude 可能在显式版本字符串不变时跳过更新。固定 beta 期间，不要假定 Update 已
获取新提交；应采用全新安装或文档规定的卸载/重装/重新加载流程，并核验 build_id。
不得自动删除用户插件缓存或项目 `.sdlc` 目录。

## 项目初始化

包内包含项目级 INIT。对每个选定项目运行已安装的 `sdlc-000-init`，详见
[INITIALIZATION.md](INITIALIZATION.md)。已有兼容的最小 `.sdlc` 数据可在不删除
文档的前提下补全。安装插件本身不会初始化任意业务项目。原生 INIT 调用和模型驱动
行为仍需用户实际验证。

## 官方参考资料

- OpenAI 打包与 Codex 兼容路径：https://developers.openai.com/plugins/build/plugins
- Claude 组件路径、缓存与版本：https://code.claude.com/docs/en/plugins-reference
- Claude Marketplace 来源：https://code.claude.com/docs/en/plugin-marketplaces
- Cursor 原生清单与显式发现：https://cursor.com/docs/reference/plugins
- Cursor 团队及本地安装：https://cursor.com/docs/plugins

这些资料支持格式选择，不代表已安装客户端认证。不要把全部宿主适配器放进同一默认 Skill 扫描目录。

## 插件标识迁移

插件 ID 从 `sdlc` 改为 `sdlc-ai-spec`，显示名为 **SDLC AI SPEC**。十个编号入口
目录采用 README 中的 ID；sdlc-status 是无编号本地辅助能力。11 个入口均位于
dist/skills，三个清单通过原生发现语义选择同一组能力。生成入口省略三项获准的
展示/选择字段；业务执行与显式宿主绑定不变。

旧 ID 和新 ID 应视为不同安装。通过客户端正常管理流程移除/禁用旧插件，从准确
目标来源安装新 ID，再核验 11 个入口和新 build_id。不要合并两个包目录树，也不要
假定固定 beta 版本会使缓存失效。不执行自动缓存移除或业务数据迁移，不宣传或安装
旧公共命令别名。安装/更新插件不重写已有文档；用户自定义覆盖中的历史命令引用需显式审查。

## 统一公共入口与 STATUS

当前包在 `dist/skills` 中恰好提供 11 个入口：九项上游核心 Skill 加本地 INIT 和
STATUS，不保留宿主私有包装入口。所有公共入口省略 `user-invocable`、
`disable-model-invocation` 和 `argument-hint`，使用宿主默认行为。INIT 保留已有项目数据。
Claude 默认发现 `skills/`，不重复配置自定义路径；其他清单选择 `./skills/`。
所有包装入口向上两级解析包根目录。

STATUS 是可选本地只读辅助能力，不是额外生命周期阶段或上游命令。它容忍未完成/
未初始化状态，不持久化需求切换、不初始化、不执行建议的下一项 Skill。
详见 [STATUS.md](STATUS.md)。不为 STATUS 保存历史而修改现有核心正文、模板或运行行为。

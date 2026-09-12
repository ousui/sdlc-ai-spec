# 可重复的上游升级

## 开发工具环境

通过仓库锁定的 uv 项目运行升级工具：先执行 `uv sync --locked`，再使用
`uv run --locked ...`。候选上游 CLI 仍按 DEVELOPMENT.md 在独立的
`uv venv` / `uv pip` 环境中创建。uv 不进入安装后的 `dist` 运行时。
`pyproject.toml`、`uv.lock` 和 `.python-version` 是需审查的构建输入，必须保持同步。

## 锁定范围

`upstream.lock.json` 记录准确 Spec Kit 提交、所选 Bash/仅核心能力配置、复制的
源码标识，以及受监视渲染器/集成标识。`src/upstream/` 保留原始字节和许可证。
派生源码位于 `src/templates/` 和 `src/scripts/`；九项命令直接读取
`src/upstream/templates/commands/`。`src/adapters/` 保存已审查的适配变更，
`tools/port.py` 使用严格锚点应用这些变更。`dist` 由生成器产生，不手工编辑。

受监视文件包含 `integrations/base.py`、`agents.py`、Codex/Claude/Cursor 集成、
调用风格、init、共享基础设施和 events。即使补丁仍能应用，受监视文件变化也必须
审查。若这些文件开始依赖其他生成器模块，还需审查传递导入。
固定监视清单不能保证检测未来所有上游架构变化。

## 准备候选：不覆盖、不下载

使用本仓库干净 checkout 和单独获取的干净上游 Git checkout。维护者显式获取并
选择版本；不得自动跟随 `main`，也不得删除已接受的锁文件来绕过验证。

```sh
uv sync --locked
uv run --locked python -B tools/upgrade.py prepare \
  --upstream /absolute/path/to/spec-kit \
  --ref <EXACT_COMMIT_OR_TAG> \
  --out /absolute/path/outside/this-repo/sdlc-candidate
```

所选 ref 必须等于上游 HEAD。候选位置按解析后的文件系统路径检查，因此父目录
符号链接不能将候选放回任一源码 checkout。命令从当前已接受提交创建 detached
Git worktree，写入候选锁文件、生成派生源码、构建单包并生成 Marketplace。
同级文件 `sdlc-candidate.upgrade.json` 记录来源/基线身份、所有变化的受监视或
复制路径、就绪状态，以及准确内容/权限指纹。活动工作树、分支和已接受 dist 不变。
失败时保留 BLOCKED 候选供检查，不留下更新一半的已接受产品。

新增核心命令、补丁锚点变化、宿主行结构差异、受监视模块缺失或未知来源清单都需要
审查。不得静默排除或放宽等价检查。若必须变更适配代码，先审查并提交该变更，再准备新候选。

## 独立验证

在隔离工具环境安装候选的准确上游版本，使用 Codex、Claude、Cursor、Bash、
`--events=false` 且无 presets/extensions，初始化三个新的空目录。使用候选自身的
`tools/verify.py` 对照这些输出验证，证据保存在两个工作树之外。
详见 [DEVELOPMENT.md](DEVELOPMENT.md)。不得从初始化目录构建；它们仅是独立比较基准。

报告必须将 `source_digest` 绑定到包括 dist 在内的完整候选字节与可执行权限，不能
仅凭上一源码提交的 PASS 声明通过。还必须包含受支持的验证契约版本、全部必需检查组、
测试及差分数量、环境标识和分发清单；截断或手动精简的 PASS JSON 会被拒绝。
同版本重放属于工程回归，不是新版本接受。既有合成项目夹具覆盖现行 `.sdlc` 格式
的持续使用。真实格式不兼容需单独显式迁移项目数据；更新/安装插件不得重写用户项目。

## 审查并接受

检查全部变化的原始代码，尤其是被移植补丁整体替换的函数：上游函数可能名称不变，
但增加了必要修正。也要检查新增的原始英文指令；不得归一化掉行为、权限、清单所有权
或停止条件变化。

完成审查后，在外部创建审查 JSON：

```json
{
  "decision": "accept",
  "reviewer": "<maintainer>",
  "candidate_digest": "<from the candidate record and verifier>",
  "reviewed_paths": ["<every changed upstream path, exactly once>"]
}
```

```sh
uv run --locked python -B tools/upgrade.py accept \
  --record /absolute/path/sdlc-candidate.upgrade.json \
  --evidence /absolute/path/candidate-evidence/result.json \
  --review /absolute/path/review.json --check
```

检查成功后，同一命令去掉 `--check`，仅使用维护者 Git 身份提交候选 detached
worktree。它不推送、不合并、不改变当前分支，也不创建或移动 tag。通过正常审查的
Git 流程集成该准确候选提交；此前成员继续安装已接受的 dist。`accept` 拒绝候选
字节变化、过期报告、不完整审查、来源 HEAD 移动或来源工作树不干净的情况。
JSON 审查是显式本地流程记录，不是加密身份证明，也不是防范控制本机开发者的安全边界。

## 版本与回退

调试期间产品版本保持 `1.0.0-beta`，它独立于上游 tag，不得混用。记录提交和
BUILD.json build_id。回退时选择较早的已接受源码/分发提交，再按客户端流程重新
加载缓存或重装并验证。不得删除项目数据。

## 来源映射

| 上游 | 本地派生 | 验证 |
| --- | --- | --- |
| templates/commands/*.md | 原始源码 → 源码渲染器 → 宿主公共片段提取 | 完整解析正文与三个已安装 CLI 基线比较 |
| templates/*-template.md | 默认需求路径和逻辑能力 ID | 除显式路径/引用映射外文本精确相等 |
| scripts/bash/*.sh | 严格移植锚点及全局资源绑定 | 源码差异及夹具上的返回码、输出和文件 |
| integrations/base.py, agents.py, three integrations | 受监视原始源码 → 已审查渲染器/适配器 | 各宿主元数据和原始生成正文 |
| LICENSE | 源码及 dist 中保持原样 | 字节相等 |

源码复制、渲染、公共片段提取、清单和比较均为确定性过程，工具不调用 AI。
未来不受支持的上游变化会阻止候选，不触发无控制的 AI 重写。

## 升级中的本地初始化器

`init` 是本地命令，不属于上游命令清单。候选生成必须保留 `src/adapters/INIT.md`、
`src/scripts/python/init_project.py` 及其测试。受监视上游 `commands/init.py`
变化时，审查项目数据映射（模板初始化和默认值），不盲目复制安装器。
重复初始化不将已有项目重写为新上游版本，也不重置文档；布局不兼容需单独迁移，
绝不是插件安装的隐式动作。

上游包版本从受监视的 `pyproject.toml` 读取，与 tag/ref 分别记录。按准确 SHA
准备升级时，不得把该 SHA 写入项目 `speckit_version`。INIT 保留已有项目默认值，
不会在包更新后静默执行数据迁移。

## 必须应用的命名映射

变更上游版本前，阅读 [NAMING.md](NAMING.md) 和 [naming-map.json](naming-map.json)。
`tools/naming.py` 在原始源码渲染后应用已审查映射；`tools/naming_check.py` 是独立
维护的有限比较基准。构建身份包含命名映射。上游锁与复制的源码路径保留原名，
生成工作流使用 `references/workflows/<full-skill-id>.md`，loader 调用使用相同公共 ID。
未知来源引用必须阻止准备；不得猜测新缩写，也不得削弱完整正文等价检查来接受候选。

## 共享入口与本地化候选恢复

当前分发包在 `dist/skills/` 中提供 11 个公共入口，包含本地 INIT 和 STATUS，
不保留宿主私有包装入口。原始英文源码渲染仍独立检查；中文来源资源在
`src/locales/zh-CN` 中绑定版本。构建和安装不运行翻译服务。原始英文模板映射
继续供独立比较。已审查中文默认模板呈现会重新生成，已有项目数据保持不变。

上游输入变化可能以 `LOCALIZATION_REQUIRED` 阻止准备。此状态下仅可编辑候选
翻译子树。显式完成翻译审查后，`tools/upgrade.py refresh-localization --record ... --review ...`
验证已冻结的非翻译输入，重新检查中文并构建候选，生成新候选摘要，而不是新的已接受
版本。旧测试证据不得复用。完整命令和审查记录格式见 [LOCALIZATION.md](LOCALIZATION.md)。
审查字符串是流程记录，不是身份认证。

在这一明确、狭窄的翻译恢复路径之外，仍适用“不得编辑候选”规则。
适配器/代码变化需要已审查的源码更新和重新准备候选，不能直接编辑摘要。

## 统一公共入口与 STATUS

当前包在 `dist/skills` 中恰好提供 11 个入口：九项上游核心 Skill 加本地 INIT 和
STATUS，不保留宿主私有包装入口。所有公共入口省略 `user-invocable`、
`disable-model-invocation` 和 `argument-hint`，使用宿主默认行为。INIT 保留已有项目数据。
Claude 默认发现 `skills/`，不重复配置自定义路径；其他清单选择 `./skills/`。
所有包装入口向上两级解析包根目录。

STATUS 是可选本地只读辅助能力，不是额外生命周期阶段或上游命令。它容忍未完成/
未初始化状态，不持久化需求切换、不初始化、不执行建议的下一项 Skill。
详见 [STATUS.md](STATUS.md)。不为 STATUS 保存历史而修改现有核心正文、模板或运行行为。

升级必须保留 src/adapters/STATUS.md、src/locales/zh-CN/status.md 及其本地资源
目录记录、src/scripts/python/project_status.py 和测试。这些是本地源码，不是
复制的上游命令。派生源码生成重建同一 11 项入口包，不覆盖此辅助能力。影响字段
解释的源码变化需进行 STATUS 兼容性审查和测试；不得静默迁移业务数据。
既有本地化刷新路径仍仅限已审查的本地化资源变化。

模板和需求示例的新鲜度参与 LOCALIZATION_REQUIRED 检查。`localize.py export`
包含这些英文输入；`record --presentation NAME` 在既有本地化专用刷新前记录已
完成的来源审查。新本地化模板位于已授权的本地化子树；刷新不允许修改其他位置或
手工编辑候选摘要。

# 开发与工程验证

## 元数据与目录布局

仓库根目录的 `plugin-metadata.json` 是插件名称、版本（`1.0.0-beta`）、作者
（Blade）、声明仓库和许可证的唯一来源。`homepage` 和 `keywords` 是三个宿主
共用的发现信息；`presentation` 是构建输入，不原样写入宿主清单。生成器将其
映射为 Codex 的 `interface`、Claude 的 `displayName`、Cursor 的 `logo` 及
Marketplace 展示字段。`src/assets/` 中的图标复制到 `dist/assets/`，并纳入构建摘要。
显示标签使用 `v1.0.0-beta`，机器清单使用 `1.0.0-beta`。调试期间不递增版本，
普通代码变更不创建或移动 tag；使用准确提交 SHA 标识构建。

根目录保存实现源码。`src/upstream/templates/commands` 保留上游英文原文；
`src/templates` 和 `src/scripts` 保存已记录的移植差异；`src/adapters/` 提供
资源绑定和宿主差异。`tools/build.py` 生成一个自包含的 `dist`，含 11 个唯一公共
入口（九项上游核心、本地 INIT 和 STATUS），不导入上游 CLI，也不读取已初始化的
项目。加上 `--marketplaces` 可同时重新生成根目录的三个目录清单。
根目录是源码与构建工作区，因此不放置根插件清单。

所有入口位于 `dist/skills/`，不保留私有入口目录。Claude 默认扫描 `skills/`；
Codex/Cursor 显式选择 `./skills/`。生成入口均省略三项已批准的展示/选择字段。
原始上游元数据和执行契约仍独立检查。英文源码渲染结果继续与上游输出独立比较；
完整中文正文则对照已审查、绑定来源的本地化资源验证。
增量翻译和受保护 token 见 [LOCALIZATION.md](LOCALIZATION.md)。

## 开发环境：统一使用 uv

`dist/` 之外的开发、构建、测试和验证依赖统一由 **uv** 管理。
`pyproject.toml` 声明直接开发依赖，已提交的 `uv.lock` 锁定传递依赖图。
`.python-version` 选择 Python 3.12 作为标准开发解释器，项目接受 Python 3.11–3.15。
工具项目版本 `0.0.0` 不是插件或产品版本；产品元数据以 `plugin-metadata.json` 为准。

使用 uv `0.12.13`，或 `tool.uv.required-version` 允许的其他兼容 `0.12.x` 版本：

```sh
uv sync --locked
uv run --locked python -B tools/build.py --marketplaces
uv run --locked python -B -m unittest discover -s tests -v
git diff --check
```

`uv sync` 创建并管理 `.venv`，无需激活。CI 精确锁定 uv `0.12.13` 并使用
`--locked`；锁文件过期或缺失时停止。依赖变化时，更新 `pyproject.toml`，运行
`uv lock`，审查 `uv.lock`，再一起提交。项目不提供 `tools/requirements.txt`，
不得引入第二个依赖权威来源。

`dist/` 运行时**不使用 uv**，不分发 `pyproject.toml`、`uv.lock`、
`.python-version` 或虚拟环境。安装后的插件仍只需要 Bash、Python 3.9+ 和标准
POSIX 工具。构建元数据可记录 uv 项目文件的摘要作为复现输入，这不构成运行时依赖。

## 复现派生源码

在独立 checkout 获取 `upstream.lock.json` 记录的上游提交。以下命令使用该目录的
绝对路径；工具会根据锁文件核对所选源码的摘要。

```sh
uv sync --locked
uv run --locked python -B tools/port.py --upstream "$UPSTREAM"
uv run --locked python -B tools/build.py --marketplaces
```

不得使用上游初始化产物构造移植源码；这些产物仅作为独立比较基线。
不得在运行时脚本中加入 CLI 回调。

## 使用已安装工具独立比较

在仓库和业务项目之外准备三个新的空目录，以及一个通过 uv 创建的独立上游工具
环境。先为 `UPSTREAM`、`TOOL_ENV`、`BASELINES` 和 `EVIDENCE` 设置绝对路径。
上游 checkout 必须准确为 `a4e25ce6b96dc8e85f84206c6a54353fa9c5260b`
（Spec Kit `v1.0.5`）。

```sh
test "$(git -C "$UPSTREAM" rev-parse HEAD)" = a4e25ce6b96dc8e85f84206c6a54353fa9c5260b
uv sync --locked
uv venv "$TOOL_ENV" --python 3.12
uv pip install --python "$TOOL_ENV/bin/python" "$UPSTREAM"
"$TOOL_ENV/bin/specify" version
for agent in codex claude cursor-agent; do
  mkdir -p "$BASELINES/$agent"
  (cd "$BASELINES/$agent" && "$TOOL_ENV/bin/specify" init . \
    --integration "$agent" --script sh --ignore-agent-tools \
    --non-interactive --integration-options="--events=false")
done
uv run --locked python -B tools/verify.py --upstream "$UPSTREAM" \
  --baselines "$BASELINES" --evidence "$EVIDENCE"
git diff --check
```

`uv pip` 仅用于上述明确隔离的上游 CLI 环境，不替代仓库项目的锁文件。
使用 Bash，不启用 events、presets 或 extensions。这些 CLI 调用不会启动 Codex、
Claude 或 Cursor。其项目设置和宪法与本地 `sdlc-000-init` 输出独立比较；宿主注册表
和已安装工具资源明确排除在外。每次都使用新的空基线目录。

## CI 与证据

`.github/workflows/engineering.yml` 在 Ubuntu 24.04 和 macOS 15 ARM64 执行同一
工程契约。每个任务获取触发仓库的准确提交和锁定上游，安装锁定 uv 版本，执行
`uv sync --locked`，通过 `uv venv` / `uv pip` 创建隔离上游 CLI 环境，初始化
三个空项目，再验证已提交的包。CI 不得重新生成并提交包，也不得因文件缺失静默跳过检查。

工作流对仓库只有读取权限。源码传输使用 `GITHUB_REPOSITORY`，包元数据使用单独
声明的仓库。这允许在明确的仓库转移前后验证，但不代表转移已经发生。不需要生产凭据。

证据以 `sdlc-engineering-<runner>-<source-sha>` 上传，包括已安装工具日志、基线
摘要、源码快照和验证结果。报告记录源码 SHA、实际源码仓库、声明仓库、产品版本、
环境、各项检查和分发包摘要。详见 VERIFICATION.md。

## 升级锁定上游

不得修改摘要来使检查通过。按 [UPGRADING.md](UPGRADING.md) 准备 detached 候选，
比较已安装工具输出，审查变化的原始源码，仅接受已验证的准确字节。
BUILD.json 标识可复现构建，产品 beta 版本保持固定。

## 本地项目初始化器

`src/adapters/INIT.md` 是本地工作流，不是第十项上游命令。
`src/scripts/python/init_project.py` 是仅依赖标准库的确定性实现。
构建使用与九项上游命令相同的 loader，生成一个公共 INIT 入口和一份共享初始化
正文，但不要求项目已经初始化。`COMMANDS` 和上游锁仍保留九项；`ALL_COMMANDS`
加入本地 INIT 和 STATUS，用于包清单。升级准备必须保留这些本地源码及测试。

`tests/test_init.py` 覆盖首次初始化、人工状态补全、字节/权限/mtime 幂等、安全
失败、不回退调用 CLI、本地忽略规则及下游脚本兼容性。这些是合成脚本测试，不是 Agent 执行。

## 必须应用的命名映射

变更上游版本前，阅读 [NAMING.md](NAMING.md) 和 [naming-map.json](naming-map.json)。
`tools/naming.py` 在原始源码渲染后应用已审查映射；`tools/naming_check.py` 是独立
维护的有限比较基准。构建身份包含命名映射。上游锁与复制的源码路径保留原名，
生成工作流使用 `references/workflows/<full-skill-id>.md`，loader 调用使用相同公共 ID。
未知来源引用必须阻止准备；不得猜测新缩写，也不得削弱完整正文等价检查来接受候选。

## 只读 STATUS 辅助能力

`src/adapters/STATUS.md` 定义这项本地能力（不是上游能力）；中文资源为
`src/locales/zh-CN/status.md`。`project_status.py` 仅使用 Python 3.9+ 标准库，
只向 stdout 输出。详见 [STATUS.md](STATUS.md)。本地测试使用合成目录，覆盖空数据、
格式错误、别名、只读和并发变更。比较文件内容/权限/mtime、目录清单及 Git index/config；
atime 不作为不可变性指标。

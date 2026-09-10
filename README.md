# SDLC

**版本：v1.0.0-beta · 作者：Blade**

插件声明仓库：[goedgecloud/sdlc-ai-spec](https://github.com/goedgecloud/sdlc-ai-spec)。
基于 [GitHub Spec Kit](https://github.com/github/spec-kit) 的用户级插件移植，面向 Codex、Claude Code 和 Cursor。
共享 Skill、脚本和模板随插件安装；项目工作数据保存在各自的 `.sdlc/`。

> 当前为核心迁移测试版，**尚未提供 `sdlc-init`**。已有验证仅覆盖工程完整性、静态检查和合成文件系统场景，未完成客户端原生安装或真实业务验证。版本在调试期间固定为 `1.0.0-beta`；区分构建请使用 Git 提交 SHA。

## 范围

保留上游九项能力：`constitution`、`specify`、`clarify`、`plan`、`tasks`、`analyze`、`checklist`、`implement`、`converge`。调用标识使用 `sdlc-*`，具体语法按宿主生成。

英文流程和模板保持上游语义；仅适配名称、资源路径、项目数据位置和插件包装。当前不包含 INIT、GitHub、模板翻译、团队规则、事件 Hook、扩展安装管理或工作流引擎。

固定上游：Spec Kit `v1.0.5`，提交 `a4e25ce6b96dc8e85f84206c6a54353fa9c5260b`。原始源码身份记录在 [upstream.lock.json](upstream.lock.json)。

## 仓库结构

```text
.
├── plugin-metadata.json       # 唯一产品版本、作者、声明仓库等元数据
├── upstream.lock.json         # 上游身份与选定配置
├── src/                       # 上游命令、模板及迁移后的必要脚本
├── adapters/                  # 资源绑定与宿主差异
├── tools/                     # 源码移植、构建、工程验证工具
├── tests/                     # 静态、布局和合成场景测试
├── dist/
│   ├── codex/                 # 自包含 Codex 工程包
│   ├── claude/                # 自包含 Claude Code 工程包
│   └── cursor/                # 自包含 Cursor 工程包
├── docs/
│   ├── DEVELOPMENT.md         # 开发和验证步骤
│   ├── MIGRATION.md           # 允许的上游差异
│   └── VERIFICATION.md        # 证据定位与验证边界
├── LICENSE                    # 上游 MIT 许可
└── NOTICE                     # 原始来源和移植归属
```

仓库根目录是源码和构建入口，不是第四个插件包。三个独立包位于 `dist/<host>/`，共享内容由同一构建器生成，不能直接分别修改。旧实现和旧规划不再保留在当前目录，历史通过 Git 追溯。

## 工程使用

运行期需要 Bash、Python 3.9+（路径检查仅使用标准库）及上游脚本使用的 POSIX 工具；`jq` 可选。不需要 `uv` 或 `specify-cli`。项目缺少 `.sdlc` 时明确报错，不会自动初始化。

开发工具需要 Python 3.11+，依赖见 [tools/requirements.txt](tools/requirements.txt)。从仓库根目录执行：

```sh
python -m pip install -r tools/requirements.txt
python -B tools/build.py
python -B -m unittest discover -s tests -v
```

完整的“实际安装固定上游工具 → 三个空项目初始化 → 已提交工程包对照”步骤见 [开发说明](docs/DEVELOPMENT.md)。工程包尚不是可以直接完成首次项目初始化的成品，不要通过手工复制 `.specify` 或运行旧安装器绕过当前边界。

## 来源与声明

Spec Kit 原作者为 GitHub, Inc.，使用 MIT 许可证；本移植作者为 Blade。原始英文命令的来源元数据保留，插件作者单独定义。每个工程包携带 `LICENSE`、`NOTICE` 和 `UPSTREAM.json`。

本项目不是 GitHub、OpenAI、Anthropic 或 Cursor 的官方发行版。插件声明仓库、当前 Git 托管位置和实际构建来源是不同概念；CI 从当前运行的仓库读取准确提交，不将声明地址当作已经迁仓成功的证明。

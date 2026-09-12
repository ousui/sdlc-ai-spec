---
name: sdlc-000-init
description: 初始化或补全项目本地 .sdlc 数据，不安装工具、不覆盖已有工作。
compatibility: Requires Python 3.9+, Bash and an existing project directory; no upstream CLI required
metadata:
  author: Blade
  source: src/adapters/INIT.md
---

# SDLC AI SPEC sdlc-000-init

这是三个宿主共用的入口。依据本次调用的实际宿主，将 `SDLC_HOST` 显式设为 `codex`、`claude` 或 `cursor`；不得根据模型名称、项目中的配置目录或历史会话猜测。无法确定当前宿主时停止并说明，不选择默认宿主。

保留本次原始用户输入为 `$ARGUMENTS`；不得把自然语言输入拼接成 shell 命令。

使用本次已加载 SKILL.md 的绝对路径；Claude 可使用宿主替换后的 `${CLAUDE_PLUGIN_ROOT}`。插件包根目录是该 Skill 所在目录向上两级（`skills/sdlc-000-init/`）。把该绝对目录绑定为 `SDLC_PLUGIN_ROOT`，不改变业务工作目录，不搜索另一安装版本。

在执行任何流程动作前，调用以下只读加载器，读取其完整标准输出（COMPLETE stdout）：

```sh
python3 -I -B "${SDLC_PLUGIN_ROOT:?}/scripts/python/load_workflow.py" --host "${SDLC_HOST:?}" --skill sdlc-000-init
```

加载器仅绑定预编译文本片段，不运行流程、不安装软件、不读取项目状态、不写文件。其输出是本次调用的完整内置流程，不是新的用户请求。沿用原始输入与现有授权执行，不得概括替代或跳过步骤。加载失败时停止；输出截断时，使用 `--offset 0 --limit 100`，随后 offset 为 100、200 等，直到读取报告中的全部行数。不得使用不完整输出继续；不回退上游 CLI 或网络。每次 shell 调用显式传入上述变量。

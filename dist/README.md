# SDLC AI SPEC v1.0.0-beta

作者：Blade

仓库：https://github.com/goedgecloud/sdlc-ai-spec

11 个公共入口位于 skills/，由 Codex、Claude Code 和 Cursor 共用；使用宿主默认展示与调用选择策略。完整流程正文及摘要为简体中文；模板说明和示例为中文，标题保留英文定位锚点并附中文释义，机器语法保持不变。不因升级或语言要求重写已有业务文档。

安装不需要构建、uv、上游 CLI 或网络。Runtime requires Bash, Python 3.9+ and standard POSIX tools. No install-time build, uv, upstream CLI or network is required.

每个项目通常运行一次 sdlc-000-init；重复调用只补全兼容状态，不重置已有工作。sdlc-status 只读查看项目和产物，不初始化、不修改文件、不执行其他阶段。原生发现、模型行为与真实业务验收不由静态工程检查代替。

Based on Spec Kit by GitHub, Inc. (MIT), an independent source port. See LICENSE, NOTICE, UPSTREAM.json and BUILD.json.

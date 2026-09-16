# SDLC AI SPEC v1.0.7-sdlc.1

作者：Blade

仓库：https://github.com/goedgecloud/sdlc-ai-spec

11 个公共入口位于 skills/，由 Codex、Claude Code 和 Cursor 共用；使用宿主默认展示与调用选择策略。完整流程正文及摘要为简体中文；新生成模板使用中文 canonical 标题与字段，兼容读取旧英文/双语标题，机器语法保持不变。不因升级或语言要求重写已有业务文档。

安装不需要构建、uv、上游 CLI 或网络。Runtime requires Bash, Python 3.9+ and standard POSIX tools. No install-time build, uv, upstream CLI or network is required.

每个项目通常运行一次 sdlc-000-init；重复调用只补全兼容状态，不重置已有工作。sdlc-status 只读查看项目和产物，不初始化、不修改文件、不执行其他阶段。原生发现、模型行为与真实业务验收不由静态工程检查代替。

sdlc-210-huma 生成需求质量评审清单，推荐在 PLAN 后、TASK 前按需使用；不新增 TASK 前置门禁，不是 CONV 后的功能验收。新清单条目保持未勾选，评审者明确要求后 Agent 才协助评估。IMPL 读取清单，有未勾选项时询问是否继续并等待回答，不修改清单标记。CONV 收敛不等于项目测试、业务验收或发布通过。

Based on Spec Kit by GitHub, Inc. (MIT), an independent source port. See LICENSE, NOTICE, UPSTREAM.json and BUILD.json.

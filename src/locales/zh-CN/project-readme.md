# SDLC AI SPEC 项目数据

本目录保存当前项目的 SDLC AI SPEC 流程数据。
- memory/constitution.md：项目原则/治理骨架，使用 sdlc-010-rule 审阅和维护。
- memory/.constitution-template.json：宪法可选生成基线，只记录来源与生成内容摘要，不表示阶段完成或审批。
- init-options.json：项目默认配置，不是全局 Agent 选择配置。
- specs/：功能规格、实施方案和任务。
- feature.json：由 sdlc-100-spec 写入，初始化不创建此文件。

Skills、脚本、应用和核心模板保留在用户安装的插件中。
不要在此运行上游初始化器，也不要将插件资源复制进本目录。
重复执行 sdlc-000-init 只补全缺失的兼容数据，不重置需求，也不覆盖人工文档。
本地 .gitignore 防止这些数据被新加入 Git；已经由 Git 跟踪的文件仍保持跟踪。

# SDLC AI SPEC 项目数据

本目录保存有效本地资料库或权威库的 SDLC AI SPEC 流程数据。
- memory/constitution.md：项目原则/治理骨架，使用 sdlc-010-rule 审阅和维护。
- memory/.constitution-template.json：宪法可选生成基线，只记录来源与生成内容摘要，不表示阶段完成或审批。
- init-options.json：项目默认配置，不是全局 Agent 选择配置。
- specs/：功能规格、实施方案和任务。
- feature.json：由 sdlc-100-spec 写入，初始化不创建此文件。
- memory/long-term.md：可选的项目共享事实、决策及其来源。
- workspaces/：各共享权威库 worktree 的当前需求选择。
- store.json：main 显式登记的权威位置与来源。
- transactions/：候选变更与恢复记录，不从其他副本导入。

Skills、脚本、应用和核心模板保留在用户安装的插件中。
不要在此运行上游初始化器，也不要将插件资源复制进本目录。
重复执行 sdlc-000-init 只补全缺失的兼容数据，不重置需求，也不覆盖人工文档。
本地 .gitignore 防止这些数据被新加入 Git；已经由 Git 跟踪的文件仍保持跟踪。

本地副本优先；没有本地副本的 worktree 正常读写权威库。只有 main 发起归拢。INIT 新建本地副本时默认导入知识，需求须明确选择。导入不复制当前需求选择。

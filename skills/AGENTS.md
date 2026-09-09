# Skills Subtree Agent Instructions

正式入口为sdlc-init、sdlc-000-ctx、REQ/DSN/PLN/IMP/VFY/RLS及sdlc-status。
命名、中文描述、七节结构与显式调用策略遵守docs/plugin-development/SKILL-STYLE.md。
本次十入口依据已批准v2设计与用户连续实施授权，不重走旧v1逐阶段确认流程。

Skill是当前Agent的操作入口，不复制Runtime或SQL。共享约定放_shared，私有interface只描述本阶段真实命令。
本次没有source-lock/Markdown Authority/Gate确认文件；Schema及语义由同一公共协议和Runtime验证。
裸调用应利用明确工作区和现有状态，ID及嵌套请求由Agent读取回执后组织，不要求用户手填。
用户授权完整需求时，当前Agent按顺序读取已授权入口；各Skill只处理自身阶段。
单阶段任务不得扩充到后续阶段、安装依赖或外部系统。

保持disable-model-invocation:true及Codex allow_implicit_invocation:false。
每个入口必须有SKILL.md、agents/openai.yaml、references/interface.json；不要创建空目录。
已安装包运行不读取本AGENTS、开发docs或tests。实际验证与开发fixture、原生发现认证分别报告。

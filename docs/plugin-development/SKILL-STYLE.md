# Skill内容与格式约定 v2

固定七节：适用范围、约定与边界、子命令、参数、执行流程、输出与完成条件、资源索引。
阶段入口目录为`sdlc-000-ctx`至`sdlc-600-rls`，辅助入口为`sdlc-init`、`sdlc-status`、`sdlc-github`，辅助入口不加阶段编号。
目录、frontmatter name与interface.skill一致；标题和display_name统一为目录名的大写形式加` · 中文描述`。
SKILL description与UI short_description完全一致，使用中文准确描述入口能力。所有客户端共用同一SKILL、共享Runtime和授权边界；格式统一不改变各入口实际能力。
保持现有显式调用策略：disable-model-invocation:true和allow_implicit_invocation:false。
UI short_description为25–64字符。入口按实际复杂度精简，硬上限200行，不为凑行数重复规则。

子命令表与references/interface.json一致，每个命令须存在于公共Runtime，写入属性与READ_COMMANDS一致。
参数只描述实际唯一CLI：--root/-r、--request/-i、--contract、--version/-V、--help/-h。
业务请求字段以公开机器Schema为准，使用Runtime分配身份与client_key，不保留不再支持的v1开关。

共享细节放skills/_shared/runtime.md，设计领域按需读design-domains.md；没有SKILL.md的_shared不可调用。
Skill不得读取开发文档、旧Source Lock或兄弟私有资源。
运行tools/validate_skill_style.py检查格式和接口；安装副本与真实Agent行为独立验证，不用样式PASS冒充认证。

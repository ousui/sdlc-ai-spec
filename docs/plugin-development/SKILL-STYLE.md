# Skill内容与格式约定 v2

固定七节：适用范围、约定与边界、子命令、参数、执行流程、输出与完成条件、资源索引。
一个SDLC标题，目录与frontmatter name一致，description使用中文并准确描述阶段能力。
保持现有显式调用策略：disable-model-invocation:true和allow_implicit_invocation:false。
UI short_description为25–64字符。入口按实际复杂度精简，硬上限200行，不为凑行数重复规则。

子命令表与references/interface.json一致，每个命令须存在于公共Runtime，写入属性与READ_COMMANDS一致。
参数只描述实际唯一CLI：--root/-r、--request/-i、--contract、--version/-V、--help/-h。
业务请求字段以公开机器Schema为准，使用Runtime分配身份与client_key，不保留不再支持的v1开关。

共享细节放skills/_shared/runtime.md，设计领域按需读design-domains.md；没有SKILL.md的_shared不可调用。
Skill不得读取开发文档、旧Source Lock或兄弟私有资源。
运行tools/validate_skill_style.py检查格式和接口；安装副本与真实Agent行为独立验证，不用样式PASS冒充认证。

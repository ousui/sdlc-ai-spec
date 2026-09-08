# Shared Skill Execution Contract

所有正式 `sdlc-NNN-xxx` Skill 必须遵守本 Contract。

## Invocation

- 只允许显式调用；
- 未调用时不自动执行；
- 调用后只执行当前 Skill 的单一职责；
- 输入目标无法唯一确定时 fail closed。

## Exclusive Execution

从显式调用到完成、停止或交还控制权：

- 不调用兄弟业务 Skill；
- 不把一个授权扩展为传递授权；
- 外部输出只作为 Input 或 Evidence；
- 系统、安全、宿主权限和普通 Tool 继续生效。

## Runtime Independence

- 不读取 `docs/**`；
- 不依赖开发 Handoff 或 AGENTS；
- 使用随 Plugin 打包的 Skill 私有资源、`skills/_shared/**` 和 `packages/**`；
- 不联网、不安装依赖；唯一例外为显式 `sdlc-github` 操作经其固定 GitHub MCP Transport 联网，其他 Phase/支撑 Runtime 不继承此例外；
- 删除 `docs/**` 后行为仍可执行。

## Standard Output

每次运行必须同时形成：

1. 符合 Result Schema 的结构化结果；
2. 清晰中文摘要；
3. 明确成功、等待、阻塞或失败；
4. 必要时给出一个准确下一动作。

不得把内部异常、未执行检查或部分结果描述为成功。

## Side Effects

- 默认不 commit、push、merge、release；
- 默认不写外部系统；
- 只在 Contract 与当前请求共同授权的范围内写项目 Runtime；
- 不持久化 Secret。

## 用户输入整理与程序契约

本节适用于所有正式 Phase、Utility 和 Support Skill。用户自然语言不是 Runtime JSON；Agent 负责把诉求、已知上下文和已观察事实整理成随包契约要求的标准输入，不要求用户填写枚举、内部 ID、摘要或 Invocation。

明显错字、单词拼写和中英文表达在上下文唯一时直接整理，例如构建语境中的“bulid”或“构建”对应 `build`；无需为纯格式纠正再次询问。程序端仅按本 Skill 已登记的无歧义归一化规则处理，不进行自由模糊匹配。使用正式入口，不临时导入私有模块来绕过初始化或参数校验。

范围、资源类型、依赖对象、环境可访问性等判断必须有事实支持。Authority、Revision、ID、路径、命令、摘要、权限、Exception 和最终确认不能按拼写相似度猜测或修正。缺失业务事实进入真实 Open Item；确有歧义才一次询问。格式规范化不是用户身份、授权或产品通过证明。

提交前根据随包字段说明检查完整性；格式问题在产生效果前由 Agent 修正，不把内部 JSON 错误机械地交回用户。正式调用失败后遵守停止契约，保留首个失败，不自动重放未知或部分效果；纯输入拒绝明确零效果时也不能顺势扩大原任务授权。输入错误、未执行检查和真实产品失败分别说明。

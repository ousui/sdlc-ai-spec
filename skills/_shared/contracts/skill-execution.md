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
- 不联网、不安装依赖；
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

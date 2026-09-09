# 接口示例范围

本目录的 JSON Schema 仅具体化 **PLN 创建任务、检查及前置条件的 phase.submit 请求**，并提供合法例子与自依赖反例。它是详细设计的实例，不是完整Runtime，也没有冒充所有命令族已经实现。完整命令集、响应Schema与黄金向量在实施A建立。

Schema负责字段/类型和引用形状；自依赖、DAG、跨作用域等由统一领域validator处理。bad-self-dependency.json在JSON结构上合法，预期被业务规则拒绝；不得误报为Schema拒绝。

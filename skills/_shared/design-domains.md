# 适用设计领域

从准确需求和现有代码选必要领域，不创建固定数量空对象：

- components / architecture：职责、接口与模块依赖。
- data：模型、约束、迁移、事务与持久化。
- api：参数、响应、错误、兼容和幂等。
- ux：可见交互、状态、异常、键盘可用性。
- security：身份、权限、会话、敏感信息边界。
- concurrency：共享状态、竞争、隔离与锁。
- operations：配置、可观测性、恢复、部署目标。
- verification：实际可执行方法、验收断言与收敛审阅。

每个design保存decision/rationale/alternatives/detail及requirements关系。
领域名用于组织解释；执行关系只由结构化任务/Check/依赖/条件控制。

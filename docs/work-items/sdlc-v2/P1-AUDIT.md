# P1 基础审计与决策

基线：`d39601d0272c77ccece51a9751a5e865c55ea603`。主 Agent 实现，独立 Agent 只读评审；
内存 SQLite 复现，不采用未挂接草稿或历史测试数量作为代码证据。

## 已修复

1. 生产端未知字段/枚举/引用数组均返回真实 JSON Pointer；省略与 null 分开。
2. 批次先分配带类型的身份，再解析同批引用；更新也支持前向引用。跨版本/类型引用拒绝。
3. 批次使用 savepoint；即使调用者捕获错误，也不会提交部分业务对象。
4. 正式依赖操作统一为批准契约的 `add_task_dependency`。
5. 共享依赖服务建立 task.start/execute/complete 事件图。显式执行前驱要求 predecessor.complete；
   检查由责任任务 execute 产生，按消费者指定时点约束。完成时自检合法；混合环和逆阶段依赖拒绝。
6. producer 必须匹配 check.task；省略 producer 时从 check.task 获取，不允许用空值隐藏自锁。
7. 任务摘要包括依赖/条件生产者、完整 Check 定义、来源及覆盖闭包；允许合法完成时关系而不递归溢出。
8. Store 只读多查询持有同一读取事务，防止输入包混读两个提交状态。

## 最小设计细化

明确检查生产时点为责任任务 execute，而不是 task completed。这样完成时自检可执行，
消费者仍必须等真实 check pass；步骤完成绝不自动替代条件通过。SQL 32 表无需因此改变。
人工/Agent 自审只能使用 inspection/analysis 等真实审阅方法；test 必须实际 command 执行。

## 验证

`python3.11 -B -m unittest discover -s tests/v2 -v`：24项通过，含原5项与19项领域回归。
首次回归暴露2个 precondition SQL错误，原日志保存于实验室忽略归档
`.local-runs/sdlc-v2/P1-domain-first-failure.log`；已在字段校验层修复后全部通过。

本检查点尚未证明请求级幂等、generation CAS、公开 Runtime、执行/交付或真实项目闭环。
下一步用公开命令事务层实现这些能力，不手写业务SQL或伪造成功回执绕过。

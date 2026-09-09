# 公开命令与证据

入口：python3 scripts/sdlc.py --root PROJECT --request request.json；--request - 从stdin读取。
--contract返回同一套机器契约。stdout仅一个JSON；0完成、2输入/冲突、3阻塞/needs_work/unknown、4Runtime故障。
operation_id可由Runtime分配；重试用原请求与原operation_id。prepare返回具体快照、generation、
上下文、全部关系、附件和Schema。field error采用真实JSON Pointer，非法批次原子回滚。
Run在正式IMP输出之前建立；失败保存输入、版本摘要、准确错误及恢复入口。数据库不能打开时
独立bootstrap诊断保留原库。视图失败不能将已提交业务副作用重新执行。
IMP/VFY 执行入口见 400-imp.md、500-vfy.md。RLS与工作区移交见600-rls.md和workspaces.md。

run.get的status/error描述当前运行现场。受保护的业务进展、明确resume或实际reconcile后，
只有待答、未知操作和预算均不阻塞时才恢复running并清旧错误；真实RLS关闭保持completed并清旧错误。
读取、render、export、无关configure和历史回执查询不表示恢复，不清当前阻塞或重开终态。
投影刷新不改写原失败回执；reconcile仍按原意图登记真实回查结果，未收集确定结果时保留indeterminate。
phase.prepare 同时返回本阶段公开命令Schema，嵌套文件变更和finding结构与消费者共用定义。

# 公开命令与证据

入口：python3 scripts/sdlc.py --root PROJECT --request request.json；--request - 从stdin读取。
--contract返回同一套机器契约。stdout仅一个JSON；0完成、2输入/冲突、3阻塞/needs_work/unknown、4Runtime故障。
operation_id可由Runtime分配；重试用原请求与原operation_id。prepare返回具体快照、generation、
上下文、全部关系、附件和Schema。field error采用真实JSON Pointer，非法批次原子回滚。
Run在正式IMP输出之前建立；失败保存输入、版本摘要、准确错误及恢复入口。数据库不能打开时
独立bootstrap诊断保留原库。视图失败不能将已提交业务副作用重新执行。
IMP/VFY 执行入口见 400-imp.md、500-vfy.md。RLS及复制交回在P4补齐并验收。
phase.prepare 同时返回本阶段公开命令Schema，嵌套文件变更和finding结构与消费者共用定义。

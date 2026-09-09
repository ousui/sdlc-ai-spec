# SDLC v2 当前规范

spec_version=2.0-draft；api_version=2；schema_version=1。本分支正在替换旧链，尚未发布。
批准设计在 ../work-items/sdlc-v2/approved-design；运行合约在 packages/sdlc/protocol.py、domain.py。
contracts/v2.json 是程序生成的语言无关投影；Runtime 不读取 docs 或从 Markdown 表格提取控制语义。
固定六阶段 REQ→DSN→PLN→IMP→VFY→RLS；INIT/CTX 是项目级准备。连续执行来自用户总授权。

入口：[核心](core.md)、[存储](storage.md)、[工作区](workspaces.md)、[Runtime](runtime.md)、[INIT/CTX](000-ctx.md)。
阶段：[REQ](100-req.md)、[DSN](200-dsn.md)、[PLN](300-pln.md)、[IMP](400-imp.md)、[VFY](500-vfy.md)、[RLS](600-rls.md)。

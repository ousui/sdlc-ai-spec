# Q1 交付验收覆盖修补

SpringGear Q1 把本地交付验收显式关联到 required 原生 release_readback Check，
DSN 却在静态覆盖校验仅计入 acceptance，返回 COVERAGE_MISSING。
原请求016及失败018保存在实验室 `.local-runs/sdlc-v2/q1-springgear`；未删除验收或伪造 VFY PASS。

静态覆盖现在允许 required acceptance 或合法原生 release_readback；后者与 delivery.prepare
共用 purpose、command executor、精确 argv 的定义判据。optional、Agent 自述或任意命令不能占交付覆盖。
VFY 仍排除回读；RLS 必须实际写包、独立回读并验证当前适用性。这是覆盖归属修正，不是提前交付。

原 AC10 同时包含完整工作区归档。保留其来源与总要求，将验证义务明确分成：
RLS 真实包回读，以及 RLS 后 workspace.export 的完整文件/资产摘要核对；两项都完成才满足整体要求。
原生包回读不能代替管理归档，新修补不自动扩充导出授权或闭 Run 后执行能力。

独立证据 `reviews/acceptance-release-coverage`：64次公共CLI请求，4项测试通过，
含59次exit0和5次预期exit3；源码快照为586d133加本批改动。
已审阅并集成其4项回归：真实REQ/DSN/PLN、IMP写入/命令检查、VFY没有回读结果、
两次RLS未执行拒绝，实际execute后关闭；三个伪覆盖负例保留精确错误。

`q1-release-coverage-full`：139项全部通过，43.245秒；契约投影、九Skill风格、安装版和单一Runtime检查通过。
后续从本提交构建独立冻结包恢复Spring，保留q1-entry和q1-dsn先前执行版本。
最终H_final九场景真实链与回归要求不变。

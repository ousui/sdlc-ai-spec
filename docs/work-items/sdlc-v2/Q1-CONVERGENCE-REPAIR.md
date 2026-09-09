# Q1 诊断作用域与正常退修

## 已复现的问题

- 同一Store的第二项目在真实命令结束、结果写入中断后，check.evaluate错用配置默认workspace，报告converged=true且unknown为空。两项目的phase.complete均正确拒绝UNRESOLVED_EFFECT，没有观察到推进绕过。
- Spring Q1的真实Maven25项通过，但交付基线验证脚本读取不存在字段而失败。验证任务合法的complete条件要求检查pass，其后继审阅无法开始；旧phase.complete先拒绝未完成任务，因而已知失败不能正常退IMP。
- 独立53次CLI证明存在run.resume和PLN修订的管理恢复路线，不需删条件或伪造完成。但该路线不消耗repair_round，不满足普通VFY自动退修要求，正式产品等待内核修补。

## 修补范围

只读诊断和三个交付门禁使用已核验的当前workspace；仍保留change及本地Run/operation来源过滤，涵盖该workspace的历史Run未知操作。

VFY先拒绝未知操作和不确定检查。已知失败或blocking finding允许按既有规则退修，当前Run活动任务尝试留为interrupted/unknown。原任务依赖和完成条件不变，修复后新任务尝试必须真实满足条件；仅missing/pending仍返回VERIFICATION_PENDING，不消耗修复轮次。既有修复任务选择和预算保持。

无Schema或公开请求形状变化。安装版VFY与共享流程说明同步；此共同流程改动纳入FINAL全部九条真实Agent链重跑要求。

## 证据

实验室忽略目录`.local-runs/sdlc-v2/`：

- `reviews/acceptance-multiproject-unknown/`：旧包63次CLI，保留第二项目错误诊断及正确mutation拒绝；修补后独立Session测试61次真实公开Runtime请求，两项目均false/unknown→回查→收敛。
- `reviews/q1-springgear-independent/`：真实25项原样复验、增加4边界探针的独立29项验证、基线字段错误。
- `reviews/q1-springgear-recovery-independent/`：旧包53次CLI安全管理恢复与修补后的正常退修对照。`automatic-retest-001`在固定dirty预览包上97次CLI全部满足断言：45次真实红→退IMP→修复→新验证任务→绿→RLS；24次纯missing/pending不耗预算；28次真实collector中断，已知失败不能绕过仍活动的unknown。
- `q1-convergence-full-001/`：当前140项完整回归通过，42.559秒；机器契约、九Skill结构、独立安装和实际命令测试通过。

`tests/v2/test_multi_project_unknown.py`和`test_vfy_pending_repair.py`共新增3项；集成后完整142项通过，43.729秒，证据`q1-convergence-full-002/`。不同包/dirty源码执行不改写为同版本通过。
Run恢复后的旧status/error残留已独立复现，作为下一项诊断状态修补，不与本次退修死锁混为同一缺陷。

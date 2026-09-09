# Q1 Run 当前状态恢复

## 事实与责任层

Spring Q1的019 change.revise缺少generation后已继续到VFY，049 run.get仍显示failed及旧GENERATION_REQUIRED。
独立固定da6751d安装包130次CLI进一步复现：正确phase.submit/change.revise、真实阶段推进未恢复当前Run；
RLS关闭虽为completed仍带旧错误；真实工具结果保存中断并成功reconcile后仍为interrupted/RUNTIME_IO。
这是Run状态投影缺陷，原预算、待答、未知副作用和关闭门禁仍有效。

## 最小修补

在列明的内容/任务/检查/交付业务进展和明确恢复点刷新当前Run；普通管理操作、只读和历史回执重放不刷新。
根据相同change及当前workspace待答/本地未知操作、修复/格式预算和已收集结果确定是否恢复。
成功关闭保留completed并清旧错误，cancelled不重开。阶段控制已报预算耗尽时同步当前error。
澄清回答也采用同一投影，不能因为一个问题已答而抹掉仍耗尽的格式预算。

无Schema、请求形状或历史结果语义变化。投影刷新不改变失败回执或原始trace；operation.reconcile仍按既有机制保存真实回查。

## 验证

独立原反例及负向管理调用证据：实验室`.local-runs/sdlc-v2/reviews/acceptance-run-status/run-001/`。
共享测试`tests/v2/test_run_status.py`覆盖内容纠正、真实unknown恢复、历史reconcile查询、明确resume、待答、修复预算、格式预算与回答组合、RLS错误清理和cancel终态。
集成7项状态回归后，完整149项通过，42.809秒；机器契约、Skill结构和安装副本检查通过，证据`q1-run-status-full-001/`。
独立复验8/8通过，190次公开Runtime.invoke请求，2.297秒，原6候选及2项预算/历史reconcile组合均满足断言；证据`reviews/acceptance-run-status/fixed-tests-001/`及`FIX-RETEST.md`。
执行前后Runtime与测试字节未变；这是Session公开入口证明，不称新CLI或Spring产品复跑。不同源码版本保持各自真实边界。

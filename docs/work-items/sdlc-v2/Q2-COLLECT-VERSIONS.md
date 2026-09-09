# Q2 独立草稿版本交回修补

Admin 的真实主工作树与实施工作树从同一个 DSN 草稿 UUID 分叉。来源提交该草稿并形成 PLN 后代，主库则放弃原草稿并继续自己的 DSN 草稿。原 collect 虽保留完整 ZIP，但因同 revision 主键异内容回滚，来源 head 不存在于目标 Store；原 next_action 却指向无法消费该 head 的 change.resolve。这是 Runtime 缺陷，不能把原包保存描述成逻辑交回完成。

本修补增加显式 `workspace.collect.conflict_policy=preserve_revision_versions`。缺省仍拒绝同键异内容；仅对冲突的已冻结 revision 及来源后代分配确定性本地别名，重写 Schema 声明的 revision 外键及其附件链接身份。原始请求、响应、结果摘要、日志和来源 ZIP 不变。父版本身份参与内容摘要，因此派生内容重新计算 digest，并返回原/本地 ID 与 digest 映射。

其他对象的同键差异、映射后冲突、未提交来源草稿仍拒绝。来源 Run/授权/operation 维持 imported，不成为本机权限或新执行。目标 active、草稿内容及 generation 不变。`rows_imported` 区分事务回滚和已导入但尚有分歧；后者返回可用的 `imported_source_head`，由正常内容 checkpoint 后的 change.resolve 消费，不扩展自动合并代码。

相同 bundle 的既有 row_conflict 可用新 operation_id 和显式策略恢复；旧操作仍返回原失败回执，imports 保存 prior_conflict。成功后重复 collect 返回同一映射，不再次创建业务版本。同 logical bundle 的另一 ZIP 编码不能覆盖原包，须选择原保留 ZIP 重试。后续 export 携带本次映射与原 ZIP；第三个工作区再次转交时嵌套保留继承来源，避免解释材料依赖旧工作区绝对路径。嵌套包只作为来源证据。

验证证据保留于实验室 `.local-runs/sdlc-v2`：

- `q2-collect-first.log`：第一次新测试缺少两处草稿 CAS，且调用侧相对 PYTHONPATH 导致三个既有工具测试环境拒绝；原失败保留，纠正测试调用和请求，未放宽 Runtime。
- `q2-collect-tests-002.log`：29 项 transfer 测试通过。新增四项覆盖真实公共操作分叉、原失败重试、两端提交、后代摘要、目标/控制草稿保留、原回执重放、导出原包、非 revision 冲突回滚、来源草稿与非法策略拒绝。
- `q2-collect-full-001`：157 项完整测试通过，50.496 秒，含安装副本、机器契约与 Skill 格式检查。
- `reviews/q2-collect-independent/retest-001`：4 项新分叉断言通过，2 项额外来源保存断言真实失败，225 次公开请求全部留档；分别暴露原 ZIP 被不同编码覆盖和第三库再导出丢继承证明。
- `tests/v2/test_transfer_provenance.py` 纳入独立两项负例；针对原包拒绝还断言正确拒绝码，以及随后选择原包恢复成功。修补后的 `q2-collect-full-002` 完整159项通过（50.879秒），机器契约、安装副本和格式检查通过；独立 retest-002 原两项断言未改，2/2通过（0.975秒、77次公开请求），未发现额外阻塞。

本工作包的下一步是在 clean 安装包上恢复 Admin 原归档，实际完成 target checkpoint → change.resolve → 再导出/回读；之后才统一提交 Q2 三项目并进入 FINAL。原产品 RLS 仍绑定 q2-entry，不能改写成新包执行。

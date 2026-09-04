# IMP Runtime Contract

Runtime 使用共享 Invocation / Result Envelope。Stage 私有输入放在 inputs；
CLI 仅解析参数和分发，领域实现由独立模块承担。

## Binding、Owner 与 Context

PLN Binding 严格为 PLN-ID@正整数 Revision#WI-NNN。
REQ/DSN Direct Binding 必须完整、唯一，PLN=n/a/waived，IMP=required；
REQ 还必须 DSN=n/a/waived 并具有准确 Direct IMP Scope。
DSN=waived 必须有批准的上游 Exception；Dependency 的 Current State 不能替代
State Check Reference 的重新读回。当前核心只接受能确定性核实的 frozen Artifact 状态来源，
其他可变状态来源返回上游选择可用检查方式。
多个 Outcome、Scope 不明或协调义务返回 PLN。

Owner 优先级：显式 --owner > SDLC_EXECUTOR_TOKEN；不使用 session、UUID、
时间、PID、hostname、用户名或 Git author。缺失或冲突返回 action_required。

Context 读取准确上游 Canonical Artifact 的 context，再解析真实 frozen CTX。
所有 REQ/DSN/PLN 解析链使用同一准确 CTX；Manifest 若声明 Context 关系也必须唯一且一致。
IMP 保存 PLN Reference、WI Binding、Context Reference 和 Lineage；check 重新解析并比较。
携带上游已确认的 Lifecycle Applicability 与未关闭 Exception；
RLS 的 pending 必须先由上游解决，不能在 IMP Gate 中当作 PASS。

## 内部实施输入

inputs.implementation 包含：

- considerations：固定七项，每项 name、disposition、basis、steps、exception。
- steps：id、order、purpose、target、basis_references、considerations、logic、
  expected_result、transaction_boundary、failure_boundary、blocks。
- resources：每项 id 与项目内相对 root；与 Claim resource token 一一对应且不重叠。
- operations：每项 resource、path、step、op、expected_sha256。
  write_text 使用 content；replace_text 使用唯一准确 before / after；delete 删除准确已有文件。
  新文件 expected_sha256=absent，已有文件使用实际当前内容 SHA-256。
- checks：每项 id、name、resource、kind。contains、equals、python_syntax、json
  另含 path 和必要的 expected。project_command 另含 cwd、command 参数数组和可选
  timeout_seconds；只接受固定的 Python、Go、Cargo、npm/pnpm/yarn、Maven 或 Gradle
  检查/构建/单测入口，禁止 shell、安装与任意子命令。项目命令只在完整 Resource
  Snapshot 的临时隔离副本中运行；Python audit hook 或 OS Sandbox 禁止网络和副本外
  写入，并使用不含凭证的环境；当前主机没有可实际执行的隔离器时在产品写入前失败关闭。Evidence 绑定最终
  Snapshot 摘要、声明命令、实际适配命令、退出码和输出。
- exceptions、open_items；新公共抽象、依赖或跨模块接口必须声明 design_decision_references。

inputs.input_references 保存 CLI 的稳定输入顺序，Claim 的 Dependency / Rework 集合准确绑定。
inputs.final_confirmation 使用共享确认字段，并以 subject_digest 绑定
当前 Method、Baseline、Result、Checks、Claim、准确 Artifact Revision 和全部 Supporting Members。
`delegated` 还必须提供当前 Control Input Digest、Evaluation Contract Set、Check Set Result
Digest、不同于 Claim Owner 的稳定 Reviewer 身份、等于 Claim Owner 的 Reviewed Executor，
并引用符合 Core 固定结构的独立 Authority 文件。Runtime 对该文件的 Front Matter、单行表、
Delegation Basis 摘要、RFC 3339 时间、三项摘要与固定集合逐项校验。Authority 文件不进入
Supporting Manifest；Final Confirmation 只保存在 canonical primary Artifact，内部 IMP-STATE
不复制 Authority Reference，避免 Supporting Manifest 与当前摘要形成自引用。
write_policy=confirm 的 confirmations 项使用 kind=product_write、decision=approved
和当前预览的 subject_digest；该确认不等于 Final Confirmation。

输入和确认由 Agent 根据上游事实与用户决定生成，不要求用户手写协议。

Claim 前已有、且被提议满足当前 Binding 的工作区变化只能通过
`inputs.candidate_material` 进入执行支持。当前本地核心只接受工作树候选：每个 Resource
提供 `baseline_reference=vcs:<resource>@<当前完整 HEAD object>`、已排序且唯一的准确
`changed_paths`，以及当前完整 Resource Snapshot 的 `candidate_digest`；不接受调用方提供
Baseline bytes。Runtime 从只读 Git object 为这些路径重建 Baseline，同时把其他当前用户
变化保留在 Baseline 中，并证明当前工作区准确等于 digest-bound Candidate、候选差异非空
且完全位于 Claim Scope。目录结构变化、非普通文件、可移动引用、非当前 HEAD 或无法区分
候选变化与真实 Baseline 时，在 acquire 前失败关闭。重建的 Baseline、Candidate Snapshot、
不可变 VCS 来源及其差异绑定随 open Payload 持久化并读回后，Runtime 才只恢复已声明差异
到准确 Baseline，再按当前 Method 重放；最终 Result 必须逐字节等于 Candidate。无关的用户
已有变化同时存在于两份 Snapshot，不得被恢复或冒充当前变化。
Candidate Material 不提供 Claim、Artifact 或上游 Authority，且不能与 Frozen Control
Recovery 合并为同一请求。

## Authority 顺序

readiness → acquire → exact Artifact/Revision Reservation → open Payload →
Baseline/Method readback → product operations → immutable Result / Checks →
Final Confirmation → freeze → Claim complete。

只有正式 Claim Provider 授权产品写入。项目内序列化锁只保护物化与读回顺序。
active 请求的 Owner、Binding、Scope、Input 或 Rework 不同均拒绝。
同请求不重复产品操作、不新建空 Revision；completed 无新 Rework 只读返回当前结果。
合法新 Binding / 当前前驱 Result / VFY Return / RLS Issue / 准确控制恢复引用才能开始新的返工序列。
Return / Issue 的 Evidence 必须能沿准确 Evidence Item 与 Digest 解析到 frozen immutable Member。
当前返工序列保留原始 Result Subject，恢复和幂等重复请求不能将它误指向新 Revision。
同一返工集合不可反复创建 Attempt；abandoned 需显式 retry_abandoned 或合法 Rework。

同 Resource 前驱的完整不可变 Result 必须与实际 Baseline 一致。
active 恢复时验证已保存的 Baseline 与前驱关系，同时验证工作区与本 Attempt 最后 Result 一致。
Baseline 包含 dirty 工作区、untracked 内容、文件及目录权限；
用户已有未提交修改的目标文件拒绝覆盖。Snapshot 不使用 HEAD 替代实际工作区。
Result 为完整 Snapshot Member，摘要与 Manifest closure 由 ArtifactStore 验证；
每个资源恰一行，沿用行 Baseline=Result，Changed Scope=None。

Scope 在 acquire 后不可变。所有操作先整批校验，执行前再检查当前 Claim、
Revision generation 和实际 Baseline。符号链接、硬链接和特殊文件失败关闭。
当前核心不执行任意 shell。项目代码检查只允许上述固定适配器，并在断网、无凭证、
副本外只读的 Python audit hook 或 OS Sandbox 与完整 Resource Snapshot 临时副本中运行，避免检查扩大
产品或外部写入范围。
执行中断保留 open Artifact、Baseline 和产品现场；未证明的部分变化不能自动恢复或通过 Gate。

普通 abandon 必须先终止 open Revision，再以相同原因 CAS Claim；
frozen Artifact 只允许 complete 永久失效后的专用恢复路径。
complete 临时失败保留 frozen+active；依赖永久失效保留 frozen 历史，
以 complete:错误码:具体原因将仍匹配的 active Claim 转 abandoned。
Claim 终结失败继续 active，不报告完成。complete / abandon 首次转换和终态幂等重试
都必须核对准确 Attempt、预期 Owner、Artifact ID 与 Revision；abandon 另存实际
`abandoned_by`，恢复调用方不得冒充被阻塞 Owner，重复终结还必须保持 Actor 与 Reason。

## Frozen Control Recovery

只有显式 `--input <同一 IMP Artifact 的当前准确 frozen Revision>` 才能提出控制恢复。
旧 Payload 必须通过关闭上游和外部 Authority 解析的本地完整性校验，且确实因
Lifecycle Authority 或当前 Dependency 链失效；仍有效的完成结果不能空返工。
当前 Binding、Context、Scope、Resource roots、Method 与候选结果必须一致。
未解决的产品 Return、Exception、Open Item、失败事实或不可读回的外部效果不能走 no-change。

恢复引用只进入 Rework References，不进入 inputs，不授予旧 Authority。
Provider 沿用唯一 Artifact ID，递增 Attempt 和不可复用 Revision Reservation；
旧 frozen Payload 不改写。新 Claim 下重新持久化 Checklist，再逐项读取 Resource
与旧不可变候选比较；EVD-RECOVERY 保存候选原始 Binding / Result 字段及当前读回摘要。
只有完全一致才把本 Attempt 记录为 Baseline=Result、Change=N/A、Changed Scope=None、Steps=None。
必须执行当前 Checks、生成当前 Evidence、获得绑定新 Attempt 的 Final Confirmation，
再 freeze、complete；相同恢复集合幂等，陈旧/跨 Lineage/空引用失败关闭。
check 不执行恢复；只有新的 Current completed + frozen + 依赖有效才可投影 VFY ready。

## Side Effects

| Commands | Effect | Boundary |
|---|---|---|
| help/version/commands/examples | none | 仅安装包元数据 |
| check | none | 严格只读 ArtifactStore / Claim / immutable Members |
| auto/create/revise | product/local | 明确授权的 Claim Scope 与项目内 .sdlc |
| abandon | local | 当前 Owner、Attempt、Revision 的精确终结 |

check 不运行执行器，不初始化、不 acquire、不修复、不 freeze、不 complete。
所有局部结论只允许表示 VFY ready，不产生完整 VFY 或 RLS 结论。

## 本地核心范围

本 Contract 不包含 Lifecycle Query、独立 Source Lock 门禁、Runtime Independence、
Fixed Eval、真实宿主适配或真实项目验收结论；这些由后续工作包独立验证。

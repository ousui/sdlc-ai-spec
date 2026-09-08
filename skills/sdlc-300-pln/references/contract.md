# sdlc-300-pln Runtime Contract

`PLN` converts complete frozen REQ/DSN scope authority into one immutable Plan
Artifact containing delivery scope, lifecycle applicability and stable `WI-NNN`
work-item bindings. It never stores live task status and never executes product
changes. `create` allocates only when authoritative PLN applicability is
`required`; `n/a`, `embedded`, `waived` and `pending` return without a Plan
Artifact. `check` is strictly read-only.

## 标准程序输入

业务 stdin 中使用 `inputs.plan`；准确上游集合放 `inputs.scope_inputs`，控制输入放 `inputs.control_inputs`，最终确认放 `inputs.final_confirmation`。字段及枚举见 [输入字段速查](input-reference.md)，语义见 [随包 PLN Spec](300-pln-spec.md)。

plan 可包含 title、summary、profile、pln_disposition、delivery_scope、aggregated_applicability、obligations、work_items、lifecycle_applicability、open_items、evidence、supporting_members、exceptions。scope 与适用性由冻结上游解析，调用者不能用 plan 字段覆盖它们。

`work_items` 是对象数组，每项字段：id=`WI-NNN`、target_phase、outcome、execution_scope、source_references、constraint_references、depends_on、completion_criteria、expected_evidence、responsible_role。引用/执行范围字段为字符串集合；outcome、completion_criteria、expected_evidence、responsible_role 为具体非空文本。编号/顺序由 Agent 根据计划整理，用户不手填；depends_on 必须闭合，不能用依赖说明替代编号。

execution_scope 使用现有标准令牌：`resource:<id>`、`path:<resource-id>/<relative-path>`、`environment:<target>`。IMP 要绑定实际资源，RLS 要绑定唯一环境，前后阶段和依赖顺序不可倒置；不得按文件列表拆出无结果语义的工作项。上游来源、完成条件和实际 Evidence 义务必须闭合，不接受泛泛的“完成/证据”。

delivery_scope Canonical 行使用 source_artifact_reference、inclusion_basis；aggregated_applicability、obligations 与 WI 覆盖来自完整冻结 Scope，缺少上游时正确等待。合法片段：`{"id":"WI-001","target_phase":"IMP","outcome":"实现已批准行为","execution_scope":["resource:app"],"source_references":["<exact-upstream>#R-001"],"constraint_references":[],"depends_on":[],"completion_criteria":"批准的验收条件通过","expected_evidence":"对应测试结果及差异摘要","responsible_role":"developer"}`。其中引用是待物化占位，不是实际 Authority。

`help/version/commands/examples` 不读取业务 stdin、项目或 Store；这不忽略命令自身的非法参数。

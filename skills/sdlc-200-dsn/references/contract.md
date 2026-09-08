# sdlc-200-dsn Bundled Runtime Contract

本目录是安装后 DSN Skill 的自包含运行合同。`200-dsn-spec.md` 与 `200-dsn-domains/*.md` 保留设计期规范的准确字节，并由 `source-lock.json` 绑定；生产 Runtime 不读取开发仓库的 `docs/**` 路径。

- 父合同：`200-dsn-spec.md`
- 固定 Domain：`200-dsn-domains/*.md`，共 16 份
- 用户接口：`interface.json`
- 构建来源锁：`source-lock.json`

这些文件随 Plugin 分发，不提供独立 Artifact Authority，也不构成可单独调用的 Skill。

## 标准程序输入

CLI 参数承载命令/项目/准确上游引用，业务 stdin 对象的 `inputs.design` 承载设计；`inputs.scope_inputs`、`inputs.control_inputs`、`inputs.final_confirmation` 与 design 同级。不要把 Markdown 标题直接当成 JSON 键。枚举见 [输入字段速查](input-reference.md)；领域义务仍由本目录 bundled Spec 确定。

| design 字段 | 实际结构 |
|---|---|
| title、summary、boundary、profile、change_type | 文本；profile/change_type 使用固定枚举 |
| baseline_references、target_state_summary、impact_summary | 基线引用集合及目标/影响文本，不能用用户自述代替上游 Authority |
| changes | 对象数组：object_or_boundary、change、baseline_references、baseline_state、target_state、affected_domains |
| traceability | 对象数组：source_references、design_references、decision_references、vfy_references、na_reason |
| decisions | 对象数组：requirement_references、question、options、decision、rationale、affected_domains；无决策另给 decision_none_reason |
| domains | **对象**：键为 DOM-NNN，值为下述 Domain 对象；不是数组 |
| composite_subdomains | 对象数组：domain_code、subdomain、disposition、basis_references、reason、exception_references；只用于已定义复合领域 |
| cross_domain_conflicts、scope_expansion、simplicity_rationale | 冲突集合、范围扩展标记、简化依据；不得凭这些字段覆盖上游决定 |
| lifecycle_applicability、evidence、supporting_members、open_items、exceptions | 对应本 Skill 正式内容集合；缺省不是全部已确认无 |

每个 Domain 对象：`disposition` 为 required/n/a/waived/pending，`completion` 与其匹配；required 使用 not_started/in_progress/complete，n/a 使用 not_applicable，waived 使用 waived，pending 使用 not_started。还包括 responsible_role、basis_references、reason、exception_reference、design_result_markdown、constraints_impacts、vfy_points、evidence_references。

required complete 必须有可追踪依据和 Design Result 内容；DOM-510 始终 required，包含 VFY Objectives、VFY Methods、Pass Criteria、Evidence Contract；其他 required complete Domain 要有 VFY Point。n/a 有明确依据/理由，waived 有真实 Exception，pending 的 reason 引用 OPI。不得为了格式完整把 16 Domain 全填 required 或 complete。

片段示例：`{"inputs":{"design":{"domains":{"DOM-110":{"disposition":"pending","completion":"not_started","reason":"Pending — OPI-001","basis_references":[]}}}}}`。这是缺口表达，不是可冻结的完整设计。`help/version/commands/examples` 及合法别名不消费业务 stdin、不定位项目或读取 Store；错误命令参数仍拒绝。

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

## Domain 嵌套输入与空值

`constraints_impacts`、`vfy_points`、`evidence_references` 都是**对象数组**，不可传字符串数组。
三个集合均可缺省、为 `null` 或 `[]`；但非 DOM-510 的 required/complete Domain 仍须至少一个完整 VFY Point。
Runtime 的 Python 调用兼容这些集合的 tuple；JSON 使用数组。提供了记录就必须满足该记录的结构，不能用半条 evidence 表示尚未收集的事实。

| 集合 | 每个对象的字段与条件 |
|---|---|
| evidence_references | `reference`：必填、非空具体引用字符串；`supports`：必填、非空引用集合；`purpose`：必填、非空说明文本。缺少依据时 Agent 读取已有上下文或记录缺口，不虚构引用、用途或支持关系 |
| vfy_points | `references`：必填、非空引用集合；`verification_object`、`observable_result`、`expected_evidence`：必填、非空具体文本；`id` 可缺省，沿用 Runtime 默认 VFP ID |
| constraints_impacts | `id`、`type`、`content`、`affected_phase`、`reference` 均保持可选，提供时为字符串或 `null`，允许合法空字符串；缺省 ID 沿用 Runtime 默认 CIM ID，无 reference 时使用既有 N/A 表达 |

引用集合推荐非空字符串数组；原有逗号分隔字符串简写仍支持。数组中的空引用、非字符串元素和重复引用不能被悄悄删除或转成文本；Domain basis 继续遵守原有引用 token 规则。
说明、purpose 与设计正文不新增语言、关键词或固定句式门禁；已有明确占位符/必需章节规则不变。扩展字段不会仅因未列出而被拒绝。
`changes[].affected_domains`、`decisions[].affected_domains` 是 Domain code 字符串数组，缺省为 `[]`（不接受字符串或 `null`）；未知 Domain code 仍由既有 Gate 拒绝。
`traceability` 等已有引用集合使用同一引用类型检查；`final_confirmation` 可缺省/null，提供时为对象，其 mode 必须是既有 human/delegated，摘要、授权与时间不做猜测纠正。

完整的可执行**未完成设计**见 [input-example.json](input-example.json)。Agent 仅将 `${REQ_REFERENCE}` 绑定到真实的准确 frozen REQ，确认其 R-001/AC-001 实际存在，再按以下接口提交；不要请用户手工编写 JSON。
示例缺少最终确认和部分领域决策，dry-run 可构建但不能宣称 Gate 通过，create 只应生成 open/waiting_input；真实设计内容仍须根据实际需求构造。

```text
python3 <plugin>/skills/sdlc-200-dsn/scripts/runtime.py create --project-root <project> --input <exact-REQ-reference> --dry-run --output json
# stdin：绑定准确引用后的 input-example.json 对象
```

## 错误与持久化边界

create 在 Artifact/Revision 分配前运行同一个 Analyzer 的结构检查；revise 保留写前候选构建检查。输入错误使用既有 errors 协议；结构问题的 `details` 包含 `path`（数组使用从 0 开始的索引）、`expected`、`actual`、`problem`、`hint`，Agent 按路径整理格式后重试。
若已分配后失败，返回准确 Artifact/Revision 标识、原始错误类别和 `details.cleanup` 的读回状态。仅清理本次新分配的 open Revision，不按全库差集判断所有权；不 abandon 原有 open/frozen Revision，CAS 冲突保留观察到的并发状态。abandoned 是保留失败记录，不是删除 Artifact。
清理调用失败、未确认生效或读回失败分别明确报告；`unknown` 不等于已清理。未知实现异常标为 `DSN_INTERNAL_ERROR`，不伪装成格式错误。修复输入后可创建新 Artifact，或在原 frozen Artifact 上分配后续 Revision；不得重用 abandoned Revision。

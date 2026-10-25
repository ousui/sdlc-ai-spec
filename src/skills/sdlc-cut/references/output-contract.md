# CUT 输入、记录和输出契约

## 目录

- [适用范围](#适用范围)
- [路径与输入](#路径与输入)
- [cutjson](#cutjson)
- [来源与定位](#来源与定位)
- [目标与草稿](#目标与草稿)
- [条目任务和检查清单](#条目任务和检查清单)
- [实现依赖与决定](#实现依赖与决定)
- [摘要](#摘要)
- [来源说明与归属](#来源说明与归属)
- [receiptjson](#receiptjson)
- [检查与错误](#检查与错误)

## 适用范围

这是 CUT 自身的 format_version=1 契约，不是原 SDLC 状态格式。所有操作只服务一次拆分。不得依据它改写原生阶段、选择文件或父子业务状态。

用户输入为 source、action、goal、groups、targets、workspace、operation。action 默认 preview；明确授权或已有批准覆盖 apply 时继续，不重复逐文件询问。只有执行 apply 才向正式目标发布。

## 路径与输入

- project：经过解析的绝对项目根目录。所有正式输出相对这个目录。
- feature：一个现有正式需求目录；source.directory 相对 project，且不得是项目根或 .sdlc 根。
- feature workspace：project/.sdlc/cuts/<operation_id>，仅一个直接子目录。可指定名字，不支持放到其他任意位置。
- intake：一个或多个明确文件，或至多一份 stdin 原始文字；项目可以尚未初始化。
- intake workspace：项目内一个明确普通目录，不能靠它伪造 .sdlc；未指定目录时只在会话预览。
- snapshot_path、draft_directory、source_notice.draft_path 相对操作目录；draft_files.path 相对对应目标草稿目录。
- 正式来源、操作目录和目标不得互相包含；目标之间互不包含。source/ 与 draft/ 是操作目录内部结构，不受此条禁止。
- 输出路径不得为绝对路径或包含 ..、控制字符、换行；实际写入不能借符号链接/硬链接触及原文件或项目外。不得跟随符号链接递归收集来源。
- 只读的 intake 外部输入文件可以是用户明确的绝对路径，正式写入仍在 project 内。来源链接或不能快照的特殊文件应报告限制并明确处理，不能静默漏过。

## cut.json

下表字段全部出现，条件不适用时用约定的 null 或空数组。inspect 初始文件允许尚未填完；只有补齐并验证后的文件可 apply。

| 字段 | 类型 | 定义 |
| --- | --- | --- |
| format_version | integer | 固定为 1 |
| operation_id | string | 本次操作名，等于操作目录名；非需求编号 |
| project | string | 绝对项目根目录 |
| kind | string | feature 或 intake |
| source | object | 下节规定的来源身份 |
| source_files | array | 全部受保护输入的清单、摘要、用途和快照 |
| source_notice | object/null | feature 必需；intake 必须 null |
| observed_code | object | git、files、limitations，允许没有 Git 或实现观察 |
| targets | array | 至少两个目标，key/目录互异 |
| draft_files | array | 所有目标草稿文件，含每个后继 cut.md |
| items | array | 来源义务及处置 |
| task_mapping | array | 原任务到后继任务的映射，没有任务时 [] |
| checklist_mapping | array | 原清单到后继清单的映射，没有清单时 [] |
| carryover | array | 实现/评审承接依据，无继承时 [] |
| dependencies | array | implementation、release 或 sequence 依赖 |
| questions | array | 问题、归属、是否影响边界、决定或下一步 |
| handoff | object | first_target（可 null）、instruction；不写原生选择 |
| decision | object | boundary_confirmed、apply_authorized、basis |
| content_review | object | completed、summary、limitations |

字段类型和必需条件由标准库校验实现。未知 format_version 拒绝；已知版本的未知顶层字段报告，避免拼错 silently ignored。不要加会改变业务状态的扩展字段。

## 来源与定位

feature 的 source：

~~~json
{"directory": ".sdlc/specs/002-agent", "inputs": []}
~~~

intake 的 source：

~~~json
{"directory": null, "inputs": [{"id": "input-1", "path": "/explicit/input.md"}]}
~~~

stdin 输入的 path 为 null，原文固定到快照；source.inputs 的 id 唯一。stdin 只用于 intake。

source_files 每项：

- id：唯一，如 S001。
- path：feature 为项目相对文件路径；intake 为绝对输入路径，stdin 为 null。
- input_id：feature 为 null；intake 对应 inputs[].id。
- sha256：实际字节的 64 位小写十六进制摘要。
- snapshot_path：相对操作目录；没有使用的历史/忽略文件可 null。
- handling：input、history 或 ignored。
- reason：该文件用途或保留理由。

feature 的清单必须覆盖来源目录全部普通文件；任何新增、删除、修改都触发重新分析。恢复时只豁免本次固定的来源说明。实际作为判断或引用依据的文件必须有快照。

来源定位 source_ref 用对象，不依赖 Markdown HTML 锚点：

~~~json
{"file": "S001", "anchor": "FR-001"}
~~~

也可使用 {"file":"S001","lines":[12,18]}，表示绑定上述文件摘要的一段原始行；anchor 与 lines 二选一。需要整文件时 {"file":"S001"} 即可。anchor 是实际文本中的稳定业务/任务 ID，脚本只按已支持的格式解析；未知格式使用明确行段及内容复核，不假装识别。

对人显示时补上来源目录/文件，例如 002-agent/tasks.md#T014，不能只输出孤立 T014。

## 目标与草稿

targets 每项：

- key：A/B 等本次唯一标识。
- directory：项目相对的新输出目录，父目录必须已经存在。
- draft_directory：操作目录内 draft/<key>。
- outcome：可理解的交付结果。
- next_step：对象，包含 name 和 reason；是按本地原版实际能力给出的建议，不是状态。

draft_files 每项为 {target, path, sha256}。target 匹配 targets.key，path 是该目标内部路径。相同目标不能登记两次同一路径。

feature 草稿只迁移已有且适用的标准材料，不造空 plan/tasks。intake 草稿包含 brief.md；不得用它声称 SPEC 已通过。所有目标还包含 cut.md 归属说明。

draft 实际普通文件集合必须等于登记的目标文件加 source_notice.draft_path；无遗漏、无额外文件、无外部链接。不能把未列出的文件偷偷发布。

source_notice 为 {path,draft_path,sha256}：path 位于正式来源目录内，为新增且不冲突的说明文件；draft_path 位于 draft/。默认 cut.md 冲突时在预览阶段改用明确的新名称并固定，apply 不现场换名。

## 条目、任务和检查清单

items 每项：

- id、source_ref、kind、targets、disposition、reason。
- kind：goal、story、requirement、constraint、acceptance、task、checklist、question、decision 或 artifact。
- disposition：assigned、shared、baseline、deferred、excluded。
- assigned：至少一个明确后继；具体建设责任不能借多目标重复分配。
- shared：至少两个后继，只用于明确共同适用的约束/义务，分别说明责任。
- baseline：引用已存在能力和适用依据，不能借此省略新工作。
- deferred：至少一个后继；延期不等于 excluded。
- excluded：保留用户既有取消/排除依据，不能由程序凭空产生。

task_mapping 每项：

~~~json
{
  "source_ref": {"file": "S003", "anchor": "T014"},
  "source_checked": true,
  "destinations": [{"target": "A", "path": "tasks.md", "anchor": "T006", "checked": true}],
  "carryover_ids": ["C001"],
  "reason": "新范围与现有实现仍相符"
}
~~~

单一后继内任务编号唯一。来源和目标的勾选值必须与实际快照/草稿一致。一个来源任务拆成多个义务时，各目标描述应明确；共享建设只保留一个执行责任。

checklist_mapping 使用同样的 source_ref/source_checked/destinations/carryover_ids/reason 结构。没有稳定条目 ID 时，destinations 使用 lines:[起始,结束] 代替 anchor。适用清单条目都有处置；取消或不适用条目的依据记在 items/reason 中，不能删除未勾项绕过原流程。

所有源任务/清单项均须可定位并有处置。无法按已支持格式清点时，明确输出不支持位置，要求 Agent 提供逐项行段映射并复核，不把扫描得到 0 当成实际没有任务。

## 实现、依赖与决定

observed_code：

~~~json
{"git": null, "files": [], "limitations": ["未作实现完成判断"]}
~~~

新观察的 git 包含 state、实际取得的 head、branch（可 null）；有 HEAD 时还记录 Git 根目录和说明。state 区分 `head`、`unborn`、`no_repository`、`git_unavailable`、`query_failed`，未知不表示 clean。files 项含项目相对 path、当前普通文件的 sha256（已删除时为 null）、reason 和 vcs。vcs 记录相关 HEAD 树项、索引项及 HEAD→索引、索引→工作区的变化状态；选定未跟踪文件记录为 `untracked`，其当前字节仍由 sha256 标识。删除、冲突或查询失败保留明确状态与限制。只读观察与承接有关的路径；摘要和 Git 对象 ID 不是代码备份或完成判定。

旧记录没有 vcs 分层时不补造历史状态：已完成操作的成功重试仍按原回执处理；含相关代码观察的旧预览须重新 `inspect` 并复核方案，已开始发布的旧操作须保留原回执并人工核查写入范围。重新观察会改变方案摘要并撤销旧的应用授权和内容复核结论。

carryover 每项含 id、source_ref、targets、claim、evidence、applicability、remaining。evidence 是可定位的文字/路径或来源引用列表。适用已完成任务或评审勾选必须引用对应 carryover：来源须定位到同一原条目，targets 须包含该后继。共享证据通过明确列出多个 targets 承接。后继草稿中所有已勾选任务和清单项都须登记映射；只在草稿中新增勾选不能绕过检查。有记录不等于程序认定证据充分。

dependencies 每项含 from、requires、external、kind、reason。from 是目标 key；external=false 时 requires 也是目标 key。kind 固定 implementation、release、sequence。分别检查两种硬依赖图，不把序列或代码调用图并入。外部条件使用 external=true 并给出可理解的前置对象。

questions 每项含 id、text、affects_boundary、targets、resolved、resolution、next_step。影响边界且未解决时阻止 apply；内部后续问题可未解决，但必须分配目标和下一步。

decision 的两个布尔值记录已有用户决定；basis 记清对应请求/确认，不编造批准人。摘要不是授权证明。Agent 必须核对真实会话授权。

content_review.completed=true 表示 Agent 已进行本次内容复核，不是业务验收通过。summary 记录结论，limitations 保留不能证明的事项。边界已确认且发布隔离尚未实施可以通过拆分条件，前提是明确归属和下一步。

## 摘要

1. 取 cut.json、cut.md、draft/ 中全部计划普通文件的实际字节。
2. 每个文件计算 SHA-256，路径规范为操作目录相对的 / 分隔路径。
3. 按路径字典序排序。
4. 每行是 hex + 两个空格 + path + LF，UTF-8 编码，最后一行也有 LF。
5. 对整个清单字节计算 SHA-256，得到 plan_sha256。

不归一化文件内容，不重排 JSON 再算。receipt、source 快照和技术锁不直接加入清单；源摘要已绑定在 cut.json 内，快照仍要独立核对。

plan_sha256 由 validate 输出，apply 从 --expected-plan-sha 接收；仅回执保存最终值，禁止写入被其覆盖的文件。

## 来源说明与归属

后继 cut.md 的首行必须为以下形式，JSON 单行且字段固定：

~~~text
<!-- sdlc-cut-origin {"operation_id":"cut-example","target":"A","operation_directory":".sdlc/cuts/cut-example"} -->
~~~

intake 的 operation_directory 为普通操作目录的项目相对位置。该文件正文继续说明来源、承接范围和后续入口；它不作为原版业务状态。

父来源说明首行：

~~~text
<!-- sdlc-cut-source {"operation_id":"cut-example","operation_directory":".sdlc/cuts/cut-example"} -->
~~~

两类标记都随草稿计算摘要。路径与当前记录一致，不从任意未校验的标记跳转到项目外。

父说明不能单独证明已完成；需匹配本次回执身份和 applied_at。后继说明用于确认本次目录归属。一个同内容文件但没有操作归属，不能接管。

## receipt.json

| 字段 | 类型 | 定义 |
| --- | --- | --- |
| format_version | integer | 1 |
| operation_id | string | 与 cut.json 相同 |
| project | string | 已确认项目根 |
| kind | string | 与 cut.json 相同 |
| source | object | 与 cut.json 的来源身份相同 |
| plan_sha256 | string | 本次已确认清单摘要 |
| targets | array | key、directory、origin_path、origin_sha256 |
| writes | array | 固定全部输出：path、sha256、role、target、completed |
| applied_at | string/null | 完成前 null；全部写入验证后为 UTC ISO 8601 时间 |

writes.path 相对 project；role 为 successor-origin、successor-material、source-notice。source-notice 的 target 为 null，其他为目标 key。所有字段在正式发布前固定，completed 逐项更新。回执采用同目录临时文件加原子替换保存，不能据此声称多个需求目录是全局事务。

成功后重复 apply 先核对身份，按当前保留的 cut.json、cut.md、draft 重算原方案摘要，要求它与 expected-plan-sha 和 receipt.plan_sha256 三者一致，再只报告已有结果。不重新检查来源当前内容，不要求后继等于旧草稿，不以旧草稿覆盖后继。后继后来的业务变更不使本次成功失效。

同次未完整操作可恢复已证明归属且字节未变的输出。已写文件与回执尚未同步时，凭提前固定的写入意图、归属和摘要核对。截断、未知文件、归属缺失或外部修改时保留并报告冲突。

## 检查与错误

validate 输出结构错误、来源变化、未决边界、应用阻塞、方案摘要和限制。至少明确 semantic_completeness=not_decided_by_program。

退出码：0 为该命令职责完成；2 为参数/格式错误；3 为本次写入前发现的校验、来源、目标或恢复冲突；4 为本次调用开始正式发布后未完整完成。3 或 4 都必须保留已有现场，并报告此前已发布与尚未发布清单。

结构验证零错误不代表可上线、业务验收或原 SDLC 阶段通过。不使用无范围限定的 PASS/READY_FOR_IMPL。

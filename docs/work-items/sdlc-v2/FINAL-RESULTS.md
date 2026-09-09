# FINAL 同版本验收报告

状态：P0–P4、Q0/Q1/Q2及FINAL已完成本次批准的本地范围。九个产品场景均有实际当前Agent实施、验证和交付回读；fansite R2准确按原实施与新验证交付恢复联合计入。46项映射中43项已有适用证据，3项延期。原失败不改写为首次成功。

## 版本与交付对象

执行版本 H_final 为 `495177acf777251d378652e2a50e47a1b5c4c41a`，对应 clean 安装包 `final-v1`，53个文件。
包内容摘要为 `a3ecb85d9286fe61b80f98882da4e4f6b91ca33aa25616401d0b043967f9a310`，ZIP SHA-256 为 `2ff7ab13010ea7bf8a8831e4149e6bc1127f07ef8216032195d16c5281b968cc`。
执行证据绑定该版本，冻结后的进度文档提交不替换其 source_head。

实现分支 `impl/sdlc-v2-structured-runtime`；实验室分支 `verify/sdlc-v2-structured-runtime`。
实验室 FINAL R0/R1源码与索引分别提交于 `ef4213b4e2f15ef29731d7fa50fce39cccac5215`、`ee4652e8516b40cb8737077861f2fdf1edab04db`；R2及最终映射已提交于 `dde73bc4525522ed8298396b2f129bb884db64b5`。三轮共490份源码逐字节等于实际本轮RLS包；V2-022新验证说明另存，不计第十个产品场景。
本文所在文档提交不作为新执行版本。最终实现/实验室本地HEAD、完整待同步提交列表和清洁状态由提交后[实际回读CLOSEOUT.json](/Users/shuaiw/Workspace/goedge.cloud/test-sdlc/.local-runs/sdlc-v2/CLOSEOUT.json)记录；相对本地跟踪引用计算，不冒称已查询当前远端。

安装目录为 `~/Workspace/goedge.cloud/test-sdlc/.local-runs/sdlc-v2/installed/final-v1`，同级 `final-v1.zip` 是已验证原包。
源码与紧凑索引在实验室 `v2/FINAL`、`v2/final-candidates`；原始请求、stdout/stderr、Store、资产和完整ZIP在忽略目录 `.local-runs/sdlc-v2`。

## 实际验证

同一H的内核测试 **159/159通过**，51.055秒，覆盖真实工具执行、交付回读、工作区导入及独立安装副本；机器契约、九入口格式与接口及唯一v2源码边界检查另行通过，不计入159。
另有 **7组公共CLI确定性重放**，覆盖8个验收ID、346次请求；不并入159，也不计作真实Agent新业务链。
五个重放源码及其原字节摘要已保存在实验室 `v2/FINAL/regression-sources`，原始运行证据及版本保留。

批准46项的[最终独立映射](/Users/shuaiw/Workspace/goedge.cloud/test-sdlc/v2/FINAL/ACCEPTANCE-MAP.md)及[机器明细](/Users/shuaiw/Workspace/goedge.cloud/test-sdlc/v2/FINAL/ACCEPTANCE-MAP.json)逐项保存验收原文、具体代码与测试、原日志和真实链路来源。结论为43项批准本地范围已证；040其他客户端原生认证、045Rust、046SpecKit延期。根复核了映射所引30份代码/测试文件摘要，以及五组独立目录147份证据字节；这不是新增147个测试。

| 场景 | 业务检查 | 独立核验及专项 | 本地交付与根回读 |
|---|---|---|---|
| Admin R0 | 原13保留，最终16通过 | 独立19次含1重叠；编辑唯一性及会话撤销两轮修复 | 已完成 |
| Admin R1 | 32通过 | 独立35次含重叠；真实切分支保留主/控制需求；一次页面修复 | 已完成 |
| Admin R2 | 59通过 | 独立59加1项COMMIT原子性边界；同需求冲突公开恢复 | 已完成；022独立新需求专项另列 |
| SpringGear R0 | 四模块10JUnit；38类major65 | JDK21；离线依赖选型修复后重新实际构建 | 已完成 |
| SpringGear R1 | 25JUnit；41类major65 | 另3项观察器/异常边界 | 已完成 |
| SpringGear R2 | 43JUnit；41类major65 | 另5项上下文边界；真实无关merge继续，组件变化后拒绝旧PASS并复验 | 已完成 |
| fansite R0 | 原24及原UI保留；4条reset断言 | 实际DOM与HTTP红绿，两轮产品修复 | 已完成 |
| fansite R1 | 34Go、47JS、4reset | 真实迁移、Unicode/分页及30项前端绑定检查 | 已完成 |
| fansite R2 | 45Go、47/49JS、4reset及原UI通过并新Run复验 | 独立4探针、29绑定；真实硬中断/unknown/复制恢复 | 原RLS超限保留；新验证交付链已完成 |

表中数字是各自套件或方法执行次数，存在跨轮回归和独立重跑，不相加为独立验收目标数。
原Admin13、Spring10、fansite24来自真实锁定项目来源；Spring不以JDK26或删除模块计通过。
fansite R2为适配明确CAS接口而调整原测试公共请求helper，保留原24条业务断言；helper大小写缺口由独立评审发现并修复，不掩盖原失败。

## 真实Agent与证据边界

当前Agent在用户总授权下显式读取安装版Skill，依次形成阶段输入、在IMP产生代码与测试、实际执行VFY及RLS；不把确定性重放、六个DB状态或事后报告当作自然语言执行证据。
独立审阅结合实际客户端rollout中的Skill完整正文、可见工具输入与输出、源码形成时序、原始公共回执和归档，未提取模型私有思维过程。
三R0客户端记录为Codex Desktop0.153.4、provider openai、配置模型gpt-6-astra、推理级别xhigh；这些是客户端记录，不是服务端effective model认证。
子任务委派正文在本地日志中加密，总任务授权以用户目标文件及根会话为准，不声称重新读到了该密文的原文。
自审和独立子Agent审阅分别标注，未伪造human或原生客户端认证。
Admin R1同Agent先前已完整读取同H Skill，一次重读与提交在同工具调用中，不能说新全文先于该次模型决策。fansite恢复DSN重读输出被截断，完整正文以同Agent原实施链已实际读取为据，不声称本次再次消费了不可见全文。根visible总授权和有界恢复协调保留，不能概括为九原Run首次零错误或无需协调恢复。

Admin R2先在主工作区完成REQ，再公开clone并在实施工作树的新Run完成DSN至RLS；这是明确版本继承，不把无关恢复Run的阶段拼入原产品链。
首次主库collect因clone后共有Run状态分歧被拒，原现场保持。后续同change内容工作树pair保留261行版本映射、原22份源码和59项实际结果/日志，完成冲突、正常checkpoint/resolve、幂等与再导出；其中原业务Run仍是VFY/running历史。
最终原实施Run的RLS/completed归档另存。同需求恢复支持023/024，另以独立验证型新需求完成V2-022：新Run实际59项PASS、完整六阶段/RLS后，new_change交回成功，6旧需求/21原Run/配置/22业务源码保持，外来completed Run不能获取本机执行能力，重复包和原请求幂等成立。源/再导出215行仅31个来源标记变化，135展开成员逐字节相同，原ZIP在imports中独立保存。额外自拟“ZIP内嵌原ZIP”格式没有发生；它未进入正式3项criterion，也非批准022要求，原文与判定均保留，不能声称全部自拟格式无例外通过。见[022索引](/Users/shuaiw/Workspace/goedge.cloud/test-sdlc/v2/FINAL/admin-v22.json)。

fansite R2原实施链因在REQ重复附入R1交付包与完整归档，共91,510,407字节，使本次native ZIP超过64MiB。
原`ASSET_LIMIT`、原Change/Run、45项通过结果和完整归档保持；公开恢复使用新Change准确描述“验证并交付本次已经实际实施的结果”，以小谱系索引连接原对象，实际重跑完整检查并交付。
原failed Run与104,573,133字节完整归档保留；新Run确已completed，原12项业务criterion条件/预期保留，27源码由原5次真实task.write重建后与新native包逐字节相同。新包6,531,478字节，SHA `10c0918e9ca44d70ddd2b7ebe8fdc5373de2e4ae04731a34d4ec039894823e04`，实际execute和回读完成。这是同一场景的公开恢复，不是原Run成功或另一次从零实施。见[fansite R2索引](/Users/shuaiw/Workspace/goedge.cloud/test-sdlc/v2/FINAL/fansite-r2.json)。

根只读汇总器的两个适用性修订另有补记：历史check.run摘要误读status字段，实际应读outcome；六阶段回执现在逐项绑定指定Run/change，允许有证据的clone前REQ继承。
旧回读保留，ZIP字节、原始结果和测试执行未被这些汇总修订改变。

## 修补与范围

P0至Q2的实现及修复已逐工作包本地提交。关键责任层及回归见P1/P2/P3/P4、Q0、Q1、Q2对应报告：

- `715d737`、`cd80ab5`：嵌套输入、作用域、计划依赖、结构化内容及公开事务。
- `d967d47`、`17fc37d`、`b7e558a`：真实执行与收敛、本地交付/逻辑交回、九入口及独立安装包。
- `f5f0c0a`、`b4d4bc4`：修复任务恢复、依赖完整归档、澄清/中断/交付边界。
- `da6751d`、`f31bef3`、`7d71793`：原生交付验收覆盖、VFY退修、Run状态恢复。
- `fc07245`、`6214e5c`：完整认证Header脱敏、分叉revision保留与原归档交回。
- `495177a`：Q2收口及公开内容合并入口文案，是本次最终执行版本。

FINAL不修改冻结Runtime。产品缺口、环境选型、Agent输入/辅助脚本错误、预期负例及公开恢复分别留证。
实际业务执行中的人工SQL/Store/Authority/协议绕过为0；不将曾发生的错误描述成首次零错误。159项开发测试中的明确故障注入及只读取证与实际业务执行分开计量。

已知限制：实际命令收集在macOS Seatbelt验证；其他客户端原生认证、Rust实现对照、Spec Kit实测及MySQL平台未完成，按用户范围另列。
native交付ZIP上限64MiB，当前公开接口不能原地解除已继承的附件链接；应先按大小选择必要原始附件，完整历史归档保持独立。
工作区逻辑交回不合并产品代码；外来源权限/执行历史不会变为本机能力。远端部署适配器与push/merge/deploy执行认证不在本次完成声明中。

## 本地使用与收口

按包内[USAGE.md](/Users/shuaiw/Workspace/goedge.cloud/sdlc-ai-spec/USAGE.md)给出产品副本、需求/验收、本地编辑和检查授权以及固定交付目录。
当前Agent从sdlc-init/CTX进入六阶段，公共CLI为`<python3.11> -B <plugin-root>/scripts/sdlc.py --root <product-root> --request -`，请求从stdin输入；用户不需要填写UUID或SQL。
`.sdlc`默认不入Git；可用sdlc-status只读查看状态，RLS必须实际execute和回读后才算交付。

本次不push、merge主干、tag或release，也不修改宿主配置。历史接管仅为缺失的SpringGear精确Git对象做过一次最小fetch；FINAL未重新下载项目。
大型证据保留本地忽略目录，临时提交消息及部分隔离测试使用/tmp；未将真实凭证写入证据。
本地验收完成；不继续扩充范围。最终文档收口使用已通过的quick检查与独立Skill风格检查，追加diff/范围/源码摘要核对。实验室Spring原有3份空白例外逐字节保留，命令级例外不改宿主配置；其他文件严格检查。提交后的确切状态与待同步列表见CLOSEOUT.json。

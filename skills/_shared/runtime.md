# SDLC v2 安装后共享执行约定

## 入口与绑定

当前Agent负责理解与实际实现，Runtime保存结构化事实、验证范围/依赖/证据及执行操作。
不读取docs、开发AGENTS、测试或Handoff；不解析Markdown表头来恢复控制状态。
插件根目录是本文件上两级目录；唯一入口为 `<plugin-root>/scripts/sdlc.py`。
先确认当前用户指定的产品root和可用Python3.11+，不要使用插件根目录作为产品root。

```text
<python> -B <plugin-root>/scripts/sdlc.py --root <product-root> --request -
```

stdin为单个JSON请求，stdout是单个JSON回执。`--contract`只读返回完整机器契约。
请求字段：api_version固定字符串`2`；command为公开命令；payload为对应对象；
project_id/workspace_id/change_id/run_id只使用Runtime真实回执或明确选择。
新库/新需求/新Run的ID由Runtime分配；批次使用client_key并消费返回ids，不要求用户构造UUID。
请求直接走stdin；若保存请求文件，放在产品输入范围外或.sdlc内，避免请求日志导致代码指纹变化。

```json
{"api_version":"2","command":"workspace.init","payload":{"name":"本地项目"}}
```

phase.prepare提供准确Revision、generation、结构化内容、Context、附件及本阶段Schema。
操作中的关系使用`{"client_key":"名称"}`或`{"id":"Runtime返回的UUID"}`，不能把字符串当引用对象。
phase.submit和内容阶段phase.complete带回expected_generation；成功后更新本地绑定。
REQ/DSN完成会返回下一阶段的新草稿；PLN完成返回采用的已提交Revision。
提交内容不可变，修订用change.revise产生草稿。阶段命令的字段/枚举以公开契约为准。

## 总授权、阶段与实际身份

用户明确授权完整本地需求时，当前Agent可依次加载INIT/CTX及REQ→DSN→PLN→IMP→VFY→RLS，
不反复要求逐阶段review。每个Skill只执行当前阶段；当前Agent在阶段完成后根据总授权选择并读取下一入口。
只有单阶段授权时，达到该阶段完成条件即停止。不得自行扩充目标、改用生产环境、Git或远端交付。
执行身份使用current-agent或宿主实际身份，auto不是human审阅。业务分歧需要决定时只问最小必要问题。
已识别的目标冲突用run.request_input保存当前revision_id、question、conflict及field_path；
Runtime返回needs_input并保存待答事项，在实际回答到达前不得继续正式内容/代码写入。
收到用户回答后用run.answer_input保存question_step_id、原回答和basis_text，再按原阶段修订。
回答不是权限授予或human审阅证明；不得自答、把时间经过当作确认，或用新Run绕过待答事项。

change.create从原始用户请求记录local edit_local/run_check/package_local授权及准确target/basis_text，
不能虚构用户批准。授权随目标工作区隔离。缺前置阶段时，在已有总授权下由当前Agent加载相应入口补齐；
未获相应授权时返回缺口。Skill不自行分派其他能力或读取兄弟私有资源。
网络、全局设置、安装依赖与外部写入不由这些入口自动授权；环境补齐遵守用户明确范围。

## 执行、验证与自动修复

Run先于正式IMP输出建立。run.acquire取得工作区执行lease，后续使用真实lease_id。
任务前驱、start/execute/complete条件和资源冲突分别判断，准备任务不能等待自己的未来产物。
使用task.start→task.write→task.finish保存实际代码与实现事实；写入内容由当前Agent实际编写。
必要的外部工具通过声明的Check argv和check.run执行；不能以本地tool输出外的自述替代Check结果。
任务完成不等于检查pass。验收由实际命令退出码/断言和适用结果支持；Agent审阅独立标注。

check.run的argv是数组，资源/输入范围明确，输出有界且脱敏。input_paths为空默认完整main；
Task写范围不是Check读取范围。实际构建/环境依赖也参与摘要；HEAD改变本身不否定结果。
Check input_paths的access只允许read；workspace.bind/rebind的resources是完整替换映射，须保留`"main":"."`及仍需使用的资源。
公开命令Schema列有environment时，通过payload.environment传非秘密变量，直接使用真实工具argv，不用env前缀掩盖解释器身份。
现有白名单为PATH、JAVA_HOME、GOPROXY、GOTOOLCHAIN、GOCACHE、GOPATH、GOFLAGS、PYTHONDONTWRITEBYTECODE、PYTHONPATH、LANG、LC_ALL、MAVEN_OPTS和JAVA_TOOL_OPTIONS。
Runtime强制GOPROXY=off、GOTOOLCHAIN=local、禁止pyc写入并补齐Java FORK选项。相同检查链的task、check、phase.complete及delivery.prepare使用同一环境映射；缓存写入还须绑定资源并列入Task写范围。
工具必须先通过当前平台实际预检。当前命令收集器支持macOS Seatbelt；不支持的宿主或spawn机制明确blocked。
原始工具stdout/stderr、代码字节/补丁及结果保存为证据，不能手写pass或使用占位日志。
收集器执行期间持续落盘已收到的完整脱敏行；未结束的末行到EOF才保存，硬中断时可能缺失。
部分日志不证明命令完成或pass；unknown仍先检查原工具状态再恢复。

VFY发现合理业务缺口时，记录finding并按返回phase修订内容或修复代码；重新执行受影响检查、
finding.address后使用适用新result做finding.resolve。addressed不等于resolved。
退回执行阶段后用task.next取得待修复任务；修复是新任务尝试，旧完成记录继续保留为历史。
执行完整范围的convergence审阅，检查未实现、部分实现、矛盾和越界功能；未解决blocking缺口不能关闭。
默认格式重试3、修复5、无进展2；触发预算后先诊断，增加预算须有实际依据并用run.configure记录。
不通过删除合法依赖、放宽验收、虚构授权或手工SQL清除阻塞。

## 幂等、诊断与恢复

成功回执保留operation_id。响应丢失时用原ID与原请求查回，同键不同请求冲突。
unknown先operation.reconcile，不能重新发同一副作用或改绑资源来绕过；恢复检查原意图与真实状态。
已关闭run_id不再复用，新操作使用新Run；workspace.export/inspect等管理调用不附已关闭Run。
失败先保留原始错误、请求、Run和证据，再判断产品/Runtime/Skill/环境/测试责任层。
数据库打不开查看返回diagnostic_path，保留原库。视图失败不重做已提交业务效果。
asset.inspect只读列出未登记文件、缺失资产和非法路径；不删除孤立文件，也不宣称已校验全部内容摘要。

## 完成与交付

RLS目标在REQ固定。local包必须真实写出、独立回读且当前输入/时效仍适用，才能完成RLS。
DSN/PLN中native release_readback Check的input_paths确定交付源码范围；省略时包含整个main。
同root多个产品须显式声明本需求的只读源码范围，避免把兄弟项目纳入本地包；不能到交付时临时缩减。
之后workspace.export保留完整内容、CTX、版本、Run/结果、附件和原始诊断的离线归档。
默认摘要向用户报告实际改动、验证、交付位置和剩余问题；JSON回执不掺叙述、不改字段。
.sdlc为本地数据，不默认提交VCS；不存在可用Store时显式INIT，不覆盖旧库或静默降级。
不同版本结果保留各自源码/插件摘要，真实Agent轨迹与确定性重放分别记录。

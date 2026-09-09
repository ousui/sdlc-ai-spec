# 来源与判断边界

> **附录速读：来源支持“当前工具/规范是什么”；新表结构、默认auto、目录布局和实施取舍均为本次设计建议，并非上游标准的现成规定。**

查阅日期：2026-09-09（Asia/Singapore）。sdlc-ai-spec main 已通过GitHub连接器核实为 `f25ed518f662c0ac7306c94f845297f5642c44b2`；Spec Kit main 已核实为 `3a19a6ba900e34a9f5e02848fb8737d1c364a04b`。网页是该日期读取的公开说明，可能继续更新。

当前规范审查为本次关切的关键章节加前轮同SHA已读资料，不声称已经逐条重新审查全部设计域子规范。新设计域清单将在实施A中按实际保留条目补齐。

<a id="source-S01"></a>

**S01 · [Spec Kit 官方首页](https://github.github.io/spec-kit/)**  
默认SDD与多Agent接入；未作性能/质量保证。

<a id="source-S02"></a>

**S02 · [Spec Kit：Existing Projects](https://github.github.io/spec-kit/guides/existing-projects.html)**  
既有项目边界明确的变更；implement/converge循环。

<a id="source-S03"></a>

**S03 · [Spec Kit：Workflows](https://github.github.io/spec-kit/reference/workflows.html)**  
状态、日志、循环、resume以及流程可扩展性。

<a id="source-S04"></a>

**S04 · [Spec Kit：Presets](https://github.github.io/spec-kit/reference/presets.html)**  
命令和模板覆盖机制，不据此声称已有SQL存储插件。

<a id="source-S05"></a>

**S05 · [SQLite Backup API](https://www.sqlite.org/backup.html)**  
一致数据库副本；整体附件闭包仍需本设计导出实现。

<a id="source-S06"></a>

**S06 · [SQLite：Faster Than Filesystem](https://www.sqlite.org/fasterthanfs.html)**  
历史小Blob基准，反对未测量就宣称Blob慢。

<a id="source-S07"></a>

**S07 · [Git worktree 官方说明](https://git-scm.com/docs/git-worktree)**  
登记工作区发现；本设计未把main/worktree定为强制工作方式。

<a id="source-S08"></a>

**S08 · [SQLite STRICT Tables](https://www.sqlite.org/stricttables.html)**  
3.37起STRICT类型能力及约束。

<a id="source-S09"></a>

**S09 · [Anthropic：The AI-Native SDLC playbook](https://claude.com/blog/the-ai-native-sdlc-playbook)**  
阶段循环、控制执行与人的决策责任；本文auto/不入VCS是用户选择。

<a id="source-S10"></a>

**S10 · [当前 core-spec](https://github.com/ousui/sdlc-ai-spec/blob/f25ed518f662c0ac7306c94f845297f5642c44b2/docs/v1.1/core-spec.md)**  
审查开头240行重点：阶段、格式、Identity、Claim和引用。

<a id="source-S11"></a>

**S11 · [当前 artifact-store-spec](https://github.com/ousui/sdlc-ai-spec/blob/f25ed518f662c0ac7306c94f845297f5642c44b2/docs/v1.1/artifact-store-spec.md)**  
审查开头160行重点：Canonical Payload和存储操作。

<a id="source-S12"></a>

**S12 · [当前 CTX spec](https://github.com/ousui/sdlc-ai-spec/blob/f25ed518f662c0ac7306c94f845297f5642c44b2/docs/v1.1/000-ctx-spec.md)**  
审查开头115行：边界、身份、版本和存储。

<a id="source-S13"></a>

**S13 · [当前 DSN spec](https://github.com/ousui/sdlc-ai-spec/blob/f25ed518f662c0ac7306c94f845297f5642c44b2/docs/v1.1/200-dsn-spec.md)**  
审查开头125行：设计边界、16域总纲、成员和追踪。

<a id="source-S14"></a>

**S14 · [当前 PLN spec](https://github.com/ousui/sdlc-ai-spec/blob/f25ed518f662c0ac7306c94f845297f5642c44b2/docs/v1.1/300-pln-spec.md)**  
审查开头105行：计划与工作项、适用性和输入。

<a id="source-S15"></a>

**S15 · [当前 IMP spec](https://github.com/ousui/sdlc-ai-spec/blob/f25ed518f662c0ac7306c94f845297f5642c44b2/docs/v1.1/400-imp-spec.md)**  
审查开头95行：Binding、Claim、结果和边界。

<a id="source-S16"></a>

**S16 · [当前 VFY spec](https://github.com/ousui/sdlc-ai-spec/blob/f25ed518f662c0ac7306c94f845297f5642c44b2/docs/v1.1/500-vfy-spec.md)**  
审查开头100行：Verification/Validation、方法与回流。

<a id="source-S17"></a>

**S17 · [当前 RLS spec](https://github.com/ousui/sdlc-ai-spec/blob/f25ed518f662c0ac7306c94f845297f5642c44b2/docs/v1.1/600-rls-spec.md)**  
审查开头90行：发版、目标回读、适用性和结果绑定。

<a id="source-S18"></a>

**S18 · [当前 REQ spec](https://github.com/ousui/sdlc-ai-spec/blob/f25ed518f662c0ac7306c94f845297f5642c44b2/docs/v1.1/100-req-spec.md)**  
前轮已读取的同一固定SHA：来源、需求、验收与依赖。

<a id="source-S19"></a>

**S19 · [当前存储架构决策](https://github.com/ousui/sdlc-ai-spec/blob/f25ed518f662c0ac7306c94f845297f5642c44b2/docs/architecture/artifact-store-and-projection.md)**  
前轮同一固定SHA：Blob权威和首版不完全关系化。

<a id="source-S20"></a>

**S20 · [当前 AGENTS](https://github.com/ousui/sdlc-ai-spec/blob/f25ed518f662c0ac7306c94f845297f5642c44b2/AGENTS.md)**  
前轮同一固定SHA：工程规则与独立Skill执行限制。

<a id="source-S21"></a>

**S21 · [Spec Kit converge命令模板](https://github.com/github/spec-kit/blob/3a19a6ba900e34a9f5e02848fb8737d1c364a04b/templates/commands/converge.md)**  
参考闭环思路；实际新接口由本设计定义。

<a id="source-S22"></a>

**S22 · [Spec Kit LICENSE](https://github.com/github/spec-kit/blob/3a19a6ba900e34a9f5e02848fb8737d1c364a04b/LICENSE)**  
复用实际资产时保留版权许可；本包没有复制其实现。

<a id="source-S23"></a>

**S23 · [SQLite omitted features](https://www.sqlite.org/omitted.html)**  
本地文件权限与服务端授权的区别。

<a id="source-S24"></a>

**S24 · [Python sqlite3 官方文档](https://docs.python.org/3/library/sqlite3.html)**  
连接、事务与backup接口参考。

<a id="source-U01"></a>

**U01 · 用户当前会话与附件**  
用户对初衷、默认auto、Python、本地SQLite、不入VCS、薄worktree能力、assets路径、可移除旧实现/测试的明确指令，是本次设计的产品需求。`Agent 插件开发指南.txt` 只作为历史工程约束参考；两份真实需求的失败消息用于新回归案例。未对这些项目重新执行IMP/VFY或访问其外部环境。

**已做与未做的验证**  
本地执行了随包SQL模型测试；结果见model-validation.json。没有执行生产Runtime、真实Skill链、Spec Kit对照试用或Rust迁移。

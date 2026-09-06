# Post-integration Skill Conformance — Work Package

## Authority and baseline

用户授权在新分支重新分析八个 Skill 的阶段完成度、在 Web 修复适宜缺口，再移交真实 Client 工作。本包是明确批准的跨 Skill 修复例外，不重新启动 accepted IMP/VFY/RLS。

- Repository: `ousui/sdlc-ai-spec`
- Baseline main: `0289a5ee8d702450fb3f3bc73c89f30a11664bdb`
- Tree: `bb1aa513fe9a67a6cbec0775a6570fae6e50f877`
- Tree-equivalent accepted RLS E3: `2db5b77288ea890f60ed7b07fc8e01b955ebaa13`
- Owned branch: `fix/post-integration-skill-conformance`
- Initial planning checkpoint: `a9700bcc22f343bf8571fc2db10a76b23ed557d7`
- Draft PR: #11 to main; never merge in this work package.

## Required work

1. 独立区分源码存在、固定行为、历史 Evidence、当前部署及 native host certification，不以百分比或目录存在替代验收。
2. 修复已复现 Status 准确引用失败、未知异常/调试回显、JSON meta 与多目标展示；保留只读共享 API，不能引入 Store 副本或 sibling invocation。
3. 保持原 `STS-E01..STS-E14` Plan/Oracle，建立唯一真实主测试映射、无 skip 的 runner、Source Lock 和 installed-copy 测试。锁不等于运行权限。
4. 更新全局 Handoff 和逐 Skill/载体证据台账；澄清按需 evals，不改写历史评测。
5. 对 exact 新源码运行可执行检查，保存失败与通过记录；提供完整 Client Goal 和独立 Web Review 指令。

## Allowed / forbidden paths

允许本工作项、Status 工作项的增量文档、全局 Handoff/Compatibility、开发期 AGENTS/README/DEVELOPMENT、Status 私有源码和测试，以及专用 conformance/status 工具与固定映射。

禁止修改 main、`docs/v1.x/**`、七个 accepted Phase Runtime、历史 Evidence、共享 Package、`.github/**`、真实产品仓库、系统配置或生产 Target。不 force-push、不重写历史、不创建 Release/Tag。不用 Actions 作为执行器。只保存本分支的正常 Commit 和 PR checkpoint。

## Execution and review boundary

已批准的 14 项 Status 功能预期不变。原 Plan 的 CI 文字是历史执行要求；本次用户指定 Web/local-first 和无 Actions，以 exact-source 回执、原始日志及独立 Review 作为执行证据，不虚构 CI 通过。

本包可提交 producer 自检与实际 Web 执行记录，但不自行签署独立 ACCEPTED。真实 Client 候选记录与 portable Python 测试分开。最终缺少 native 能力时只交接该部分，不重新执行已经 accepted 的阶段开发 Goal。

# sdlc-github — 设计交接

## 当前状态

- Work Item：`sdlc-github-foundation/v1`。
- Design：ready；Maintainer decision：pending。
- 实施：not started。
- 当前分支：`design/sdlc-github-foundation-v1`。
- 审查基线：`main@9d9dbf8bc1b9241f80af53cdf5b0426fcbfe3ab9`。
- 本分支仅新增本目录的设计、验证计划、执行提示与交接，不创建正式Skill或修改现有运行时代码。

## 唯一权威输入

- DESIGN.md：目标、能力、接口、认证、目录、结果与实现边界。
- EVAL-PLAN.md：固定验收项、分层Oracle和证据要求。
- EXECUTE-WEB.md：获批准后的新会话任务。

## 唯一下一工作包

Maintainer批准本设计后，按EXECUTE-WEB.md在 `impl/sdlc-github-foundation-v1` 完成Web实施与可运行验证。新会话实际发送该提示词即构成所述工作包的明确批准；本设计会话不自行记录approved。

## 本轮验证范围

核对仓库当前工程规则、共享接口、非Phase Skill样式与官方MCP工具文档；检查设计操作计数、链接、文件范围和文本格式。

Runtime Contract Validator、运行时单元测试、真实MCP调用、三个客户端与长任务均属于实施后的验证，本设计轮未执行，不报告PASS。

## 并行边界

不修改共享 `docs/plugin-development/HANDOFF.md`，不调整其他工作包。实施仅使用自身分支；完成后需要独立Review。设计PR与实施PR的存在不构成main合并或发布授权。

# REQ 顶层文本与澄清应用修复

## 范围与基线

开发分支 `fix/v2-review-github-sharing`，本次起点 `ef7d159d6c67dd6e1acd4a9918b5acba109ee0ec`。
保留该提交的权威插件来源、十入口展示元数据和样式规则。代码交付仍在用户指定的开发仓库；不发布到权威仓库，不合并主干。

## 根因

五个 Revision 文本只在 change.create 写入，子版本整行复制，phase.submit 没有修改入口。
run.answer_input 的职责是保存回答而非自然语言写库；但已回答的顶层字段缺少后续应用跟踪。
所以需求明细更新后，旧 in_scope 仍可随合法的 REQ 提交传播到 DSN 和阅读投影。
同样的公开 CLI 反例已在本次基线安装包重新执行：两种 field_path、共29次请求；旧顶层与新明细共存。

## 修改

- `phase.submit` 增加 REQ-only 的 `update_revision_text`：title、summary、goal、in_scope、out_of_scope；至少一项，省略保持，一批最多一个。
- 不增加平行的 change.update，不接受任意 JSON 路径写入；已提交快照不能原地更新。
- 使用原 generation、事务、幂等回执；顶层文本、条目和关系同批成功或回滚。
- `phase.prepare.pending_applications` 返回已回答但尚未落实的明确顶层字段。回写对应字段后，提交回执 `applied_inputs` 自动绑定问题与内容版本。
- 内容应用关系沿 Revision 祖先检查，包括复制和导入；换 Run 或仅修改其他字段不能清除。
- `phase.complete` 拒绝遗漏应用。非指定字段的通用问题不默认修改 goal；不通过“等待明确”等自然语言关键词设门禁。
- goal/in_scope/out_of_scope 参与任务和检查定义；整体 convergence 还包含 title/summary。纯展示文本变化不让所有业务任务失效，但需要整体审阅刷新。
- 更新机器契约、REQ Skill、共享执行约定、当前 REQ 规范和 USAGE。没有数据库结构变化或兼容迁移分支。

## 测试与边界

`tests/v2/test_revision_text.py`：17条确定性回归，包含完整安装副本的公开CLI澄清/修订/提交/DSN/Markdown/HTML/GitHub预览/归档链，五字段部分更新、幂等、CAS、原子回滚、错误字段、阶段/需求隔离、不可变历史、克隆、新问题、指纹和旧审阅不可复用。
其中一个测试明确注入写后校验故障以证明回滚；这些回归不是新的业务需求或真实模型认证。GitHub只读生成预览，未发送真实业务产物。
原澄清测试补齐“回答应用到目标字段”的断言，便携套件纳入本次新测试。最终准确提交的CI及日志结果附在现有PR中；不将运行中的测试预填为通过。

## 本地重新处理

更新开发分支和实际安装副本，确认 `--contract` 的 REQ 操作出现 `update_revision_text`。
在同一个 Change 内，先读取最后明确的用户回答；当前是 DSN 等后续阶段时以 `change.revise` 回到新 REQ 草稿。
用一个 `phase.submit` 批次修订顶层文本及相关需求/验收，回读 `pending_applications` 和正文后完成 REQ。
保留原始输入、旧Revision和digest。历史来源中出现旧待定描述是允许的，但当前范围不得继续表达旧结论。
“复用已有详情页面”与“不允许跳转”不能互相替代；遇到未覆盖的业务差异由用户明确，Runtime不代替语义判断。

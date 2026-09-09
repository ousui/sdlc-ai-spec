# 可选 GitHub 产物共享

用户显式请求由 sdlc-github 经统一 Runtime 的 github.preview/publish/status/reconcile 操作完成。
当前仅向已有 github.com Issue 追加 Markdown 快照评论。唯一传输为已安装且用户认证的 gh api，不恢复v1私有Store/MCP链。

preview从准确已提交revision生成与本地相同模板的阶段投影，脱敏并绑定Issue、正文和摘要。
publish验证当前身份及目标，在本库operations中先提交intent（run_id=NULL），后执行远端POST及GET回读。
同快照同目标同身份防重复；同调用ID不同请求冲突。unknown不更换ID重发，只分页回查唯一marker及完整正文/身份/目标。
远端人工修改不会被覆盖，分页不完整不能证明不存在。

共享是六阶段之外的可选支持能力，不改变业务状态。发布回执随change归档，导入后只作历史、不成为本机执行能力。
用户只需表达需求及首次Issue地址，UUID和公开payload由Skill按Runtime回执组织。正文不上传整个数据库、日志或附件字节。

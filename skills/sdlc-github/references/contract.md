# GitHub Skill Contract

Contract ID: `sdlc-ai-spec/github-skill/v1`。非 Phase 支撑能力，遵守共享 Skill Interface / Exclusive Execution，结果使用 `sdlc-ai-spec/github-result/v1`。

工具固定为 `sdlc_github_status`、`sdlc_github_read`、五个 `issue_create / issue_update / comment_create / pr_create / pr_update` 写工具及 `sdlc_github_operation_status`。

## 只读 operation

| 组 | 完整目录 |
|---|---|
| repo | `repo.files`、`repo.branches`、`repo.commits`、`repo.commit`、`repo.tags`、`repo.tag` |
| issue | `issue.list`、`issue.get`、`issue.comments` |
| pr | `pr.list`、`pr.get`、`pr.diff`、`pr.files`、`pr.reviews`、`pr.review-comments`、`pr.comments`、`pr.checks`、`pr.status` |
| actions | `actions.workflows`、`actions.runs`、`actions.jobs`、`actions.artifacts`、`actions.run`、`actions.logs` |
| release | `release.list`、`release.get`、`release.latest` |

每次读取一页；page/per-page 或 after 参数只在对应操作有效，默认 30，最大 100。文件可指定 path/ref/sha；ref 与 sha 不能并存。commit 必须 sha/ref 字符串；tag/release.get 必须 tag；Actions jobs/artifacts/run 必须 run-id，logs 必须 job-id，runs 可选 workflow-id。number 为准确正整数。上游工具/参数漂移阻断，不自动扩展能力。

## 写入与恢复

独立 schema 禁止 extra、raw payload 与未知字段。title 不得空白；body 最多 65,000 字符，body-file 最多 64 KiB UTF-8；body 与 body-file 互斥。普通创建正文附加 `<!-- sdlc-github:<request_id> -->` 标记；这不是隐藏批准字段。

所有写入绑定 repository、真实 actor.id、UUIDv4 request_id。跨进程独占 intent 先 fsync，再发一次上游写请求；收到 ID/URL 后只读核对字段和目标。回执只保存必要标识、摘要与观察，不保存正文/Token。更新只能证明当前字段匹配，不宣称跨请求事务。

重复 ID 参数相同返回已有回执；不同参数冲突；未完成 intent 返回 unknown。receipt 默认本地读取（新进程须先 status），reconcile 显式联网且只读。创建仅在完整扫描范围内唯一标记、账户与属性匹配时恢复。分页不完整、多候选、标记丢失或权限变化保持 unknown。已知对象读回可独立证明对象当前状态，不需要猜测标题。

## 调用例子

```text
/sdlc-github status
/sdlc-github read --repo owner/repo --kind pr.get --number 12
/sdlc-github read --repo owner/repo --kind repo.files --path README.md --sha <40位SHA>
/sdlc-github issue-create --repo owner/repo --title "确认标题" --body "确认正文"
/sdlc-github receipt --repo owner/repo --request-id <原请求UUID> --reconcile
```

生产 stdio 启动：`python <plugin-root>/scripts/sdlc_github_mcp.py --data-root <absolute-stable-root>`。仅宿主负责注入 PAT 和原生工具审批。安装配置与代码路径分开绑定，升级代码不迁移或删除稳定根。首版安全文件实现要求 POSIX descriptor/O_NOFOLLOW，直接 Windows 进程不在本次已实现安装边界；WSL 使用其内部真实绝对路径。

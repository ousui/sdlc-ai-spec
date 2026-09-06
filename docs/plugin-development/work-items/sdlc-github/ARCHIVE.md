# GitHub 历史证据索引

按 main@7a454c76 的治理规则，长日志、旧 Goal 与历史执行证据不继续堆积在当前源码树。
原始内容保持在准确提交 `f0c32a06cb65a4718486ab23e7aad95b71df7791`；本轮不重写它们，也不移植历史 PASS。
恢复路径、Work Item 树摘要与外部归档 SHA-256 见 `ARCHIVE.json`。

```bash
git show f0c32a06cb65a4718486ab23e7aad95b71df7791:docs/plugin-development/work-items/sdlc-github/CLIENT-VALIDATION.md
git archive --format=tar.gz -o /absolute/outside/github-history.tar.gz f0c32a06cb65a4718486ab23e7aad95b71df7791 docs/plugin-development/work-items/sdlc-github
```

该 Client 批次为 25 PASS / 1 FAIL / 6 BLOCKED；原 Runtime 为 b035880a6135c1f126ae1a35e1c173221f28807a。
`56de6913-edfc-4beb-bc98-a0f0265b7be5` 仍属 unknown，真实用户 data/live 未被本轮触及；历史归档副本不是可写的运行时状态。
不得删除真实 intent、换 UUID 重放或因查无结果改记 none。原生认证如今不再是门禁，不代表历史未运行项目获得 PASS。

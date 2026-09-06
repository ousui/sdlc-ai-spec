# sdlc-github — 实施工作包交接

## 当前范围

- Work Item：sdlc-github-foundation/v1。
- Maintainer 已在本会话明确批准设计提交：`97c5f17bfcdb2751d446a89b068db2400436631d`。
- 本轮附加指令：完成全部代码与内容，先通过 Mock；真实连接、Token 和本地宿主验证留给 Client。
- 独立分支：`impl/sdlc-github-foundation-v1`；既有 Draft PR #14。
- 生产实现、确定性测试、真实 stdio/Fake HTTP MCP、三份安装配置已完成；准确被测源码 SHA 为 `b035880a6135c1f126ae1a35e1c173221f28807a`；最终 Web 程序结果为 offline 212、integration 6、全仓 1336 项通过，完整证据见 WEB-VALIDATION。
- 本文不改变 DESIGN.md、EVAL-PLAN.md 的已批准定义；批准依据是用户明确指令，不是 Agent 自行批准。

## 唯一下一工作包

本地 `CLIENT-GOAL.md`：只执行真实 GitHub、双实例真实身份与 Codex/Cursor/Claude Code 原生验证，保存独立证据，再移交一次 fresh-context Web Review。不是交给 Client 补写主体 Runtime。

## 并行和安全边界

不改根级共享 HANDOFF、其他 Work Item、docs/v1.x、ArtifactStore 或各 Phase 业务语义。不修改 main/其他分支，不 merge、tag、release、强推或自动扩大宿主权限。真实测试仍限定先前授权仓库及本次标记对象；没有可靠 Fixture 的操作保持 BLOCKED，不创建禁止的 Tag/Release 来凑齐覆盖。

## 状态含义

代码/Mock 完成与产品接受分开。C/D 未运行时整体未接受，PR 保持 Draft。记录中要分别列源代码 SHA、实测 SHA、文档交付 SHA、远端实际 HEAD；只有本地 Git Bundle 中存在的提交不得称已推送。

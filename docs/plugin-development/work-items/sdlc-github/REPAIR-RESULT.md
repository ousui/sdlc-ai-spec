# sdlc-github — main 合并与 Web 修复结果

main@`7a454c76b62c41525fa3990dffdaa9a52b975679` 已通过真正双父合并提交 `1f9340923b66ea2bc06b0ab58a145fa4fbb0b6dc` 合入 `impl/sdlc-github-foundation-v1`；main 自身未改动。
修复 Runtime：`9491c0ef7d9d017d666cca71917e1c3679346824`，tree `03d8615b8853af8192ee8bc5eed34eba0ee5e3c2`。修复已推送，PR #14 保持 Draft。后续报告提交仅改本工作包文档。

## 实际验证

仓库统一 `tools/validate.py --profile full --source-sha 9491c0ef7d9d017d666cca71917e1c3679346824` 返回 exit 0，**1206/1206 测试成功，完整集合执行一次**；执行前后 exact SHA、tree 和干净状态一致。
七项结构检查（Runtime/接口/七节格式/九 Skill 库存/全部 source-lock/Status/Lifecycle）均通过。GitHub 专项在集合内共 231 项，含原有 6 个真正 stdio→loopback Fake HTTP MCP 测试及 13 项新增返修回归；不重复累计数量。

IMP 82、VFY 80、RLS 87、Status 14 的正式 Case 绑定不缩水。总测试数与旧 1336 不直接比较：main 已移除重复包装与旧认证台账，本次采用 main 的去重集合。full 未执行 strict/e2e 的 OS 沙箱与外部项目链，不将 VFY 可移植拒绝用例说成真实沙箱执行。

## 修复

| 组 | 已完成 |
|---|---|
| R1/R2 | issue.list 的 open/closed/all 正确映射；探针复用同一 mapper；评论使用非空探针，空更新正文仍合法 |
| R3/R4 | 明确规范化一层 jobs 包装及其分页，拒绝错误 Run/ID/结构；正确支持轻量 Git Ref 与附注 Git Tag |
| R5/R6 | 先判断完整范围的 marker 唯一性，再查作者/属性；后续读回失败保留 confirmed、URL 与原回执，并追加观察 |
| R7 | 安装生成解释器绑定 launcher，准确相对合约路径；系统 python3 不再是默认执行后门，缺依赖安全阻断 |
| R8 | 哈希不变仅证明内容未改；可选反馈必须区分宿主发现与 Skill 委派扫描/读取/写入 |

Client 捕获的公开 Schema 及响应形状已加入独立 Fixture，真正 HTTP Mock 同步使用这些约束，不靠放松 Fake 迎合实现。

## 主仓新规则

遵守 main 的七节精简 Skill 格式与唯一 full 入口；移除临时合并输入 Workflow 和重复的 GitHub CI 回归路径。
原生独立认证现为 OUT_OF_SCOPE，可选实际使用反馈不再是三端强制门禁；未发生的真实行为也不伪造 PASS。
历史长日志、旧 Goal 和 Client 证据从当前工作树移入可恢复历史索引，原始字节仍在 `f0c32a0`，外部归档 SHA 见 ARCHIVE.json。不修改旧提交或用户本地 data。新验证日志放在仓库外。

## 保留的边界与下一项

本轮未使用真实 PAT，未执行测试仓库业务写入或重放任何真实请求。原 unknown `56de6913-edfc-4beb-bc98-a0f0265b7be5` 的实际状态保持 unknown，必须复用原稳定根、actor 和 UUID，只读核对；查无标记不能记 none。

唯一下一项为 `CLIENT-GOAL.md` 的定向真实复验：status、issue.list、actions.jobs、非空评论、既有两类 Tag、原 unknown 的只读恢复，以及解释器绑定 launcher 冷启动。缺权限/Fixture 如实 BLOCKED，不补建 Tag/Release，不重跑旧全写入批次、不强制三端认证。

禁止修改 main/其他工作分支、其他工作包 Handoff，禁止 merge PR、tag/release、强推或扩大 Token 权限。修复后的真实 Hosted 行为仍未验证；本报告只证明所列程序检查通过。

外部证据的 full.json SHA256：`cd930c4b5f03f140a3f7a38b9a2d9a91db0e1065e0b69bbcdc78aa7bd5128667`；suite.json SHA256：`c25056fb8fc8c17c0d7d36b1f3c11fb54535e5a6ecd22e6f096dc62ba5411544`。原始日志、逐个测试 ID、源码摘要与命令退出码放在同名外部交付包，不重新塞入源码库。

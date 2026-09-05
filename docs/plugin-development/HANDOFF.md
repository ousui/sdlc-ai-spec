# Plugin Development Handoff

## 当前集成基线

本交接替代旧“remaining phases 待批准/未开始”的实时状态。旧记录保留在 Git：`0289a5ee8d702450fb3f3bc73c89f30a11664bdb:docs/plugin-development/HANDOFF.md`。不改写历史结果或冻结 Eval Plan。

- 本轮起点 main：`0289a5ee8d702450fb3f3bc73c89f30a11664bdb`。
- Tree：`bb1aa513fe9a67a6cbec0775a6570fae6e50f877`，与已接受 RLS E3 相等。
- 修复分支：`fix/post-integration-skill-conformance`；唯一新 Draft PR：#11。
- 当前目标：跨 Skill 的实现一致性、Status 缺口和 Client 证据范围；不是重新实现七阶段。

## 阶段矩阵

| Skill | 当前源码/交付状态 | 历史证据与当前限制 |
|---|---|---|
| CTX 000 | Runtime、Eval、锁、Lifecycle 已集成 | 历史 Portable 和 Codex CLI 实际报告存在；不代表当前八 Skill / 五载体全部 Verified |
| REQ 100 | Runtime、固定评测、锁、Lifecycle 已集成 | 历史 Codex 静态 Partial；本轮 Codex CLI 已触发，但在 Authority 预检拒绝，正式 Runtime NOT_RUN；候选待独立复核 |
| DSN 200 | Runtime、33 Case、锁、Lifecycle 已集成 | 历史 Portable 通过；真实 Client 证据仍需逐载体验证 |
| PLN 300 | Runtime、19 Critical tests、锁、Lifecycle 已集成 | 历史结果为指定源码；不外推为当前宿主认证 |
| IMP 400 | accepted Runtime 和正式 Evidence 已集成 | Subject `207a4a16bea8979faee0474cc43cb642cef1f655`；本轮不改写 |
| VFY 500 | accepted Runtime、80 Case 和正式 Evidence 已集成 | Subject `5ea3ba9aa7288021c4d99b14cff76ec0fc405841`；本轮 macOS strict 80/80；CLI 只读候选待独立复核 |
| RLS 600 | accepted S3、87 Case 和正式 Evidence 已集成 | Subject `b790af812cd8d317675d264583711aed59e1460c`；仅 Fake/Sandbox，不是生产批准 |
| sdlc-status | 已修复准确引用/只读错误边界和展示；增加锁、14 Case 独立映射与安装测试 | 新源码的最终执行结果见本工作包回执；独立 Review 未自签 |

完整八 Skill 路径索引：`work-items/post-integration-conformance/SKILL-INVENTORY.json`。
当前 Client 认证：`COMPATIBILITY.json`；历史报告保持原始字节。`NOT_RUN` 是本轮当前部署认证状态，不撤销历史限定范围内的成功。

## 本轮 Client 执行

- 实际被测源码：`fb1d8fb989e5e31d75cd6f311c0e5e663437262d`，tree `cb1a9aa31a2fadb8a434493b75c7a244d38d029b`。
- 与 Web 实际被测源码 `ac6d846a1b0c22d0f284c9ebffd976dc59698a99` 的 Runtime、测试和验证器字节一致；Client 对收到的完整 Head 重新执行。
- Portable 10/10、Strict 13/13；普通回归各 1104/1104；Status 14/14 与安装 12 命令、VFY strict 80/80、RLS 87/87、八锁和 VFY/RLS 安装验证通过。
- Codex CLI `0.153.4`：八个 Skill 独立原生安装、registry discovery、显式调用和未调用对照均有归档。七个 Skill 实际调用正式 Runtime；REQ 只到前置 Authority 拒绝，Behavior PARTIAL。
- 只读/缺输入 Fixture 不外推正向写入和完整生命周期。JSON 进度消息、CTX/IMP 最终 JSON 改写、宿主失败尝试和所有非零退出均保留，等待独立判断。
- `COMPATIBILITY.json` 原字节不变，40 个当前认证单元仍 NOT_RUN/receipt=null；未自签独立 ACCEPTED。
- 当前完整记录：`work-items/post-integration-conformance/CLIENT-VALIDATION.md`、`CLIENT-VALIDATION.json`、`CLIENT-NATIVE-SUMMARY.json` 和 `CLIENT-SHA256-MANIFEST.json`。准确 DELIVERY_HEAD_SHA 见 PR #11 的交付表及提交后远程 readback；文档提交不是实际被测源码。

## 唯一下一工作包

`POST_INTEGRATION_WEB_REVIEW`：按 `work-items/post-integration-conformance/WEB-REVIEW.md`，独立审查 PR #11 的准确 source/delivery SHA、Runtime 回执、150 个流绑定、八份七维 native 候选及保留的失败轨迹。Review 可分别决定 Runtime 与逐载体候选，不推导全产品或三端兼容，不自动合并。

Status 原始 14 项 Oracle 与旧 Phase Case Expected 未改；本次实际执行取代“尚待 Client 验证”的当前描述，不覆盖历史事实。分发仓库元数据差异仍由 Maintainer 在发布前决定。

## 停止与写入边界

只推进本修复分支，保持 Draft。main、已接受各阶段 Evidence、`docs/v1.x/**`、共享包与 `.github/**` 不修改，不创建发布效果，不重新合并历史 PR，不重建 RLS S4/E4。当前包不包含最终发布版本提升、Marketplace 发布或完整业务产品验收。

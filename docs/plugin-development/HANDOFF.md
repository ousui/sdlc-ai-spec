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
| REQ 100 | Runtime、固定评测、锁、Lifecycle 已集成 | 历史 Codex 静态 Partial；真实宿主行为 Unknown；兼容层重构不在本轮 |
| DSN 200 | Runtime、33 Case、锁、Lifecycle 已集成 | 历史 Portable 通过；真实 Client 证据仍需逐载体验证 |
| PLN 300 | Runtime、19 Critical tests、锁、Lifecycle 已集成 | 历史结果为指定源码；不外推为当前宿主认证 |
| IMP 400 | accepted Runtime 和正式 Evidence 已集成 | Subject `207a4a16bea8979faee0474cc43cb642cef1f655`；本轮不改写 |
| VFY 500 | accepted Runtime、80 Case 和正式 Evidence 已集成 | Subject `5ea3ba9aa7288021c4d99b14cff76ec0fc405841`；严格执行仍需可用 OS 沙箱 |
| RLS 600 | accepted S3、87 Case 和正式 Evidence 已集成 | Subject `b790af812cd8d317675d264583711aed59e1460c`；仅 Fake/Sandbox，不是生产批准 |
| sdlc-status | 已修复准确引用/只读错误边界和展示；增加锁、14 Case 独立映射与安装测试 | 新源码的最终执行结果见本工作包回执；独立 Review 未自签 |

完整八 Skill 路径索引：`work-items/post-integration-conformance/SKILL-INVENTORY.json`。
当前 Client 认证：`COMPATIBILITY.json`；历史报告保持原始字节。`NOT_RUN` 是本轮当前部署认证状态，不撤销历史限定范围内的成功。

## 唯一下一工作包

`POST_INTEGRATION_CLIENT_VALIDATION`：读取 `work-items/post-integration-conformance/CLIENT-GOAL.md`。先核验此修复分支 exact HEAD，然后执行 strict post-integration 验证；真实 Client 适配一次只处理一个实际可用的 Client/Surface。其余载体保留 NOT_RUN，不因此伪造总体认证或启动所有 Client。

现有 Status Eval Plan 的 14 项 Oracle 不变。原 Plan 的“CI green”条款在本次用户明确 local/Web-first 且不使用 Actions 执行的修复包中，由 exact-source、本地归档与独立 Review 承担执行证据；旧 Plan 不被静默修改，具体限制记入新结果。

## 停止与写入边界

只推进本修复分支，保持 Draft。main、已接受各阶段 Evidence、`docs/v1.x/**`、共享包与 `.github/**` 不修改，不创建发布效果，不重新合并历史 PR，不重建 RLS S4/E4。当前包不包含最终发布版本提升、Marketplace 发布或完整业务产品验收。

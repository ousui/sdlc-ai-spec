# RLS 最终设计绑定与实施入口

本文件与16号 Goal 定义当前输入；00号保留历史基线。Maintainer 于2026-09-05明确授权本次最终实现、验证与两个 owned refs 交付。旧文档内合并 #7/#9/#8 与直接继承 main 的条件已失效，其余领域规范和87个案例保持。

- Accepted VFY Subject：`5ea3ba9aa7288021c4d99b14cff76ec0fc405841`
- Accepted VFY Evidence：`46509eb6688df30e71ed094132b2d10e81ceb2ac`
- main：`644218e02876c5649fd87cfca12e1876d3b3b8bf`
- 两者 Tree：`3a75052b5ab1a10b91eb4cc1582b527a86e7dd5b`
- Final Web Review：[exact pair ACCEPTED](https://github.com/ousui/sdlc-ai-spec/pull/9#issuecomment-5548759714)
- B：`f171118380535d8c27a1929d0ef061510f82305f`，父顺序为 accepted Evidence、main，Tree 不变。
- 最终拓扑：B → D（RLS设计）→ S（RLS实现）→ E（绑定S的正式证据）。旧RLS Commit仅作为路径来源。

## 宿主预检

当前 macOS 现有 sandbox-exec 的真实 strict E041/E046 已执行2/2 PASS。默认 Codex 受限进程内首次 activation 失败；授权宿主重试仍使用相同 VFY OS 沙箱，网络禁用、exit分别0/1、source前后相等、无skip，无安装和真实目标效果。该结果只证明宿主能力，不替代最终S的80/80 VFY回归。

两个固定外部项目精确 SHA 已读取并干净检出；只记录输入可用，不宣称完整链路通过。

## 最终实现约束

1. INT-001..004：真实 ArtifactStore value objects及CAS；CTX/profile/直接inputs/Artifact Status按Core解析；DomainVerification同时验证approved及当前binding。
2. INT-005与A01..A12：adapter集中读取真实VFY Primary/State/Manifest，重建Final Confirmation，保留producer source_digest并另算transport digest；共享Lifecycle/Claim提供当前性，真实producer差分覆盖正负输入。
3. 保留Effect Sandbox及87案例，修复可信授权、不可回改历史、效果后回写失败恢复；只允许专用临时目标。
4. additive query_rls及status接线，保持VFY行为；最终Source Lock及installed runtime independence；quick/phase/full/external/fresh attest全部绑定稳定S。

逐路径来源及不迁入范围见17-MIGRATION-MANIFEST.json。正式证据只能在全部验证后生成；本设计记录不代表A01..A12 CLOSED或RLS CLOSED LOOP PASS。

## 唯一下一工作包

依16号 Goal 完成 RLS 最终实现、全部验证与精确Ref交付；仅在真实不可恢复HARD_BLOCKED时保存checkpoint并停止，不自签Web Review或合并PR。

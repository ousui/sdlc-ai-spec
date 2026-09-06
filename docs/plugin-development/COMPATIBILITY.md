# Skill / Client Compatibility

## 当前与历史必须分开

机器可读 Authority：`COMPATIBILITY.json`。八个 Skill 分别记录五个载体：Codex CLI、Codex App、Claude Code CLI、Cursor IDE、Cursor CLI；共 40 个独立单元。当前源码部署的 native certification 全部为 **NOT_RUN**。这不是“不支持”，也不撤销历史 CTX Codex CLI 运行记录。

| Skill | Codex CLI | Codex App | Claude Code CLI | Cursor IDE | Cursor CLI |
|---|---|---|---|---|---|
| sdlc-000-ctx | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| sdlc-100-req | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| sdlc-200-dsn | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| sdlc-300-pln | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| sdlc-400-imp | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| sdlc-500-vfy | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| sdlc-600-rls | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| sdlc-status | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |

历史 CTX `ADAPT-CODEX-RESULTS.md` 记录 Codex CLI 0.151.0-alpha.7.1 的实际安装、发现、调用和行为；证据只用于它记录的源码/载体。REQ/DSN 的同名报告明确为静态 Partial、真实宿主 Unknown。三个历史文件的 SHA-256 由 JSON ledger 绑定，不用其证书覆盖其他 Skill 或当前依赖树。此前全插件 Codex Verified 的概括已撤回。

## 提升规则

每个单元提升为 VERIFIED 前，须有 `sdlc-ai-spec/native-skill-receipt/v1`，精确 source SHA、版本、带时区时间、操作者、安装 Runtime 的路径/mode/字节摘要，以及以下七维的实际结果和非空原始文件摘要：installation、discovery、explicit_invocation、negative_invocation、behavior、permissions、installed_independence。

`tools/validate_skill_conformance.py` 会核对部署字节与声明 Git 对象、证据文件摘要、七维完整性和独立 Review 字段。它验证绑定与结构，**不能自行证明操作者或 Review 声明真实**；接受还需要独立审阅实际宿主轨迹。fixture-only 测试不能用于真实认证。

未审阅的执行记录保存为候选归档，不把 ledger 单元伪装成 VERIFIED。每次仅评测一个实际可用载体；另一个载体或 Skill 不从它继承 PASS。依赖代码变化使当前认证失效，需要重验。

## 发布来源待 Maintainer 决定

工作仓库为 `ousui/sdlc-ai-spec`，现有各平台 Manifest/Marketplace 的 homepage/repository 指向 `goedgecloud/sdlc-ai-spec`。本轮未获得变更正式分发目标的明确决定，因此保留元数据，标记 `distribution_target_decision=UNCONFIRMED`，不将其直接判成错误，不据此自动发布或切换仓库。

## 可执行检查

```bash
python3 tools/validate_skill_conformance.py --json-out /tmp/conformance.json
python3 tools/validate_skill_conformance.py --require-client codex-cli --json-out /tmp/codex-certification.json
```

第一条只检查结构和现有证据绑定，不宣称 native PASS。第二条在八个 Codex CLI 单元尚未全部独立接受时必须失败。完整宿主执行与审查流程见 `work-items/post-integration-conformance/CLIENT-GOAL.md`。

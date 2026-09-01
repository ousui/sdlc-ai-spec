# Plugin Development Handoff

## 当前基线

- 当前远端 `main`：`4b8be64accf40467e82502dc7a76ec50fc714588`，包含不完整 DSN，主线 CI 失败。
- 恢复分支：`revert/incomplete-sdlc-200-dsn@4b37924db6ced95d2465ee8e69bb1c3a2a4be4f4`。
- 完整实现分支：`skill/sdlc-200-dsn-v2`，基于恢复分支。
- 已完成正式能力：`sdlc-000-ctx`、`sdlc-100-req`、Lifecycle Query Graph、`sdlc-status`、`sdlc-200-dsn`。

## sdlc-200-dsn 状态

```text
Stage: complete
Design: approved via APPROVAL.md
Evaluate: PASS
Adapt Codex: PARTIAL
Review: PASS
Finalization: ACCEPTED_FOR_PULL_REQUEST
```

## 完成证据

- Fixed Critical Eval：`33/33 PASS`；
- Full repository regression：`177/177 PASS`；
- Runtime Contract / Skill Interface / Lifecycle Query / Status Validator：`PASS`；
- DSN Source Lock：26 项；
- Bundled Runtime Contract：17 份；
- Runtime Independence：`PASS`，开发文档复制 0、外部依赖安装 0；
- SpringGear temporary integration：`PASS`，`ousui/springgear@e855096ff19dcdb303dc4250ba19c30acd743ac7`；
- SpringGear 源码快照和 Git 状态恢复一致，远端写入 0；
- Review Open Findings：Blocker / Major / Minor = `0 / 0 / 0`。

## 重要实现边界

1. DSN 是父 Artifact Set：primary、required Domain Member、Supporting Member、Manifest-Member closure 原子一致。
2. 固定 16 个 bundled Domain Contract，不创建 16 个可调用 Skill；`DOM-510` 固定 required。
3. 生产 Runtime 使用稳定 Contract ID + SHA-256，不依赖开发期物理路径。
4. `--input/-i` 可重复且失败关闭；Meta Command 绝对无执行副作用。
5. 上游 REQ `DSN=n/a/waived` 不创建空 DSN；`pending` 在分配前停止。
6. Lifecycle Query 读取 DSN Applicability，准确投影 PLN 或直接 IMP；异常时不猜测。
7. `check` 严格只读；失败的新 Control Reservation 准确 abandon。
8. Codex 仅有静态 Adapter 证据，真实安装后行为仍为 Unknown。

## 唯一下一工作包

创建并审查：

```text
skill/sdlc-200-dsn-v2 → main
```

该 PR 的净效果应同时撤销不完整实现并引入完整实现。推荐 `Squash and merge`。不得自动 merge、tag 或 release。

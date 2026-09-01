# Plugin Development Handoff

## 当前基线

- 远端 `main`：`0c38135e3e8bdad0d60d674c93ad42078e880134`。
- `main` 最新 validate：success。
- 已完成正式能力：
  - `sdlc-000-ctx`
  - `sdlc-100-req`
  - `sdlc-200-dsn`
  - Lifecycle Query Graph
  - `sdlc-status`
- 当前 Design Branch：`design/remaining-phase-skills`。
- 本分支只包含开发期 Design、Eval Plan、Architecture 和 Handoff；未创建新的正式 Skill Runtime。

## 批量设计状态

| Skill | Design | Eval Plan | Maintainer Decision | Implement |
|---|---|---|---|---|
| `sdlc-300-pln` | ready | ready | pending | not started |
| `sdlc-400-imp` | ready | ready | pending | not started |
| `sdlc-500-vfy` | ready | ready | pending | not started |
| `sdlc-600-rls` | ready | ready | pending | not started |

共同设计基线：

```text
docs/plugin-development/architecture/remaining-phase-skill-design.md
docs/plugin-development/architecture/remaining-phase-interface-extension.md
docs/plugin-development/architecture/remaining-phase-foundations.md
```

## 关键设计决定

1. 一阶段一个主 Skill；不按平台、语言、测试工具或执行方式拆兄弟 Skill。
2. `sdlc-300-pln` 统一拥有 Delivery Scope、Work Item Set、Coverage 和 Dependency Authority。
3. `sdlc-400-imp` 实现前先完成共享 Claim Provider 与 immutable Resource Result Foundation。
4. `sdlc-500-vfy` 统一管理 Inspection、Analysis、Demonstration、Test，不拆 QA/Test Skill。
5. `sdlc-600-rls` 保持平台中立；外部 Target Effect 必须使用与 `write_policy` 分离的准确授权。
6. 所有 Skill 继承 Shared Skill Interface，裸调用合法，默认只在真实决策或高影响副作用时询问用户。
7. Phase Interface 从固定精确命令集合扩展为核心命令子集加已声明附加命令；现有 Skill 行为保持不变。
8. Claim、Resource Result、Execution Evidence 和 Effect Authorization 的逻辑 Contract 已冻结，物理实现按后续 Foundation 工作包完成。
9. Design 可以批量完成；Approval、Implement、Evaluate、Adapt、Review、Finalize 必须逐 Skill 进行。

## 实现顺序

```text
sdlc-300-pln
    ↓
Claim Provider + Resource Result Foundation
    ↓
sdlc-400-imp
    ↓
sdlc-500-vfy
    ↓
sdlc-600-rls
```

不得在前一项尚未合入 `main` 且联合 CI 未通过时实现后一项。

## 唯一下一工作包

Maintainer 对本分支中的四份 Design Contract、四份 Eval Plan 和三份共同架构设计进行批量审查，并作出以下之一：

```text
APPROVE_REMAINING_PHASE_DESIGNS
CORRECT_REMAINING_PHASE_DESIGNS
```

批准只表示设计与 Foundation 逻辑边界可以作为后续工作基线，不授权同时实现四个 Skill。批准后第一个实现工作包固定为：

```text
sdlc-300-pln implement
```

不得在本设计分支创建 `SKILL.md`、Runtime、Fixture、Source Lock、Adapter、Claim Provider 或外部执行代码；不得自动 merge、tag 或 release。

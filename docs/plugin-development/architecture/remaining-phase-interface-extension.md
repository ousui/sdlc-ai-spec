# Remaining Phase Interface Extension

## 1. Problem

当前 `tools/validate_skill_interfaces.py` 对所有 `sdlc-NNN-*` 强制要求命令集合严格等于：

```text
auto, create, revise, check, help, version, commands, examples
```

后续阶段存在真实、独立的用户意图：

- IMP：`abandon`
- VFY：`run`
- RLS：`execute`、`confirm`、`cancel`

把这些行为塞入 `revise` 会降低可发现性、审计性和副作用边界；为每个行为创建兄弟 Skill 又会分裂 Artifact Authority。因此需要一个向后兼容的 Interface 扩展。

## 2. Design Decision

Phase Skill 命令规则从“精确集合”调整为“核心子集 + 已声明扩展”：

```text
required core:
  auto, create, revise, check,
  help, version, commands, examples

optional phase commands:
  lowercase kebab-case,
  必须在 interface.json 中声明，
  必须定义 writes/effects、参数、状态前置和 Eval。
```

现有 CTX、REQ、DSN 不添加新命令，行为和 Interface JSON 保持不变。

## 3. Validator 规则

实现阶段修改 `validate_skill_interfaces.py`：

- `PHASE_COMMANDS` 改为 `PHASE_REQUIRED_COMMANDS`；
- 校验 `required ⊆ declared`，不再要求严格相等；
- 附加命令不能覆盖元命令或公共参数名；
- 每个附加命令必须有 description 和 `writes`；
- 声明外部副作用的命令必须引用独立授权 Contract；
- `help/commands/examples` 必须展示附加命令；
- 未声明命令仍返回 `COMMAND_UNKNOWN`。

## 4. 参数扩展

共享 Parser 保持公共参数不变。Phase 私有参数通过统一 Extension 描述注册，不允许每个 Skill 自由解析第二套语法。

计划扩展：

| Skill | Parameter | Cardinality | Meaning |
|---|---|---:|---|
| IMP | `--binding/-b` | one | 准确 IMP Binding |
| IMP | `--owner` | one | 稳定执行身份 |
| VFY | `--method/-m` | repeatable | 当前 VFY Method ID |
| RLS | `--item` | repeatable | 当前 RLI/RCF ID |
| RLS | `--target` | one | Release Target |
| RLS | `--release-reference` | one | 稳定发版标识 |

所有扩展都必须支持空格和 `=`，检测缺值、重复、冲突、元命令组合和 `--` 自由文本边界。

## 5. Side-effect Classification

`writes=true` 只表示命令可能修改项目内状态，不代表远端或目标副作用授权。

建议 Interface 增加可选声明：

```json
{
  "effects": "none | local | product | external"
}
```

- `none`：help/check；
- `local`：ArtifactStore；
- `product`：Claim Scope 内产品文件，例如 IMP create/revise；
- `external`：RLS execute/cancel 等目标效果。

若暂不提升 Interface Schema Version，第一版可以在 Skill 私有 Contract 中声明，并由专用 Validator 检查；在第二个真实使用者出现后再升级共享 Schema。

## 6. Backward Compatibility

- 现有命令解析结果不变；
- 未使用私有参数时现有 Skill 不受影响；
- `auto/create/revise/check` 始终存在；
- Source Lock 和 Artifact Evaluation Contract 不因 UI 命令扩展改变；
- Interface Contract 仍是用户入口 Contract，不是 Artifact Authority Contract。

## 7. Eval

必须覆盖：

- 核心命令仍全部存在；
- 附加命令被 help/commands/examples 发现；
- 未声明命令失败；
- 元命令与执行参数冲突；
- 附加命令状态前置；
- product/external 副作用授权不能被 `write_policy=auto` 错误扩大；
- CTX、REQ、DSN、Status 全部回归通过。

本文件只批准设计方向；实际共享 Contract、Schema、Parser 和 Validator 的修改应在第一个需要附加命令的实现工作包中完成，并由后续 Skill 复用。

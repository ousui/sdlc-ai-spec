# sdlc-400-imp 标准输入字段速查

由 `tools/generate_input_reference.py` 从现有 Runtime 常量生成；勿手工编辑。
本表不是新协议；结构之外的语义、来源及授权见 [contract.md](contract.md)。

## Method blocks

| consideration | ID 前缀 | 必填字段 | 数组元素字段 |
|---|---|---|---|
| Calculation Rules | `CAL` | `boundary_and_invalid_values`, `expression`, `inputs_and_units`, `output`, `precision_and_rounding` | 非空文本字段 |
| Decision Rules | `DEC` | `rules` | `conditions`, `id`, `outcome`, `priority` |
| State Transitions | `STA` | `transitions` | `current`, `effect`, `event`, `id`, `illegal_handling`, `next` |
| Algorithm & Invariants | `ALG` | `inputs`, `invariants`, `outputs`, `pseudocode`, `scale_or_limits` | 非空文本字段 |
| Data Contract & Transformation | `MAP` | `mappings` | `null_or_default`, `source`, `target`, `transformation`, `validation` |
| Boundary & Failure Handling | `ERR` | `classification`, `handling`, `observable_result`, `recovery`, `trigger` | 非空文本字段 |
| Effects & Consistency | `EFF` | `consistency_or_atomicity`, `failure_handling`, `idempotency`, `order_and_condition`, `resource_or_effect` | 非空文本字段 |

每个 Block 还需 `id`、`consideration`。`rules/transitions/mappings` 为数组，其余字段为非空字符串。
这些是 Method 的条件必填内容，不要求每个 Step 都具有全部七类 Block。

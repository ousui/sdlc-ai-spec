# sdlc-200-dsn 标准输入字段速查

由 `tools/generate_input_reference.py` 从现有 Runtime 常量生成；勿手工编辑。
本表不是新协议；结构之外的语义、来源及授权见 [contract.md](contract.md)。

| 字段 | 标准值 / 字段集合 |
|---|---|
| `profile` | `full`, `hotfix`, `lite` |
| `change_type` | `incremental`, `new`, `reuse` |
| `changes[].change` | `add`, `modify`, `remove`, `reuse` |
| `disposition` | `n/a`, `pending`, `required`, `waived` |
| `lifecycle_applicability[].phase` | `IMP`, `PLN`, `RLS`, `VFY` |

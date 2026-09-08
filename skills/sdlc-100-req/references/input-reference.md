# sdlc-100-req 标准输入字段速查

由 `tools/generate_input_reference.py` 从现有 Runtime 常量生成；勿手工编辑。
本表不是新协议；结构之外的语义、来源及授权见 [contract.md](contract.md)。

| 字段 | 标准值 / 字段集合 |
|---|---|
| `profile` | `full`, `hotfix`, `lite` |
| `requirements[].type` | `behavior`, `constraint`, `quality`, `rule` |
| `sources[].type` | `artifact`, `conversation`, `document`, `incident`, `other`, `text` |
| `disposition` | `embedded`, `n/a`, `pending`, `required`, `waived` |
| `lifecycle_applicability[].phase` | `DSN`, `IMP`, `PLN`, `RLS`, `VFY` |

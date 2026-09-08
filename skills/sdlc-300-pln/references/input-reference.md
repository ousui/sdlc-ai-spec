# sdlc-300-pln 标准输入字段速查

由 `tools/generate_input_reference.py` 从现有 Runtime 常量生成；勿手工编辑。
本表不是新协议；结构之外的语义、来源及授权见 [contract.md](contract.md)。

| 字段 | 标准值 / 字段集合 |
|---|---|
| `work_items[].target_phase` | `IMP`, `RLS`, `VFY` |
| `disposition` | `embedded`, `n/a`, `pending`, `required`, `waived` |
| `work_items[] 字段` | `completion_criteria`, `constraint_references`, `depends_on`, `execution_scope`, `expected_evidence`, `id`, `outcome`, `responsible_role`, `source_references`, `target_phase` |

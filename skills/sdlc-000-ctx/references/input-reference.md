# sdlc-000-ctx 标准输入字段速查

由 `tools/generate_input_reference.py` 从现有 Runtime 常量生成；勿手工编辑。
本表不是新协议；结构之外的语义、来源及授权见 [contract.md](contract.md)。

## 集合行（位于 inputs.context）

| 集合 / ID 前缀 | 行字段 |
|---|---|
| `resources` / `RSC` | `id`, `type`, `name`, `role`, `locator`, `baseline_reference`, `basis`, `basis_references` |
| `technologies` / `TEC` | `id`, `category`, `name`, `version_or_constraint`, `purpose`, `basis`, `basis_references` |
| `engineering_entries` / `ENG` | `id`, `purpose`, `command_or_entry_point`, `working_scope`, `preconditions`, `basis`, `basis_references` |
| `components` / `CMP` | `id`, `name`, `type`, `resource_reference`, `responsibility`, `entry_point`, `depends_on`, `authority_reference`, `basis`, `basis_references` |
| `rules` / `RUL` | `id`, `category`, `rule_summary`, `scope`, `authority_reference`, `basis`, `basis_references` |
| `environments` / `ENV` | `id`, `environment`, `purpose`, `accessibility`, `data_and_network_boundary`, `basis`, `basis_references` |
| `constraints` / `CON` | `id`, `constraint`, `scope`, `impact`, `required_handling`, `authority_reference`, `basis`, `basis_references` |

## 固定枚举

| 字段 | 标准值 |
|---|---|
| `basis` | `confirmed`, `observed`, `referenced` |
| `resources.type` | `application`, `database`, `document-set`, `infrastructure`, `library`, `module`, `other`, `repository`, `service` |
| `resources.role` | `primary`, `supporting` |
| `technologies.category` | `build`, `framework`, `language`, `other`, `package`, `quality`, `runtime`, `test` |
| `engineering_entries.purpose` | `build`, `format`, `lint`, `other`, `package`, `run`, `test` |
| `rules.category` | `branch`, `code`, `commit`, `compatibility`, `documentation`, `other`, `release`, `security`, `test` |
| `environments.environment` | `development`, `local`, `other`, `production`, `staging`, `test` |
| `environments.accessibility` | `available`, `restricted`, `unavailable` |

## engineering_entries.purpose 的无歧义别名

| 输入 | 标准值 |
|---|---|
| `buidl` | `build` |
| `bulid` | `build` |
| `其他` | `other` |
| `启动` | `run` |
| `打包` | `package` |
| `构建` | `build` |
| `格式化` | `format` |
| `测试` | `test` |
| `编译` | `build` |
| `运行` | `run` |
| `静态检查` | `lint` |

仅描述性枚举接受标准值大小写及首尾空白整理；不改写命令、引用、摘要、权限或事实。

## Evidence 输入字段

`id`, `type`, `supports_references`, `source_or_producer`, `reference`, `integrity_or_digest`, `produced_at`, `sensitivity_or_access`

`empty_reason` 是 Canonical 输出字段，不是输入字段。

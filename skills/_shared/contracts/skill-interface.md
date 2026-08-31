# Shared Skill Interface Contract

| Field | Value |
|---|---|
| Contract ID | `sdlc-ai-spec/runtime/skill-interface/v1` |
| Contract Version | `1` |

本 Contract 定义所有正式 Skill 的用户调用、参数归一化、默认推断、决策权、标准写入和用户可见输出。目标是让用户通过短命令稳定执行统一 SOP，而不是重新编写长提示词或理解内部 Artifact 协议。

## 1. 调用模型

推荐语法：

```text
/<skill> [command] [options] [-- free-form request]
```

- 裸调用合法，默认 `command=auto`；
- 命令和参数只负责表达用户意图，不直接等同于 Runtime Invocation；
- Skill 必须先归一化参数、观察工作区、解决确定性默认值，再构造完整 Runtime Invocation；
- 不得把空 Invocation 直接提交 Runtime 后将内部错误转嫁给用户。

## 2. 标准命令

所有正式 Skill 必须提供：

- `auto`：默认，依据唯一工作区、已有 Artifact、准确 Reference 和状态机选择唯一合法操作；
- 业务命令：由 Skill 定义，Phase Artifact Skill 至少包含 `create / revise / check`；
- `help`：显示用途、默认行为、参数、写入范围和示例；
- `version`：显示 Skill Version 与本 Interface Contract；
- `commands`：列出全部命令及一句话说明；
- `examples`：显示最小、常用和显式参数示例。

标准元命令别名：

```text
help       -h --help
version    -V --version
commands      --commands --list-commands
examples      --examples
```

元命令不得执行项目扫描、Runtime 或写入。`create --help` 可显示命令级帮助。

## 3. 参数语法

### 3.1 推荐写法

```text
create
--command create
--command=create
--operation create
--operation=create
-p /absolute/project
--project-root=/absolute/project
```

采用 GNU/POSIX 风格：长参数以 `--` 开头，短参数为单字符；带值参数支持空格或 `=`。不支持长参数自动缩写，也不组合短参数，避免 Agent 解释漂移。

### 3.2 Command / Operation 兼容写法

以下形式必须归一化为同一 `command=create`：

```text
--create
create
command create
cmd create
command=create
--command=create
-c create
-c=create
operation create
op create
operation=create
--operation=create
-o create
-o=create
```

说明：

- `create` 是首选子命令；
- `--command` / `-c` 是跨所有 Skill 的通用显式参数；
- `--operation` / `-o` 是 Artifact Phase Skill 的兼容参数；
- `command/cmd` 与 `operation/op` 是面向自然语言调用的宽松别名；
- `--create` 是快捷选择器；
- Unix 工具常把 `-o` 用作 output，本 Contract 将输出格式短参数固定为 `-f`，不得在同一 Skill 中复用 `-o`。

不同业务命令同时出现时必须返回 `ARGUMENT_CONFLICT`，不得采用“最后一个覆盖前一个”。重复同值可接受并返回非阻塞 warning。

### 3.3 公共参数

| Long | Short | Default | Meaning |
|---|---:|---|---|
| `--command` | `-c` | `auto` | 通用业务命令或自动解析 |
| `--operation` | `-o` | `auto` | Artifact Phase 的 command 兼容名 |
| `--project-root` | `-p` | `auto` | 唯一当前工作区或显式绝对路径 |
| `--reference` | `-r` | `auto` | 准确 Artifact Revision Reference |
| `--decision-policy` | `-d` | `user` | `user / model / experiment` |
| `--write-policy` | `-w` | `auto` | `auto / confirm / deny` |
| `--dry-run` | `-n` | `false` | 只构造和验证，不持久化 |
| `--output` | `-f` | `summary` | `summary / json / debug` |

快捷别名：

```text
--no-write       == --write-policy=deny
--confirm-write  == --write-policy=confirm
```

`--` 结束结构化参数，之后内容作为自由文本请求传给 Skill，不再解析为参数。

## 4. 参数解析优先级

按以下顺序解析，每层只能补充尚未确定的值：

1. 用户显式参数；
2. 当前请求中已有准确事实；
3. 宿主提供的唯一工作区或选中 Artifact；
4. ArtifactStore 与状态机给出的唯一合法动作；
5. 100% 唯一的工作区观察结果；
6. 用户决策。

不得以模型主观置信度代替唯一性。若存在两个或以上合法选择且没有可证明的最优解，必须进入决策流程。

## 5. 决策策略

### `decision_policy=user`（默认）

- 模型排除非法选项并给出一个推荐项、理由、影响和备选项；
- 用户作出最终业务或设计决定；
- 不得要求用户填写 Evidence ID、Digest、Confirmation JSON 等内部协议。

### `decision_policy=model`

仅在用户明确授权时，模型可在合法候选中选择。结果必须记录选择、理由、被放弃选项和残余风险。

### `decision_policy=experiment`

仅在用户明确授权时，通过预先定义的候选、指标、范围、成本和停止条件进行测试后选择。模型偏好不得冒充实验结论。

## 6. 写入策略

### `write_policy=auto`（默认）

显式调用 Skill 即授权执行其 Contract 已声明的标准、项目内、局部且可恢复写入，例如创建或更新 `.sdlc/store.sqlite3` 中当前 Artifact。宿主仍必须授予实际文件权限。

### `write_policy=confirm`

在第一次标准项目内写入前请求一次自然语言确认。

### `write_policy=deny`

不得执行任何项目写入；等同只读或 dry-run 边界，具体由命令 Contract 决定。

无论何种 write policy，以下行为始终需要单独明确授权：

- 删除或覆盖不可变 / frozen 内容；
- 修改 Project Root 外文件；
- Git commit、push、merge、tag、release；
- 远程 API 或外部系统写入；
- 安装依赖或扩大作用域。

工作区可写权限只表示技术能力，不自动授权以上高影响副作用。

## 7. 自动观察与事实处理

Skill 应读取完成当前任务所需的最小工作区内容，自动生成 observed / referenced Evidence，并将用户自然语言确认转换为 confirmed Basis。禁止：

- 将 observed 事实冒充 confirmed；
- 因“不允许猜测”而拒绝读取 README、构建清单、目录、配置或已有 Store；
- 让用户手工构造 Evidence ID、basis_references、Manifest 或 Runtime Envelope。

## 8. 用户交互

仅在以下情况提问：

- 目标项目或准确 Artifact 无法唯一确定；
- 存在多个合法业务 / 设计选项且无确定最优解；
- 需要高影响或外部副作用授权；
- Contract 明确要求真实人工确认。

提问必须：

1. 只提出当前最小决策；
2. 提供推荐项及原因；
3. 列出主要备选及影响；
4. 接受编号、短值或自然语言答案；
5. 内部完成 ID、Evidence 和 Confirmation 映射。

## 9. 输出模式

### `summary`（默认）

面向用户输出：状态、实际完成内容、Artifact、主要依据、实际副作用、待决策项和唯一下一动作。默认隐藏内部 JSON、Digest 和 Manifest。

### `json`

只输出结构化结果，供程序或其他 Agent 消费。

### `debug`

输出参数归一化、来源、Evidence、内部 Invocation、Runtime Result、文件和摘要。不得泄露 Secret。

## 10. 稳定错误

参数层至少提供：

- `ARGUMENT_QUOTE_ERROR`
- `ARGUMENT_UNKNOWN`
- `ARGUMENT_VALUE_REQUIRED`
- `ARGUMENT_VALUE_INVALID`
- `ARGUMENT_CONFLICT`
- `COMMAND_UNKNOWN`
- `INTERFACE_SPEC_INVALID`

未知参数必须失败并给出 help 入口；不得静默忽略拼写错误。

## 11. Skill 打包要求

每个正式 Skill 必须包含：

```text
references/interface.json
```

并符合 `skills/_shared/schemas/skill-interface.schema.json`。该文件声明 Skill Version、默认命令、命令说明和示例。用户参数经共享 `packages/sdlc_runtime/skill_args.py` 归一化；Skill 不得自行实现不兼容的第二套解析器。

## 12. Eval 要求

每个 Skill 至少验证：

- 裸调用与 `command=auto`；
- 推荐子命令和全部已声明别名；
- `-h/--help`、`-V/--version`、`commands`、`examples`；
- 默认值和显式覆盖；
- 参数冲突、未知参数、缺值和引号错误；
- 唯一推断与多候选用户决策；
- `decision_policy` 三种路径；
- `write_policy` 三种路径；
- `summary/json/debug`；
- 标准写入不重复询问，高影响写入必须询问；
- 用户无需接触内部 Evidence / Confirmation JSON；
- Runtime Independence 与真实 Client 行为。

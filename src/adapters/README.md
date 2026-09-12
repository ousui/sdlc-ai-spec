# 移植适配源

本目录保存 **SDLC AI SPEC 相对于锁定 Spec Kit 上游所维护的显式移植适配源和本地能力源**。

它属于产品源码层，而不是最终安装包或运行时目录：

- 不属于 `src/upstream/`，不得冒充上游原文；
- 不直接发布为 `dist/adapters/`；
- 插件 Runtime 不直接读取本目录；
- 由 `tools/port.py`、`tools/render.py`、`tools/localize.py`、`tools/build.py` 等构建工具消费；
- 修改后必须重新执行本地化校验、构建、上游等价性检查和回归测试；
- 不允许为了让测试通过而修改 `src/upstream/`，也不允许手工修改对应的 `dist/` 生成物。

## 当前文件分类

### 自然语言适配源

- `BINDING.md`：插件安装位置、业务项目位置、宿主和项目状态之间的绑定约束；其中文审查版本会进入九个核心 Skill 的最终流程。
- `INIT.md`：本项目原创 `sdlc-000-init` 的英文源基线。
- `STATUS.md`：本项目原创 `sdlc-status` 的英文源基线。
- `PROJECT-README.md`：新项目 `.sdlc/README.md` 的英文源基线。

这类文件保持英文，目的是保留“英文适配源 → 审查后的中文呈现 → `dist`”的前后对照。对应中文资源位于 `src/locales/zh-CN/`。

### Runtime 代码适配片段

- `path-functions.sh`：在上游脚本 materialization 过程中替换/补充项目根、状态目录和插件边界相关逻辑。
- `invocation-functions.sh`：将上游 command 调用映射到 SDLC AI SPEC Skill 调用约定。

这类文件由构建/移植工具合入 `src/scripts/`，最终再生成到 `dist/scripts/`；Runtime 不回读本目录。

## 数据流

```text
src/upstream/                     # 锁定的 Spec Kit 原始源码
       │
       ├──────────────┐
       │              │
       ▼              ▼
src/adapters/      tools/*         # 显式适配输入 + 构建/校验工具
       │              │
       └──────┬───────┘
              ▼
src/scripts/ + src/templates/      # 已适配的 Runtime/英文模板基线
              │
              ├──────────────┐
              │              ▼
              │      src/locales/zh-CN/   # 审查后的中文呈现
              │              │
              └──────┬───────┘
                     ▼
                   dist/            # 最终插件产品
```

其中：

- `src/upstream/**` 必须保持锁定上游原始字节；
- `src/templates/**` 保留英文适配基线，用于独立上游对照；
- 本目录中的 Markdown 保留英文 source baseline；
- `src/locales/zh-CN/**` 保存中文呈现；
- `dist/**` 面向 Agent 和最终使用者。

## 修改规则

1. 修改 `BINDING.md`、`INIT.md`、`STATUS.md` 或 `PROJECT-README.md` 后，必须检查对应中文资源是否因 source hash 变化而过期，并经过现有 review/record 流程后再构建。
2. 修改 `path-functions.sh` 或 `invocation-functions.sh` 后，必须重新 materialize/验证受影响脚本，并执行上游差分、Runtime 和确定性构建回归。
3. 目录内源文件不得依赖业务项目中的临时状态、用户密钥、宿主会话或当前工作树之外的隐式文件。
4. `dist/` 只能由构建器生成；目录迁移、翻译或维护文档调整不得借机改变 Skill 的业务语义、权限边界或执行顺序。
5. 新增适配内容时，优先明确它是“自然语言适配源”还是“Runtime 代码适配片段”；无法归类时先更新本 README 的职责定义再落文件。

## 将来的目录演进参考

当前文件数量较少，优先保持平铺结构。**本轮不执行以下拆分**。

当本地 Skill、适配类型或文件数量明显增加，平铺目录已经影响浏览和职责识别时，可演进为：

```text
src/adapters/
├── README.md
├── workflows/
│   ├── INIT.md
│   └── STATUS.md
├── resources/
│   ├── BINDING.md
│   └── PROJECT-README.md
└── scripts/
    ├── invocation-functions.sh
    └── path-functions.sh
```

建议在以下情况之一出现时再考虑拆分：

1. 本地 Skill 数量明显增加；
2. adapter 类型超过当前 workflow / resource / script 三类；
3. 同类文件数量已经影响代码审查和查找；
4. 引入 GitHub、Preset、Extension 等需要独立维护的适配域。

如果未来继续扩展，可以进一步按领域形成 `github/`、`presets/`、`extensions/` 等子目录，但必须保持“上游原文、显式适配、中文呈现、最终产物”四层职责可追溯，不能为了目录整齐复制或隐藏业务逻辑。

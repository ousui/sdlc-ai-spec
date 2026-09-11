# 公共 Skills 与简体中文呈现

## 当前交付

九个上游核心入口在 `dist/skills/<id>/SKILL.md` 共用。仅本地 INIT 保留三个
宿主专用包装：Claude 的 `disable-model-invocation: true` 不传播到其他宿主。
Core 原有自动/手动调用默认策略一致，公共头部保留等效默认值。每个宿主发现
九个核心和自己的 INIT，共 10 项。不要扫描 `dist/adapters` 整棵树加载三个 INIT。

Claude 自带默认 skills/ 扫描，自定义路径只指向其 INIT；Codex/Cursor 的清单
显式列出两条路径。以官方 native manifest 为准，不另放 portable root manifest。
核心入口从已经加载 Skill 的目录向上两级找插件根；INIT 向上四级。公共入口
要求实际调用环境明确宿主，不根据模型名、配置目录或历史会话猜测。

## 中文范围与等价宪法

Skill 摘要、完整流程正文、入口/绑定说明及 INIT 指引使用简体中文，不是缩写
摘要替代上游正文。每个能力仅维护一份译文，再绑定三宿主调用差异。

模板骨架保留英文：固定标题、文件名、机器占位符、JSON/YAML 键、事件键、
参数、代码块与任务语法不翻译。正常执行原流程时，用中文填写自然语言业务
描述、理由、验收场景与任务内容；不因语言约定新增写入、不重写未授权内容。
`User Story`、`Success Criteria`、`NEEDS CLARIFICATION`、`FR-001`、`T001`、
`[US1]`、`[P]` 等保持原样。刚复制的未填写模板可能是英文，这不触发自动回写。
现有业务文档和用户覆盖模板不会在插件升级时批量中文化。

保留原版逻辑、流程、条件、数量限制与缺陷；不在本项目修复上游 bug。已纠正
本项目引入的事件键改名、无关环境变量整体拒绝、外部合法状态别名整体拒绝。
本地化不扩展支持的核心/Bash/no-events/no-extensions/no-presets profile。

## 来源、编译顺序与检查

`src/upstream/` 保持锁定原文。已有英文渲染与名称/路径适配先完成，随后只将
明确的宿主命令/宿主值映射成命名占位符，得到三宿主完全一致的待译正文。
中文文件位于 `src/locales/zh-CN/workflows/<source-id>.md`，`catalog.json` 将
实际待译全文与译文字节分别绑定，并保存自然语言元数据的原文/译文。
绑定说明和 INIT 源码说明有独立来源绑定。最后再做无损 factoring，写入 dist。

```sh
uv run --locked python -B tools/localize.py check
uv run --locked python -B tools/build.py --marketplaces
uv run --locked python -B -m unittest discover -s tests -v
```

编译/安装/运行不调用网络、模型或翻译服务。`check` 验证九项覆盖、来源新鲜度、
已审查译文字节、代码块与内联代码的精确多重集合、命名占位符和标题层级；
单元测试包括过期原文、篡改译文、即使重算摘要仍损坏的参数等失败对照。
源码英文渲染仍保留与独立原版 CLI 产物的完整比较，不能用中文摘要取代。
这些程序检查不证明语义完全等价或模型实际输出；译文还需要逐条对照审查。
当前 catalog 的 reviewer 是 AI 源文对照审查声明，不冒充用户逐条批准。

## 升级与增量补译

1. 在外部干净上游 checkout 选择准确版本，沿用 `tools/upgrade.py prepare`。
2. 未变化的待译内容可复用译文，升级不因仓库 SHA 改变就全量重译。
3. 来源/渲染结果/元数据发生变化时，过期翻译会阻止新包构建。候选记录变为
   `LOCALIZATION_REQUIRED`，现有正式源码与 dist 不变；不回退英文伪装成功。
4. 使用候选自身的 `tools/localize.py export --out <新的外部目录>` 导出当前
   英文待译输入。只在候选的 `src/locales/zh-CN/` 更新受影响的译文和元数据。
5. 完成原文逐条审查后，以显式命令更新来源/译文摘要，不手算或直接改候选摘要：

```sh
# 在候选目录内；该操作记录已完成的审查，不是自动翻译或身份认证
uv run --locked python -B tools/localize.py record \
  --command constitution --reviewer '<实际审查人或 AI 审查标识>' --reviewed
uv run --locked python -B tools/localize.py check
```

若 description/argument-hint 原文也变化，先在 catalog 对应 metadata 中明确更新
source 与 zh_CN；record 不会替新原文自动批准旧译文。绑定/INIT 说明变更可以用
`--resource binding` 或 `--resource init`，同样先完成对照审查。

随后计算候选当前翻译目录摘要（程序维护，不是 Git author 身份证明）：

```sh
uv run --locked python -B -c 'from pathlib import Path; import sys; sys.path.insert(0,"tools"); from upgrade import localization_digest; print(localization_digest(Path.cwd()))'
```

外部 review JSON：

```json
{
  "decision": "refresh-localization",
  "reviewer": "<实际审查标识>",
  "upstream_sha": "<候选准确上游 SHA>",
  "localization_digest": "<上述程序输出>"
}
```

```sh
uv run --locked python -B tools/upgrade.py refresh-localization \
  --record /absolute/external/candidate.upgrade.json \
  --review /absolute/external/translation-review.json
```

refresh 只接受因本地化而受阻的 detached 候选，核对源 HEAD 和所有非翻译文件
保持不变，然后验证中文并重新生成、冻结完整候选。代码/上游/旧 dist 擅自变化
会拒绝恢复，必须重新准备；不能用补译入口夹带其他变更。完成后必须重新跑测试
和 AI review，报告绑定新的完整候选摘要；旧 PASS 不再有效。

同版本重放验证稳定性；来源文本变化的夹具验证“过期→补译→重新冻结”路径。
这不等于当前已切换正式上游版本，也不保证未来任意上游架构变化都无需人工适配。
遇到新命令、英文渲染不再对应或未支持的结构，继续停止并审查。

## 边界

此处没有新增维护者发版平台、权限规则、STATUS 或 RULE 自动初始化。review JSON
不是访问控制；也没有改变远端分支、创建 tag 或发布 Release。现有移植审查中
已确认继承的上游问题保持记录，不通过翻译暗中修正。

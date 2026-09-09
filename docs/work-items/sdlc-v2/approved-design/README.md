# SDLC v2 详细设计包

**先打开 `DESIGN.html`。** 这是单文件离线阅读入口，含章节摘要、可折叠的阶段设计/字段字典、可放大的图表和来源引用。无需另外加载脚本或字体文件。

## 需要优先看的内容

00：为什么自研，为什么也应该直接试用 Spec Kit。  
03—04：默认自动推进、VFY收敛以及每个Skill的工作。  
05／附录A：数据库模型、关系、字段与约束。  
09—10：本地工作区交回，以及v1.1规范如何替换。

## 主要决策

首版Python＋SQLite、本地不入VCS；六阶段允许用户一次授权连续执行；内容快照与运行结果分别保存；数据按需求身份交回而非覆盖数据库；附件使用assets/ab/cd/完整摘要。新领域规范建议标识2.0-draft，当前有效文档统一放docs/spec/。

这是设计，不是已实现系统。自研价值应通过与Spec Kit的等价试用验证，不把流程自动化、日志或跨Agent支持误说成独有能力。

## 文件说明

| 文件 | 内容 |
|---|---|
| DESIGN.html | 全部设计的离线阅读入口 |
| DESIGN-COMPLETE.md | 全部正文与附录的Markdown版本 |
| DESIGN.md | 设计主文档 |
| DATABASE.md | 32张表的完整字段及关联 |
| schema-model.sql | 可执行的SQL结构模型草案 |
| validate_schema_model.py / model-validation.json | 28项已运行的SQL模型检查及结果 |
| ACCEPTANCE.md | 46条新系统待实施验收用例 |
| contracts/ | 一组PLN请求Schema与正反例；非完整API实现 |
| diagrams/ | 6张SVG及对应Graphviz DOT源文件 |
| DOCS-V2-CHANGE-MAP.md | 规范替换清单 |
| HANDOFF.md | 分工作包实施交接 |
| SOURCES.md / SOURCE-BASELINES.json | 来源与准确审查基线 |
| DELIVERY-VALIDATION.json | 交付文件与阅读页面检查范围 |

## 模型检查

在支持SQLite 3.37及以上的Python环境运行：

```bash
python validate_schema_model.py
```

脚本仅创建临时内存数据库并更新本目录的model-validation.json，不访问业务项目、外部数据库或网络。

已验证SQL模型：28/28。尚未验证生产Runtime、真实Agent全链路、产品业务、工作区逻辑合并、Rust或MySQL。

本轮未创建仓库分支、提交、推送，也未删除现有代码或测试。

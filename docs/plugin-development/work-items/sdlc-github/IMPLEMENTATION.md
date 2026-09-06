# sdlc-github 当前实现与返修

批准领域设计仍为 97c5f17bfcdb2751d446a89b068db2400436631d 的 DESIGN/EVAL-PLAN，未改领域语义。
main@7a454c76b62c41525fa3990dffdaa9a52b975679 已先通过合并提交 1f9340923b66ea2bc06b0ab58a145fa4fbb0b6dc 进入本工作分支；main 本身未改。

| Review | 修复与固定 Oracle |
|---|---|
| R1 issue.list | open→OPEN、closed→CLOSED、all→省略；所有能力探针均使用同一个 mapper |
| R2 comment.create | 合法非空探针；空白普通评论拒绝；Issue/PR 更新的显式空正文仍合法 |
| R3 actions.jobs | 仅展开已观察到的一层 jobs 包装，使用其 total_count，校验 Job ID/run_id，拒绝冲突与任意递归提取 |
| R4 repo.tag | 轻量 Git Ref 与附注 Git Tag 分别验证 selector、object 类型和 SHA |
| R5 marker 唯一性 | 完整分页范围先统计所有同标记对象，再校验作者/属性，不能靠过滤隐藏重复 |
| R6 confirmed 保真 | 后续读回/存储失败不抹去已确认效果、URL/receipt；失败观察追加，不改旧 receipt |
| R7 安装入口 | 安装器生成准确解释器 launcher、相对资源定位；缺依赖明确阻断，不用全局安装补洞 |
| R8 扫描证据 | 文件哈希仅证明内容未改；可选反馈区分 host discovery 与 Skill 委派扫描/读取/写入 |

`tests/skill_github/fixtures/hosted-contracts.json` 保存 Client 捕获的公开 Schema、形状及原提交/文件摘要，合成 payload 不含真实业务正文。
`test_review_repairs.py` 与 `test_repair_installation.py` 是新回归入口；旧 fixture 已修为真实枚举、非空约束、嵌套 jobs 和轻量 Tag，不从实现输出反向生成期望。
8 工具/32 操作、固定官方 MCP 地址、SDK 版本和无 REST fallback 边界保持不变。全仓治理由 main 的统一 quick/full/strict/e2e 与七节 Skill 格式检查；新增 Skill 已登记第九项。旧实际证据可按 ARCHIVE 精确恢复。

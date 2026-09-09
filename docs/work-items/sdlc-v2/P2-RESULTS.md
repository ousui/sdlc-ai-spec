# P2：公开内容流程与事务检查点

已实现统一 JSON CLI、机器输入定义、INIT/CTX、多项目、REQ/DSN/PLN、阶段覆盖、
批次 ID 映射、generation CAS、成功/失败幂等回执、独立早期 Run 和 bootstrap 诊断、
原始输入附件及内容/运行离线视图。没有正式 IMP/VFY/RLS 执行能力，未计入项目闭环。

## 验证

- Python3.11：43项测试通过（24项已有领域/存储 + 19项公共入口/事务/诊断）。
- 一项独立进程 CLI 测试实际 INIT/CTX/REQ/DSN/PLN，检查三个不可变快照和三个阶段步骤。
- 覆盖同键重放/冲突、旧generation、非法批次零残留、多项目引用拒绝、真实字段路径、
  只读数据及文件不变、附件不可变、九验收跨设计覆盖、回REQ修订保留草稿、配置/JSON故障。
- `tools/build_v2_contract.py --check` 通过，契约由生产端描述符生成。
- 原始日志：实验室忽略归档 `.local-runs/sdlc-v2/P2-pass.log`。
- 独立只读评审发现的问题已变成回归，包括记录写入失败、嵌套配置、幂等ID脱敏、DB/HTML错误文本脱敏。

## 必要模型细化

1. 严格遵守D-08：`changes.active_revision_id`只采用committed；prepare另选唯一draft。
2. `revisions.state`增加`abandoned`。从未完成DSN/PLN返回上游时，先CAS保存当前草稿为
   不可改的放弃记录，再创建子草稿；不会将未完成内容误标committed，也不丢输入或附件。
   active保持原已提交版本。32表数量不变。
3. 开发期尚无已发布v2数据库；Schema摘要不符时明确拒绝并保留旧库。本包测试均新建隔离库，
   不建设v1兼容或静默迁移。最终H_final后按正式版本策略维护。

## 下一包

P3实现实际产品操作、短事务工具执行、工作区执行令牌、准确代码/环境对象、结果来源、
finding和自动修复复验、严格收敛。P4后才切换正式Skill与安装入口、清理旧链。

# Skill 开发流程

## 正常流程

设计/评测计划 → Maintainer 批准 → 实现与短回归 → 一次最终验证 → 独立审查 → 合入。用户可明确授权同一分支完成相关修复，但不能省略实际授权、测试或独立接受边界。

新 Skill 先登记名称、目标、Runtime Contract、Case Expected 与允许路径；按 [SKILL-STYLE.md](SKILL-STYLE.md) 和模板书写统一入口。现有 Skill 改格式时不修改领域枚举、准确引用、授权或 Gate 语义。

## 测试与记录

日常用 quick；变更集完成用 full；需要真 OS 沙箱/全链时用一次 e2e，见 [TESTING.md](../TESTING.md)。不要将 private+full+phase+attest 叠加为默认长循环。日志写源码树外，源码库只保存长期 Case、Fixture、设计、当前 Handoff 和归档索引。真实失败保存在交付包，不删除或改成 skip。

## 宿主与发布

原生 Client 认证当前由 Maintainer 明确暂停作为 Runtime 门禁；实际手动反馈单独记录，不能填造 Verified。发布版本、分发仓库和生产效果必须另外授权。

## 停止条件

缺准确 Authority、权限、支持能力或必要外部对象时失败关闭；不要猜测。完成后给出实际 SHA、测试与未运行边界，同一分支等待审查，不自动 merge/main/tag/release。

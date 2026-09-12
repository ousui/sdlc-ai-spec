# Specification Quality Checklist: [FEATURE NAME]（规格质量清单）

**Purpose**: 进入规划之前，验证规格的完整性与质量
**Created**: [DATE]
**Feature**: [指向 spec.md 的链接]

## Content Quality（内容质量）

- [ ] 不包含实现细节（语言、框架、API）
- [ ] 聚焦用户价值和业务需求
- [ ] 面向非技术利益相关方编写
- [ ] 所有必需章节已填写

## Requirement Completeness（需求完整性）

- [ ] 不再残留 [NEEDS CLARIFICATION] 标记
- [ ] 需求可测试且无歧义
- [ ] 成功标准可衡量
- [ ] 成功标准与技术无关，不包含实现细节
- [ ] 所有验收场景均已定义
- [ ] 已识别边界情况
- [ ] 范围边界清晰
- [ ] 已识别依赖和假设

## Feature Readiness（功能准备情况）

- [ ] 所有功能需求都有明确验收标准
- [ ] 用户场景覆盖主要流程
- [ ] 功能满足 Success Criteria 中定义的可衡量结果
- [ ] 规格没有混入实现细节

## Notes（说明）

- 标记为未完成的条目必须在 `{{SDLC:CLARIFY}}` 或 `{{SDLC:PLAN}}` 前通过更新规格解决

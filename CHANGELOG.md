# Changelog

当前产品版本：`1.0.0-beta`。调试和发布定位以准确 Git SHA 与 `dist/BUILD.json` 为准。

## 重构前

- 建立 SDLC 研发规范、阶段 Skill、Runtime 与 Artifact Store，并形成跨 Agent 插件骨架。
- 逐步补齐需求、设计、实施、验证和发布等阶段能力，完成早期可运行版本。

## 重构后

- 以锁定的 Spec Kit v1.0.5 为核心移植基线，保留上游源码、行为边界和可追溯对照。
- 统一为单一 `dist` 分发，提供 11 个公共 Skill，并支持 Codex、Claude Code 和 Cursor。
- 提供简体中文流程与模板、项目 INIT、只读 STATUS 和宪法生成来源记录。
- 完善源码/适配层结构、可重复构建、Ubuntu/macOS 验证，以及路径和升级边界加固。

# P4-E 正式Skill、安装包与旧链清理

## 结果

- 九个入口为INIT、CTX、REQ、DSN、PLN、IMP、VFY、RLS及status；共享合同、领域Schema与CLI随整个Plugin打包，无开发文档依赖。
- CLI支持长短参数、帮助和版本；只读入口不创建Store。安装包包含52个文件、文件摘要和源HEAD/dirty事实，可重复构建并拒绝覆盖不同包。
- 移除v1运行包、MCP配置、阶段测试、规范及旧构建链；保留Git历史、批准设计与v2检查点。当前开发索引和三个平台清单已切换v2。
- 新增5项安装测试与12个语言无关黄金向量（1项参数化测试）；统一115项测试通过，耗时32.306秒。安装测试实际执行公开CLI内容、检查、交付回读和归档。
- 独立Agent仅阅读安装版Skill，先分析再逐阶段执行小型文本规范化案例：41次公开CLI调用，11项真实业务测试，RLS succeeded、独立回读pass、完整归档成功。人工协议修补0、非预期阻塞0、格式/产品修复0。

## 证据

实验室忽略目录`.local-runs/sdlc-v2/`：

- `P4-E-full-first/result.json`与`unittest.log`：115项，exit0；源父提交17fc37d，明确记录本包dirty文件。
- `P4-E-installed-first-tests.log`：安装5项，exit0。
- `P4-E-removed-v1-paths.json`：授权清理98个旧路径根的清单。
- `P4-E-preview-package.json`：独立前向实际使用的预览包及摘要；该包保留不覆盖。
- `skill-forward/INDEX.md`、`REPORT.json`、逐调用原始请求/输出/退出码与交付/归档附件。
- 提交后的正式本地构建记录另存`P4-E-package.json`，绑定清洁源提交；预览证据不冒称运行在后续提交。

## 验证边界

独立前向是当前Codex子Agent显式读安装版Skill并走公开CLI，非原生客户端发现认证，非Q0三项目证明。收敛审阅明确为self_review。两次外层嵌套Seatbelt拒绝保留原始失败，经已授权宿主升级启动同一公开CLI后通过，Runtime本身的沙箱仍启用。

仓库无依赖Skill格式检查九个入口通过。通用skill-creator的quick_validate因本机无PyYAML未执行成功；没有为此安装依赖。CI配置已切换本地同款v2检查，但没有运行远端Actions；Rust实际运行、其他客户端认证未声称通过。

`/tmp`用于可丢弃测试、Skill生成脚本、提交正文及安装前向案例；前向产品副本暂留作证据，不修改用户现有产品。下一工作包只有Q0。

# SDLC v2工程规则

规范来源为docs/spec；Runtime来源为packages/sdlc；语言无关投影为contracts/v2.json。
构建工具可以读源码和开发文档，安装后执行只能依赖随包文件。

Skill负责当前Agent分析、组装请求和实际产品实现；Runtime负责结构化校验、ID、事务、证据和效果。
版本快照不从Markdown解析；不保留旧ArtifactStore/Claim/Source Lock兼容运行链。
标准库优先。变更增加必要行为回归，保持真实失败和准确源码/安装摘要。
统一验证见../TESTING.md；构建用tools/build_plugin.py。输出到仓库外或明确忽略目录，不修改宿主设置。
阶段/远端授权按当前用户任务，原生认证按真实证据登记；没有能力时不伪造证书。

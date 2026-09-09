# SDLC AI Spec v2

Python标准库＋本地SQLite的结构化软件交付Runtime与九个Skill入口。
当前为2.0开发分支：九个正式Skill与安装包已有115项回归检查点；独立前向小案例已完成，三项目真实链继续验证，尚未发布。
准确进度见[PROGRESS](docs/work-items/sdlc-v2/PROGRESS.md)。

流程为INIT/CTX→REQ→DSN→PLN→IMP→VFY→RLS。用户授权完整本地任务后，当前Agent依次读取Skill，
保存原始需求和结构化关系，实际形成代码与测试，验证并修复缺口，最后交付本地包与离线归档。
Runtime管理身份、快照、事务、依赖、证据、权限及恢复；Markdown/HTML由数据投影。

- [本地使用](USAGE.md)：完整包、产品root和公开CLI。
- [当前规范](docs/spec/README.md)：结构化模型与执行语义。
- [验证方式](docs/TESTING.md)：测试、安装独立性与证据边界。
- [安装版Skill](skills)：INIT、CTX、六阶段与status，共用一套Runtime。

```text
python3 -B tools/validate.py --profile full --evidence-dir /tmp/sdlc-v2-evidence
python3 -B tools/build_plugin.py --output /tmp/sdlc-v2-plugin
```

.sdlc默认不入VCS。当前实际工具执行收集器支持macOS；原生客户端认证、其他执行宿主、
Git/deploy adapter、Rust运行对照、MySQL和Spec Kit实测按实际能力单列。
旧v1规范/实现/测试已由本次批准的重构移除，其历史保留在Git；没有旧库迁移或静默兼容。

# sdlc-200-dsn Bundled Runtime Contract

本目录是安装后 DSN Skill 的自包含运行合同。`200-dsn-spec.md` 与 `200-dsn-domains/*.md` 保留设计期规范的准确字节，并由 `source-lock.json` 绑定；生产 Runtime 不读取开发仓库的 `docs/**` 路径。

- 父合同：`200-dsn-spec.md`
- 固定 Domain：`200-dsn-domains/*.md`，共 16 份
- 用户接口：`interface.json`
- 构建来源锁：`source-lock.json`

这些文件随 Plugin 分发，不提供独立 Artifact Authority，也不构成可单独调用的 Skill。
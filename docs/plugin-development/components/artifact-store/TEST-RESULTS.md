# ArtifactStore Foundation Test Results

## 执行基线

| Field | Value |
|---|---|
| Date | `2026-08-30` |
| Python | `Python 3.14.7` |
| Source baseline HEAD | `496328e25d8bdd4fa3f0aea7be21dd725c08ebbd` |
| Tested content | 当前 Foundation 工作树；最终交付提交以完成后的本地 `main` HEAD 为准 |
| SQLite Schema Version | `1` |
| Third-party dependencies | `None` |

## 实际命令与结果

```text
python3 -m compileall packages scripts
```

- Result：`PASS`
- Exit code：`0`

```text
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

- Tests run：`34`
- Passed：`34`
- Failed：`0`
- Errors：`0`
- Result：`PASS`

```text
git diff --check
```

- Result：`PASS`
- Exit code：`0`

## 覆盖结论

- 首次/重复 initialize、Schema Version 不匹配、Schema 缺失：`PASS`
- Artifact ID 唯一分配、同秒 `NN`、全部已登记前缀：`PASS`
- Revision 单调、单 open、Control Reservation 隔离、abandon：`PASS`
- 完整 Payload 原子物化、open 原地重写、事务失败 rollback：`PASS`
- primary / Member 摘要、唯一 ID / Name、Media Type、Manifest-Member closure：`PASS`
- frozen 不可写、abandoned 不提供 Authority、exact Reference 无 fallback：`PASS`
- verifier 缺失、拒绝、stale、通过：`PASS`
- 乐观并发代次拒绝 last-write-wins：`PASS`
- 严格只读缺失 Store 不创建、读取前后文件集合/摘要不变、无 journal/WAL/SHM：`PASS`
- 不同 CWD 的 CLI Project Root 定位、单 JSON 输出、稳定 verifier 错误：`PASS`
- root `.gitignore` 不变、Git-tracked `.sdlc` fail closed：`PASS`
- 无第三方 import、无网络/安装调用：`PASS`
- 外部准确 IMP Artifact ID / Revision Reservation 幂等采用与冲突拒绝：`PASS`

## 未测试或未实现

- 未实现、未测试真实 CTX / Phase domain verifier；本轮只用 deterministic fake verifier 验证 protocol 的通过、拒绝和 stale 路径。
- 未执行 `sdlc-project-context` 正式行为 Eval、三端 discovery / invocation / compatibility 测试。
- 未做多进程压力或性能基准；并发正确性当前由 `BEGIN IMMEDIATE`、唯一索引和 generation conflict 自动化案例证明最小边界。
- 未实现 Human Review View、Projection Import、Candidate Material、远程 Store、多 Provider、Migration framework 或 Claim Provider。
- 未执行网络访问或依赖安装；实现与测试均不需要这些能力。

## 临时目录使用

- 自动化案例全部使用 `tempfile.TemporaryDirectory`，退出时清理，不写入真实项目 `.sdlc/`。
- 初步 compile/test 的 Python bytecode cache 定向到 `/tmp/sdlc-artifact-store-pycache`；该目录不属于交付内容。

# Shared Runtime Core Test Results

当前文件登记自动化测试合同。实际提交与结果以对应 GitHub Actions 运行记录为准。

## Required Commands

```bash
python3 -m compileall packages scripts
python3 tools/validate_runtime_contracts.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## Required Coverage

- Invocation / Result Envelope 合法与非法路径；
- Contract Registry 与 Source Lock 集合、排序、版本和摘要；
- Canonical Markdown/YAML、固定表格与摘要算法；
- Frozen Artifact Authority 的 human / delegated、stale、tampered 与缺失文件路径；
- CTX Boundary Key 原子保留、重复幂等和只读发现；
- Artifact Catalog 只读列表；
- 既有 ArtifactStore 全部回归测试。

测试通过只能证明固定 Fixture 和确定性边界；不能替代真实 Phase Runtime Eval 或宿主调用证据。

# Lifecycle Query Test Contract

实际结果以对应 GitHub Actions 运行记录为准。

## Commands

```bash
python3 -m compileall packages tools
python3 tools/validate_runtime_contracts.py
python3 tools/validate_skill_interfaces.py
python3 tools/validate_lifecycle_query.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 tools/test_springgear_lifecycle_query.py --source _integration/springgear
```

## Required evidence

- Store 缺失时不创建 `.sdlc`；
- 准确 REQ Revision 选择；
- 多 REQ Lineage；
- Context Edge；
- Open Item / failed / abandoned；
- 缺失依赖；
- 下一阶段和 Skill Availability；
- SpringGear 正式 CTX/REQ Runtime 纵向链路；
- Query 前后项目文件摘要完全一致；
- springgear 远端仓库零写入。

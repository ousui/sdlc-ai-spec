# SDLC v2验证

```text
<python3.11> -B tools/validate.py --profile full --evidence-dir /tmp/sdlc-v2-evidence
<python3.11> -B tools/validate_skill_style.py
```

quick检查公共机器契约、九个Skill的格式/命令/写入属性和唯一v2源码边界。
full同时运行tests/v2全部测试，包括真实工具收集、交付回读、工作区逻辑移交和独立安装副本CLI。
实际子命令目前要求macOS Seatbelt；不能在不支持的宿主把blocked改成pass或删除这些反例。
日志、退出码、源码HEAD与dirty状态存指定仓库外目录，失败保持原始记录。

contracts/golden-vectors.json固定语言无关的输入/错误样例；Python验证这些向量不等于Rust实现对照。
安装包由tools/build_plugin.py创建，仅包含Runtime、契约、Skill及用户用法，不含docs/tests/开发工具。
安装独立性测试实际走副本CLI到本地交付与归档；它是确定性fixture，不是真实产品Agent场景。

真实Agent前向评测必须实际读取安装入口并按阶段工作。三项目九场景证据单独存实验室，
先需求再实现，不预制候选答案后补记录。最终按同一H_final与安装摘要重跑相应验证。
客户端原生发现/调用、外部集成及发布认证只能根据实际证据登记。

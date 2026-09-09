# SDLC v2 本地使用

本安装包包含Python标准库Runtime、SQLite Schema、机器契约和九个Skill。
使用Python3.11+；当前实际命令收集在macOS验证，未知宿主返回明确blocked，不静默关闭沙箱。

将完整包保存在本机目录，在客户端选用相应插件/Skill入口。当前客户端若不能原生加载，
可明确读取包内SKILL.md并走公开CLI，记录这种方式，不能冒称原生认证。

向当前Agent给出产品目录、完整需求/验收、允许本地编辑与执行测试的范围、交付目录。
例如：“在此产品副本实现下面需求，允许本地代码与测试，连续执行六阶段并交付到
.sdlc/exports/my-change”。当前Agent先读取sdlc-init和sdlc-000-ctx，
然后依次读取sdlc-100-req到sdlc-600-rls；每阶段按其真实回执衔接。
已有有效上下文则复用明确版本；多个需求须选定change_id。

```text
<python> -B <plugin-root>/scripts/sdlc.py --version
<python> -B <plugin-root>/scripts/sdlc.py --contract
<python> -B <plugin-root>/scripts/sdlc.py --root <product-root> --request -
```

业务请求由Agent生成并直接从stdin传入，用户不需要填写UUID或SQL。
.sdlc默认不入Git。用sdlc-status只读检查状态；按明确请求生成HTML视图。
local交付先真实写包与独立回读，再导出完整离线归档。
复制/交回只处理.sdlc事实与证据，不自动合并产品代码，不继承来源执行权限。
本包不安装依赖、不修改宿主配置、不连接MCP、不提交Git或发布。

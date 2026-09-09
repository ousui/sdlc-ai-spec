# Repository Agent Instructions

## 目标与来源

插件唯一权威仓库为goedgecloud/sdlc-ai-spec。ousui个人仓库仅用于开发；历史PR、CI和基线链接仅为开发证据，不作为安装、发布或规范来源。

本仓库实现可独立安装的SDLC v2 Plugin：Python标准库、SQLite结构化事实及十个Skill入口。
当前规范在docs/spec，公开协议在packages/sdlc/protocol.py与domain.py，机器投影为contracts/v2.json。
批准设计和唯一工作进度在docs/work-items/sdlc-v2；历史版本以Git保存，不作为运行时依赖。
安装后的Skill只读取skills/_shared及随包私有资源，通过scripts/sdlc.py调用共享Runtime。
不得读取开发docs/AGENTS/Handoff、直接SQL或重建私有Store。

## 工作区、授权与阶段

使用用户指定的仓库、分支与工作树，每次写入前核对root、branch、HEAD和status。
保留未知staged/unstaged/untracked数据；范围不明确时先辨别归属。
Git作者用当前有效配置；commit/push/远端写入按当前工作包授权，不自动merge/tag/release。
本次v2工作包已明确授权持续本地实现、验证、修复与commit，默认不push，详见V2-WORK-PACKAGE.md。
一般开发工作仍按明确授权的design/implement/evaluate/review/finalize范围执行。
业务Skill允许用户总授权下由当前Agent连续完成六阶段，单阶段授权则在对应完成条件停止。
不得用旧开发阶段隔离规则阻断已授权的业务闭环；不得借auto扩充权限或伪造human身份。

## 运行模型

来源/覆盖、任务前驱、条件时点和资源冲突分别建模。Run先于正式IMP输出建立。
草稿generation并发保护、已提交快照不可变、同键同请求幂等，unknown先回查。
任务完成不等于Check通过；addressed不等于resolved；准备包不等于交付完成。
真实验证来自实际工具/断言，Agent审阅独立标注，结果按当前输入/环境/定义/时效判断适用性。
.sdlc默认不入VCS；附件为assets/ab/cd/完整SHA256。原始日志、补丁和资产必须归档。
工作区复制使用Backup API，逻辑交回不覆盖DB或产品代码，来源权限与执行记录不成为本机能力。

## 共享与工程

packages/sdlc为唯一Runtime，scripts/sdlc.py为唯一业务CLI，tools为构建/验证工具。
skills/_shared没有SKILL.md；业务私有资源不跨读。Skill保持七节结构及与真实CLI一致的命令/参数表。
开发测试位于tests/v2，执行证据存仓库外；不伪造原生客户端认证、产品链或相同版本通过证明。
不自动安装依赖或修改宿主设置，不写入真实凭证。当前macOS命令收集器的限制须明确说明。

## 完成检查

运行适用测试及python3 -B tools/validate_skill_style.py，完成git diff --check和改动范围检查。
更新唯一PROGRESS与相应紧凑证据索引，区分已验证、未验证和真实边界。
完整任务授权持续推进，遇到真正不能自主解决的范围/环境/权限问题才停止。

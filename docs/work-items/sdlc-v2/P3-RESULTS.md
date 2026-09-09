# P3 实际执行与收敛检查点

已完成 IMP/VFY 公共入口、共享任务时点判定、工作区租约、实际产品文件操作与命令收集、
不可变结果、证据适用性、finding 修复复验、持久化预算及明确恢复入口。
验证性质为确定性公共 Runtime 测试及真实本机工具调用；尚不是安装版 Skill 的 Q0/Q1/Q2 产品验收。

## 实现与必要契约修正

- Run 保存阶段、执行令牌、修复/格式/无进展预算；恢复轮换令牌，未知效果阻断同需求进一步修改。
- operations 保存原意图和 Collector 回执摘要。文件写入及外部工具都在 SQLite 写事务外执行；
  回查检查完整性，保留失败，已有回执不重复执行命令。
- Check 新增 input_paths，默认完整 main；任务写权限不能充当检查的输入依赖闭包。
- 结果的定义摘要包含来源/需求/验收、Context及相关任务；快照保存实际输入字节和补丁。
  HEAD变化本身不使结果失效；明确无关文件变化可复用，相关代码/构建/环境/定义/时效变化必须复验。
- check.reuse 创建 reused_from_id 并保持原 observed_at/expires_at，不以复用时间延长有效期。
- finding 新增问题身份参数 issue_key，不同缺口不互相覆盖，重复缺口保留更高 blocking 严重度。
- phase.prepare 返回当前阶段的公开命令及嵌套Schema；运行时代码不读取此文档。

## 已执行证据

实验室忽略目录 `.local-runs/sdlc-v2/`：

- `P3-final-tests.log`：Python3.11.15，70项，exit0，9.842秒。
- `P3-toolchain-probes-fixed.json`：JDK21实际子进程、Go1.23实际编译/子进程、Node24运行均pass/exit0。
- `P3-toolchain-probes.json` 保留原 Go 临时目录拒绝及错误 Node 路径；随后明确修复 Runtime 路径归一和测试工具路径。
- `P3-boundary-tests.log` 保留测试输入使用null而非省略造成的失败；Runtime正确拒绝该输入。
- `P3-closeout-first-failure.log` 保留测试在错误时点执行Check造成的缺证据拒绝，测试按真实时点修正。
- 首轮/评审修补/扩展回归日志保留各自事实，不将早期版本拼作最终同版本证明。

测试覆盖：真实红→finding→修复→绿→适用复验关闭→Runtime收敛；准备完成但环境probe失败的阻断；
双Run租约、旧令牌、未知效果与意图篡改、完整输出/脱敏/截断/超时、需求和依赖失效、空文件、
显式证据复用有效期、格式预算、总修复预算和连续两轮无进展。

## 独立评审与平台边界

独立只读评审复现了：未知效果旁路、Check输入被误缩到写范围、PYTHONPATH漏摘要、
finding身份碰撞/严重度丢失、关闭输出绕过超时、遗留及脱离进程组的子进程、依赖symlink漏观察。
这些反例已据此修补并加入相应回归。

当前真实命令收集器支持 macOS Seatbelt。独立单线程启动器先应用策略后 exec，
禁止 syscall82/147/244，普通fork/exec可用；Java使用FORK backend。
仅让sandbox-exec套用这些规则会阻断其自身posix_spawn启动，因此没有采用该失效方案。
必须使用posix_spawn的其他工具需要明确适配；不对未知宿主静默关闭沙箱。
沙箱不是通用恶意代码虚拟机；当前本机工具能力已有实际预检，其他系统原生执行未认证。

临时产品/故障注入目录随测试回收；完整日志留在实验室忽略目录。
下一工作包仅P4：本地交付/回读、附件与工作区复制交回、安装版Skill/打包及旧链清理。

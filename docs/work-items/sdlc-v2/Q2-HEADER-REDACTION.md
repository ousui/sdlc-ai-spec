# Q2 工具日志 Header 脱敏修补

## 原始失败与责任

fansite Q2 使用 clean q2-entry / `7d7179328712194bf362b752a585e7f044ba8260` 执行真实工具后硬中断。
合成 `Authorization: Bearer …` 的已落盘 stdout 仅遮住 scheme，后面的合成凭据仍保留。
没有使用真实凭据。原 operation `9e086f00-0d8a-47ba-bdd4-3b6fc93894d9`、CLI/工具组终止及日志证据在实验室
`.local-runs/sdlc-v2/q2-fansite/interruption/`，原证据不覆盖。

责任是 `common.redact` 的通用单值赋值正则，不能把带空格或多个值的 Header 当作单个词。
新增完整 Header 值处理，先于通用赋值处理执行；覆盖 Authorization、Proxy-Authorization、Cookie、Set-Cookie及缩进续行。
正常完成和持续日志落盘共用该函数，无 Schema、Authority、任务依赖或收集器安全边界调整。

## 实际验证

- 新增4项单元测试在修前产生6个失败子例；修后4项通过。
- 完整安装副本验证：153项通过，原始结果在 `.local-runs/sdlc-v2/q2-redaction-full-001/`。
- 现有真实工具完成测试补入 Bearer/Cookie 日志及 process metadata 检查；硬 SIGKILL 测试补入已刷出的 Bearer Header。
- 独立窄审阅：21次测试执行通过（含额外导入收集项和重复项），36个保留日志/元数据文件中已知合成凭据原值0命中。
  证据 `.local-runs/sdlc-v2/reviews/q2-redaction-independent/`；精确实现文件SHA及脏树边界在该目录报告。
- 新 clean 包的 fansite 公开CLI中断复验随后登记；不把旧包失败或当前源码测试改称新安装包业务通过。

## 明确边界

Header样式文本同行余下内容和缩进续行保守遮蔽，因此日志字符串中的同行JSON公共字段可能一并消失。
下一独立公共行、非Header说明文字、结构化对象的非秘密字段保留。
输出上限仍限制原始捕获字节；脱敏占位符可能增大保存后的文本长度，仍为固定有界输出。
本修补处理已识别的凭据格式，不宣称能识别任意未标记秘密。

唯一下一工作包仍为Q2三项目收口，再进入同版本FINAL九场景。

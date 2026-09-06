# sdlc-github 跨平台收口结果

**本次修复和跨平台验证 PASS；被测源码 `f4cb770a758137c5e9c6f5d087821d08b878639d`。本轮不再生成 Client 修复提示词。**

## 范围与实际变更

从 `d271a27c98e178c9eba95ca44ac3ab96a0d477fe` 正常快进：`dd004c7ebc841a966616bdfc5f0f948e502aa142` 修复 Fixture、报告和 CI；`f4cb770a758137c5e9c6f5d087821d08b878639d` 补充修复 macOS full 新暴露的 CTX 初始化恢复计时。未修改 main、其他分支或其他工作包交接。

1. 三处测试自建临时根使用 `resolve(strict=True)`；新增三项 alias-parent 回归。生产 O_NOFOLLOW、链接/硬链接/FIFO 负例不变。
2. 两份 CLIENT-REVALIDATION 报告只移出固定连接地址并追加说明。历史 PASS/FAIL/BLOCKED、UUID、计数和外部归档摘要不变；原文可从输入 SHA 恢复。检查器没有整体豁免 docs，也没有删除规则。
3. CI 增加真实 macos-15，与 Ubuntu 各执行一次统一 full，并记录实际 Python/平台/临时路径。READY 仍只表示依赖包版本匹配，不把 Python 3.14.7 自动认证为受支持版本。
4. 第一次 macOS full 已解决全部 GitHub 测试，但暴露一项原有 CTX 并发初始化失败。可控时钟证明慢的首次尝试可消耗原恢复窗口，导致首次冲突后零重试；仅将同样一秒的恢复计时移到第一次可恢复失败。仍须成功 initialize 和只读 Schema 验证，持续错误仍失败，非恢复错误不重试，ArtifactStore 与原并发断言完全不变。新增四项确定性测试。

GitHub 生产 Runtime 仍与 `9491c0ef7d9d017d666cca71917e1c3679346824` 字节一致，因此此前真实 status/list/jobs/comment 成功记录不作废；整个仓库因 CTX 初始化补丁而有新运行时源码 SHA，不把它说成纯测试修改。

## 最终真实执行

| 环境 | full | GitHub 子集 | 静态检查 | 原 CTX 并发测试 |
|---|---|---|---|---|
| Web 容器 / Linux / Python 3.13.5 | 1213/1213 PASS | 234/234 PASS | 7/7 PASS | PASS |
| GitHub Actions / Ubuntu / Python 3.13.15 | 1213/1213 PASS | 234/234 PASS | 7/7 PASS | PASS |
| GitHub Actions / macOS 15 / Python 3.13.15 | 1213/1213 PASS | 234/234 PASS | 7/7 PASS | PASS |

每个环境对最终修复 SHA 执行一次 full。数量为包含关系；GitHub 的六项真实 stdio→loopback HTTP 测试已计入 234。新增总数为三项 Fixture 加四项恢复计时，从 1206 增至 1213，无删除/skip/expectedFailure。失败、错误、跳过、预期失败及意外成功均为零，执行前后 source SHA/tree/状态一致。

IMP 82、RLS 87、Status 14 注册用例通过；VFY 80 只证明 portable contract，不声明 strict OS sandbox/e2e。macOS 的真实临时根含 `/var` 到 `/private/var` 别名，记录位于 ENVIRONMENT.json；不是拿 Linux 的路径模拟冒充 macOS。

## 失败历史未覆盖

第一轮 `dd004c7ebc841a966616bdfc5f0f948e502aa142`：Web 与 Ubuntu 为 1209/1209；macOS 为 1208/1209，唯一失败是 CTX 跨进程首次创建（attempt=0，CONFLICT）。该次真实失败归档保留；没有对旧提交反复重跑直到变绿。随后对已修改的 `f4cb770a758137c5e9c6f5d087821d08b878639d` 执行新平台批次。

可控时钟反例把首次初始化设为两秒：旧函数在第一次冲突后立即失败且未验证；修复后进行第二次初始化并调用只读校验。它证明一个确定性计时缺陷；原 macOS Job 未记录调度时延，不能声称已测得其精确耗时。新真实 macOS full 保留十轮原并发测试并全部通过。

首次 Web 本地提交镜像尚未匹配时，exact-SHA 前置检查阻断过一次，零步骤/零测试；原拒绝记录同样保留。测试源固定后才开始实际 full。

## 证据与交接

- 最终 CI Run：`34042528875`；首次 CI Run：`34040929719`。
- 仓库外证据包：`sdlc-github-portability-f4cb770.zip`；SHA256：`36de7965630357677502fb204bbe043265f9ce8eb92e83298072c4be0707b751`。
- 包含两版的 Web/Ubuntu/macOS 原始 full.json、suite.json、标准输出、source/环境/coverage、3+4 新测试 ID、范围证明、失败反例及其运行日志。长日志不进入当前源码。
- 本目录 JSON 为紧凑汇总；文档交付 commit 在被测源码之后，仅修改本工作包报告/Handoff。

该修复不需要 Client 再修代码或重复完整验证。唯一下一项为独立审查/维护者收口，PR #14 保持 Draft；不自动 merge/tag/release。之前 Tag Fixture 与模型网关 522 未在本轮解决，仍如实保留；原生独立认证不恢复为门禁。

真实 unknown `56de6913-edfc-4beb-bc98-a0f0265b7be5` 的活动 intent、receipt 和原数据根未被本轮读取、修改或重放；它仍不代表无效果。不需要再创建一次成功评论或重跑旧全写入批次。

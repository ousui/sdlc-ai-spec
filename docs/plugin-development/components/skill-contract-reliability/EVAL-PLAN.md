# Skill 输入契约可靠性评测与复现计划

日期：2026-09-08。按本次 Maintainer 要求收窄；本文定义 Expected，不代表已执行。修复范围见 DESIGN.md。

## 1. 测试基线与方法

历史问题 HEAD=`93cef2f6cc07e5e7b6a1f4dd8670d448bf460ba8`；修复来源=`14c167e044d7a8eeada3c826d1c41bb55bc7b01b`（父提交 aed8eb6）。固定请求、Fixture、mock、真实 CLI 子进程和 Store 前后快照用于可重复的程序回归。至少核心已知缺陷在历史或来源基线上得到失败证据，然后在修复源码重放相同 Expected。

所有使用都是正式使用，不设置“首次调用实验”、独立模型实验或强制项目矩阵。模拟输入和 mock 仅用于测试，不冒称用户 approval-bot 实际工作树已运行、真实人工批准或生产部署。

本轮为原版本 bugfix，不新增 Schema 变更验证或迁移评测。沿用原版本的请求、命令和已有 Artifact 进行正常使用回归；不添加版本协商、升级开关或用户迁移步骤。

## 2. 定向案例

| ID | 案例 | Expected |
|---|---|---|
| INPUT-01 | CTX 合法完整输入但缺最终确认；缺真实事实配对 | 格式无错误，pending/真实 Open Items，不自动 ready 或 frozen |
| INPUT-02 | source_worktree、中文自由枚举、环境双字段非法 | 返回具体字段/允许值；独立错误不互相遮挡；未执行 Check 不全记 fail |
| INPUT-03 | 工程用途明确别名、大小写/空白、常见拼写配对 | 受支持无歧义归一化有 warning；标准枚举不变；未知歧义拒绝；不修改命令、授权或事实 |
| INPUT-04 | 组件依赖说明文字、未知 ID、合法集合和 None | 非法/不闭合引用准确定位；合法同 CTX 引用正常；不猜 ID |
| INPUT-05 | Evidence“不适用”、坏摘要、Supporting Member 摘要不符；真实内容配对 | 拒绝错误，合法实际字节摘要接受；会话来源与授权不由摘要替代 |
| INPUT-06 | 观察时间/可变名称作 Baseline；旧 VCS、完整 Git、内容摘要配对 | 时间不能替代不可变身份；支持旧合法表示；不凭格式宣称对象真实或 dirty 已验证 |
| INPUT-07 | 相同非法输入 create、create dry-run、revise dry-run/正式 revise | 错误类别/路径一致，拒绝无新分配/写入；既有 frozen/open 字节不变 |
| INPUT-08 | Final Confirmation 明确 rejected | 只标真实拒绝对应 Check，不把全部未执行项标 fail，不生成 Authority |
| INPUT-09 | REQ 来源/需求枚举与必要嵌套输入、旧合法请求 | 随包说明与 Runtime 一致；缺口与非法区分；不因格式兼容生成授权 |
| INPUT-10 | DSN/PLN meta＋非法 JSON/未结束 stdin/错误命令参数 | 元命令不读业务 stdin、不查项目或 Store；命令自身错误仍拒绝 |
| INPUT-11 | DSN/PLN/IMP/VFY 必要输入映射及 RLS/Status/GitHub 合约核对 | 真实字段与随包入口可发现；已有正式用例/mock 不回退；不新增无关功能 |
| INPUT-12 | 文档/枚举投影漂移；安装包删除 docs/tests 后使用 | 漂移由测试检出；正式入口及随包示例无需开发文档或测试代码 |
| INPUT-13 | malformed JSON 类型、选项及确认；未授权请求 | 有界结构化错误，不崩溃；无类型转换授权、无 Store/Claim/远端效果 |
| INPUT-14 | prepare_confirmation、Supporting Member、只读/CAS/历史 frozen | 保留已有有效回归，不因去重或新输入整理而绕过；原版本合法请求及已有记录可直接继续使用 |

REQ 的 INPUT-09/13 必须经过正式 runtime_final 入口及无 docs/tests 的安装副本；create/revise、dry-run/非 dry-run 四路径在 Store 快照和 cleanup 前拒绝非法结构。基础 Handler 单测不能替代正式入口，保留上一轮 strict 暴露的反例。

大 Case 展开为具名测试；保留原测试身份，新增子用例有明确断言。允许重构纯重复断言，但默认不删除既有有效测试。修改旧 Expected 必须说明原断言为何混淆输入错误与领域检查，且保留错误拒绝和零效果断言。

## 3. 输入宽容的测试边界

用户自然语言整理由共享 Skill SOP 约束，不要求用户填写内部字段。程序仅测试确定性、字段限定的归一化；不把 mock 理解能力包装成对所有自然语言的保证。明确别名可被标准化；无唯一解释的资源类型、依赖、访问能力、范围、引用和授权不自动修正。

## 4. 项目和副作用

测试副本及输出放在检出树外，使用专属目录，不 reset/清理用户 worktree。模拟 approval-bot 中的错误组合与单字段变体；项目名称不是分支判断条件。需要工程载体时，从 test-sdlc 固定提交复用，不修改其远端业务结果，不强制重跑三个产品完整链。

每个非法/只读路径核对 Store、源文件和测试 Target 前后状态；需要的 mock 显式禁止写入入口。meta 使用保持 stdin 打开的子进程验证不等待业务输入。真实结果、原始失败和后续修正日志分别保留。

## 5. 验证顺序

开发期间运行受影响测试及配对正例。变更稳定后以干净准确源码执行一次 tools/validate.py 的最高可用且本任务所需 profile（优先 strict，环境不足则 full 并明确边界）；不先叠加执行 full＋strict＋e2e。现有统一回归保留其他阶段的安全检查，但无关缺陷不扩大本次修复范围。

记录 Implementation SHA、Test SHA、源码 tree、Runtime 路径/摘要、解释器、命令、退出码、准确测试 ID、结果及未执行项。工作流触发 SHA 与被测 SHA 不相等时分别登记。发布/运输成功不代表测试通过。

## 6. 完成条件

已知输入反例和配对正例符合 Expected；同类随包输入缺口得到修正并有漂移保护；错误不虚构项目失败；dry-run/拒绝无副作用；安全与旧合法输入回归保持。保存准确源码及原始日志并更新 Handoff 和 PR。环境阻塞、无关既有失败和未执行项不得写入 PASS；不再将模型实验或 approval-bot 本地工作树不可访问列为本次必须补齐的验收项目。

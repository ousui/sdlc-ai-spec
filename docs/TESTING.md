# 测试与全流程验证

## 选择一个入口，不堆叠重复套件

| Profile | 用途 | 实际执行 |
|---|---|---|
| quick | 每次小修改后的结构检查 | 八 Skill 接口/格式/锁、完整 test collection、IMP/VFY/RLS/Status 注册表可解析性；**不宣称行为 PASS** |
| full | 合入前普通回归 | quick + 所有有效测试一次；按真实成功 ID 验证 Case 覆盖；VFY 缺 OS 沙箱时仅证明拒绝行为 |
| strict | 可用 OS 沙箱的正式回归 | 同一全仓测试集合一次；VFY 主案例启用真实执行并验证命令 Evidence，不另跑一遍 80 Case |
| e2e | 本次整理完成后的最终验收 | strict + 安装独立性与两个固定本地项目的 CTX→REQ→DSN→PLN→IMP→VFY→RLS；仅 Sandbox Target |

源码必须是干净 exact SHA，输出目录必须在检出树之外：

```bash
SHA=$(git rev-parse HEAD)
python3 -B tools/validate.py --profile quick --source-sha "$SHA" --json-out /tmp/sdlc-quick.json
# 日常需要时选择 full，不必同时再跑各个 private/fixed 子集：
python3 -B tools/validate.py --profile full --source-sha "$SHA" --json-out /tmp/sdlc-full.json
# 最终在具备现成 OS 沙箱的宿主上选择 e2e，不再先重复 full/strict：
python3 -B tools/validate.py --profile e2e --source-sha "$SHA" \
  --project-cache /absolute/path/to/local-project-cache \
  --json-out /tmp/sdlc-e2e.json
```

项目缓存包含 `springgear/` 和 `gin-vue-admin/` 两个现有 Git 仓库，分别能解析固定 SHA `e855096ff19dcdb303dc4250ba19c30acd743ac7`、`a6882210a80bb27e3aa5dff0b4c21aa4afe8988a`。入口先验证可用性；不自动联网下载或安装依赖。测试只在一次性 clone 中工作，核对源/refs/权限/清理，不改用户项目，不生产发布。

## 保留的质量底线

授权、只读、准确引用、Secret 脱敏、Evidence 篡改、CAS/Claim、崩溃恢复、Scope 漂移等回归均保留。IMP 82、VFY 80、RLS 87、Status 14 的正式 Case ID 与 Expected 不缩水。完整测试收集拒绝重复 ID、缺引用和未执行结果；skip/expectedFailure/unexpectedSuccess 不计入 PASS。

VFY 的独立正式 runner 与 coverage 工具仍可用于专项诊断，默认执行必须有 OS 沙箱。结构检查使用明确的 STRUCTURE_ONLY，不能当作 80/80 PASS。普通 full 与 strict 的差别是执行能力和 Evidence，不是删掉失败案例。

## 已退役的冗余

VFY 八个分类包装器重复调用同一批 80 个 harness，保留一个完整主表；旧 RLS provisional 87 Case/仿真 CLI 被真实 Store 87 Case 和现有边界测试替代。REQ helper 从 TestCase 分离，避免继承和别名导入重复收集。原生认证台账测试按本轮授权退役，长期库存/样式检查保留。

旧 `run_rls_delivery_validation.py` / `run_vfy_delivery_validation.py` 是固定历史 Subject 的过程脚本，现明确报错并指向新入口，不伪装成功。`run_post_integration_validation.py` 是兼容薄入口，不递归重复验证。

## 日志管理

一次最终 e2e 只保存一份实际命令/时间/退出码/脱敏日志/准确 source 状态及外部项目 Evidence。失败尝试保留在该运行目录中，不改写原始结果；成功后打包放到仓库外的交付系统或提供给审查会话。源码库仅保留当前测试定义、必要 Fixture、紧凑 Handoff 与归档索引，不再每次提交几百份历史日志。没有记录的手动 Client 反馈不伪造自动认证，也不阻塞本轮 Runtime 验收。

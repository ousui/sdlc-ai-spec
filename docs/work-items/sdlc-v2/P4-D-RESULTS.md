# P4-D 本地交付与工作区移交检查点

完成固定本地目标的交付准备、实际写出、独立命令回读、RLS关闭，以及逻辑归档、
SQLite Backup复制、按需求交回、分歧保留与显式合并。本文件不宣布整个P4完成；
正式Skill、安装独立性及旧链清理属于唯一后续P4-E。Q0/Q1/Q2真实产品链尚未开始。

## 行为与必要契约修正

- 固定目标为 `.sdlc/exports/<name>`，包为 `<sha256>.zip`；修复后可在相同目标留下新包，旧包原样保留。
  包含实际代码、结构化内容、验证依据、附件和用法；来源摘要、环境与必要VFY结果须仍适用。
- RLS计划一个required、command、release_readback Check，argv为 `[@runtime, delivery.readback]`。
  专用worker独立读取同一份有界字节，校验ZIP条目和完整文件摘要；一般check.run不能伪装该adapter。
  关闭还要检查当前产品/环境、结果时效、目标字节、RLS任务及VFY收敛。
- 同目录临时文件fsync后以不覆盖已有文件的link安装；同操作重试回历史回执。
  unknown先回查；已有成功回读可以重新回读而不重新发布；丢失目标不由重复回读补发。
- workspace.export保留选定单project/change的全部Revision/CTX关系、运行与结果、附件、
  原始请求/回执/输出/意图及未执行写入的资产，附离线HTML链接。
  文件与关系闭包、版本、UUID、资产摘要/大小、嵌套JSON和路径均验证；恶意压缩流返回结构化错误。
- workspace.clone使用SQLite Backup API，保留业务身份、历史与资产，重新分配store/workspace/instance。
  外部资源默认unbound。旧Run/授权保留为来源历史，不变成本机执行权限。
- workspace.collect不覆盖数据库：相同内容幂等；新需求新增；祖先关系决定快进或补历史；
  分歧保留双head、目标active不变。目标草稿在事务内完整保留，不妨碍来源不可变历史入库。
  change.resolve创建parent=目标、merged_from=来源的新草稿，再走正常阶段校验。
- 相同主键内容不同会冲突并保留原归档，不自动更换业务UUID。独立同字节附件按摘要复用目标资产，
  asset_id_aliases显式记录映射，关系/快照/意图引用随之转换，原包和历史回执保留。
- authorizations增加workspace范围；runs/authorizations/operations增加local/imported来源。
  collect强制新导入行是imported，不信包内声明。本机授权、Run恢复、租约、unknown与回执重放
  只使用本机来源；导入的未来时间、阶段或预算不覆盖本机续接状态。
- workspace.bind/rebind使用持久化前后config摘要和operations.config_applied_at。
  已应用旧回执不会撤回新绑定，未应用的已提交操作可恢复；本机未知效果或活动租约阻止改绑和交回。
  手工复制/移动检测root_path漂移，显式rebind换身份并隔离来源授权。
- CTX摘要统一根据实际关系行计算，导入可验证Context完整性；表数仍为32。

## 已执行证据

实验室忽略目录 `.local-runs/sdlc-v2/`：

- `P4-integrated-first-tests.log`：Python3.11.15，109项，exit0，27.168秒；其中16项交付、23项移交。
- `P4-delivery-content-addressed-tests.log`：13项交付回归通过。
- `P4-transfer-first-tests.log`：9项初始移交回归通过。
- `P4-transfer-expanded-tests.log`保存配置重放持有读事务造成锁冲突的原始失败，修补后
  `P4-transfer-provenance-tests.log`的15项通过。
- `P4-transfer-boundary-tests.log`与`P4-transfer-closure-tests.log`保留重打包未排序、附件传绝对路径的
  测试输入错误；修正测试后均纳入109项最终同版本回归。
- 独立只读评审实际复现并回验：过期/变更包关闭、并发目标覆盖、回读字节切换、
  旧配置回滚、unknown写入改投、目标草稿丢失来源head、导入授权/Run激活、畸形JSON、
  压缩流异常、待写资产遗漏及跨project JSON引用。对应最小反例已进入回归。

上述为确定性Runtime回归与实际本机命令收集，不是九场景Agent执行证据。
实际macOS子命令依旧受P3 Seatbelt收集器约束；其他宿主、Git/deploy adapter尚未认证/实现。
Schema开发期仍严格匹配摘要，不覆写旧Store、不提供v1库迁移。

测试临时目录随fixture回收；日志保留在实验室忽略目录。本地commit后继续P4-E。

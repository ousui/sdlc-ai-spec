# 本地工作区与逻辑移交

workspace.discover只检查Git登记worktree，不扫描Home。workspace.clone以当前root为来源，
payload.target为已存在的独立产品目录，使用SQLite Backup API复制.sdlc；不复制或合并产品源码。
新store/workspace/instance保留原项目、需求和历史身份。外部资源明确重新绑定，
新Run必须取得当前用户针对本机的authorization.grant。

手工复制或移动通过root_path检测；workspace.inspect可以诊断，写入前需要workspace.rebind。
workspace.bind只绑定明确存在的资源目录，main为`.`。配置操作包含前后摘要和应用标记，
重放旧回执不重写新配置；本机活动执行或未知副作用期间不得改绑/交回。

workspace.export的payload.change_id选择一个需求，返回ZIP路径、逻辑bundle_digest和文件摘要。
包含单project/change、所有版本及CTX、原始Run/结果/日志、附件/意图引用资产和离线index.html。
归档最多50000行与50000个文件，压缩及展开各512 MiB；单个原始诊断最多8 MiB。
超限明确拒绝，不静默省略原始证据。依赖JAR等已压缩资产不假定还能压缩一半。

workspace.collect的payload.path选择归档。先在隔离临时数据库校验严格Schema、嵌套结构、
引用闭包和摘要，再以目标事务新增关系；不替换DB或产品代码。
同包幂等；同head不动；source后继可快进；source祖先仅补历史；分歧保留双head和目标草稿。
change.resolve显式建立parent=目标head、merged_from=来源head的新草稿后，照常提交/验证。
相同主键不同数据会保留完整原包并报冲突，不用时间戳选择一侧。

导入的新runs/authorizations/operations一律标记imported：属于可阅读历史，不能作为本机权限、
活动租约、unknown恢复或配置回执执行。导入检查结果仍须满足当前内容/代码/环境/时效的适用性。
独立附件的同字节不同ID可按摘要映射，asset_id_aliases记录映射，原始归档保留来源身份。

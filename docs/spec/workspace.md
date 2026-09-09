# 本地工作现场

.sdlc默认通过内部.gitignore全部忽略。config只保存物理绑定与选择，业务关系在Store。
分支不作为需求身份；initial_base_commit保留原始基线，不作为HEAD必须相等的门禁。
同库支持多project，每个project使用匹配workspace。切分支后仍需明确change_id。
复制、交回与准确代码影响判断属于后续P3/P4必做项，尚未由P2证明。

# Web审阅移交与首次远端CI

用户在本地收口后授权推送并处理已有PR。实现PR为[ousui/sdlc-ai-spec#22](https://github.com/ousui/sdlc-ai-spec/pull/22)，base保持main；实验室为[ousui/test-sdlc#20](https://github.com/ousui/test-sdlc/pull/20)，base保持verify/integration-three-project-20260907。两PR已转为待审阅，没有merge/tag/release。

已推送本地收口实现70e35f81d9f7bab0da681f7f446a61ea64eb10a6与实验室dde73bc4525522ed8298396b2f129bb884db64b5。后续CI修正提交在实现分支上追加，不重写历史。

## 实际失败及最小修正

首次[push CI](https://github.com/ousui/sdlc-ai-spec/actions/runs/34339186678)和[PR CI](https://github.com/ousui/sdlc-ai-spec/actions/runs/34339191327)均失败。PR合成merge SHA为8e7ad48d8142d6b57ee3f28d19968e568d979600，实际159项运行、45个失败；机器契约、Skill接口格式与唯一v2边界均通过。原日志及result.json保存在该运行的Actions artifact中。

确切错误：Framework Python启动器尝试posix_spawn到其Resources/Python.app/Contents/MacOS/Python。收集器有意拒绝该调用以阻止进程组/会话逃逸，故普通Python检查也启动失败。本机原验证使用独立Python3.11.15；Actions setup-python提供Framework Python3.11.9，启动方式不同。

只在workflow选择已安装Framework的实际解释器；非Framework使用sys.executable解析后的文件。验证和打包均调用此路径。未允许posix_spawn、未关闭沙箱、未删除或跳过断言、未改Runtime/Skill/产品源码。正确性必须由修正提交的新CI实际证明；旧45失败保留，不替换为原本地159通过。

## 审阅顺序和版本

先看[最终报告](FINAL-RESULTS.md)、[批准设计](approved-design/ACCEPTANCE.md)，再联合实验室v2/FINAL/INDEX.md、ACCEPTANCE-MAP.md和逐场景源码。H_final仍为495177acf777251d378652e2a50e47a1b5c4c41a，原53文件包/159本地检查/九场景证据保持原版本；此次后续workflow更正不改变Runtime或该冻结包。新的Actions执行与构建包按各自source_head标识。

PR说明使用GitHub可访问的固定提交链接。大型本地原始请求、日志、客户端rollout、Store和交付ZIP未推送；Web只能直接读取已提交的代码、摘要和新Actions产物，不能从本机绝对路径获得历史原始证据。CI新产物也不替代九场景原交付包。

FINAL-RESULTS/PROGRESS原收口条目及本地CLOSEOUT中的未push是当时快照；最新推送HEAD、CI结果和可下载产物以PR与Actions回读为准。

# Q0 真实链路暴露的 Runtime 缺口

三项目首次六阶段都使用 clean `8754d65` 安装包。Admin 原13项、fansite 原24项、
SpringGear 原10项及四模块 JDK21/major65 均已真实通过且本地交付回读成功。
这不抹去首次轨迹中的流程问题，也不把后续修补版本改写为首次执行版本。

## 修复与边界

- Admin：Check 归属 VFY 任务时，退回 IMP 却返回 VFY task_id，task.next 没有工作。
  现在沿完整前驱及验收关联选择对应阶段工作，追加修复标记；相关任务必须有新的完成尝试。
  原完成历史不变，无关已完成任务不重做。检查结论仍单独判断，不由任务完成生成 PASS。
- SpringGear：完整归档含约374 MiB合法依赖/历史资产，超过旧256 MiB压缩预算。
  压缩上限调整到512 MiB，展开仍512 MiB；不删除合法依赖或原始失败资产，不省略归档内容。
  文件路径、摘要、文件/行数和解压限制保持。实际大包须在新安装版重试并独立回读。
- 公开Schema纠正：Check input_paths access只允许read；资源绑定是包含main=.的完整替换映射。
  这两项与既有Runtime校验一致，Skill补齐说明。

## 验证

实验室 `.local-runs/sdlc-v2/Q0-repair-closure-full`：122项测试全部通过，30.641秒；
机器契约投影、九Skill接口风格与单一v2 Runtime检查通过。
新增真实红绿回归验证VFY owner退回相关IMP、不能跳过修复、保留无关历史；
归档回归验证限额拒绝后原始证据保留，随后可以完整导出原始二进制。

独立评审在首次119项通过后复现三个遗漏：最近前驱截断了源任务，自动finding丢失
Check验收集合，前置条件producer未参与遍历。现与task fingerprint共用完整上游闭包，
从finding的真实result及其准确revision恢复验收集合。新增三组多任务真实红绿测试已通过；
原101次公开CLI失败轨迹保留于reviews/q0-repair-guidance，不用第一次绿测覆盖反例。
修复后独立CLI复验143次请求（47/47/49）全部通过：三组均实际fail→相关任务重新写入→pass，
原finding通过适用结果关闭、VFY收敛至RLS；原任务step全字段不变，无关任务没有修复标记。
证据reviews/q0-repair-guidance-fixed，执行前后共享源码摘要一致，无新增发现。

初次全套118/119通过，失败为新测试请求缺少正确附件来源/草稿/相对路径；
三个测试编写错误的原日志保留于Q0-repairs-full-first与transfer-second/third。
修正测试后24项transfer和119项全套通过，未通过改Runtime绕过接口校验。

首次产品证据分别在q0-admin、q0-fansite、q0-springgear。后续新包实际Spring完整归档已完成；
V2-005及独立验收发现的补充见CORE-ACCEPTANCE-SUPPLEMENT.md，保留本次122项证据版本。

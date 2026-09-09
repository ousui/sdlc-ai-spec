---
name: sdlc-github
description: 将已提交阶段产物分享到指定议题，保存可查询的发送回执。
disable-model-invocation: true
---

# SDLC-GITHUB · 产物共享

## 适用范围

接受“/sdlc-github 帮我将当前产物发送至 issue”等自然语言。
共享的是指定需求/版本的Markdown快照；不要求将.sdlc加入Git。
本版向已有Issue追加评论；创建Issue可由用户或已授权的宿主GitHub工具单独完成。

## 约定与边界

首次读取[共享执行约定](../_shared/runtime.md)。使用唯一Runtime，不直接SQL。
唯一传输为已安装的GitHub CLI（gh api）；身份来自其当前认证。此支持入口明确允许GitHub网络调用，业务检查沙箱保持原边界。
不安装工具、不索取或输出Token、不切换备用连接器规避失败；无gh时说明准备步骤。
仅当前用户明确授权的Issue与内容可写。不得将数据库、原始日志或附件字节整体上传。
发布与六阶段进度分开，分享失败不使已通过阶段退回；unknown先reconcile，不另换ID重复发送。

## 子命令

| 子命令 | 职责 | 可能写入 |
|---|---|---|
| `github.preview` | 生成准确阶段的脱敏Markdown与发布摘要 | 否 |
| `github.publish` | 向明确Issue发送一次快照并核对实际回读 | 是，须满足本阶段授权 |
| `github.status` | 读取本地发布回执和已使用的Issue目标 | 否 |
| `github.reconcile` | 回查不确定发布并更新回执，不重复发送 | 是，须满足本阶段授权 |

## 参数

下列CLI参数固定；业务payload由Agent依据当前回执填写，用户无需手写UUID。

| 参数 | 短参数 | 语义／默认值 |
|---|---|---|
| `--root` | `-r` | 产品根目录，不能使用插件源码目录 |
| `--request` | `-i` | 默认从stdin接收JSON请求 |
| `--contract` | — | 读取公开payload字段 |
| `--version` | `-V` | 读取版本 |
| `--help` | `-h` | CLI用法 |

```text
<python> -B <plugin-root>/scripts/sdlc.py --root <product-root> --request -
```

## 执行流程

1. 从当前会话明确的产品root与change开始。多个候选时询问用户选择，不按时间猜需求。
2. 确定准确Issue URL。首次未提供URL且无唯一已成功目标时，仅询问一次；后续相同需求可复用唯一目标。仅接受github.com的issues URL。
3. 调用github.preview；默认选择active已提交版本而不是下一阶段空草稿。phase可为REQ/DSN/PLN/IMP/VFY/RLS或ALL。需要历史产物时传准确revision_id。
4. 向用户简述目标Issue、阶段和内容范围。用户已经明确“将当前产物发到此Issue”的本次意图可以作为该范围批准，不再强制逐字段确认；含隐私、目标歧义或超范围内容时先澄清。
5. 调用github.publish，原样携带preview_digest、相同issue_url/revision_id/phase以及confirmed=true。Runtime核对gh身份、目标、正文大小，先存intent，再写远端并GET回读。
6. confirmed才报告成功并给comment_url。同快照重复发布复用回执；unknown或conflict调用github.reconcile回查原publication_id。找不到唯一远端结果时保持unknown，不重新POST。
7. 阶段内容变化后重新preview；每份快照独立追加，不覆盖用户编辑的Issue正文或评论。github.status展示回执，未授权时不继续下一阶段或发布其他需求。

## 输出与完成条件

输出目标Issue、准确阶段/版本、远端comment_url及confirmed/unknown/conflict状态。
preview不是发送；历史回执不是当前身份授权。转移来的发布记录只作历史，不取得本机重试能力。
Markdown使用统一阶段模板并脱敏；大附件仅提供摘要索引，完整历史归档继续保存在本地。

## 资源索引

- [共享执行约定](../_shared/runtime.md)：公共命令、事实与授权边界。
- [本入口命令](references/interface.json)：公开命令及写入属性。

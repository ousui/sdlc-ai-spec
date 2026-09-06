# sdlc-github 合并与修复交接

- 工作分支：impl/sdlc-github-foundation-v1；PR #14 保持 Draft。
- 本轮用户明确授权先合入 main、再在 Web 直接修复；合并提交 1f9340923b66ea2bc06b0ab58a145fa4fbb0b6dc，main 基线 7a454c76b62c41525fa3990dffdaa9a52b975679。
- 修复范围为 R1–R8，准确修复提交为 9491c0ef7d9d017d666cca71917e1c3679346824；统一 full 1206/1206 PASS（Github 231 项含在其中，新增回归 13 项），源码前后不变；原设计文档未更改。
- 唯一下一项是修复后的真实 GitHub 定向复验，不重跑旧全流程，也不要求三端原生认证；主仓规则已暂停该门禁。
- 历史报告/日志/旧 Goal 不重写，按 ARCHIVE 恢复；新日志保存在仓库外，不增加数百份源码内证据。
- 原 unknown 请求 56de6913-edfc-4beb-bc98-a0f0265b7be5 保持原始状态与 request_id，仅可只读核对。不得把“未找到”当作无效果。
- 不改 main/其他工作分支、其他工作包交接，不 merge PR、不 tag/release、不扩大 Token 权限。

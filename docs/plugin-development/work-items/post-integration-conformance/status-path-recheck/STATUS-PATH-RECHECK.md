# Client — Status path repair exact-source recheck

本记录是 producer 在真实 Client 宿主上的 Runtime-only 复核，不是独立 Web
ACCEPTED、native 认证、发布批准或七阶段重启。

## Exact identity

| Identity | Value |
|---|---|
| Repository / branch | `ousui/sdlc-ai-spec` / `fix/post-integration-skill-conformance` |
| Baseline main | `0289a5ee8d702450fb3f3bc73c89f30a11664bdb` |
| Validated source | `295d98260e3def713dc72b12c458aa2baa8372f4` |
| Validated tree | `d90e81a94e5b7b5628eb6849cef15bb3f96deb36` |
| Sole source parent | `1b9326e7447a481453fbbeccd8d104a02f6c67e9` |
| PR state before execution | #11 OPEN / Draft；Head 与 Validated source 一致 |

验证在 detached、独立、干净 worktree 执行。源码在新增回归、两次 strict 尝试和
证据索引前后均保持上述 SHA/tree，`git status` 为空。最终 evidence/Handoff commit
以 Validated source 为唯一父提交；其准确 `DELIVERY_HEAD_SHA` 在提交后的 PR 记录、
远端 readback 和交付归档中记录，避免本文件自引用自己的 commit SHA。

## Actual execution

1. 首次启动新增回归时，系统默认 `/usr/bin/python3` 为 3.9.6，无法导入仓库已接受的
   脱敏 helper；测试进程没有启动。该启动失败按原输出保留，没有伪装为测试失败。
2. 使用宿主已有 `/opt/homebrew/bin/python3` 3.14.7 后，准确命令的 14 个新增方法全部
   实际执行并通过：`14/14`，无 failure/error/skip/expectedFailure。
3. strict attempt 1 的前十个门禁全部通过，包括普通仓库 `1118/1118`，随后 VFY
   `E041/E046` 因 Codex 外层沙箱阻止内部 `sandbox-exec` 激活而失败；结果为
   `78/80`，首份失败日志完整保留。
4. 经执行权限审查后，仅解除外层嵌套沙箱阻断，再次运行同一 strict 入口。VFY
   仍强制使用自身 macOS OS containment，不采用 capability-only 或无沙箱 fallback。
   attempt 2 的 13 个门禁全部通过。

只以最终一次完整 strict 的唯一结果报告计数，不把 attempt、subset 或旧 Profile
相加；未运行 portable，也未启动任何 native session。

| Gate | Actual result |
|---|---|
| Status new regressions | `14/14` PASS |
| Strict entry | `13/13` PASS |
| Status original fixed Eval | `14/14` PASS |
| Status installed copy | 12 commands PASS |
| Status source lock | 51 entries PASS |
| VFY strict fixed Eval | `80/80` PASS，真实 OS containment |
| RLS fixed Eval | `87/87` PASS |
| Ordinary repository suite | `1118/1118` PASS |
| Unique repository IDs | 1118 collected / 1118 unique |
| Forbidden unittest outcomes | 0 failure/error/skip/expectedFailure/unexpectedSuccess |

## Status path controls

`tests/skill_status/test_store_absence.py` 的 14 个方法与实际运行 ID 完全匹配。
真实 `.sdlc` 普通文件、数据库目录、两个 dangling link、live wrong-type link 及真实
缺失对照都在调用前后比较完整文件树 snapshot；snapshot 包含 regular-file bytes、
symlink target 和 `lstat` mode。所有映射方法均实际通过。

真实 CLI 与 installed-copy 用例验证 path conflict 只输出一个可解析 JSON document、
stderr 为空、exit code 为 2、错误为 `LIFECYCLE_STORE_PATH_INVALID`。用例也验证没有
初始化 Store、没有 sibling Skill/development assets 调用，准确引用和 meta 命令的
原有先后顺序不变。映射见 `audit/STATUS-CONTROL-MAPPING.json`。

## Evidence and historical bindings

- 新执行共有 27 份完整 process receipt、54 个脱敏 stdout/stderr 流绑定；另保留一份
  helper 导入前的 launcher failure。`validation-redaction/v2` 在每个进程流首次持久化
  前处理完整 argv、cwd、stdout/stderr 和环境 Secret。
- `audit/UNIQUE-TEST-AUDIT.json` 使用与正式 runner 相同的 discover 参数收集 1118 个
  ID，确认无重复，并确认 14 个新 ID 与独立新增回归 receipt 完全一致。
- 旧 `CLIENT-SHA256-MANIFEST.json` 没有改动；已在原交付 commit `1b9326e...` 的 Git
  tree 内逐一验证 340 个文件，零 mismatch。旧 75 份 process receipt、150 个流绑定
  和八个 native candidate 原样保留，未用后续 HANDOFF 字节反验旧摘要。
- `COMPATIBILITY.json` 原字节不变；`NATIVE_ACCEPTED_CELLS = []`，40 个单元仍为
  NOT_RUN/receipt=null。REQ Runtime 与 JSON 输出契约等既有限制继续未认证。

完整 raw receipt、stdout/stderr、首次失败、最终 PASS、source/PR 身份及摘要均位于
本目录。另行提供 byte-complete review archive、SHA-256 文件、准确源码树和可恢复
Git bundle；归档上传至 Web 会话，不以本机路径替代附件。

## Boundaries and handoff

本轮没有修改 main、七阶段 Runtime、共享 Package、原 Expected/Workflow、历史 Client
证据或分发元数据；没有重建 S4/E4、没有生产 Target effect、没有 merge。PR #11 必须
保持 Draft。唯一下一工作包是独立 Web 对准确 source、delivery commit 和完整附件进行
复核；本记录不自行签署 Web ACCEPTED。

```text
POST_INTEGRATION_STATUS_PATH_RECHECK = PASS
VALIDATED_SOURCE_SHA = 295d98260e3def713dc72b12c458aa2baa8372f4
DELIVERY_HEAD_SHA = <post-commit remote readback and archive binding>
STATUS_NEW_REGRESSIONS = 14/14
STATUS_FIXED_EVAL = 14/14
VFY_STRICT = 80/80
RLS_FIXED_EVAL = 87/87
REPOSITORY_TESTS = 1118
WEB_CONFORMANCE_REVIEW = REQUIRED
NATIVE_ACCEPTED_CELLS = []
REAL_TARGET_EFFECTS = 0
MAIN_MODIFIED = NO
PR_MERGED = NO
```

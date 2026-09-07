# GitHub Runtime Contract

Contract ID: `sdlc-ai-spec/runtime/github/v1`。

这是 opt-in 非 Phase 支撑扩展，不改变既有 Phase Result、ArtifactStore 或阶段状态机。只有显式调用 `sdlc-github` 的已声明操作可以通过 `packages/sdlc_github/transport.py` 访问固定 GitHub Remote MCP。其余 Runtime 仍保持离线边界；不得从 Phase 导入此 Transport 以绕过限制。

宿主调用固定 8 个工具；统一输出 `schemas/github-result.schema.json`。`ok/status/errors/warnings/next_action` 解释本次工具目标，不是 Gate。读取列表的 completeness 与本次一页请求成功分开；unknown/partial 不得冒充全量结果。

身份每个进程从一个 SDLC_GITHUB_TOKEN 绑定，在线 get_me 核验。写入同时校验 expected_actor_id、目标类型、白名单、write_policy、dry_run。字段并非用户授权凭据；宿主原生批准和当前请求仍是可信边界。

`.local/github/<actor>/<repository-key>/operations/<request-id>` 中的 intent 和 receipt 不可随意重建；`.cache` 不保存权威状态，删除缓存不影响去重。未知效果仅可显式只读核对，不重放。创建标记与属性匹配不足以证明全局 exactly-once；恶意同用户进程不在该机制硬隔离承诺内。

运行时不读取开发文档，不安装依赖，不调用其他 Skill，不提供 REST/CLI fallback 或任意 endpoint 配置。依赖和固定源码包由明确授权的构建步骤准备。

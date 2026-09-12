# Repository instructions

## 上游行为等价宪法

SDLC AI SPEC 是锁定版本 Spec Kit 的产品化移植，不是独立演进的流程引擎。
必须保留已纳入能力的上游业务行为、逻辑、流程顺序、条件、默认参数、询问、
停止条件、写入对象及触发语义。原版缺陷只记录、上报或等待上游，不在移植层
自行修复；本项目引入的偏差必须纠正或回退，不能以现有测试通过为由保留。
只允许明确的产品名称、入口名、资源路径及自然语言等价映射；事件名、配置键、
数据键、参数和机器标记不是普通产品文案。保持 src/upstream 原始字节，dist
由生成器产生。中文呈现不授权新增业务写入或批量重写已有产物。
本地 INIT 是独立项目初始化能力，不冒充完整原版安装器；本项目构建和升级
工具的错误由本项目负责。执行后的业务逻辑仍保持等价。Agent 的菜单展示、hint 和调用选择策略不属于
等价契约：公共入口不声明 user-invocable、disable-model-invocation、argument-hint，
使用宿主默认行为。被模型选择不增加写入、跨阶段或发布授权；流程内权限不变。

## Web 交付及补丁回退

沿用用户指定分支，修改前记录准确基线，优先完成并核实远端提交。远端写入
不能完成或无法核验时，直接提供可 git apply 的补丁、基线和验证记录，不再
反复要求用户重连。成功推送后让用户拉取，不重复要求应用补丁。工具发现、
单个 blob、局部测试、PR 评论不等于分支已经更新。没有准确证据不得宣称完成。


This repository is the SDLC user-scoped Spec Kit core port. Product metadata is
in `plugin-metadata.json`; keep version `1.0.0-beta` during the debugging period.
The declared plugin repository is `https://github.com/goedgecloud/sdlc-ai-spec`
and the port author is Blade. Git transport may use a different authorized
working repository; never silently change the declared metadata or claim a
repository transfer from a metadata edit.

## Source and scope

- Read README.md, docs/DEVELOPMENT.md, docs/MIGRATION.md, docs/LOCALIZATION.md, docs/STATUS.md and upstream.lock.json.
- Before naming changes or upstream upgrades, also read docs/NAMING.md and
  docs/naming-map.json. Apply the approved context-specific product/Skill mapping
  in the generation layer, preserve raw upstream provenance, and update all
  callers together. Naming changes do not authorize behavior changes. An approved
  target name is not evidence that the runtime migration has shipped.
- Preserve the nine pinned upstream English commands and the documented path,
  name and packaging deltas. Translation is permitted only in derived prose, not
  raw sources or machine contracts; no new process rules or legacy runtime.
- Templates use reviewed Chinese presentations with preserved machine anchors;
  keep English derivation in src/templates for independent upstream comparison.
  Never add language-tag comments or translate existing project files implicitly.
- STATUS is a local read-only utility, not an upstream stage. Never make it
  persist selection, initialize projects, run other Skills, or invent phase history.
  Constitution generation provenance is observation data only: do not equate hash
  equality/difference with RULE completion or approval, and never backfill missing
  legacy provenance from the current template. All 11 entries live in dist/skills;
  do not regenerate host-private wrappers.
- Project-only INIT is authorized and implemented by adapters/INIT.md plus the
  bundled stdlib initializer. When it actually creates a constitution it may record
  the exact generated-byte baseline/source once; existing constitutions and records
  are preserved. Provenance failure must not authorize overwrites or data repair.
  Preserve existing project data; never install tools.
- GitHub integration, real-project execution and native client installation remain
  outside automated engineering verification. They require separate authority.
- Shared resources are read-only; project state belongs to `.sdlc`. Never infer
  the business project root from the plugin installation directory.
- Keep src/upstream byte-identical to the locked upstream. Edit adapters/ and tools/;
  regenerate derived source, the single dist package and root marketplaces. Never
  hand-edit generated wrappers, host fragments or shared workflow bodies.
- Preserve upstream copyright, license and provenance. Plugin authorship does not
  replace the original authorship of the copied Spec Kit source.
- Development/build/test/upgrade tooling outside `dist/` is uv-managed. Keep
  `pyproject.toml` and `uv.lock` synchronized, use `uv sync --locked` /
  `uv run --locked`, and do not reintroduce a requirements.txt dependency source.
  `dist/` must remain uv-independent at runtime.

## Verification and delivery

Verify the repository, branch, HEAD and worktree before writes. Preserve unrelated
user work. Commit/push only within the explicitly authorized branch. Do not merge,
retag, release, rewrite history or modify other branches without authorization.

For translated inputs use the documented LOCALIZATION_REQUIRED / reviewed refresh
path; do not hand-edit candidate digests or reuse stale evidence.
Use tools/upgrade.py for detached upstream candidates; never overwrite the accepted
worktree during preparation or weaken comparisons to accept a new version.

Use the installed pinned upstream CLI only to produce independent empty-project
baselines. Never use migrated output as its own upstream oracle. Engineering
checks may use synthetic temporary directories, not business projects or LLMs.
Run the complete verifier, repository tests and `git diff --check`. CI is read-only
and reports the exact source SHA. Keep evidence outside the checkout and do not
replace raw evidence with a historical PASS statement.

A valid manifest is not native host compatibility, and engineering success is
not business acceptance. State the environment, source SHA, counts and unperformed
checks precisely. Keep docs current without adding a separate process platform.

Use the work package PR as the decision, implementation and verification record.
Keep its body current and append milestone comments with exact source SHAs,
actual tests, failures/corrections and unperformed checks. README and naming
contracts hold lasting definitions; do not create a duplicate progress platform.
Record actual Git author/committer separately from product authorship. Never
claim merge-readiness, native-host acceptance or business acceptance from a
naming-documentation check alone.

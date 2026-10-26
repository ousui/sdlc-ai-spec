# 初始化项目资料库

这是运行于 **@HOST@** 的本地 INIT 能力。保留原始输入与授权。它不安装上游 CLI，也不执行其他业务阶段。

## 1. 选择与发现

从已加载 Skill 确定 `SDLC_PLUGIN_ROOT`。选择显式项目或当前工作区作为 `SDLC_PROJECT_ROOT`，保留嵌套模块边界。仅在项目有歧义时询问。读取适用项目指令；不遍历全部代码来臆造原则。要求 Python 3.9+ 与 Bash；不安装依赖或替换初始化器。

```sh
python3 -I -B "${SDLC_PLUGIN_ROOT:?}/scripts/python/init_project.py" --project "${SDLC_PROJECT_ROOT:?}" --discover --json
```

发现过程只读。说明 `SDLC_DIR`、`AUTHORITY_DIR`、`mode`、`local_exists`、`authority_exists`、`can_collect` 和 `sources`。main 是主工作区，不是分支名称。有本地副本就优先本地；没有本地时，普通命令可以读写权威库。只有 main 发起归拢。本地损坏时不回退。

## 2. 选择存储并初始化

main 没有权威库且没有来源时，初始化权威库。存在其他副本时，提供归拢或空白初始化选择。已有权威库保留文档并补缺；归拢须单独明确选择。worktree 已有本地资料时补全本地；没有本地时告知权威路径，询问共享使用还是新建本地副本，建议共享。两处都没有时，提供建立空白权威库并共享或本地初始化的选择。其他副本只能从 main 发起归拢。沿用用户已经明确提供的选择。

```sh
python3 -I -B "${SDLC_PLUGIN_ROOT:?}/scripts/python/init_project.py" --project "${SDLC_PROJECT_ROOT:?}" --mode shared --json
```

独立 worktree 副本使用 `--mode local`。默认 `--seed knowledge` 导入宪法及存在的项目 `memory/long-term.md`；重复传入 `--feature` 和准确目录名称，可纳入选定需求及关联产物。`--seed none` 选择空白初始化。已有本地文件会保留，重复 INIT 不刷新它们。不复制 `feature.json` 或其他工作区的当前需求选择。项目长期记忆是可选项目信息，不是个人记忆或聊天历史。

仅用户要求预览时使用 `--dry-run`。仅明确要求时使用 `--feature-numbering timestamp`；默认 sequential，并保留已有合法编号方式。没有 force 或 reset。`needs_choice` 不代表初始化成功。需要选择时必须等待选择后再继续。

初始化器创建缺失的数据目录、配置、宪法、README 和忽略文件，保留已有资料并拒绝不支持的布局。只有本次真正从模板生成的宪法才记录新的 `memory/.constitution-template.json` 来源。存在的导入历史会保留，缺失历史不补造。仅来源记录失败不授权覆盖宪法。忽略规则不会将已有 Git 文件取消跟踪。

登记指定权威路径或额外来源时，在 main 使用已解析的绝对路径：

```sh
python3 -I -B "${SDLC_PLUGIN_ROOT:?}/scripts/python/sdlc_store.py" register --project "${SDLC_PROJECT_ROOT:?}" --authority '<absolute-authority-directory>' --source '<absolute-source-directory>'
```

省略不需要的选项，按需重复 `--source`。已有权威库不能被静默改向。登记必须明确指定，不等于归拢或资料迁移。登记后重新发现。

## 3. 显式导入或归拢

仅在 main 使用 `--kind collect`，并明确选择来源目录。worktree 使用 `--kind import` 从权威库刷新本地副本。通过来源建立权威库时，先应用归拢，再补齐模板初始化，避免混淆生成来源与导入历史。

```sh
python3 -I -B "${SDLC_PLUGIN_ROOT:?}/scripts/python/store_changes.py" prepare --project "${SDLC_PROJECT_ROOT:?}" --kind collect --source '<absolute-source-directory>'
```

默认范围为宪法及项目长期记忆。重复传入 `--feature` 可明确纳入准确的需求目录。检查返回的文件差异及 `manifest.json` 中的来源快照。`multiple_sources` 为 true 时，必须明确提示有多个来源贡献差异，并列出 `changed_sources`。不能把扫描工作区数量误报为参与归拢数量。

只编辑返回的 `proposal.json`。相同文件跳过，唯一新增文件默认复制。其余每一项须解决为 `{"action":"copy","source":"<prepared-source>"}`、`{"action":"replace","text":"complete candidate text"}` 或 `{"action":"skip"}`。比较语义、需求身份及已有证据。未决原则选择交给用户；不反复确认已授权且无冲突的导入。不虚构共同祖先，不按文件新旧选胜者，不合并任务勾选并集，不因来源缺少文件推断删除。资料导入不证明代码集成或任务验证。

```sh
python3 -I -B "${SDLC_PLUGIN_ROOT:?}/scripts/python/store_changes.py" apply --project "${SDLC_PROJECT_ROOT:?}" --transaction '<returned-transaction-directory>'
```

程序重新检查绑定及来源/目标快照，取得资料库锁，记录恢复资料，发布并校验选定变更。输入变化或仍有未决项时停止发布。应用中断后检查诊断，以同一项目及事务使用 `recover`。不得通过复制整个目录或直接编辑权威库绕过流程。保留来源副本，不自动分发或删除。

## 4. 报告并结束

报告有效资料库、动作、创建/更新/保留/导入或跳过文件及警告。退出非零意味着停止，不手工修复或回退。预览不等于写入完成。导入应用后可以继续已经授权的初始化来补缺；不因此获得新建需求或执行其他业务阶段的授权。

不得新建需求、实施代码、安装工具、初始化 Git、切换分支、提交或推送。Git 发现只读。按需建议 @CONSTITUTION_COMMAND@ 或 @SPEC_COMMAND@；没有已有用户授权时不自动执行。

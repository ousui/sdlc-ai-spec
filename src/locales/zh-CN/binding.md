
<!-- SDLC-PACKAGE-BINDING:BEGIN -->
## 已安装插件与业务项目绑定

本次调用宿主为 @HOST@。先完成路径绑定，再执行下面的原有流程。

- @ROOT_DETAIL@ `SDLC_PLUGIN_ROOT` 是已加载核心 Skill 目录向上两级的插件包目录（`skills/<name>/SKILL.md`）。不得从业务工作目录推断或假定变量已导出。正常执行期间使用同一完整包。更新移除该包时，从宿主当前 Skill 清单、安装记录或用户明确路径定位当前包，不按缓存版本排序猜选。读取其入口和 `skills/sdlc-refine/references/compatibility.md`，评估兼容性及先前操作结果，再从选定包完整重载流程。不得混用包或重放未经核实的写入。版本不同或旧包缺失本身不要求迁移或用户重新调用。
- 保持 shell 工作目录位于选定的业务项目。执行 `SDLC_HOST=@HOST@ bash "${SDLC_PLUGIN_ROOT:?}/scripts/bash/project-paths.sh"` 解析选定代码项目及其有效 `.sdlc` 资料库。用户明确选定项目时，以命令局部变量 `SDLC_INIT_DIR` 传入其绝对路径。将返回的 `PROJECT_ROOT` 作为 `SDLC_PROJECT_ROOT`。项目不存在或无效时停止，明确运行 `sdlc-000-init` 初始化或补全；不得回退到其他工具。
- 每次使用这些变量的 shell 调用都显式传入已解析的绝对值；工具调用之间不保证 shell 状态持久化。`${VAR:?}` 有意在变量未解析时失败。非 shell 文件工具使用实际绝对路径，不把 `${VAR}` 字面量传给工具。不得通过切换到插件目录来修复资源定位。
- 创建或更新需求文件前，通过命令局部 `SDLC_INIT_DIR` 调用同一 `project-paths.sh --feature <resolved-feature-directory>`，检查显式路径和符号链接不会指向本插件。该脚本只读，不执行初始化。项目状态、当前需求和宪法不得写到插件内。
- 本包沿用仅核心、无 Preset、无 Extension、无事件的既有 profile。不得为满足引用而安装或调用扩展、上游 CLI。项目包含 `.sdlc/extensions.yml`、已安装预设或扩展状态时，停止并说明该 profile 不受支持。下面保留上游条件钩子文本用于来源等价，不构成启用可选子系统的授权。
- `$ARGUMENTS` 表示本次调用的用户输入。宿主没有替换它时，从当前对话读取这次输入；不得将占位符字面量作为需求描述。
<!-- SDLC-PACKAGE-BINDING:END -->

## 工作区存储扩展

选定代码项目仍为 `SDLC_PROJECT_ROOT`；解析器还返回 `SDLC_DIR`、`AUTHORITY_DIR`、`FEATURE_JSON`、`mode` 和 `can_collect`。独立本地 `.sdlc` 优先；没有本地时，普通命令读写权威库。只有 main 可以归拢副本。不得通过指定权威库绕过本地资料或无效的本地需求选择。main 指主工作区，不是分支名称。

main 的登记不可用时，有效的独立本地工作可以继续：`AUTHORITY_DIR` 和 `authority_exists` 为 null，`authority_error` 说明原因。不得猜测权威路径；导入权威资料、无法核实的外部需求目标或本地目录别名仍然停止。

以下所有 `.sdlc/` 资料引用都相对于 `SDLC_DIR`；`.sdlc/feature.json` 解释为 `FEATURE_JSON`。代码、实施、测试及其他非资料相对路径仍位于 `SDLC_PROJECT_ROOT`。使用 `project-paths.sh --feature` 解析显式需求并使用返回的 `FEATURE_DIR`。有效库存在 `memory/long-term.md` 时，将其作为项目上下文读取；它不覆盖宪法或用户指令。不复制其他工作区的当前需求选择。

显式需求输入优先于已保存的选择。仅解析资料库、创建新需求或编辑明确指定的文件，不要求未使用的旧选择有效。流程需要已保存的选择时，只使用本工作区的记录，不回退到其他资料库。保留既有持久化及只读规则。显式 `.` 或 `./` 表示代码项目目录，仍受相同路径校验约束。独立本地库与权威库的资料根不得重叠。

模型编写有效库内的文件时，在编辑文档前准备候选：

```sh
python3 -I -B "${SDLC_PLUGIN_ROOT:?}/scripts/python/store_changes.py" prepare --project "${SDLC_PROJECT_ROOT:?}" --kind edit --path '<store-relative-file>'
```

本次涉及多个文件时重复传入 `--path`。只编辑返回的 `proposal.json`：每个已准备文件使用 `{"action":"replace","text":"complete candidate text"}` 或 `{"action":"skip"}`。随后通过程序发布：

```sh
python3 -I -B "${SDLC_PLUGIN_ROOT:?}/scripts/python/store_changes.py" apply --project "${SDLC_PROJECT_ROOT:?}" --transaction '<returned-transaction-directory>'
```

普通编辑的快照只包含选定文件、`init-options.json` 和当前工作区的 `FEATURE_JSON`。无关产物及其他 worktree 的需求选择不使候选失效；本次目标或必要绑定变化仍阻止应用。导入和归拢保留来源与目标快照检查。

沿用既有流程授权，不增加改动其他产物的权限。未决事项或输入变化阻止发布；重新准备，不强行应用过期变更。包内写入脚本使用同一把资料库锁。显式外部需求目录保留既有路径检查；存在本地副本时，不得将其指向权威库。只读阶段不准备或应用写入候选。应用中断后先诊断，可使用同一程序的 `recover` 动作恢复；不得删除其他操作的锁或覆盖后来的编辑以强行恢复。

INIT 或准备过程停止后若遗留锁，以选定项目使用 `sdlc_store.py recover-lock --project`。它只释放已记录进程不再运行的锁；中断的资料应用仍须使用 `store_changes.py recover`。归属信息不完整或进程仍存活时停止恢复。

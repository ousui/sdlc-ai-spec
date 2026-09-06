# sdlc-github 安装与本地复验

## 绑定解释器，不使用系统 python3 猜测

在仓库外显式创建虚拟环境，使用 Python 3.12/3.13 和 `packages/sdlc_github/requirements.lock` 安装完整哈希锁。
本轮 Web 使用 Linux/Python 3.13；macOS 默认 `/var` 临时路径应由使用者先解析为同一目录的真实路径，不放松 Runtime 的符号链接拒绝。

```bash
python3 -m venv /absolute/outside/github-venv
PY=/absolute/outside/github-venv/bin/python
"$PY" -m pip install --require-hashes -r packages/sdlc_github/requirements.lock
"$PY" tools/install_sdlc_github.py --host codex --python "$PY" \
  --destination /absolute/outside/github-installed-v2 --data-root /absolute/existing/stable-data
```

按目标宿主选择 codex/cursor/claude-code。安装目录必须新建，data 可复用已有稳定根，绝不能清除其中的 intent/receipt。
安装器不修改宿主全局设置、不展开或保存 Token。每个宿主一次仅加载一份对应插件，若市场同名版本覆盖本地副本，先解决真实加载冲突，不把旧版本当作本候选。

安装后的 Skill 使用 `<installed>/skills/sdlc-github/scripts/run`。此 launcher 绑定上述准确解释器并以自身目录定位 runtime.py；代码目录移动后 launcher 仍相对定位，但 MCP manifest 的绝对脚本路径需要显式重新绑定。源码目录的 scripts/run 只返回 INSTALLATION_REQUIRED，不走系统解释器后门。
共享合约的准确 Skill 相对链接为 `../_shared/contracts/github-runtime.md`。不通过扫描业务目录找解释器、AGENTS 或合约。

## 凭据和实际调用

生产仅从宿主进程环境接收 SDLC_GITHUB_TOKEN，换凭据后重启该实例，不在聊天/命令参数/fixture/证据中出现值或 hash。已有稳定数据根中的真实 unknown 请求只能只读核对。
配置保持既有官方宿主语法，业务实现无三端复制。启动冷测与真实权限行为需要实际本地环境；按照 main 的决定，三端独立认证为可选反馈，不作为自动门禁，也不自述 PASS。

## 一个仓库回归入口

```bash
SHA=$(git rev-parse HEAD)
"$PY" -B tools/validate.py --profile full --source-sha "$SHA" --json-out /absolute/outside/github-full.json
```

统一集合已包括 GitHub 离线/真实 stdio 到 Fake HTTP/安装/修复反例，只运行一次，不再叠加私有套件。full 不声明 VFY 的 strict OS 沙箱执行。
真实 GitHub 定向复验见当前 Client 提示词；不要使用旧归档 Goal 强制再做三端认证或重放旧 live 批次。

## Python 环境与 READY 的边界

`--check-install` 的 READY 仅表示固定依赖包版本匹配，不验证或认证解释器版本。3.12/3.13 是现有声明范围；当前回归选用 Python 3.13。Client 的 Python 3.14.7 运行结果仍保留为环境差异，不因依赖 READY 扩大支持声明。测试自建临时目录先解析为已存在的物理路径；这不允许生产 Runtime 接受未经核对的符号链接，也不修改用户稳定数据根。

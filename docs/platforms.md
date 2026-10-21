# 平台安装、路径与验证范围

同一套发行源码面向 macOS、Linux、Windows 原生和 WSL2；每个平台仍分为独立的 Codex 包与 Claude 包。操作系统适配不改变快修准入、升级锁定、独立 QA/review、模型质量或回修预算。

## “把文件放到 Windows”具体指什么

Codex 可以使用普通文件安装，但必须**完整复制到正确的位置**，不能只复制四个 `SKILL.md`：

| 发行内容 | 原生 Windows 默认位置 |
| --- | --- |
| `packages/codex/agents/` 内的 8 个 TOML | `%USERPROFILE%\.codex\agents\` |
| `packages/codex/skills/` 内所有技能和 `_shared` | `%USERPROFILE%\.agents\skills\` |

`_shared` 放在 `skills` 里面，与四个技能目录并列；其中包括模型解析程序、规则和本端平台约定。优先用安装器，避免漏文件或覆盖已有定制。手动复制不产生安装清单，后续 `check`/`uninstall` 不能将这些未经管理的文件当作自己安装的文件；切换安装器时会先检查冲突，需要明确 `--replace` 才备份替换。

Claude 插件发行包含 `${CLAUDE_PLUGIN_ROOT}` 引用，**应整体按插件安装**，不能把里面的角色/技能单独摊平到个人目录后期待插件变量仍自动解析。保留 `packages/claude/.claude-plugin/plugin.json`、`agents/` 和 `skills/`，使用市场安装或 `--plugin-dir` 加载；两种方式都不读取 Codex 包。

Claude 也支持个人目录安装：执行 `packages/claude/install.py install`、`check`（Python 3.11+），自动生成 `~/.claude/agents` 与 `~/.claude/skills` 所需的独立普通文件。若要手动复制，先用 `install --home <空暂存目录>` 生成个人形式，再复制，不能直接摊平插件源码。插件和个人安装二选一；详细命令见根 README。

这解决的是文件分发和定位。运行仍需要受支持的宿主版本、模型权限、必要的委派能力以及项目工具；不能因文件已复制就假定全部业务验证可运行。

## Windows 原生 Codex

Windows 使用 `packages/codex/install.ps1`，无需固定依赖 `py`。入口尝试 `py`、`python`、`python3` 及注册表、用户常见安装目录中的 Python，实际执行版本检查（3.11+），跳过商店占位命令。未找到时不会写入专家团文件，会提示安装 Python。

如果未安装 Python，从 [官方 Windows 下载页](https://www.python.org/downloads/windows/) 安装 Python 3.11+；传统安装器勾选 **Add python.exe to PATH**，完成后新开终端。自定义安装可设置 `$env:EXPERT_PYTHON = 'D:\Tools\Python\python.exe'`（替换为真实解释器路径）。入口本身不下载依赖，也不修改系统执行策略。

在仓库根目录执行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\packages\codex\install.ps1 install --dry-run
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\packages\codex\install.ps1 install
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\packages\codex\install.ps1 check
```

有同名文件默认停止；确认替换时加 `--replace`，保存原文件备份。更新代码后重复 `install`、`check`；卸载用 `uninstall`。新开 Codex 会话后使用 `$quick-fix` 等技能调用语法。

无写入预览通过仍不等于完整业务流程已通过。安装器不调用模型，不更改全局配置或账号。

隔离演练使用独立目录，`--home` 只指定本安装器的测试目标：

```powershell
$expertTestHome = Join-Path ([IO.Path]::GetTempPath()) ("expert-test-" + [guid]::NewGuid())
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\packages\codex\install.ps1 install --home "$expertTestHome"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\packages\codex\install.ps1 check --home "$expertTestHome"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\packages\codex\install.ps1 uninstall --home "$expertTestHome"
```

它不会切换现用 Codex 的用户目录。非默认 `CODEX_HOME` 布局仍不在本安装器支持范围内。

## Windows 原生 Claude

Claude 官方支持原生 Windows 和 WSL。原生环境可能提供 PowerShell 或 Git Bash，本包八个角色允许使用宿主实际可用的 `Bash`/`PowerShell`，原职责边界不变。老客户端缺少 PowerShell 时需已有可用的 Git Bash，或自行更新宿主；专家团不会自动修改系统或升级客户端。

在 Claude 会话中，已发布版本的安装命令仍是：

```text
/plugin marketplace add liusiyangiOS/dev-expert-plugin
/plugin install dev-expert-plugin@dev-expert
```

验证本地未发布版本，可以在仓库根目录的 PowerShell 执行：

```powershell
$expertRepo = (Get-Location).Path
claude plugin marketplace add "$expertRepo"
claude plugin install dev-expert-plugin@dev-expert
claude plugin details dev-expert-plugin@dev-expert
```

或只加载当次会话：

```powershell
claude --plugin-dir ".\packages\claude"
```

不同时加载同名插件的两个版本。安装后仍用 `/dev-expert-plugin:quick-fix` 等命令。插件安装与运行不要求 Python；个人目录安装器和仓库维护测试要求 Python 3.11+。

官方参考：[Windows 设置](https://code.claude.com/docs/en/setup#set-up-on-windows)、[PowerShell 工具](https://code.claude.com/docs/en/tools-reference#powershell-tool)、[插件资源定位](https://code.claude.com/docs/en/plugins-reference)。

## macOS、Linux、WSL2

沿用各端 README 的 POSIX 命令，Python 3.11+。在 WSL 内安装就使用 Linux 用户目录和 Linux 工具链；在 Windows 原生 Agent 中使用则安装到 Windows 用户目录。集成终端选择和 Agent 执行环境分别确认，不能只看窗口标题。

不要链接 Windows 与 WSL 的角色、规则或模型缓存；也不要把 macOS 的验证结果当作 Windows 项目通过结果。相关 OS、依赖、环境变化按历史失败协议重新核验。

Codex 官方参考：[Windows 原生和 WSL 环境](https://learn.chatgpt.com/docs/windows/windows-app)、[WSL2](https://learn.chatgpt.com/docs/windows/wsl)。

## 路径是否写死了作者电脑

两端源码使用相对资源路径、当前用户主目录或插件根目录，不使用作者的用户名、盘符或 checkout 路径：

- `~`：当前 **Agent** 用户的主目录；文件工具/外部程序调用前展开为真实绝对路径。
- `${CLAUDE_PLUGIN_ROOT}`：当前安装的 Claude 插件根目录，不是作者目录，也不是必然存在的 shell 环境变量。
- Python `Path.home()`：按实际操作系统解析用户目录；路径包含中文/空格也作为完整参数传递。
- `~/.cache`、`~/.local/state`：本包选定的用户内数据布局，Windows 也能创建对应目录，不代表依赖 Unix 目录或系统级服务。

可以只读检查：

```powershell
py -3 -X utf8 .\tests\audit_paths.py
py -3 -X utf8 .\tests\audit_paths.py --installed
```

POSIX 用 `python3`。`--installed` 只扫描本团角色和技能源码，不读取认证/会话，不更改配置。它检查个人绝对路径残留；资源存在性、跨端隔离由另外的分发测试验证，单一扫描不能证明完整可用性。

## 验证边界

仓库包含 Windows/macOS/Linux × Python 3.11/3.14 的离线 CI 矩阵。只有用户提交并推送后，相应 GitHub Actions 才会运行；存在 CI 配置不等于 Windows 已通过。

本次修改在 macOS 执行了回归和宿主安装测试，新增中文/空格路径、显式 UTF-8、Windows 路径形式、子进程目录隔离与目录联接拒绝逻辑测试。真实 Windows 目录联接测试在非 Windows 明确标 skipped，不能计为已通过。

`tests/host_smoke.py` 两端宿主测试需要实际 CLI；Windows 的测试程序选择原生 `.exe`，不拼接 `.cmd`/`.ps1` 包装器参数。此要求只针对宿主测试器，不影响通过支持的宿主方式使用专家团。测试只使用临时 HOME/USERPROFILE、应用数据和配置目录，不继承模型凭据；原生 Windows Codex 已通过 4 技能/8 角色的隔离宿主发现验证；Windows Claude 宿主与完整线上业务流程仍待验收，见 [验证记录](validation.md)。

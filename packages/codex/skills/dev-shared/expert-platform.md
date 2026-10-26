# Codex 平台与路径约定

适用于本包四个 skill 和八个专家；只处理平台适配，不改变模型选择、准入、验证、权限或回修预算。

## 先识别执行环境

区分 Agent 实际运行的原生 Windows、WSL2、macOS、Linux，以及本次执行工具的 PowerShell、CMD、Bash/Zsh。终端界面或项目路径不能单独证明 Agent 在哪运行；不要因为系统是 Windows 就假定所有命令都是 PowerShell。

本包采用默认用户布局。文档中 `~` 是**当前 Agent 用户的主目录**，不是作者目录或项目目录。原生 Windows 通常由 `USERPROFILE` 解析，Python 使用 `Path.home()`；WSL 使用 Linux 主目录。传给文件读取工具或外部程序前，先解析成实际绝对路径，含空格/中文的路径按当前 shell 正确引用；不能假定工具会展开 `~`、`$HOME` 或 `%USERPROFILE%`。

| 内容 | 相对当前用户主目录 |
| --- | --- |
| 专家 | `.codex/agents/` |
| 技能和本端规则 | `.agents/skills/`（`dev-shared` 必须完整保留） |
| 宿主模型目录 | `.codex/models_cache.json` |
| 专家团模型缓存 | `.cache/codex-expert-workflows/expert-model-cache.json` |
| 默认历史失败记录 | `.local/state/expert-workflows/<repo-key>/known-failures.json` |

非默认 `CODEX_HOME` 尚未适配：检测到与默认用户布局不同就报告路径不匹配，不偷偷读取另一个用户/平台目录或新建第二套缓存。安装器同样拒绝默认安装到不匹配布局。不要在 Windows/WSL 间链接规则、角色或缓存。

## Python 与模型解析命令

仅在需要运行解析器时核对解释器：Windows 优先检查 `py -3`，没有时检查 `python` 或 `python3`；POSIX 检查 `python3`。用候选解释器执行 `-c "import sys; print(sys.executable); print(sys.version)"`，确认实际可执行文件和 Python 3.11+，后续复用该选择。命令不存在不表示模型不可用；不能通过跳过解析/降低模型要求解决。

POSIX 示例（路径必须加引号）：

```bash
python3 "$HOME/.agents/skills/dev-shared/expert_models.py" status
```

PowerShell 示例（使用已核验的 Python Launcher）：

```powershell
py -3 -X utf8 "$env:USERPROFILE\.agents\skills\dev-shared\expert_models.py" status
```

CMD 使用 `%USERPROFILE%`，不要混用 PowerShell 的 `$env:`。`refresh`、`resolve` 使用同一解释器和同一个绝对脚本路径，参数和模型规则仍以 `expert-model-policy.md` 为准。Windows 不存在 `py` 时使用已核验的 `python` 或绝对解释器路径，不安装假定版本。

缓存与 JSON 显式以 UTF-8 读写。调用脚本可以设置 Python 的 `-X utf8`；这只作用于该次 Python 进程，不改系统区域/编码设置。临时目录使用宿主临时目录 API 或 Python `tempfile`，不要把 `mktemp`、`/tmp` 当作跨平台前提。

## 项目工具和验证

读取项目实际构建/测试命令；有 `rg` 时优先，没有时用宿主搜索工具。Windows 原生命令与 WSL 的路径、工具链、环境分别核验，不混用两端生成物来证明通过。

测试/诊断结论记录实际 OS、shell、Python、依赖和运行时。平台变化可能使历史失败诊断或验证证据失效，继续执行原来的精确匹配规则。缺少项目工具时报告缺口，不用跳过必要测试来宣称跨平台通过。

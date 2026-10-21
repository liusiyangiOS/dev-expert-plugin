# Claude 平台与路径约定

适用于本插件的四个技能与八个角色。平台适配不降低准入、模型、验证、权限或预算要求。

## 执行环境与工具

先识别当前 Agent 实际在原生 Windows、WSL、macOS 还是 Linux，核对调用工具真实使用的 shell。原生 Windows 的 Claude 可能使用 PowerShell，也可能使用 Git Bash；有 Bash 工具不等于所有 Windows 路径都能原样传入，终端类型也不等于工具执行环境。

角色允许使用 `Bash` 与 `PowerShell` 中宿主实际提供的工具；缺少某个工具不伪称其存在。旧客户端如果没有 PowerShell 工具，可在已安装且可用的 Git Bash 下执行；两者都不可用时报告能力缺口。只读角色在任何 shell 下都保持只读职责，team-lead 不借 shell 编写业务实现/测试。

## 插件资源与本端状态

`${CLAUDE_PLUGIN_ROOT}` 是**当前安装者这一版本插件的实际根路径**。由宿主在加载技能/角色 Markdown 时替换，附属文档中的同名占位符按已解析的插件根路径解释；不要假定它是 Bash 已导出的环境变量，不猜测作者或宿主缓存目录。

读取文件时使用真实绝对路径；相对 Markdown 链接从所在文件解析。路径包含空格/中文时按实际 shell 引用；需要转换 Git Bash/Windows 路径时以本机工具输出为准，不能拼作者盘符。插件缺少资源时报告安装错误，不从个人旧技能或其他平台补读。

文档中 `~` 表示**当前 Agent 用户主目录**：原生 Windows 解析用户配置目录（通常 `USERPROFILE`），WSL 解析 Linux 用户目录。传给 Read、外部程序或 shell 前展开，不依赖文件工具替你展开 `~`。本插件的模型与诊断数据按用户主目录保存：

| 数据 | 相对当前用户主目录 |
| --- | --- |
| 本端模型缓存 | `.claude/cache/expert-team/expert-model-cache.json` |
| 默认历史失败记录 | `.claude/state/expert-workflows/<repo-key>/known-failures.json` |

`CLAUDE_CONFIG_DIR` 决定宿主配置位置；本插件上述自有数据位置仍明确按用户主目录计算。隔离测试必须同时隔离宿主配置和用户主目录，不能只换宿主配置却写真实用户缓存。Windows 与 WSL 不共享这两类数据，也不读取 Codex 模型目录。

## 命令、编码与证据

模型选择直接用 Claude 宿主能力，不依赖 Python 或其他平台解析器。项目确需 Python 时，Windows 核对 `py -3`/`python`，POSIX 核对 `python3`，以实际 `sys.executable` 和版本为准。原生 Windows 的 UTF-8 JSON 使用显式 UTF-8 编码；Python 可加 `-X utf8`，不要改系统编码设置。

根据实际 shell 选择 PowerShell 的 `$env:USERPROFILE`、CMD 的 `%USERPROFILE%` 或 POSIX 的 `$HOME`；仅用于访问对应变量，不重新赋值这些系统变量。临时文件使用平台临时目录接口，不把 `mktemp` 或 `/tmp` 当作必备。

项目构建/测试工具按当前平台核对。记录 OS、shell、工具链和运行时，跨平台或环境变化按原协议使相应验证/历史失败记录失效；不能把别的平台通过结果当成本次通过。Apple 构建能力等平台专属工具不因安装了技能就变成跨平台可用。

# Claude Code 开发专家团

独立 Claude 插件：8 个专家、4 个完整 skill、Claude 自己的规则与动态模型策略。不读取 Codex 或 `.agents`，不链接另一端文件。

同一包适配 Windows 原生、WSL、macOS、Linux。所有入口与角色会读取本端 `skills/dev-shared/expert-platform.md`，选择宿主实际提供的 Bash/PowerShell 并解析插件资源。当前实测宿主平台是 macOS，Windows 原生验收尚待执行。

## 安装

需要支持插件、技能、自定义 Agent 与角色 `effort` 的 Claude Code。插件安装、模型权限和项目工具是不同前提；账号必须能调用要求的模型/强度。

发布新版后，在 Claude Code 内输入：

```text
/plugin marketplace add liusiyangiOS/dev-expert-plugin
/plugin install dev-expert-plugin@dev-expert
```

未发布的本地 checkout 使用其绝对路径注册市场：

```bash
claude plugin marketplace add /absolute/path/to/dev-expert-plugin
claude plugin install dev-expert-plugin@dev-expert
claude plugin details dev-expert-plugin@dev-expert
```

首次安装后新开会话。市场名称和插件名称沿用旧版；市场来源指向 `packages/claude`，不会安装 Codex 包。

Windows PowerShell 在仓库根可运行：

```powershell
$expertRepo = (Get-Location).Path
claude plugin marketplace add "$expertRepo"
claude plugin install dev-expert-plugin@dev-expert
claude plugin details dev-expert-plugin@dev-expert
```

角色允许 `Bash`、`PowerShell` 两种 shell 工具，实际只调用当前宿主提供的工具，不改变只读职责或权限。旧客户端若缺 PowerShell，可使用已配置的 Git Bash；没有必要命令工具时报告缺口，不跳验证。官方 [Windows 设置](https://code.claude.com/docs/en/setup#set-up-on-windows) 与 [工具说明](https://code.claude.com/docs/en/tools-reference#powershell-tool) 列出实际前提。

只拿到本端目录也可直接加载，不需要另一端或仓库根文件：

```bash
claude --plugin-dir /absolute/path/to/claude-package
```

这是当次会话加载，后续会话仍需带该参数，不等同永久安装。不要同时加载市场版与相同的 `--plugin-dir` 版本。

Windows 在仓库根也可用 `claude --plugin-dir ".\packages\claude"`。必须保留整个插件结构；不能把角色和技能拆出来放到普通用户目录后继续依赖 `${CLAUDE_PLUGIN_ROOT}`。详细路径与安装边界见 [平台说明](../../docs/platforms.md)。

## 使用

插件技能使用命名空间：

```text
/dev-expert-plugin:dev-expert-team-review 实现需求：背景…目标…约束…验收…
/dev-expert-plugin:dev-bugfix-pipeline 修复缺陷：复现…预期…实际…日志…
/dev-expert-plugin:dev-quick-fix 处理这个局部问题，先准入，不满足就升级。
/dev-expert-plugin:dev-post-coding-pipeline 只检查当前改动，不修改、不提交。
```

单独角色请指定插件来源，例如“使用 dev-expert-plugin 的 dev-code-reviewer 审查当前 diff，不修改代码”。调度者按宿主实际角色列表选择 `dev-expert-plugin:<角色>`，避免误用用户目录的旧同名角色。

快速修复主动/自动调用均先准入；首次失败、复杂或不确定即升级且禁止同一问题回切。完整流程只允许简化符合条件的局部实现，原必要验证、独立 QA/review 和累计预算保留。post-coding 默认只读，不因找到简单问题自动获取修复授权。

## 更新与卸载

```text
/plugin marketplace update dev-expert
/plugin update dev-expert-plugin@dev-expert
```

更新后新开会话。保持市场与插件 ID 不变，新的源码随插件版本进入宿主缓存；不要手改缓存目录再期待插件更新保留修改。

```text
/plugin uninstall dev-expert-plugin@dev-expert
```

插件生命周期由 Claude 管理。我们另外保存在本端的模型缓存、历史诊断和项目 ledger 不随源码分发；卸载后如果需要清理这些个人运行数据，应另行确认，不盲删整个 `~/.claude`。

## 从旧 workflow / 个人安装迁移

仓库的旧三条 JS workflow 已由四个 skill 替代；当前插件没有活动 `workflows/`。旧脚本历史可在 Git 中查询，运行不依赖旧脚本。

若此前手工复制到 `~/.claude/agents`、`~/.claude/skills`、`~/.claude/workflows`，插件安装不会自动删除它们。先备份，再由用户明确停用同名旧入口，避免双重调度；保留无关角色和技能。迁移完成使用带 `dev-expert-plugin:` 前缀的新命令。插件管理命令不替你迁移个人文件；下面的个人目录安装器只管理本团清单中的源码文件。

## 路径、模型和状态

运行规则从当前 `${CLAUDE_PLUGIN_ROOT}` 下读取，附属 Markdown 的相对路径按所在文件解析。绝不从个人旧技能或另一平台读取缺失规则。模型策略中的角色路径也指向本插件，安装路径变化不影响规则定位。

默认 `dev-qa/dev-researcher` 为 `sonnet`，其余为 `opus`；dev-researcher 强度 `medium`，其余 `high`。用户明确要求优先，模型别名要结合实际提供方与调用证据核验，不能仅凭别名宣称全球最新。疯狂模式仅为需要的角色核验当前最强通用开发模型，不静默降低其他约束。

默认/疯狂模式分别保存核验时间与相关配置指纹，72 小时后重新核验；一次模式刷新不能替另一模式续期。缓存只保存脱敏证据：

| 数据 | 位置 |
| --- | --- |
| 模型核验缓存 | `~/.claude/cache/expert-team/expert-model-cache.json` |
| 历史失败诊断 | `~/.claude/state/expert-workflows/<repo-key>/known-failures.json` |
| 默认任务 ledger | 项目 `.expert-workflow/claude/<task-id>/state.md` |

缓存不随包预填，不读取其他平台模型目录。没有必要模型、强度或独立角色能力时报告阻断。图谱工具可选，必要测试和当前源码证据不可替代。

## 验证

```bash
claude plugin validate .
claude plugin validate packages/claude
```

以上在仓库根执行。清单校验之外还要实际安装、检查组件清单。隔离演练由 `tests/host_smoke.py` 完成：创建空用户目录和独立 Claude 配置，只在子进程使用它，不读取个人登录或写入真实安装。结果见 [验证报告](../../docs/validation.md)。

参考：[市场与子目录插件](https://code.claude.com/docs/en/plugin-marketplaces)、[插件路径与组件](https://code.claude.com/docs/en/plugins-reference)、[模型配置](https://code.claude.com/docs/en/model-config)。

## 个人目录安装与同步（插件方式的替代方案）

需要 Python 3.11+。在仓库根执行 `python3 packages/claude/install.py install --dry-run`，确认预览后执行 `install`、`check`；Windows 将解释器换为 `py -3 -X utf8`。只拿到本端目录时可在该目录调用 `python3 install.py`，无需 Codex 包。

目标为 `~/.claude/agents` 和 `~/.claude/skills`（含 `dev-shared`）；使用 `/dev-quick-fix` 等不带插件前缀的入口。安装器将插件资源路径与命名空间转换为个人形式，质量/模型/路由规则仍来自同一 Claude 源码。不要同时启用插件版和个人版；非默认 `CLAUDE_CONFIG_DIR` 不支持个人自动安装。

更新前执行 `check` 检查本机与包的差异，审阅后再 `install`、`check`。未登记同名文件或被改动的文件默认拒绝覆盖；`install --replace` 会备份后接管。卸载用 `uninstall`，不会清除缓存/状态或无关配置。清单在 `~/.claude/expert-team/install-manifest.json`，备份在相邻 `backups` 目录。

手动安装先用 `install --home <空暂存目录>` 生成个人形式，再复制其中 `.claude/agents` 和 `.claude/skills` 的本团普通文件；后续用安装器接管才能做受管校验。不要将个人形式直接覆盖回插件源码；在本端包维护，安装器负责路径转换。具体见[根 README 的维护说明](../../README.md#手动复制与本机同步)。

## 3.1.0：按需性能与 UI 实现验证

保持 8 角色、4 技能；仅涉及性能目标、退化或改善主张时读取 [性能协议](skills/dev-shared/expert-performance.md)，需要时使用 [轻量记录](skills/dev-shared/expert-performance-record.md)。要求有来源的目标、可比的前后测、原始样本及正确性/资源护栏；缺证据不宣称改善，普通任务不默认压测。项目工具和现有专项 skill 按实际能力复用，无新增工具安装依赖。

收到既有产品设计/审查输入时使用 [UI 实现回执](skills/dev-shared/expert-ui-verification.md)，按页面/状态/视口/版本核验并回传事实；不重新裁决产品价值或依赖产品包。完整复制 `dev-shared`，三份新增共享资源均由安装器预检；受管 3.0.0 安装沿原命令更新，保留备份和本机修改冲突保护，2.0.1 迁移兼容边界不变。

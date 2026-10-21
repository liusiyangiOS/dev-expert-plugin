# 开发专家团 · Claude Code 与 Codex

把需求开发、根因诊断、条件式快速修复和提交前检查组织成可验证的专家协作流程。每端包含 **8 个专家角色、4 个 skill**；按任务复杂度选节点，准确性优先，必要验证不因快修而省略。

**同仓库、独立发行。** `packages/claude` 与 `packages/codex` 各自包含完整角色、规则和模型策略；运行时互不读取，不使用软链接或硬链接，不共享模型缓存。安装一端不要求安装另一端。

同一套包提供 Windows 原生、WSL2、macOS、Linux 的平台适配，不另建 Windows 专家团。**跨平台处理已加入；目前实际宿主验收在 macOS 完成，Windows/Linux CI 与实机结果尚未取得。** [平台安装与验证范围](docs/platforms.md) 说明手动复制位置、PowerShell 命令、路径与工具前提。

## 选择平台并安装

| 平台 | 安装方式 | 完整文档 |
| --- | --- | --- |
| Claude Code | 原生插件市场，或独立个人目录安装器 | [Claude 安装、更新与使用](packages/claude/README.md) |
| Codex | Python 安装器复制角色与技能，默认不覆盖已有同名文件 | [Codex 安装、更新与使用](packages/codex/README.md) |

### Claude Code

本地准备版本为 2.0.1；发布到 GitHub 后，在 Claude Code 中执行：

```text
/plugin marketplace add liusiyangiOS/dev-expert-plugin
/plugin install dev-expert-plugin@dev-expert
```

新开会话后使用：

```text
/dev-expert-plugin:expert-team-review 实现这个需求：目标…约束…验收标准…
/dev-expert-plugin:bugfix-pipeline 修复这个问题：复现…预期…实际…
/dev-expert-plugin:quick-fix 修复这个局部问题，先判断快修准入条件。
/dev-expert-plugin:post-coding-pipeline 检查当前改动，不修改、不提交。
```

更新：`/plugin marketplace update dev-expert`，然后 `/plugin update dev-expert-plugin@dev-expert`，再新开会话。

**验证尚未发布的本地版本**：终端执行 `claude plugin marketplace add /absolute/path/to/dev-expert-plugin`，再执行 `claude plugin install dev-expert-plugin@dev-expert`；临时加载可用 `claude --plugin-dir /absolute/path/to/dev-expert-plugin/packages/claude`。这里的路径要替换为自己的 checkout，不要同时加载同名插件的多个版本。

Windows PowerShell 中可在仓库根执行 `claude plugin marketplace add "$((Get-Location).Path)"` 后安装；临时加载为 `claude --plugin-dir ".\packages\claude"`。本包角色适配宿主实际提供的 Bash/PowerShell。应整体加载插件，不把 `${CLAUDE_PLUGIN_ROOT}` 版角色/技能单独摊平到个人目录。

### Claude 个人目录安装（与插件方式二选一）

适合已有 `~/.claude/agents`、`~/.claude/skills` 安装的使用者。需要 Python 3.11+；在本仓库 checkout 根目录执行：

```bash
python3 packages/claude/install.py install --dry-run
python3 packages/claude/install.py install
python3 packages/claude/install.py check
```

Windows PowerShell：

```powershell
py -3 -X utf8 .\packages\claude\install.py install --dry-run
py -3 -X utf8 .\packages\claude\install.py install
py -3 -X utf8 .\packages\claude\install.py check
```

安装器把同一 Claude 包转换为个人目录形式：角色、四个技能、全部 `_shared` 规则都在当前用户 `.claude` 下；只转换资源路径和调用命名空间，质量规则保留。使用 `/expert-team-review`、`/bugfix-pipeline`、`/quick-fix`、`/post-coding-pipeline`，不带插件前缀。不同时启用本团插件和个人安装。非默认 `CLAUDE_CONFIG_DIR` 暂不支持此安装方式。

同名文件或本机改动默认阻止覆盖；审阅后使用 `install --replace` 才备份替换。更新重复 `install`、`check`，卸载用 `uninstall`；缓存、历史失败和全局设置不变。

### Codex

要求 Python 3.11+，以及支持独立 TOML 自定义角色、技能发现和子 Agent 的 Codex。

```bash
git clone https://github.com/liusiyangiOS/dev-expert-plugin.git
cd dev-expert-plugin
python3 packages/codex/install.py install --dry-run
python3 packages/codex/install.py install
python3 packages/codex/install.py check
```

Windows PowerShell 在仓库根使用已核验的 Python 3.11+（没有 `py` 时改用实际 `python` 命令）：

```powershell
py -3 -X utf8 .\packages\codex\install.py install --dry-run
py -3 -X utf8 .\packages\codex\install.py install
py -3 -X utf8 .\packages\codex\install.py check
```

更新/卸载使用同一解释器调用 `install`/`uninstall`。路径按当前用户解析；Windows 的角色在 `%USERPROFILE%\.codex\agents`，技能在 `%USERPROFILE%\.agents\skills`，`_shared` 在该 `skills` 内。中文/空格路径按完整参数处理，不写死作者目录。

上述 GitHub 命令需要新版已发布；当前本地审阅直接在本 checkout 执行 Python 命令即可。角色安装至 `~/.codex/agents`，技能及本端规则安装至 `~/.agents/skills`；Claude 包不读取这个目录。不改全局配置、凭据、无关文件，也不创建链接。有同名文件时先停止，确认需要替换后加 `--replace`，安装器会保存原文件备份。

新开 Codex 会话，在聊天中输入：

```text
$expert-team-review 实现这个需求：目标…约束…验收标准…
$bugfix-pipeline 修复这个问题：复现…预期…实际…
$quick-fix 修复这个局部问题，先准入，不满足就升级。
$post-coding-pipeline 检查当前改动，不修改、不提交。
```

更新：在 checkout 执行 `git pull --ff-only`，然后再次 `install`、`check`。卸载：`python3 packages/codex/install.py uninstall`。被用户修改的受管文件默认不会覆盖/删除。非默认 `CODEX_HOME` 暂不支持自动安装，详见本端文档。

## 手动复制与本机同步

**可以手动复制，但必须复制完整本端包并保持目录结构。** macOS 的 `~` 与 Windows 的 `%USERPROFILE%` 均指实际 Agent 用户主目录；WSL 使用其 Linux 用户目录。

| 安装方式 | 复制内容与目标 |
| --- | --- |
| Codex | `packages/codex/agents` 内文件 → `~/.codex/agents`；`packages/codex/skills` 内所有目录（含 `_shared`、references 等）→ `~/.agents/skills` |
| Claude 插件 | 保留完整 `packages/claude`，通过市场或 `claude --plugin-dir <包目录>` 加载；不要直接摊平到个人目录 |
| Claude 个人目录 | 先用本端安装器 `install --home <空的暂存目录>` 生成，再将暂存目录中 `.claude/agents` 和 `.claude/skills` 的本团文件复制到用户 `.claude` 下；不要复制备份或其他个人数据 |

手动复制不会自动建立本机安装清单，`check` 不会把未登记文件判为受管安装。需要后续可校验、可备份更新时，用对应安装器 `install --replace` 接管。普通复制即可，不使用软链接或硬链接，不覆盖无关角色/技能。

**维护以仓库 `packages/<平台>` 为源码基准，修改后再安装到本机。** Codex 安装内容与包逐字节一致；Claude 个人版与安装器生成的内容逐字节一致，插件版保留插件路径，所以两种 Claude 形式不能直接互相覆盖。两端角色、策略和缓存仍完全独立。

在更新仓库前、改完本机文件后，都可在仓库根运行以下检查；Windows 将 `python3` 换成 `py -3 -X utf8`：

```bash
python3 packages/codex/install.py check
python3 packages/claude/install.py check
```

第二条用于 Claude 个人安装；插件版由插件管理器更新，不在缓存目录直接改源码。检查会报告缺失、被修改、版本不一致的受管文件。**如果曾在实际安装目录改过内容，先审阅这些差异并把需要保留的修改合入对应包，再安装；不要整目录反向覆盖仓库。** `install` 默认拒绝覆盖被改过的文件，只有显式 `--replace` 才备份替换；备份分别在 `~/.codex/expert-team/backups`、`~/.claude/expert-team/backups`。这不是后台双向同步，修改后需主动校验和安装。

## 模型自动选择与更新

**通常无需自己追踪新模型或手改型号。** 每次调用专家团时，主理人按本端策略检查用户指定、账号/宿主可用模型与缓存；正常缓存最长使用 72 小时，到期、失效或实际调用拒绝时重新核验，再用于本次专家分配。Codex 根据当前可用模型目录与官方信息解析型号；Claude 默认使用宿主模型别名并核验提供方映射，默认/疯狂模式分别记录有效期。

这是**调用时检查、按策略刷新**，不是后台实时监听，也不保证新模型发布瞬间切换。用户显式指定优先，不擅自更换主对话模型，不自动升级 CLI。模型权限不足、提供方映射或家族命名变化、无法取得可靠依据时会明确报告，必要时需要处理；不会为了完成任务悄悄降档。模型缓存不随安装包发布，也不会因更新源码被重置。

## 四个流程与八个角色

| Skill | 用途 |
| --- | --- |
| `expert-team-review` | 需求研发；按风险选择调研/计划/实现/测试/审查节点，以任务依赖图编排 |
| `bugfix-pipeline` | QA 复现、根因定位、最小修复、回归与审查；支持偶发问题受控诊断 |
| `quick-fix` | 有根因证据、影响局部、低风险且可可靠验证的条件式快修 |
| `post-coding-pipeline` | 构建、测试、独立审查和最终快照核对；默认只检查，不自动修复或提交 |

| 角色 | 职责 |
| --- | --- |
| `team-lead` | 唯一调度、任务图、责任分配、状态和证据验收，不代写业务实现 |
| `researcher` | 技术与方案调研，区分事实和推断 |
| `planner` | 方案、依赖、契约、风险与验收映射 |
| `dev` | 在指定范围实现和修复，保留回归保护 |
| `debugger` | 复现与根因诊断，不以猜测代替因果证据 |
| `qa` | 按需求独立验收、影响矩阵和失败归属；仅获分配时改测试 |
| `code-reviewer` | 审符合性、正确性与质量，只读审查 |
| `security-auditor` | 按实际风险检查信任边界、敏感数据、执行与依赖安全 |

### 保留的质量规则

- **快修严格准入**：主动调用也先判断；首次修复失败、复杂或不确定立即升级完整 bugfix，同一问题禁止回切。完整 bugfix 可以简化合格局部实现，但不撤销原有必要关卡。
- **根因与独立验收**：局部行为修复保留真实 red→green、相关边界、独立 QA/review。机械改动按实际语义判断，不能靠弱化测试制造通过。
- **有界回修**：完整 bugfix 最多三次生产修复尝试（含初次），QA 自修最多两轮，测试通过后的审查定向回修最多一轮；升级、恢复和换人不清零。需求流程初次实现后最多两轮生产回修。
- **图谱辅助且核验源码**：区分代码关系图与任务依赖图；检查图的新鲜度与动态调用盲区，缺失时回退源码检索，不强制安装图数据库或执行引擎。
- **复用历史诊断，必要测试照跑**：按精确 case、失败签名、基线、关联输入与环境匹配，默认 30 天复核；变化、过期或恢复后复发重查。历史失败仍计入 failed，不伪造全绿，不绕过 CI 硬门禁。
- **证据绑定最终版本**：包含未提交/新文件内容、测试配置和环境；相关变化使旧证据失效。单一调度者维护累计预算和恢复记录。
- **动态模型选择**：各端独立核验模型，保留默认/疯狂模式、72 小时刷新、用户覆盖与真实调用证据；不能为了速度静默降档。

这些是 Agent 执行协议，不是确定性工作流引擎、自动 CI 失败过滤器或零缺陷保证。必要工具、模型或验证缺失时明确阻断。技能本身不授予提交、推送、部署权限。

## 推荐搭配的 Skills / 插件

全部可选，**不是安装前提，也不承诺安装后自动更快或更准确**。先用宿主和项目已有能力，明确缺口再添加；两端分别配置，不通过另一端安装目录复用。以下依据上游文档核对于 2026-10-20。

| 工具 | Claude Code 建议 | Codex 建议 | 何时值得加 |
| --- | --- | --- | --- |
| [gstack](https://github.com/garrytan/gstack#other-ai-agents) | 可选增强；上游列为 full 支持 | 可选试用；上游列为 experimental，部分安全技能是提示约束，不能当作 Claude hook 的等价拦截 | 浏览器验收、视觉检查、产品/设计评审等专项能力 |
| [Serena](https://github.com/oraios/serena) | 大仓库按需 | 同样按需；已有可靠符号检索时不必重复安装 | LSP 符号定位、引用检索与影响分析；支持程度取决于项目语言 |
| [Context7](https://github.com/upstash/context7) | 经常使用第三方库时按需 | 同样按需；不是 Codex 专属必需组件 | 查询与实际依赖版本匹配的文档，仍须核对版本和一手资料 |
| [MobileBuildMCP（原 XcodeBuildMCP）](https://github.com/getsentry/MobileBuildMCP) | Apple 项目按需 | Apple 项目按需；已有 XcodeBuildMCP CLI/skill 时先复用 | iOS/macOS 构建、测试、模拟器与 UI 验证；非 Apple 项目不需要 |
| [Playwright MCP](https://github.com/microsoft/playwright-mcp) | Web 项目按需 | Web 项目按需；已有浏览器自动化或可靠 E2E 时不必叠加 | 交互验证、浏览器状态与用户路径；项目持续回归仍用自己的测试套件 |
| [claude-mem](https://github.com/thedotmack/claude-mem) | 确有跨会话记忆需求再选 | 默认不需要；上游现在也提供 Codex 支持，不能因为名字就判定不兼容 | 长期项目历史检索；需另行配置，不是本团历史失败协议的依赖 |

### gstack 如何搭配

建议加入推荐项，定位为**专项能力补充**。不要让 gstack 与本团同时编排完整开发/修复流程，也不要把两个 QA/review 流程机械串起来重复验证。只读检查场景优先选只读能力，不能因为外部 skill 会修复、提交或部署就自动扩大授权。

上游提供 `./setup --host claude` 和 `./setup --host codex`；按所需端显式选择，不使用自动给所有宿主安装的方式。Codex 的命令命名、模型选择与 hook 支持和 Claude 不完全相同；具体安装前提及升级行为以其 README 为准。外部评审功能可能需要另一平台已登录的 CLI，这属于该可选功能的额外依赖，不是专家团依赖。

### claude-mem 是否需要

**运行 Codex 专家团不需要 claude-mem，Claude 专家团也不需要。** 已知失败复用通过本团自己的持久记录实现。claude-mem 当前已支持多个宿主，若确实需要通用跨会话检索可以单独评估，但不能把记忆当作当前源码、测试通过或授权的证明，也不要自动启用跨宿主记忆共享。该插件不随本仓库安装。

## 目录与维护

```text
.claude-plugin/marketplace.json   # Claude 市场入口
packages/claude/                 # 自包含 Claude 插件
packages/codex/                  # 自包含 Codex 安装包
  install.py
docs/                           # 迁移记录、能力对照和验证结果
tests/                          # 安装边界、引用、宿主加载验证
```

各端 `_shared` 仅表示本端内部共用。可一起维护功能要求，也可分别修改模型适配；运行时不能引用另一包。发布前同时核对 [能力对照与来源](docs/migration.md)、[验证报告](docs/validation.md)。只同步明确的源码清单，绝不复制整个个人配置目录、账号模型缓存、认证文件、会话、日志或历史失败数据。

当前仓库未附许可证；本次整理不替维护者作出新的授权选择。正式对外发布前应补充选定许可证。本地安装/校验完成不代表已提交、推送或发布。

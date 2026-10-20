# Codex 开发专家团

独立的 8 个角色、4 个 skill，以及本端模型解析程序和执行规则。不需要安装 Claude，也不读取 Claude 配置。`skills/_shared` 只在 Codex 包内部使用。

## 前提

- 支持独立 `~/.codex/agents/*.toml` 自定义角色、技能发现和子 Agent 委派的 Codex。旧版只有 `config_file` 注册方式时先升级客户端；本包不重写旧版全局配置。
- Python 3.11+，用于安装、模型目录解析及本地测试。
- 当前账号可调用策略需要的模型和推理强度；安装成功不代表账号拥有所有模型。
- 项目自身的构建、测试工具按项目需要准备。

依据：[自定义角色](https://learn.chatgpt.com/docs/agent-configuration/subagents)、[技能发现与显式调用](https://learn.chatgpt.com/docs/build-skills)。本包采用用户级普通文件安装，包含技能之外的角色；不是 Claude 插件安装命令。

## 安装

从仓库根目录执行：

```bash
python3 packages/codex/install.py install --dry-run
python3 packages/codex/install.py install
python3 packages/codex/install.py check
```

也可以只复制 `packages/codex` 整个目录到另一台机器，在该目录运行 `python3 install.py install`，不需要仓库其他目录。

安装器复制：

| 内容 | 用户目录 |
| --- | --- |
| 8 个 TOML 角色 | `~/.codex/agents/` |
| 4 个完整 skill、内部规则与解析器 | `~/.agents/skills/` |
| 安装清单及必要备份 | `~/.codex/expert-team/` |

不会修改 `config.toml`、`AGENTS.md`、凭据或无关技能。不会创建软链接/硬链接，不读取另一端包。安装完成新开 Codex 会话，让角色和技能重新加载；自动路由由宿主判断，不是后台自动化。

**已有同名文件时默认停止，且不会部分覆盖。** 确认要用本发行包替换后，执行：

```bash
python3 packages/codex/install.py install --replace
```

原文件会备份到安装器打印的目录，修改过的已安装文件也受同样保护。共享 `_shared` 目录中的无关文件不删除。

当前安装器支持默认用户布局。设置了非默认 `CODEX_HOME` 时会拒绝默认安装，避免角色与模型目录落到错误位置。不要为绕过检查直接换环境变量；需要先适配本包路径和模型目录策略，再验证自定义布局。

## 更新、检查与卸载

在自己的仓库副本中更新代码后重新执行安装；安装器只更新自己管理且未被本地修改的文件，移除包中已经废弃的受管文件，并保留备份：

```bash
git pull --ff-only
python3 packages/codex/install.py install
python3 packages/codex/install.py check
```

存在本地修改时先查看差异，需要替换才加 `--replace`。`check` 对照当前 checkout 的内容与安装清单，失败不代表历史版本一定损坏，也可能只是尚未更新。

```bash
python3 packages/codex/install.py uninstall --dry-run
python3 packages/codex/install.py uninstall
```

卸载只处理安装清单列出的文件；不删除其他技能、模型缓存、历史诊断和备份。被修改的文件默认保留并阻止卸载，明确备份后卸载可加 `--replace`。空目录可以保留。

若要恢复安装前文件，从打印的备份目录 `files/` 按相同相对路径还原，结合备份 `manifest.json` 核对当时新增/原有文件；不要整目录覆盖用户后续改动。

## 使用

在 Codex 输入（`$` 是技能调用语法，不是终端命令）：

```text
$expert-team-review 实现这个需求：背景…目标…约束…验收标准…
$bugfix-pipeline 修复这个问题：复现步骤…预期…实际…日志…
$quick-fix 修复这个局部问题；先判断是否满足快修条件，不满足就升级。
$post-coding-pipeline 检查当前改动，不修改、不提交。
```

也可以明确派 `researcher` 调研、派 `code-reviewer` 只读审查。工作流中的专业成员不再自行创建团队。

快速修复主动调用也必须先准入。复杂、不确定或首次快修失败立即升级，同一问题锁定完整 bugfix。完整 bugfix 中合格局部实现可以快修，但原 QA 复现、debugger 根因门、最终 QA 和必要审查不能省略。

## 模型与持久状态

默认 `qa/researcher` 使用经核验的最新可用 Terra，其他角色使用最新可用 Sol；researcher 为 `medium`，其余为 `high`。疯狂模式的其他角色使用当前经核验的最强通用开发模型。用户明确模型/强度优先，不静默换低档。型号由实际目录和官方资料确认，不随包提供个人账号缓存。

```text
用 bugfix-pipeline 的疯狂模式处理这个问题：…
用 expert-team-review，所有专家使用我指定的模型 <实际可用模型 ID>，强度 high：…
```

解析器用当前账号模型目录，72 小时失效后重新核验；不会自动升级 CLI。查看缓存状态（缺失/过期时非零退出是预期结果）：

```bash
python3 ~/.agents/skills/_shared/expert_models.py status
```

模型缓存：`~/.cache/codex-expert-workflows/expert-model-cache.json`。历史失败：默认 `~/.local/state/expert-workflows/<repo-key>/known-failures.json`。任务 ledger 默认在项目 `.expert-workflow/<task-id>/state.md`。这些是运行数据，不进本仓库、不与 Claude 同步。

图谱、AST、LSP 可选；缺少图谱时回到精确源码检索。历史失败复用的是经过核验的诊断，必要测试仍运行，变化/过期/恢复后复发要重查。

## 验证与限制

隔离安装演练：

```bash
test_user_dir="$(mktemp -d)"
python3 packages/codex/install.py install --home "$test_user_dir"
python3 packages/codex/install.py check --home "$test_user_dir"
python3 packages/codex/install.py uninstall --home "$test_user_dir"
```

`--home` 是模拟用户目录，不会切换当前 Codex 会话。自动化宿主发现测试见仓库 `tests/host_smoke.py`；完整测试结果见 [验证报告](../../docs/validation.md)。

安装与宿主发现通过，只说明文件、角色、技能可加载；真实任务仍依赖当前账号、模型、项目测试和权限。缺少必要委派能力时如实阻断，不能用主 Agent 自审代替独立验收。

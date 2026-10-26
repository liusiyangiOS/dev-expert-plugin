# 3.0.0 命名迁移验证记录

日期：2026-10-26（Asia/Taipei）。基线：`5658436eb04d837586bc5a3e4faa97b15e67ef72`；分支：`feature/1026/dev-expert-namespace`。变更尚未提交、推送或发布。2.0.x 历史原文单独保留在 [validation-2.0.1.md](validation-2.0.1.md)，其旧名称和当时结果不用于证明新版。

## 结果

| 检查 | 实际结果 |
| --- | --- |
| 发行/迁移/命名契约测试 | 54 项：39 通过、15 跳过、0 失败 |
| 模型策略测试 | 19 项全部通过；输出只含 8 个新角色键，默认/疯狂/用户覆盖规则保留 |
| Skill 元数据 | Codex 与 Claude 合计 8 个 skill 全部通过 quick_validate.py |
| 活跃引用与源清单 | 两端实际安装 payload 无裸旧角色、技能或共享目录引用；45 条来源清单当前目标及哈希匹配，历史 source 字段保留 |
| Claude 真实宿主 | 隔离市场安装、发现 8 角色/4 技能、文件字节一致、更新、卸载通过 |
| Codex 真实宿主 | 隔离上下文发现 4 新技能；本机回环捕获的原生委派工具包含 8 新角色 |
| 旧聊天恢复探针 | 同一隔离 Codex CLI 聊天在进程退出、2.0.1→3.0.0 安装迁移、resume 后发现 8 新角色/4 新技能 |
| 独立审查 | 代码审查、安全审查均通过，无阻断发现；未修改生产代码 |
| 本机安装 | Codex 与 Claude 个人版均已迁移到 3.0.0，check 与逐文件 SHA-256 通过；全部旧版受管文件已清理并备份 |
| 配置保护 | 抽查的全局配置、规则和专家团模型缓存安装前后 SHA-256/存在状态一致 |
| 路径/格式 | 包与现用安装路径审计、git diff --check 通过 |

合计 **58 个自动测试通过、15 个平台专属测试跳过**。元数据校验和宿主探针单独列示，不重复计入自动测试总数。

实际环境：macOS 26.3.1 arm64、Bash、Python 3.14.6、Claude Code 2.1.201、Codex CLI 0.164.0-alpha.11.1。

## 迁移保护与新增回归

新增 10 个迁移测试，覆盖双端完整旧安装升级、备份与清理、旧文件被修改、无安装清单的同名文件保留、新名称冲突无部分写入、旧清单身份/版本/路径/哈希拒绝、写文件和写清单失败回滚、链接保护、独立包和中文/空格路径等场景。

`tests/fixtures/legacy-2.0.1.json` 保存基线真实完整载荷：Codex 28 文件逐字节等于基线；Claude 20 文件等于基线安装器当时的个人版渲染。测试运行不依赖 Git 历史或另一个平台包。不能用改名后的文件逆向替换来冒充真实旧版本。

新增 5 个命名契约测试，覆盖角色文件名与内部身份、技能目录与 UI 调用、模型输出角色键、安装器实际 payload 旧引用残留、来源清单历史与当前字段。原有资源链接、平台隔离、安装生命周期和模型策略测试继续执行。

Windows 的 `.cmd`/PowerShell 入口沿用同一个已更新的 Python 安装器；相关测试期待的新角色路径、CI 中模型测试目录也已更新。15 个跳过项为原生 Windows junction 和 PowerShell 启动器测试。本次没有 Windows 主机，未运行 Windows/macOS/Linux 远端 CI，不能称 Windows 真机已验收或 Windows 本机已安装。

## 本机安装结果

当前机器原有两端均是受管 2.0.1，升级前 check 完整；Claude 未登记本专家团插件版，实际更新的是其个人安装，不额外安装第二份插件。

- Codex：28 个新载荷文件；旧 28 个受管文件移除；安装器报告 56 个变更。
- Claude：20 个新载荷文件；旧 19 个角色/技能文件移除，稳定位置的个人安装 README 更新；安装器报告 39 个变更。
- 新安装清单均为 3.0.0，所有目标哈希与当前包（Claude 为个人版渲染）相同。
- 旧名称兼容数据仅留在备份、迁移白名单、历史文档与 fixture；不提供无前缀活动别名。空旧目录可以保留。
- 备份相对用户目录：`.codex/expert-team/backups/20261026T072901556316Z`、`.claude/expert-team/backups/20261026T072905167393Z`。
- 受保护哈希记录保存在未纳入版本控制的 `.test-artifacts/namespace-3.0.0/`，不包含配置或凭据正文。

## 已有聊天的证明边界

官方 [技能文档](https://learn.chatgpt.com/docs/build-skills) 说明技能变更可自动发现，未出现时重启；[专家文档](https://learn.chatgpt.com/docs/agent-configuration/subagents) 说明角色以文件内 name 为身份。

`tests/codex_reload_probe.py` 实测 CLI 进程重启并恢复同一保存的 thread 后读取新名称，支持“可以保留聊天历史并重新加载”的 CLI 场景。该探针仅向隔离的本机回环服务发请求，服务固定返回 HTTP 400；这证明加载和工具注册，不证明模型业务任务执行。

真实桌面当前聊天在安装后尝试创建 `dev-researcher`，工具返回 `unknown agent_type 'dev-researcher'`。因此不能认为改完磁盘文件就已经让当前聊天使用新角色。没有为了测试而重启用户正在工作的 ChatGPT，也未验证重启后该桌面聊天的角色列表。建议完全退出并重启应用后回到原聊天，先核对新角色/技能是否实际可用，再继续任务；不能承诺所有宿主版本都不需要新聊天。

## 重启后的原桌面聊天补充验收

2026-10-26，用户完全重启 ChatGPT 后回到同一聊天：工具定义已列出全部 8 个 `dev-` 自定义角色，技能目录已列出全部 4 个新版技能。主任务读取了现用 `dev-expert-team-review/SKILL.md`，并按现用模型策略实际创建 `dev-researcher`（gpt-5.6-terra / medium，任务 `restarted_role_probe`）；创建成功，子专家完成并返回“dev-researcher 调用成功”。该探针不调用其他工具、不读写文件。

这补齐了上节当时尚未验证的桌面原聊天场景：本次用户的重启确实刷新了专家列表，且新角色实际可调用，无需为使用新版而另开聊天。上节 `unknown agent_type` 是重启前的历史结果。该证据不扩大为所有宿主版本保证，也不等同于八个角色分别执行完整业务流程。

## 旧安装目录清理

2026-10-26，经用户要求，复查本机两端旧技能目录：旧 `SKILL.md` 和受管资源已经由迁移安装器删除，剩余仅为空目录及少量 `.DS_Store`。确认不存在其他文件或链接后，清理 `.agents/skills` 和 `.claude/skills` 下四个旧技能目录及旧 `_shared`，共 10 个目录。新版安装载荷和备份保持完整。

## 复跑命令

在仓库根执行，Windows 使用已核验的 Python 3.11+（如 `py -3`）替代 `python3`：

```bash
python3 -X utf8 -m unittest discover -s tests -p 'test_*.py' -v
python3 -X utf8 -m unittest discover -s packages/codex/skills/dev-shared -p 'test_expert_models.py' -v
python3 -X utf8 tests/audit_paths.py --installed
python3 -X utf8 tests/host_smoke.py --codex-wire
python3 -X utf8 tests/codex_reload_probe.py
python3 packages/codex/install.py check
python3 packages/claude/install.py check
git diff --check
```

宿主测试使用空用户目录，不复制个人凭据、不连接真实个人 app-server。回环服务需要允许本机监听的执行环境；本次首次在限制环境因 bind 权限失败，授权同一隔离测试后通过，不计作产品失败。未用线上模型跑四种完整业务流程；Windows、Linux、WSL 原生宿主和重启后的既有桌面聊天仍未验收。

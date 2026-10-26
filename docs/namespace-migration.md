# 3.0.0：开发专家团名称迁移

2026-10-26。本版本统一使用 `dev-` 团队前缀。这是调用名称不兼容升级；Codex、Claude 插件和 Claude 个人安装使用相同的基础名称。

## 名称契约

| 2.0.1 历史名称 | 3.0.0 名称 |
| --- | --- |
| `team-lead` | `dev-team-lead` |
| `planner` | `dev-planner` |
| `researcher` | `dev-researcher` |
| `dev` | `dev-developer` |
| `debugger` | `dev-debugger` |
| `qa` | `dev-qa` |
| `code-reviewer` | `dev-code-reviewer` |
| `security-auditor` | `dev-security-auditor` |
| `expert-team-review` | `dev-expert-team-review` |
| `bugfix-pipeline` | `dev-bugfix-pipeline` |
| `quick-fix` | `dev-quick-fix` |
| `post-coding-pipeline` | `dev-post-coding-pipeline` |
| `skills/_shared/` | `skills/dev-shared/` |

角色文件名、内部 `name`、工作流委派类型、模型解析输出键、技能目录与 `name`、UI 默认 prompt、共享引用、历史 JS 示例中的名称、安装器白名单、测试、Windows 命令示例和 CI 路径同步更新。`dev-shared` 仅为共享资源目录，不含 `SKILL.md`，不会多注册一个技能。

Codex 入口为 `$dev-quick-fix` 等；Claude 个人版为 `/dev-quick-fix` 等；Claude 插件版为 `/dev-expert-plugin:dev-quick-fix` 等，角色全名为 `dev-expert-plugin:dev-researcher` 等。插件 ID 与市场 ID 不变，避免把改名误作第二个插件安装。

生产修复路由同步从历史 `ROUTE=dev` 改为 `ROUTE=dev-developer`。恢复旧任务记录时，调度者按上表解释旧角色和路由，记录本次名称转换；继续沿用原有尝试次数、证据有效性与权限，不重置预算，不按旧角色名创建专家。

## 受管安装升级

更新仓库后，使用各端已有安装入口依次执行 `install --dry-run`、`install`、`check`。Windows 的 `install-windows.cmd` 仍调用同一个 Codex Python 安装器，默认依次执行上述三个阶段。Claude 个人版使用 `packages/claude/install.py`；插件版使用插件管理器更新，不能用个人安装器改插件缓存。

- 迁移只接受匹配本端包身份和受支持版本的历史安装清单，旧路径使用精确白名单。
- 属于清单且内容未变的旧文件，备份后移除；新文件写入后，安装清单只保留新版路径。
- 旧受管文件被修改、新名称已被其他内容占用、路径越界或链接异常，均在写入前阻止升级。审阅差异后，可用 `install --replace` 备份替换已确认的冲突。
- 没有登记的旧同名文件不会因文件名匹配而被删除。它们可能属于其他专家团；手动安装升级需要先核对归属和内容。空旧目录可能保留，不代表旧角色或技能仍注册。
- 写入失败回滚载荷和清单；备份不参与技能发现。缓存、历史失败记录、全局配置保持原位置，不为了名称排序迁移运行状态。

不提供无前缀运行别名，避免继续占用公共名称。安装器兼容代码、旧版测试夹具、历史记录和 `source-manifest.json` 的 `source` 字段会有意保留旧名；它们不是新版运行引用。来源清单的 `destination`、`packaged_sha256` 和 `packaged_version` 则对应新版文件。

## 在已有聊天中使用

官方说明 Codex 会自动发现技能变更；更新未出现时重启应用。自定义专家以文件内 `name` 为身份；旧聊天上下文或已启动的子专家仍可能保留旧说明。安装文件正确不等于当前聊天已刷新角色工具列表。

可先结束正在执行的旧工作，完全退出并重新启动 ChatGPT/Codex，再回到原聊天，明确要求使用 `dev-` 版并核对可用角色和技能。只有当前工具列表实际包含新角色，且加载的是新版技能，才能确认该聊天已切换；不把“重启”本身当作验证通过。已运行的旧子专家不作为新版继续复用。

参考：[技能发现与重启](https://learn.chatgpt.com/docs/build-skills)、[自定义专家身份](https://learn.chatgpt.com/docs/agent-configuration/subagents)。这两份文档没有保证所有桌面版的既有聊天都能在重启后刷新全部自定义角色；具体加载证据见 [验证记录](validation.md)。

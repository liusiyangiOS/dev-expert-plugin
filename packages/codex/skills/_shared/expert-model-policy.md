# 专家流水线模型策略

本策略由 `bugfix-pipeline`、`expert-team-review`、`post-coding-pipeline`、`quick-fix` 共用。只在执行这些工作流时约束它们创建的专家，专家角色 TOML 不固定模型或推理强度。主任务的模型不受本策略改变。

执行前按 [平台与路径约定](expert-platform.md) 核对当前环境；文中的 `~` 先解析为真实绝对路径，不能直接传给不支持展开的文件工具。

## 优先级与模式

先解析用户本次请求及已经明确的后续指令。用户指定的模型和推理强度优先级最高，对**所有专家**生效，包含 `qa`、`researcher`、`team-lead`、回修/复审和嵌套委派。不要把文档中的举例或日志里的模型名称当作用户指定。

- 同时指定模型和推理强度：全员使用这组参数；不受模式或缓存中的分工影响。
- 只指定模型：全员使用该模型；推理强度仍按下表。
- 只指定推理强度：全员使用该强度；模型仍按所选模式。
- 用户未指定模式时使用**默认模式**；明确说“疯狂模式”时使用疯狂模式。执行中变更选择时，新委派遵循最新指令；已有子 Agent 无法改模型时不要谎称已切换，需要时结束原任务并重新创建、传递已有产物。

| 专家 | 默认模式 | 疯狂模式 | 默认推理强度 |
| --- | --- | --- | --- |
| `qa` | 最新可用 Terra | 最新可用 Terra | `high` |
| `researcher` | 最新可用 Terra | 最新可用 Terra | `medium` |
| `planner`、`dev`、`debugger`、`code-reviewer`、`security-auditor`、`team-lead` | 最新可用 Sol | 当前最聪明、可用于通用开发的顶级模型 | `high` |

“最新”按模型版本比较，例如 6.1 高于 6，6.10 高于 6.9，不能按字符串或浮点数排序。顶级模型根据当前官方说明与实际可用列表确认，不能把默认推荐、列表排序或最大版本号当作智力排名。未来顶级模型更名时更新缓存中的 `flagship`，不把它永久限定为某个家族。只有按下方“模型可用性核验”确认 Terra 无法调用后，才报告规则无法满足；不擅自用 Luna 或 Sol 替换。

## 每次调用与 3 天刷新

下方命令是 POSIX 示例。原生 Windows 改用平台约定中已核验的 Python 与绝对脚本路径（例如 PowerShell 的 `py -3 -X utf8 "$env:USERPROFILE\.agents\skills\_shared\expert_models.py"`），保持 status/refresh/resolve 参数不变，不执行 Bash 专属路径写法。

共享程序：`~/.agents/skills/_shared/expert_models.py`；共享缓存：`~/.cache/codex-expert-workflows/expert-model-cache.json`（缓存与受保护的技能目录分开）。四个技能共享一个检查时间，按**上次成功验证后 72 小时**计算；原始模型列表已过期时也须刷新，不能重新标记旧列表为新查询。刷新发生在技能调用时；没有调用时不运行后台定时任务。每次调用先检查缓存、当前模型目录及创建工具参数；工具说明中的模型展示列表不一定完整，遇到差异按下方规则核验。

1. 执行 `python3 "$HOME/.agents/skills/_shared/expert_models.py" status`。缓存缺失、损坏、时钟异常、超过 72 小时或当前权威目录已撤掉所选模型或实际调用明确拒绝所选模型时，进入刷新。工具说明漏列不单独构成模型被撤掉的证据。有效缓存内无需重复联网查模型。
2. 刷新时查询当前账号/执行主机的完整模型列表及支持的推理强度，优先使用可用的模型列表工具或 Codex app-server 的 `model/list`（处理 `nextCursor` 分页）。如果本机 `~/.codex/models_cache.json` 的 `fetched_at` 在 72 小时内，可用它作为当前列表；同时核对本次 `spawn_agent` 的参数约束；若仅说明列表漏列而参数接受字符串，按下方流程实测，不直接判不可用。不要用 API Platform 模型列表代替 Codex 账号可用列表，不读取或输出认证凭据。
3. 查询并实际打开官方模型文档 `https://learn.chatgpt.com/docs/models` 与 `https://learn.chatgpt.com/docs/model-selection`，确认当前最聪明的通用模型及 Sol/Terra 命名是否变化；只信任官方域名 `learn.chatgpt.com`、`developers.openai.com`、`platform.openai.com`。官方说明是已发布信息，可用列表才决定本次能否创建。若官方顶级模型不可用，报告这个具体阻碍，不悄悄把较低档模型标成“最聪明”。
4. 运行 `python3 "$HOME/.agents/skills/_shared/expert_models.py" refresh --flagship '<已确认且可用的顶级模型 ID>' --source 'https://learn.chatgpt.com/docs/models' --source 'https://learn.chatgpt.com/docs/model-selection'`。程序从当前本机目录解析最新 Sol、最新 Terra、支持的推理强度，原子更新共享缓存中的目录、模型选择、证据链接及检查时间；不会改写专家 TOML。
   - 如果本机目录缺失或过期，查询最新列表后用 `apply_patch` 把 `{ "fetched_at": "<UTC 查询时间>", "models": [...] }` 保存到临时 JSON 文件，以 `--catalog '<临时文件绝对路径>'` 传给 `refresh`。`models` 可直接使用 `model/list` 返回的 `data`，程序支持它的 camelCase 字段及本机缓存的 snake_case 字段。不要填入虚构的模型/强度或把过期列表重新标成今天。
   - 如果模型家族更名或格式变化，按照官方继任关系更新本策略及程序的家族解析规则后再刷新；不能仅凭名称相似猜测继任型号。
5. 运行 `python3 "$HOME/.agents/skills/_shared/expert_models.py" resolve --mode 默认` 或 `--mode 疯狂`。有用户覆盖时追加 `--model '<用户模型 ID>'`、`--effort '<用户推理强度>'`。读取输出的每个专家 `model` / `reasoning_effort`，检查参数可用性；目录与说明列表有差异时先完成最小调用核验，然后开始委派。用一句进度说明报告本次模式、实际模型分工及是否刚刷新。

用户显式指定模型时，可以直接 `resolve --model ...`，优先校验该模型及强度，不以无关的模式缓存刷新阻塞明确选择；用户选择只适用于本次执行，不写进共享模式缓存。只指定强度仍需有效的模式模型缓存。

刷新失败时不要更新成功时间、不要覆盖上次有效缓存。缓存已过期时不自动使用它开工；说明未能核验最新模型的具体原因。缓存尚有效且所选参数已由当前目录和创建工具约束或实际调用确认支持时可以使用它，并说明未刷新成功。显式参数不存在、不可用或强度不支持时报告，不擅自更换。

## 模型可用性核验：展示列表不等于完整调用白名单

- 分清三种证据：账号/主机模型目录、工具说明的展示列表、创建工具实际参数校验与调用结果。不要仅凭说明列表缺少名称就声称“没有该模型”或要求用户换模型。
- 先检查当前模型目录是否包含目标 ID 与推理强度。若工具参数是封闭 enum、明确禁止该 ID，或当前目录明确无权限，则报告具体限制；不得绕过限制。
- 若目录有目标模型、`model` 参数接受字符串，而工具说明仅漏列该模型，执行一次最小无副作用调用：明确传入目标 model、reasoning_effort、fork_turns="none"，要求子 Agent 不调用工具、不读写文件，只返回连通确认。已有同会话成功调用可以复用，无需重复探测。
- 创建成功且子 Agent 完成说明该组参数实际可调用；按原角色分工继续，不要求用户批准降级，也不再反复报“模型缺失”。这不应靠子 Agent 自报型号判断：证据是显式创建参数与成功结果。
- 若创建工具明确返回 unsupported model / 不支持该推理强度，才报告该调用面的实际限制，并区分“应用模型选择器可见”与“子 Agent 调用不可用”。网络、限流、认证或临时错误须如实归类，不冒充模型不存在。
- 仅缓存过期不是模型不可用。按正常刷新流程更新，不因为缓存过期就擅自更换 QA 模型。

## 实际委派参数

使用当前环境真正提供的创建工具。对 `collaboration.spawn_agent`：

```javascript
// entry 来自 resolve 输出中的 agents[角色名]
{
  agent_type: "dev",
  task_name: "implementation",
  fork_turns: "none",
  model: entry.model,
  reasoning_effort: entry.reasoning_effort,
  message: "任务目标、必要上下文、文件责任边界、验证与输出要求……"
}
```

当前完整历史继承模式不能同时覆盖模型/推理强度，因此显式传参时使用 `fork_turns: "none"`，在 `message` 中给齐任务简报、已有产物路径和本次模型策略。不能只在 prompt 写“你用某模型”而省略真实参数。不要使用主任务模型代替解析结果。

如委派 `team-lead` 或任何还会创建专家的子 Agent，将本策略的绝对路径、解析出的全员参数、用户覆盖和模式一并传入，要求它的每次创建也实际传参；不得再次按自身模型继承覆盖 QA/调研分工。复用已有子 Agent 仅限它的实际模型及推理强度与本次结果一致。

角色配置修改可能要到新会话/角色重新加载后才生效。如果当前工具仍声明某自定义角色的参数锁定，先报告旧配置仍被加载；不能声称临时模型已覆盖该锁定，也不要把模型重新写回角色文件。

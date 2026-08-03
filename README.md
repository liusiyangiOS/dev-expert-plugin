# 开发专家团 · Claude Code 插件（dev-expert-plugin）

一个把「开发专家团 agents」和「开发工作流 workflows」打包成 Claude Code 插件的仓库。

它适合把复杂研发任务拆成标准链路：调研 → 计划 → 实现 → 测试 → 安全审计 → 代码审查 → 交付验收。你可以单独调用某个专家 agent，也可以直接运行封装好的工作流。

## 组成

### Agents

| 名称 | 角色 |
|------|------|
| `team-lead` | 交付总监 / 主理人，只做编排不代写：任务分诊定链路、派活四要素、计划门、证据验收 |
| `researcher` | 技术调研、竞品分析、开源项目评估；事实与推断分开、结论附来源 |
| `planner` | 方案设计与任务拆解：多方案权衡、Non-goals、每步带验证方式 |
| `dev` | 资深开发工程师，按方案落地：分步自检、bug 修复先红后绿、完成前验证附证据 |
| `debugger` | 缺陷定位专家：复现、坏值向上游追源、假设挂证据、给出精确修复点 |
| `qa` | 测试影响矩阵、边界分析、回归验证；防"假绿"测试、flaky 识别 |
| `security-auditor` | 密钥泄露、危险命令、注入、认证授权、敏感数据、供应链等安全审计 |
| `code-reviewer` | 两阶段审查：先审符合性（漏做/多做/偏离方案），再审代码质量；只给意见不改代码 |

### Workflows

| 名称 | 作用 |
|------|------|
| `expert-team-review` | 专家团全链路 SOP：调研 → 计划 → 实现 → 测试（回修环最多 2 轮）→ 验收（高危回修 1 轮再复审） |
| `bugfix-pipeline` | 缺陷修复 SOP：复现 → 定位根因 → 最小修复 → 回归验证（最多 3 轮）→ 审查（有问题回修 1 轮） |
| `post-coding-pipeline` | 编码后提交前质量门：构建 → 测试 → 审查 → 提交（便宜的机器判定先跑，任一关失败即阻断） |

### 设计原则（借鉴自社区成熟实践）

- **审方案比审代码杠杆高**：人工介入放在计划门，而不是等 100 行 diff 出来再挑错（HumanLayer Research-Plan-Implement）。
- **证据优先**：任何"完成/通过"必须附跑过的命令与关键输出，不接受口头宣称（superpowers verification-before-completion）。
- **有界反馈环**：所有回修环都有轮次上限，超限升级人工决策而不是无限重试；多轮修不好要质疑架构而不是再修一次（systematic-debugging）。
- **上下文卫生**：环间只传结构化报告，不传原始日志与搜索噪音；长产出落盘为文件按需读取（Frequent Intentional Compaction）。
- **按复杂度分诊**：简单任务不走全链路，避免过度编排烧 token（Anthropic agent-teams 指南）。
- **回归安全网**：影响面结论必须有检索证据（调用方清单）；改无测试保护的遗留代码先补特征测试锁住现状；bug 修复先红后绿；大改动拆小批、每批跑绿再进下一批（Working Effectively with Legacy Code）。

## 安装

```bash
/plugin marketplace add liusiyangiOS/dev-expert-plugin
/plugin install dev-expert-plugin@dev-expert
```

安装后，Claude Code 会加载本插件中的 `agents/` 与 `workflows/`。

## 推荐搭配的 Skills / 插件（全部可选，未安装不影响专家团运行）

生产型成员（`researcher` / `planner` / `dev` / `debugger` / `qa`）的工具表已包含 `Skill`：本机装了匹配的技能它们会自动选用；**没装就按各自 agent 文件的流程执行，不阻塞、不降级**。编排者（`team-lead`）与裁判（`code-reviewer` / `security-auditor`）刻意不开，保证审查标准稳定不被外部技能稀释。同类技能冲突时以本插件 agent 文件的规则为准。

| 名称 | 类型 | 主要受益成员 | 提升什么 |
|------|------|------------|---------|
| [obra/superpowers](https://github.com/obra/superpowers) | Skills 插件 | `planner` `dev` `debugger` `qa` | 过程纪律：brainstorming 需求澄清、writing-plans 微任务拆解、TDD（red-green-refactor）、systematic-debugging 四阶段根因分析、verification-before-completion 证据验收。与本团的铁律高度同源，是首选搭配 |
| [oraios/serena](https://github.com/oraios/serena) | MCP | `dev` `debugger` `qa` | 基于 LSP 的**符号级**代码检索（找定义/找全部引用），比 `grep` 更准。直接强化本团的核心动作——影响面评估时枚举调用方清单，大仓库尤其明显 |
| [upstash/context7](https://github.com/upstash/context7) | MCP | `researcher` `dev` | 实时拉取第三方库的**最新版本文档**，避免凭过时训练数据写出废弃 API；researcher 调研开源方案时结论更可信 |
| [cameroncooke/XcodeBuildMCP](https://github.com/cameroncooke/XcodeBuildMCP) | MCP | `dev` `qa`（iOS/macOS 项目） | 构建、跑测试、模拟器管理、UI 自动化截图/点按；让 qa 的"跑测试给证据"和 UI 层验证在苹果平台真正落地 |
| [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp) | MCP | `qa`（Web 项目） | 真实浏览器 E2E/UI 测试，覆盖本团测试分层里"用户关键路径"这一层 |
| [thedotmack/claude-mem](https://github.com/thedotmack/claude-mem) | 插件/MCP | `team-lead` | 跨会话记忆：历史决策、踩过的坑、项目约定可被检索，主理人在长期项目里不重复犯错 |

安装方式以各仓库 README 为准（Claude Code 一般为 `/plugin marketplace add` + `/plugin install`，MCP 为 `claude mcp add`）。建议按需精装、控制数量：技能装得越多，选择噪音越大。

## 典型用法

### 让专家团走完整研发链路

```text
请用 expert-team-review 工作流处理这个需求：
<写清楚需求背景、目标、约束、验收标准>
```

需求描述会通过 `args.task` 传入工作流，供调研、计划各阶段引用。

### 修一个 bug

```text
请用 bugfix-pipeline 工作流修复这个缺陷：
现象：...
复现步骤：...
期望结果：...
实际结果：...
相关报错：...
```

### 提交前做质量门

```text
请用 post-coding-pipeline 工作流检查当前改动，确保安全审计、代码审查、构建和测试都通过后再进入提交步骤。
```

### 单独派某个专家

```text
派 researcher 调研这个方案的开源实现与风险。
```

```text
派 code-reviewer 只审查当前 diff，不要改代码。
```

## 目录结构

```text
dev-expert-plugin/
├── .claude-plugin/
│   ├── marketplace.json
│   └── plugin.json
├── agents/
│   ├── code-reviewer.md
│   ├── debugger.md
│   ├── dev.md
│   ├── planner.md
│   ├── qa.md
│   ├── researcher.md
│   ├── security-auditor.md
│   └── team-lead.md
├── workflows/
│   ├── bugfix-pipeline.js
│   ├── expert-team-review.js
│   └── post-coding-pipeline.js
└── README.md
```

## 维护方式

如果本机 `~/.claude/agents` 或 `~/.claude/workflows` 后续更新，可以把对应文件同步到本仓库后发布新版本。

建议每次同步后检查：

```bash
git status
find agents workflows -type f | sort
```

确认无误后再提交并推送到 GitHub。

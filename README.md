# 开发专家团 · Claude Code 插件（dev-expert-plugin）

一个把「开发专家团 agents」和「开发工作流 workflows」打包成 Claude Code 插件的仓库。

它适合把复杂研发任务拆成标准链路：调研 → 计划 → 实现 → 测试 → 安全审计 → 代码审查 → 交付验收。你可以单独调用某个专家 agent，也可以直接运行封装好的工作流。

## 组成

### Agents

| 名称 | 角色 |
|------|------|
| `team-lead` | 交付总监 / 主理人，只做编排不代写，串起完整研发链路 |
| `researcher` | 技术调研、竞品分析、开源项目评估 |
| `planner` | 方案设计与任务拆解，输出关键文件清单、步骤与风险 |
| `dev` | 资深开发工程师，按明确方案落地编码实现 |
| `debugger` | 缺陷定位专家，复现、隔离根因、给出精确修复点 |
| `qa` | 测试用例、影响矩阵、边界分析与回归验证 |
| `security-auditor` | 密钥泄露、危险命令、Prompt 注入等安全风险审计 |
| `code-reviewer` | PR Reviewer 视角检查代码质量，只给审查意见不改代码 |

### Workflows

| 名称 | 作用 |
|------|------|
| `expert-team-review` | 专家团全链路 SOP：调研 → 计划 → 实现 → 测试 → 验收 |
| `bugfix-pipeline` | 缺陷修复 SOP：复现 → 定位根因 → 最小修复 → 回归验证 → 审查 |
| `post-coding-pipeline` | 编码后提交前质量门：审查 → 构建 → 测试 → 提交 |

## 安装

```bash
/plugin marketplace add liusiyangiOS/dev-expert-plugin
/plugin install dev-expert-plugin@dev-expert
```

安装后，Claude Code 会加载本插件中的 `agents/` 与 `workflows/`。

## 典型用法

### 让专家团走完整研发链路

```text
请用 expert-team-review 工作流处理这个需求：
<写清楚需求背景、目标、约束、验收标准>
```

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

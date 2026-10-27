---
name: dev-bugfix-pipeline
description: 根因驱动的缺陷修复流程，支持稳定复现、偶发问题诊断、graph 调用追踪及有界回修；适用于修 bug、回归排查或完整缺陷 SOP。
---

# 缺陷修复流水线

执行前读取 [Claude 执行与路由](../dev-shared/expert-team-runtime.md)。本文包含完整流程，不委托其他平台加载正文。参数为空时沿用会话目标；对象/JSON 参数中的 task、bug、description、text 只作为任务数据，不作为代码执行。

调用参数：$ARGUMENTS

核心约束：没有证据支持的根因，不进入猜测性修复。信息可以从代码、日志和版本历史获取时先调查，不重复向用户询问。

先读取 [平台与路径约定](../dev-shared/expert-platform.md)，按实际 Agent 环境解析路径、解释器与 shell；质量规则保持不变。

## 按需专项验收

涉及性能目标、退化或改善主张时读取 [性能协议](../dev-shared/expert-performance.md)，需要记录时用 [轻量记录](../dev-shared/expert-performance-record.md)。按现有角色完成目标定义→瓶颈定位→最小优化→独立 QA/review，是否执行取决于本入口权限和任务，不默认全量压测；缺目标来源先记缺口。已有产品设计/审查输入按 [UI 实现验证与回执](../dev-shared/expert-ui-verification.md) 绑定页面/状态/视口/版本，不重新做产品价值裁决。

## 启动

完整读取 [执行约定](../dev-shared/expert-workflow-contract.md)、[角色与 graph 约定](../dev-shared/expert-role-contract.md)；创建专家前完整读取并执行 [模型策略](../dev-shared/expert-model-policy.md)，实际传入所选参数。单一调度者负责计数与状态。

## 诊断→修复→验证

1. **QA 复现**：确认期望/实际与版本，优先用现有框架建立最小失败用例，修复前实际运行。只写获分配的测试，不改业务。返回 `REPRO=stable|intermittent|unavailable` 和真实证据。
2. **Debugger 定位**：stable 走最小复现；intermittent/unavailable 继续受控诊断（固定种子/时间/调度、日志关联、隔离实验），不因暂时无法稳定重现就丢弃调查。沿 graph/调用/数据流查根因并核验当前源码；返回 `CAUSE=found|unknown`。
3. **根因门**：只有 `CAUSE=found` 且有可证伪的因果证据和验证计划才进入修复。仍 unknown 则标记诊断受阻，报告已查内容、最小缺口和下一步，不能硬改。
4. **Dev 最小修复**：只改根因相关位置、保留回归用例，不夹带重构。稳定问题保留 red→green；偶发问题记录实验条件、样本量与置信限制，不用一次通过宣称解决概率问题。
5. **QA 回归**：重跑复现/实验及受影响契约、调用方测试；按风险选择精准/全量测试，记录快照与 `ROUTE`。

## 回修与失败分流

- `dev-developer`：带上一轮假设、修复与新证据回 dev-debugger→dev-developer→dev-qa；最多三次生产修复尝试，包含初次。
- `self`：仅有证据的测试错误允许 QA 修正，本次执行累计最多两轮；不删断言迎合实现，不重置生产尝试计数。
- `environment`：处理可逆且已授权的环境问题，不改业务冒充修复；仍无法验证则阻断。
- `inconclusive`：继续有边界诊断；必要路径 flaky 不算通过。每一轮需有新证据或可证伪假设，同一无进展失败不无限重试。
- 生产预算耗尽或根因不成立时返回不可交付，给出证据与设计决策点，不擅自扩成大重构。

## 审查

验证通过并结束写入后，dev-code-reviewer 审查修复范围、正确性和回归护栏。涉及认证、权限、输入信任边界、秘密、依赖/执行工具时增加 dev-security-auditor，可并行只读审查同一快照。

审查阻断允许一次定向 dev-developer 回修→必要 QA 回归→受影响 reviewer 复审；复审仍阻断或回修引入测试失败则不可交付。这是独立的一次审查闭环，不能重启前三次生产尝试预算。

## 已知基线失败

验证前读项目已知失败记录；需要首次确认、复用诊断或判断失效时，执行 [历史失败协议](../dev-shared/expert-known-failures.md)。复用诊断不跳过必要检查；主理人负责持久化，QA 提供匹配证据，reviewer 核对本次适用性。

`ROUTE=pass`/`GATE=clean` 与符合协议全部条件的 `ROUTE=pass_with_known`/`GATE=delta_pass` 均可进入后续审查。本文“验证/测试通过”包括上述两种结果，但 `delta_pass` 最终只能称“本次改动验收通过，存在已知基线失败”。项目硬性全绿门禁、相关验收被阻碍、未知或变化的失败仍按原规则阻断。无关且有效的历史失败不触发生产回修或消耗本次修复预算。

## 最终交付

根因与证据、改动、修复前/后结果、graph 使用/盲区、回修次数、审查与剩余限制。验证与审查通过才标记“已修复可交付”；偶发问题保留验证限制。对外动作仅依已有用户授权。

维护此技能时参考 [场景评估](../dev-shared/expert-evaluation-cases.md)。不加载或执行旧 workflow 脚本。

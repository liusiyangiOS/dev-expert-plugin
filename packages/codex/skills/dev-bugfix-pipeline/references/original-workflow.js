export const meta = {
  name: 'dev-bugfix-pipeline',
  description:
    '缺陷修复 SOP（对齐 systematic-debugging 铁律：没有根因不许修）：复现 → 定位根因 → 最小修复 → 回归验证（失败则回 dev-debugger 重新分析，最多 3 轮；仍不过则停下质疑架构）→ 审查。缺陷描述通过 args.bug 传入。',
  phases: [
    { title: '复现', detail: 'dev-qa 写一个能稳定触发 bug 的失败测试（red），作为回归护栏；无法复现则先补证据' },
    { title: '定位根因', detail: 'dev-debugger 系统化调查（读错误/复现/查最近变更/追数据流），给出单一根因；无根因不进入修复' },
    { title: '修复', detail: 'dev-developer 按根因做最小修复，只动根因相关处，不顺手重构' },
    { title: '验证', detail: 'dev-qa 重跑：复现用例转绿 + 全量回归无新破坏；未过则回 dev-debugger 重新分析（有界回修环）' },
    { title: '审查', detail: 'dev-code-reviewer 检查修复质量、回归风险与是否夹带无关改动' },
  ],
}

// 缺陷描述：兼容 Workflow 对象参数、斜杠命令字符串参数，以及被外层转成 JSON 字符串的参数
let parsedArgs = typeof args === 'undefined' ? undefined : args

if (typeof parsedArgs === 'string') {
  const trimmedArgs = parsedArgs.trim()
  if (trimmedArgs.startsWith('{') || trimmedArgs.startsWith('[')) {
    try {
      parsedArgs = JSON.parse(trimmedArgs)
    } catch {
      parsedArgs = trimmedArgs
    }
  } else {
    parsedArgs = trimmedArgs
  }
}

const bugReport =
  (parsedArgs &&
    typeof parsedArgs === 'object' &&
    (parsedArgs.bug || parsedArgs.description || parsedArgs.text)) ||
  (typeof parsedArgs === 'string' && parsedArgs) ||
  '（未通过 args 传入缺陷描述；请在调用时用 args.bug 提供，至少包含：现象 / 复现步骤 / 期望 vs 实际 / 相关报错栈）'

// —— 阶段 1：复现（复现优先，失败测试即回归护栏）——
phase('复现')
const repro = await agent(
  `目标：为下面这个缺陷写出一个能【稳定复现】的失败测试（red），并确认它现在确实失败。\n` +
    `- 先读相关源码与错误/栈信息，确认触发路径与"期望 vs 实际"的差异。\n` +
    `- 用项目现有测试框架写最小复现用例（命名遵循 test_<name>.py / <name>.test.ts 等约定）。\n` +
    `- 只写测试、不改业务代码。\n` +
    `- 末尾单独输出一行机器可读判定：REPRO=ok（已稳定复现）或 REPRO=fail（无法稳定复现，需更多信息）。\n` +
    `缺陷描述：\n${bugReport}`,
  { label: '复现', agentType: 'dev-qa' }
)

if (/REPRO\s*=\s*fail/i.test(repro)) {
  log(
    '无法稳定复现（REPRO=fail）：按 systematic-debugging，先补数据 / 加诊断日志，不要猜着修。已停在复现阶段交主理人。'
  )
  return { stoppedAt: '复现', repro }
}

// —— 阶段 2：定位根因（铁律：没有根因不许修）——
phase('定位根因')
const diagPrompt = (extra) =>
  `遵循 systematic-debugging 铁律：没有根因不许提修复。对以下缺陷做系统化定位：\n` +
  `1) 完整读错误 / 栈信息；2) 依复现用例确认触发；3) 查最近 git 变更；4) 反向追数据流，找到坏值的源头。\n` +
  `产出：单一根因假设（文件:行 + 为什么会错），以及"改哪里、怎么改"的最小修复点建议（你自己不改业务代码）。\n` +
  `末尾单独输出一行机器可读判定：CAUSE=found（已定位根因）或 CAUSE=unknown（证据不足，未定位）。\n` +
  `缺陷描述：\n${bugReport}\n复现用例说明：\n${repro}\n${extra || ''}`

let diag = await agent(diagPrompt(), { label: '定位-round1', agentType: 'dev-debugger' })

if (/CAUSE\s*=\s*unknown/i.test(diag)) {
  log(
    '未能定位根因（CAUSE=unknown）：按铁律不进入修复，交主理人补充证据 / 加诊断后重跑。'
  )
  return { stoppedAt: '定位根因', repro, diag }
}

// —— 阶段 3：最小修复 ——
phase('修复')
let fix = await agent(
  `按根因做【最小修复】，只改根因相关处，不顺手重构、不做"顺便优化"。改完本地自测，让复现用例从红转绿。\n根因报告：\n${diag}`,
  { label: '修复-round1', agentType: 'dev-developer' }
)

// —— 阶段 4：验证 + 有界回修环（失败回 dev-debugger 重新分析，而非直接再改一次）——
phase('验证')
const verifyPrompt = (extra) =>
  `重跑测试验证修复：\n` +
  `1) 复现用例是否已从红转绿；2) 跑全量回归，确认无新增失败。\n` +
  `给通过率与任何新失败的复现步骤。\n` +
  `末尾单独输出一行机器可读判定：ROUTE=pass（复现转绿且无回归）或 ROUTE=dev-developer（仍失败 / 有回归）。\n` +
  `复现用例：\n${repro}\n本轮修复说明：\n${fix}\n${extra || ''}`

let verify = await agent(verifyPrompt(), { label: '验证-round1', agentType: 'dev-qa' })

// systematic-debugging Phase 4.4：修复失败先回 Phase 1 重新分析；累计 3 次仍不过 = 架构问题
let round = 1
while (/ROUTE\s*=\s*dev-developer/i.test(verify) && round < 3) {
  round++
  log(
    `第 ${round} 轮：修复未通过，按 systematic-debugging 回到 Phase 1 让 dev-debugger 带新信息重新分析（不是直接再改一次）。`
  )

  diag = await agent(
    diagPrompt(
      `上一轮修复未通过验证，说明上一版根因假设不成立或不完整。带着以下新信息重新分析：\n上轮修复：\n${fix}\n上轮验证：\n${verify}`
    ),
    { label: `定位-round${round}`, agentType: 'dev-debugger' }
  )

  fix = await agent(
    `按【重新定位】的根因做最小修复，只改根因处，不夹带无关改动：\n${diag}`,
    { label: `修复-round${round}`, agentType: 'dev-developer' }
  )

  verify = await agent(verifyPrompt('这是重新定位后的回修重测。'), {
    label: `验证-round${round}`,
    agentType: 'dev-qa',
  })
}

const fixed = /ROUTE\s*=\s*pass/i.test(verify)

if (!fixed) {
  // Phase 4.5：3 轮仍未修好，通常是架构 / 模式问题，停止继续修、升级人工决策
  log(
    '已尝试 3 轮仍未通过：按 systematic-debugging Phase 4.5，这通常是架构 / 模式问题而非单点 bug。停止继续修，交主理人做架构级决策。'
  )
  return {
    stoppedAt: '验证',
    escalate: '架构级问题：3 轮修复均失败，应质疑当前设计而非再修一次',
    repro,
    diag,
    fix,
    verify,
    rounds: round,
  }
}

// —— 阶段 5：审查（确认只动了该动的、复现用例留作回归护栏；有问题回修一轮再复审）——
phase('审查')
const reviewPrompt = (fixDesc, extra) =>
  `审查这次缺陷修复：\n` +
  `1) 是否只动了根因相关处，有无夹带无关重构；\n` +
  `2) 修复是否可能引入新的边界 / 并发 / 回归风险；\n` +
  `3) 复现用例是否留作了回归护栏（应保留在测试套件里）。\n` +
  `高危须显式标注。${extra || ''}\n修复说明：\n${fixDesc}`

let review = await agent(reviewPrompt(fix), { label: '修复审查', agentType: 'dev-code-reviewer' })
let hasBlocker = /需修改|存在风险|🔴/.test(review || '')

// 有界回修环：审查发现问题回 dev-developer 修一轮 + 快速回归，复审仍不过才升级主理人
if (hasBlocker) {
  log('审查发现问题：回 dev-developer 针对性修正后复审（最多 1 轮）。')

  fix = await agent(
    `以下审查报告发现问题。只修复报告中列出的问题，不扩大范围；改完确认复现用例仍绿、无新增失败，并附验证证据：\n${review}`,
    { label: '审查回修', agentType: 'dev-developer' }
  )

  const recheck = await agent(verifyPrompt('这是审查回修后的快速回归，确认复现用例仍绿、无新破坏。'), {
    label: '回修回归',
    agentType: 'dev-qa',
  })

  if (!/ROUTE\s*=\s*pass/i.test(recheck || '')) {
    log('审查回修引入了回归：升级主理人决策，不交付。')
    return { stoppedAt: '审查回修', repro, diag, fix, verify, review, recheck }
  }

  review = await agent(reviewPrompt(fix, '这是审查回修后的复审，请重点确认上一轮问题是否已解决。'), {
    label: '修复复审',
    agentType: 'dev-code-reviewer',
  })
  hasBlocker = /需修改|存在风险|🔴/.test(review || '')
}

log(
  hasBlocker
    ? '复审仍有问题：升级主理人决策，不交付。'
    : '审查通过：缺陷已修复，复现用例已作回归护栏，可交付。'
)

return {
  stoppedAt: null,
  repro,
  diag,
  fix,
  verify: { report: verify, passed: fixed, rounds: round },
  review,
  verdict: hasBlocker ? '需修改' : '已修复可交付',
}

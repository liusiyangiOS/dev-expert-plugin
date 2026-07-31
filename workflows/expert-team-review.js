export const meta = {
  name: 'expert-team-review',
  description:
    '专家团全链路 SOP：调研 → 计划 → 实现 → 测试（含 debugger→dev 回修环，最多 2 轮）→ 验收（安全 + 质量并行，高危 fail-fast 阻断）',
  phases: [
    { title: '调研', detail: 'researcher 摸清需求背景与现状' },
    { title: '计划', detail: 'planner 产出实现方案与关键文件清单' },
    { title: '实现', detail: 'dev 按方案编码' },
    { title: '测试', detail: 'qa 跑用例给路由；判 →dev 则进入 debugger→dev 回修环（最多 2 轮）' },
    { title: '验收', detail: 'security-auditor + code-reviewer 并行审查，有高危即阻断' },
  ],
}

// —— 阶段 1：调研 ——
phase('调研')
const research = await agent(
  '调研本任务涉及的需求背景 / 开源方案 / 现有代码，输出结构化调研报告',
  { label: '调研员', agentType: 'researcher' }
)

// —— 阶段 2：计划（plan 很重要，固定阶段不省略）——
phase('计划')
const plan = await agent(
  `基于调研结论产出实现方案：关键文件清单 + 有序实现步骤 + 风险与回退 + 验收标准。\n调研结论：\n${research}`,
  { label: '架构师', agentType: 'planner' }
)

// —— 阶段 3：实现 ——
phase('实现')
let impl = await agent(
  `严格按以下方案编码实现，只做方案要求的范围，写完自测编译/测试通过：\n${plan}`,
  { label: '开发者', agentType: 'dev' }
)

// —— 阶段 4：测试 + 缺陷定位回修环（有界反馈循环，GitHub 成熟编排的核心模式）——
phase('测试')
const qaPrompt = (extra) =>
  `对照方案与实现跑测试：覆盖正常/边界/异常，给通过率与失败复现步骤。\n` +
  `报告末尾**必须单独输出一行机器可读判定**：ROUTE=dev（源码有 bug）/ ROUTE=self（用例有 bug，自修自测）/ ROUTE=pass（全绿）。\n` +
  `方案：\n${plan}\n实现说明：\n${impl}\n${extra || ''}`

let qaReport = await agent(qaPrompt(), { label: '测试-round1', agentType: 'qa' })

let round = 1
while (/ROUTE\s*=\s*dev/i.test(qaReport) && round <= 2) {
  log(`第 ${round} 轮测试判定 →dev，进入 debugger 定位 → dev 回修 → 重测`)

  const diag = await agent(
    `以下测试失败判定根因在源码。系统化复现 → 定位根因 → 给出最小修复点（文件:行 + 修法），不要顺手重构。\n测试报告：\n${qaReport}`,
    { label: `定位-round${round}`, agentType: 'debugger' }
  )

  impl = await agent(
    `按缺陷定位报告做最小修复，只改根因相关处，改完自测通过：\n${diag}`,
    { label: `回修-round${round}`, agentType: 'dev' }
  )

  round++
  qaReport = await agent(qaPrompt('这是回修后的重测。'), {
    label: `测试-round${round}`,
    agentType: 'qa',
  })
}

const testPassed = /ROUTE\s*=\s*pass/i.test(qaReport)
if (!testPassed) {
  log('两轮回修后仍未全绿，记入 Known Issues 交主理人决策；仍继续走验收以暴露其余风险。')
}

// —— 阶段 5：验收（安全 + 质量并行）——
phase('验收')
const reviews = await parallel([
  () =>
    agent('审查本次变更的代码安全性（密钥/危险命令/注入/权限），高危须显式标注', {
      label: '安全审计',
      agentType: 'security-auditor',
    }),
  () =>
    agent('审查本次变更的代码质量与规范（正确性/性能/可读性/可维护性），高危须显式标注', {
      label: '代码审查',
      agentType: 'code-reviewer',
    }),
])

const hasBlocker = reviews.some((r) => /需修改|存在风险|🔴/.test(r || ''))
log(hasBlocker ? '验收发现高危/需修改：回 dev 修复后再交付。' : '验收通过：可交付。')

return {
  research,
  plan,
  impl,
  test: { report: qaReport, passed: testPassed, rounds: round },
  reviews: reviews.filter(Boolean),
  verdict: hasBlocker ? '需修改' : testPassed ? '可交付' : '带 Known Issues 交付',
}

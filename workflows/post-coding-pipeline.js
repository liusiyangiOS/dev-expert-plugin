export const meta = {
  name: 'post-coding-pipeline',
  description:
    '编码后提交前质量门：审查（安全 + 质量并行）→ 构建 → 测试 → 提交。任一关硬失败即 fail-fast 阻断，不进入下一关',
  phases: [
    { title: '审查', detail: 'security-auditor + code-reviewer 并行；发现高危即阻断' },
    { title: '构建', detail: '执行构建确保编译通过；失败即阻断' },
    { title: '测试', detail: 'qa 跑测试套件确保全绿；失败即阻断' },
    { title: '提交', detail: '三关全过后提交' },
  ],
}

// —— 关 1：审查（并行 fan-out，高危即 fail-fast）——
phase('审查')
const reviews = await parallel([
  () =>
    agent('审查当前分支相对 main 的变更的安全性（密钥/注入/危险命令/权限），高危须显式标注', {
      label: '安全审计',
      agentType: 'security-auditor',
    }),
  () =>
    agent('审查当前分支相对 main 的变更的质量与规范（正确性/性能/可读性/可维护性），高危须显式标注', {
      label: '代码审查',
      agentType: 'code-reviewer',
    }),
])

const reviewBlocked = reviews.some((r) => /需修改|存在风险|🔴/.test(r || ''))
if (reviewBlocked) {
  log('审查发现高危/需修改，fail-fast 阻断，未进入构建。请先修复后重跑。')
  return { stoppedAt: '审查', reviews }
}

// —— 关 2：构建 ——
phase('构建')
const build = await agent('执行项目构建命令，确保编译通过；失败则报出完整错误', { label: 'build' })
if (/error|failed|失败|错误/i.test(build || '')) {
  log('构建失败，fail-fast 阻断，未进入测试。')
  return { stoppedAt: '构建', reviews, build }
}

// —— 关 3：测试 ——
phase('测试')
const test = await agent(
  '运行项目测试套件，确保全部通过；给通过率与失败用例复现步骤；末尾单独输出一行 ROUTE=pass 或 ROUTE=dev',
  { label: '测试', agentType: 'qa' }
)
if (!/ROUTE\s*=\s*pass/i.test(test || '')) {
  log('测试未全绿，fail-fast 阻断，不提交。')
  return { stoppedAt: '测试', reviews, build, test }
}

// —— 关 4：提交 ——
phase('提交')
log('审查、构建、测试三关全过，准备提交（实际 git commit 由主会话确认后执行）')
return { stoppedAt: null, reviews, build, test }

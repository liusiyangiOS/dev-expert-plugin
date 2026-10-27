# 开发专家团 3.1.0 能力升级验收

日期：2026-10-27；基线 b91de1a；直接在 master 修改。macOS arm64、Bash、Python 3.14.6。提交/远端状态以 Git 为准。

## 变更

新增按需性能验证协议、轻量记录和已有产品 UI 交接的实现验证。planner 定义测量与验收，debugger 定位，developer 最小优化，QA 独立判断，review 核验主张。保持 8 角色、4 入口和原有回修/只读/授权规则，不新增压测引擎，不安装 Agency。

性能依据用户路径、正确性、基线和目标来源，绑定版本/环境/数据/计时边界，区分冷暖缓存、并发、重复样本及原始数据；分位数必须有样本依据，记录错误、超时及资源护栏。不能把均值、HTTP 200 或异环境数字当作性能达标。UI 回执与产品团字段一致，只验证已有设计和行为，不新增产品调度。

## 验证

- [离线测试](evidence/capabilities-20261027/unittest.log) 59 项：44 通过、15 项 Windows 原生用例在 macOS 跳过；[模型策略测试](evidence/capabilities-20261027/model-tests.log) 19 项通过。8 个双端 Skill 校验、包与已安装路径审计通过；三份新增资源双端字节一致。历史 2.0.1 兼容白名单未改变。
- 独立性能方法演练使用合成原始 CSV，未启动负载。补充案例平均延迟 110→105ms，但业务成功 100/100→90/100，最近秩 p95 100→600ms，方法给出不能据此交付的结论，并保留单轮/身份/计时证据限制。[原案例](evidence/capabilities-20261027/qa-results/performance-report.md)、[均值改善案例](evidence/capabilities-20261027/qa-results/performance-tail-report.md)。这是方法行为验证，不能当成任何真实项目性能结果。
- 首轮性能报告的业务判断正确，但回执出现协议外值 `ROUTE=dev-debugger / GATE=fail`，因此首次前向验证不算完整通过。保留两份原报告；仅补充双端性能方法中的既有 QA 枚举映射，定向 5 项 namespace 测试及方法复核通过。新的独立评估者未看到首轮报告，仅按原始材料和修正协议复验，两候选均正确输出 `ROUTE=inconclusive / GATE=blocked`。[独立复验](evidence/capabilities-20261027/qa-retest/performance-report.md)、[计算脚本](evidence/capabilities-20261027/qa-retest/calculate.py)。
- 独立代码和安全审查通过，无阻断；安装路径校验、写入/回滚、managed 清单等控制逻辑与基线 AST 一致，新变化仅版本及 required 预检。[结果摘要](evidence/capabilities-20261027/validation-summary.json)。
- 产品/开发真实旧基线→新版组合升级在隔离 Codex/Claude 个人目录通过，两套 check 与备份均正确。[结果](evidence/capabilities-20261027/upgrade-coexist.json)。
- 真实宿主隔离测试：Claude Code 2.1.201 市场生命周期和 8 角色/4 技能发现通过；Codex CLI 0.164.0-alpha.11.1 发现 4 技能、原生委派 schema 含 8 角色。[日志](evidence/capabilities-20261027/host-smoke.log)。schema 检查未调用模型。
- 本机开发 Codex 3.1.0 共 31 受管文件、已有 Claude 个人版共 23 文件均与当前包一致；产品 Codex 1.2.0 共 41 文件同时通过。初次升级与定向修正的备份链均已核对，全局配置哈希不变。[前](evidence/capabilities-20261027/installed-before.json)、[后](evidence/capabilities-20261027/installed-after.json)。

运行文件见 [源码快照](evidence/capabilities-20261027/source-snapshot.json)。无 Windows/Linux 原生性能或 UI 验收、无生产/外部网络负载实验；测试用例跳过不称通过。新开 Codex/Claude 会话加载角色与共享方法，若仍缓存则重启宿主。

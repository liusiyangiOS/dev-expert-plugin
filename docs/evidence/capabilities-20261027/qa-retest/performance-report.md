# 性能样本独立 QA 回执

- STATUS=done（样本分析完成，非交付通过）；两个候选均 `ROUTE=inconclusive / GATE=blocked`，`stoppedAt=test`。无实测和业务实现证据，不能判断真实产品可交付，也不能把合成数据中的失败直接归为生产缺陷。
- 候选 1：`PERF=not_improved`，该结论仅指给定同环境假设下的合成单轮样本：中位数降低，但业务成功率下降、均值及尾部变差，不满足“不损害业务成功率和尾延迟”的目标。真实系统性能及原因未证实。
- 候选 2：`PERF=not_comparable`，上下文仅绑定 b1 与 c1；candidate-tail-case 的环境、负载与基线对应关系未被证实。下列数值为各文件内的描述，差异只是假定可比下的算术对照，不是改善或归因结论。即使该假定成立，样本也不满足业务与尾部护栏。

## 目标与样本结果

目标来自 performance-context.json：R-1 save-and-list，在不损害业务成功率和尾延迟前提下降低保存完成耗时；无量化尾延迟 SLO，也无最低改善比例。JSON 声明 b1/c1 为 M1、并发 1、warm、records-v1、各 100 条、同负载单轮合成数据。候选 2 未有对应环境元数据。起止事件、业务成功判定实现、采样顺序、超时重试、资源指标及数据种子均未给出。

| 指标（全部原始记录） | 基线 b1 | 候选 1 c1 | 候选 2，环境未核实 |
|---|---:|---:|---:|
| 样本数 | 100 | 100 | 100 |
| 保存耗时均值 ms | 110 | 163（+48.18%） | 105（假定可比：-4.55%） |
| p50 ms | 100 | 70（-30%） | 50（假定可比：-50%） |
| 样本 p95 ms | 100 | 1000（+900%） | 600（假定可比：+500%） |
| 样本 p99 ms | 300 | 1000（+233.33%） | 600（假定可比：+100%） |
| HTTP 200 | 100/100 | 100/100 | 100/100 |
| business_ok=True | 100/100 | 90/100 | 90/100 |
| business_ok=False | 0/100 | 10/100 | 10/100 |

p95/p99 是 100 个合成值的描述性次序统计量，非真实业务尾延迟的稳健估计、置信区间或显著性结论；实际尾部表现 `not_supported`。没有数值 SLO 不妨碍观察样本分布的明显变化，但无法证明真实系统尾部是否受损。HTTP 状态全 200 不代表业务成功。资源护栏、吞吐、错误类型和实际端到端成功均 `not_run/unknown`。

完整分布：基线 100 ms ×95、300 ms ×5（均成功）；候选 1 70 ms ×90 成功、1000 ms ×10 失败；候选 2 50 ms ×90 成功、600 ms ×10 失败。没有删除离群值，也没有只筛成功样本后包装成整体结果。100 条的标识各不重复；是否缺失预期样本或重试无法从文件证明。

## 方法和复现

在 macOS Darwin arm64、Bash 下只读取四份输入，以 Python 标准库 csv 解析，数字升序后 nearest-rank 分位数为 `x[ceil(p*n)-1]`；p50 此处同时等于常规 median，均值为所有 latency 求和除样本数。相对变化 `(candidate-baseline)/baseline*100`，百分比为四舍五入；均包含失败记录。无数据筛选。该方法不构成独立运行负载或生产业务验证。

执行复核命令：`python3 /var/folders/2r/3t3s5pkj769fkwqc1_d3qgf0b0g8g4/T/expert-capabilities-htb3nrvc/qa-retest/calculate.py`，通过 `collections.Counter`、`statistics.mean/median`、`math.ceil` 求统计；退出 0，3 个文件各 100 样本。`git -C /Users/liusiyang/Documents/GitHubOfMine/dev-expert-plugin rev-parse HEAD`、`status --short`、`branch --show-current` 均退出 0。输入归档、统计计算、仓库状态只读；没有构建、测试、压测或网络访问。测试计数：样本统计 3/3 执行成功（这是分析任务数，不是业务通过率）；生产测试 passed=0、failed=0、skipped=0、flaky=0、not_run=未提供的全部必要实测与业务回归，数量不可知。样本级失败分别为 0、10、10。

## 契约与证据映射

| 行为/契约 | 调用方 | 证据 | 缺口 |
|---|---|---|---|
| R-1 保存后列表及业务成功 | 未提供 | CSV 的 business_ok 标记 | 无原始响应、持久化/列表结果或断言实现，不能独立核验标记 |
| 保存耗时与尾部不退化 | R-1，具体调用方未知 | 每条 latency_ms、JSON 样本上下文 | 未定义准确计时边界，单轮合成数据、无稳定性或真实运行身份 |
| 资源与可靠性护栏 | 未提供 | 无 | CPU、内存、IO、超时、重试、数据完整性未测 |

GRAPH=not_needed：本任务限定只分析输入样本，未获实际被测应用源码、调用链或构建身份；动态调用路径未知。仓库是方法规则来源，不等于样本代表的被测应用。生产源码、二进制/运行版本、依赖和脏文件及环境身份均未提供；不可将 b1/c1 标签当作已核实构建。未运行完整 post-coding 构建、测试、安全/代码审查或最终质量门。

历史失败：历史命中=0（未核查，不代表不存在）、新增/变化=未知、已恢复=未知、待复核=未知；无记录 ID。只读范围限定仓库和 fixtures，未读取仓库外历史失败记录，也未读取其他 qa-results 或前次报告。没有以历史失败为由豁免任何失败。下一步由主理人安排 dev-debugger 确认样本生成契约与失败原因；需要真实交付判断时，另行取得实际版本、可比环境、可重复测量和业务及资源护栏证据。

## 输入和规则身份（SHA-256）

仓库 HEAD `b91de1a6ec07fbe3a0d36ede06fd333b3cb3e3d0`、分支 master，工作区有既存修改和未跟踪文件；以下规则采用当前工作树内容哈希，不以 HEAD 代替脏文件身份。样本是合成输入，非真实构建快照。

| 输入/规则 | SHA-256 |
|---|---|
| performance-context.json | 3b4d152abc9540cdb5b8df0a288af3d8ab8175c0e86f70bd3b27953afb25b715 |
| baseline.csv | 4a2d55d8049003f040005b6fa037f4319b114de54ea59688e5cb9a8b36442466 |
| candidate.csv | e18a3d9231f218cfa175ee701256b382bba616068cddfd954b23d8a37e0ae287 |
| candidate-tail-case.csv | 8fa73b7f292b757b0ca367d91063462c6818962d489e139e4239a4523ac66852 |
| packages/codex/skills/dev-post-coding-pipeline/SKILL.md | 3e40cc2e9d87004d2a7203238cb6c43104d6bb8cf797f70e20a894629c7ae0fc |
| packages/codex/skills/dev-shared/expert-performance.md | f80223d63236d6ab9366e698de59408c07b5c73e210f87d0caa1b3aec5f4df15 |
| packages/codex/skills/dev-shared/expert-platform.md | a6633604fe5c9ba367e54b828fc1e682cae3e640ea4c477d09949d10610f64ae |
| packages/codex/skills/dev-shared/expert-role-contract.md | 346bdcbc31f156bc0e42588190d6d8ccabb34d2a20e2880231c2f1f288ccde1d |
| packages/codex/skills/dev-shared/expert-workflow-contract.md | b473274978facadede53ac6bafd1332c13be46506705f969eedb8dff9617b979 |
| packages/codex/agents/dev-qa.toml | dff0ee9fdabbf2fc194a9f58fc563599659f2a5b5b7289e7152b5f7775f212d3 |

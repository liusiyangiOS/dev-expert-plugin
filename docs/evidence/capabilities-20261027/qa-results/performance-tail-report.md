# 另一候选版本的性能交付判断

**不能据此交付。** 在给定的单轮合成样本中，候选的平均耗时从 110 ms 降至 105 ms，但业务成功从 100/100 降至 90/100，最近秩 p95 从 100 ms 升至 600 ms。业务成功率和尾延迟均损害了材料中的目标；HTTP 均为 200 不改变这一结论。此结果仅是合成数据分析，不是实机性能结果。

`PERF=not_improved`（综合目标在这组样本内未达成；均值确有下降）；实际系统 `insufficient_evidence`。护栏样本内失败，目标未达成；`ROUTE=dev-debugger`，`GATE=fail`（交付条件不足，需定位和复验）。

| 指标 | 基线 | 新候选 | 样本变化 |
| --- | ---: | ---: | ---: |
| 样本数 | 100 | 100 | 单轮 |
| 平均延迟 | 110 ms | 105 ms | -5 ms，-4.5% |
| p50 | 100 ms | 50 ms | -50 ms，-50% |
| p95 | 100 ms | 600 ms | +500 ms，+500% |
| p99 | 300 ms | 600 ms | +300 ms，+100% |
| 业务成功 | 100/100 | 90/100 | -10 个百分点 |
| HTTP 200 | 100/100 | 100/100 | 无变化 |

最近秩法取排序后第 ceil(p×n) 项，均值和分位数包含所有记录及失败，未剔除离群样本。基线 96–100 号为 300 ms 且成功；新候选 91–100 号均为 600 ms、HTTP 200、business_ok=False。单轮 100 条不足以推断真实尾延迟稳定性或统计显著性；分位数对算法敏感，不同算法可能得到不同 p95。

## 方法与限制
需求路径 R-1 save-and-list；目标为降低保存完成耗时且不损害业务成功率及尾延迟，源自 performance-context.json，未给数值 SLO。按任务指示仅用另一候选文件替代 context 中的候选数据；context 声明基线与候选同为 M1、并发 1、warm、records-v1、各 100 条，但没有证据将新文件独立绑定到 c1、真实机器或实际环境，这些条件均仅为上下文假定。无真实源码/脏文件和二进制身份、计时起止及层级、数据分布、依赖、测量顺序、重试超时、资源护栏或业务成功字段的独立验证。不能推断真实运行具有相同性能，也不能确认失败原因。

在 `/Users/liusiyang`、Darwin arm64、Python 3.14.6 下，用 Python 标准库 `csv` 读取两份样本，`statistics.mean` 计算平均值，`math.ceil` 按上述最近秩计算分位数，统计 `business_ok=True` 与 `http_status=200`，退出码 0；未联网、启动负载或改仓库。原始每条记录位于下列文件。建议由诊断负责人确认失败与尾部原因，在获授权的隔离环境绑定运行身份、明确计时和业务验证、以多轮交替对照复验，保留全部失败样本，再判断交付。

## 实际读取的规则与输入 SHA-256

- `/Users/liusiyang/Documents/GitHubOfMine/dev-expert-plugin/packages/codex/skills/dev-shared/expert-performance.md`: `060798fe4cf4f05b72445a93fa4d4b27bfcdc5e57c55bc5fce448868d14c0d44`
- `/Users/liusiyang/Documents/GitHubOfMine/dev-expert-plugin/packages/codex/skills/dev-shared/expert-performance-record.md`: `161960bb84a3fddaf4b9cdca9605d44fdde908b34e92837d7a9950d3e0648b85`
- `/var/folders/2r/3t3s5pkj769fkwqc1_d3qgf0b0g8g4/T/expert-capabilities-htb3nrvc/fixtures/performance-context.json`: `3b4d152abc9540cdb5b8df0a288af3d8ab8175c0e86f70bd3b27953afb25b715`
- `/var/folders/2r/3t3s5pkj769fkwqc1_d3qgf0b0g8g4/T/expert-capabilities-htb3nrvc/fixtures/baseline.csv`: `4a2d55d8049003f040005b6fa037f4319b114de54ea59688e5cb9a8b36442466`
- `/var/folders/2r/3t3s5pkj769fkwqc1_d3qgf0b0g8g4/T/expert-capabilities-htb3nrvc/fixtures/candidate-tail-case.csv`: `8fa73b7f292b757b0ca367d91063462c6818962d489e139e4239a4523ac66852`

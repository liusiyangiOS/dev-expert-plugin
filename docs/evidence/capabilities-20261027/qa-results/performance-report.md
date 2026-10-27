# 性能优化交付判断

**不能依据这组材料交付。** 合成样本中候选版本的业务成功率从 100% 降至 90%，而 p95 从 100 ms 升至 1000 ms，违反“不损害业务成功率和尾延迟”的目标。即使 p50 更低，也不能掩盖失败或尾部退化。这只是对合成数据的判定，不是实际系统的性能测试结果。

- `PERF=not_improved`：仅针对给定合成样本，声明条件一致并可比较数据分布；不是实际运行改善判断。目标未满足；正确性及尾延迟护栏在样本内失败。实际优化效果 `insufficient_evidence`。`ROUTE=dev-debugger`（诊断样本暴露的问题及实际实现）；`GATE=fail`（交付所需条件未满足，真实运行也未验证）。
- 路径 R-1 save-and-list；目标为降低保存完成耗时且不损害成功率和尾延迟，来自 performance-context.json，未给数值 SLO。业务成功仅有输入字段 `business_ok`，未提供操作结果独立证据。b1 和 c1 标签、M1、并发 1、warm、records-v1 和各 100 个样本是材料声明，不代表核验过运行身份或硬件。

| 指标 | 基线 b1 | 候选 c1 | 样本内变化 |
| --- | ---: | ---: | --- |
| 记录数 | 100 | 100 | 单轮；每行一个样本 |
| 平均延迟 | 110 ms | 163 ms | +53 ms，+48.2% |
| p50 | 100 ms | 70 ms | -30 ms，-30% |
| p95 | 100 ms | 1000 ms | +900 ms，+900% |
| p99 | 300 ms | 1000 ms | +700 ms，约 +233.3% |
| business_ok=True | 100/100 | 90/100 | -10 个百分点 |
| HTTP 200 | 100/100 | 100/100 | 无变化，但不能证明业务成功 |

分位数使用最近秩法：排序后的第 ceil(p×n) 项，全部样本包括业务失败，均值亦不剔除失败。候选 91–100 号均为 1000 ms、HTTP 200、business_ok=False；基线 96–100 号为 300 ms、成功。p95 对算法尤其敏感：该样本最近秩为 100 ms，线性插值会给出其他结果；p99 仅约两个尾部观察位置、单轮 100 条不足以支持实际尾部稳定性或统计显著性，因此表格仅描述合成样本、不外推实机。

## 可复核步骤和边界
本次在 `/Users/liusiyang` 使用 macOS Darwin arm64、Python 3.14.6 标准库 csv、statistics、math 离线读取 fixtures/baseline.csv 与 candidate.csv，排序所有 latency_ms，分别计算 mean、索引 ceil(.50*n)-1、ceil(.95*n)-1、ceil(.99*n)-1，以及 business_ok 和 http_status 计数；命令退出 0，没有发起负载或修改产品代码。输入原始文件保留每条样本。未提供真实源码/脏文件、二进制身份、计时起止/客户端或服务端层级、运行时/依赖、硬件规格、背景负载、测量顺序、超时重试、数据分布/种子、资源指标，声明一致不足以核验真实可比性。没有真实测试命令、业务结果检查、CPU/内存/IO 或错误原因；超时是否存在未知。

后续由开发/诊断负责人查明失败与尾部原因，在获授权的隔离环境绑定代码及运行身份、明确计时边界和业务正确性，预先约定尾部护栏、工作负载与停止条件，以多轮交替对照保留全部错误和原始样本，复验后再作交付判断；不得把这组合成数据作为实机结果。

## 实际读取文件及 SHA-256

- `/Users/liusiyang/.agents/skills/dev-shared/expert-platform.md`: `a6633604fe5c9ba367e54b828fc1e682cae3e640ea4c477d09949d10610f64ae`
- `/Users/liusiyang/.agents/skills/dev-shared/expert-role-contract.md`: `5663aa08e117c042543612453b8663659c5f4b0f8a49782be6ddcefffe888d0f`
- `/Users/liusiyang/Documents/GitHubOfMine/dev-expert-plugin/packages/codex/skills/dev-shared/expert-performance.md`: `060798fe4cf4f05b72445a93fa4d4b27bfcdc5e57c55bc5fce448868d14c0d44`
- `/Users/liusiyang/Documents/GitHubOfMine/dev-expert-plugin/packages/codex/skills/dev-shared/expert-performance-record.md`: `161960bb84a3fddaf4b9cdca9605d44fdde908b34e92837d7a9950d3e0648b85`
- `/var/folders/2r/3t3s5pkj769fkwqc1_d3qgf0b0g8g4/T/expert-capabilities-htb3nrvc/fixtures/performance-context.json`: `3b4d152abc9540cdb5b8df0a288af3d8ab8175c0e86f70bd3b27953afb25b715`
- `/var/folders/2r/3t3s5pkj769fkwqc1_d3qgf0b0g8g4/T/expert-capabilities-htb3nrvc/fixtures/baseline.csv`: `4a2d55d8049003f040005b6fa037f4319b114de54ea59688e5cb9a8b36442466`
- `/var/folders/2r/3t3s5pkj769fkwqc1_d3qgf0b0g8g4/T/expert-capabilities-htb3nrvc/fixtures/candidate.csv`: `e18a3d9231f218cfa175ee701256b382bba616068cddfd954b23d8a37e0ae287`

执行环境：macOS Darwin arm64，Bash；以本地文件读取、`shasum -a 256` 和 Python 标准库离线分析。无联网、联系用户、启动服务或负载；未修改仓库或真实安装。

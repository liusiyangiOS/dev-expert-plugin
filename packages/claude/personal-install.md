# Claude 专家团个人安装

此目录中的专家团由独立的 Claude 包生成：8 个角色在 `~/.claude/agents`，4 个技能和全部共用规则在 `~/.claude/skills`，平台规则为 `skills/_shared/expert-platform.md`。不读取其他平台目录，不使用链接，不共享模型缓存。

新开 Claude Code 会话，使用 `/expert-team-review`、`/bugfix-pipeline`、`/quick-fix`、`/post-coding-pipeline`。不要同时加载本团插件版和个人版。根因、快修准入和升级锁定、独立 QA/review、历史失败复核、累计预算及动态模型策略继续由技能和本端 `_shared` 规定。

源码基准为 dev-expert-plugin 仓库的 `packages/claude`。在仓库根运行 `python3 packages/claude/install.py check` 检查本机差异；更新使用 `install` 后再次 `check`。Windows 将解释器换为 `py -3 -X utf8`，要求 Python 3.11+。只有本端包时可从包目录运行 `python3 install.py`。

安装器会转换插件路径与命名空间，不能将本目录个人形式整目录反向覆盖插件源码。本机改动先审阅、合入对应源码；默认更新拒绝覆盖被修改的文件，显式 `--replace` 才备份替换。安装清单在 `~/.claude/expert-team/install-manifest.json`，备份在相邻 `backups`。卸载只处理清单文件，保留个人缓存和历史记录。

模型按调用检查、按 72 小时策略刷新，通常无需手动追踪型号；不是后台即时更新。用户指定优先，权限或核验不足会报告，不静默降档。缓存位于 `~/.claude/cache/expert-team`，历史失败记录位于 `~/.claude/state/expert-workflows`，不应打包公开。

# D5 子代理 B 运行记录

- 2026-10-20 UTC：检查项目及父目录 `AGENTS.md`；仅父目录有与本任务无关的申请材料规则。
- 只读定位 D4 本地私有备份、原报告、原 `analysis.json` 和 `post_glm_verification.json`；未通过 SSH 或网络请求取新数据。
- 新建本目录内 `calculate_strategy_gradient.py`，从 40 个备份 `run.json` 逐轮重算 160 次选择。每个输入 run 的 SHA-256 与 D4 验证清单核对，原分析文件 SHA-256 和列联表均核对通过。
- 首次执行发现保存格式的 `complete` 字段位于外层 `status`，属本次新脚本的机械读取错误；只修改该字段路径，未改变数据、分箱或检验定义，随后完整回归通过。
- 计算四分箱策略列联表、Cochran–Armitage 1 自由度线性趋势、Pearson 3 自由度独立性、0 对 6+ 的 Fisher 双侧精确检验。另重算原 D4 diverse 对其他的 Fisher，和既有值在数值误差内一致。
- 输出 `strategy_gradient_tables.csv`、`d4_report_addendum.md`；无 GLM/API 调用、无冻结物或 D4 文件写入、无 Tier B/C 判定。
- 多重比较、同种子四轮的相关性及观察性选择均已在附录中声明。

# D8盘点：按本地文件核实（2026-10-22）

所有结果均为事后分析。此盘点未操作 Git。

| 工作线 | 盘上状态 | 证据 |
|---|---|---|
| D7-A：策略表现余量、Thompson/UCB1、反馈批次数扫描 | 完成 | `outputs/d7_20261021/a_headroom_bandit/revision_11field/REPORT.md`；摘要与 CPU 轨迹清单。独立配置 1,160 个，实际运行 1,480 次，新增 GLM 调用 0。 |
| D7-B：语言模型重复性方差 | 完成 | `outputs/d7_20261021/b_model_variance/B_REPORT.md`、`B_ANALYSIS.json`、`MANIFEST_B_FINAL.json`。100 条运行，模型内 SD 2.1943；报告分析纳入重复间波动。 |
| D7-C2：六种代理表现 | 完成 | `outputs/d7_20261021/c_surrogate_factor_v2_orthogonal/C2_SIX_PUBLIC.json`。TNAP 与 DYRK3 各六项，CPU；AUC 范围因池不同。 |
| D7-C3：代理 × 策略对照 | 完成 | `C3_RUN_RECEIPT.json` / `C3_AUDIT.json`：1,880 个完整运行。五动作更正版本 `C3_FIVE_AUDIT.json`：720 个完整运行，ENS 决策为 0。 |
| D7-D：身份凭证 v3 | 部分完成 | `outputs/d7_20261021/d_identity_gate_v2/revision_v3/credential_summary.json` 与 62 行决策表。62 项重算完成，3 项可进入进一步审查，但 `campaign_ready_count=0`；目录状态为等待根目录发布验收，不能说已有新可用 benchmark。 |
| D7-E：历史记录修订 | 完成 | `outputs/d7_20261021/e_record_fixes/historical_record_checks.json`、`corrected_baseline_checks.json`。更正历史记录并核验，0 次 GLM，0 个新运行。 |
| CP-2 的 C4：TNAP × S_strong × bit | 完成 | `outputs/d7_20261021/c4_five/C4_FINAL_MANIFEST.json`、`C4_FINAL_REPORT.md`、`C4_PUBLIC_ANALYSIS.json`。40 次运行全部完成；159 次有效模型决策，161 次物理服务请求（含 2 次传输失败），返回 token 101,988。它未显示语言模型优于预先选定的 Thompson 对照。 |
| 发布流程 | A-5 阻塞 | `BLOCKED_PUBLISH_A5_20261022.md`。两份已跟踪专利样本摘录含逐记录活性数值；没有提交、推送或更改 remote。 |

## GLM 物理请求账目

D8 开始前的项目账本基数按任务卡记为 521 次。随后 C4 完成 161 次物理请求，D8 合成 API 探测新增 1 次，因此目前这个 Task 2 对照账本为 **683 次**。本卡合成探测返回 47,683 tokens；C4 返回 101,988 tokens。该数不把更早 Task 1 的独立调用日志并入 D7 Task 2 预算。若之后执行 40 个可选检查点，则为 723，仍低于 1,000 的 D7 上限。

“物理请求”包括服务端收到请求但没有有效决策的传输失败；供应商未返回用量的失败调用不计入 token 统计。token 用量不是现金账单金额。D8 的单次探测使用合成标签，不构成候选选择决策，也未查询隐藏标签服务。

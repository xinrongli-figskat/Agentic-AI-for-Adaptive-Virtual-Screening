# S1 只读盘点摘要

- 扫描开始（UTC）：2026-10-18T11:44:24.675055+00:00
- outputs 顶层条目：229
- 顶层分类：{".json": 9, ".md": 45, ".ps1": 2, ".py": 56, ".sh": 7, ".sql": 1, ".zip": 22, "directory": 64, "other": 8, "test_*.py": 15}
- 文件数：2120
- 文件总字节数：119766949
- 扫描树 SHA-256（路径与内容哈希序列）：`6c58f101564afb3bb4ff4dd9a386680e6d0f3a33dd62b6b5700ff3c02881f881`

## 最大 20 个文件

|相对路径|字节数|SHA-256|
|---|---:|---|

## 名称含 private 的目录

|目录|文件数|
|---|---:|
|`a2_llm_input_audit_private_20261017`|16|
|`a3_dyrk3_supplement_private_20261017`|20|
|`b1_nonhit_limited_private_20261017`|1|
|`b2_candidate_metrics_private_20261017`|18|
|`b3_pending_assay_private_20261017`|25|
|`brief_gap_audit_private_20261018`|10|
|`low_hit_fallback_design_private_20261017`|15|
|`p1_negcoverage_private_20261018`|21|
|`p5_init_gate_private_20261018`|16|
|`p5_standard_table_private_20261018`|5|
|`r2_threshold_counts_private_20261018`|10|
|`r3_ranked_numeric_private_20261018`|10|
|`r3_ranked_numeric_private_20261018_v2`|12|
|`r4_source_review_private_20261018`|37|
|`r5_cpu_controls_private_20261018`|290|
|`r5_glm_response_private_20261018`|6|
|`r5_matched_order_private_20261018`|17|
|`r5_reveal_accounting_private_20261018`|6|
|`r7_oracle_service_private_20261018`|7|
|`r8_task1_failures_private_20261018`|7|

## transfer zip 清单

|zip|配套校验/收据|缺配套|
|---|---|---|
|`campaign_v0_transfer.zip`|无|yes|
|`campaign_v1_transfer.zip`|无|yes|
|`campaign_v2_transfer.zip`|无|yes|
|`campaign_v3_transfer.zip`|无|yes|
|`dyrk3_prefreeze_v0_transfer.zip`|无|yes|
|`dyrk3_v1_final_prefreeze_transfer.zip`|无|yes|
|`dyrk3_v1_freeze_candidate_transfer.zip`|无|yes|
|`dyrk3_v1_glm53_probe_transfer.zip`|无|yes|
|`dyrk3_v1_reporting_transfer.zip`|无|yes|
|`dyrk3_v1_retry_transfer.zip`|无|yes|
|`dyrk3_v1_review_transfer.zip`|无|yes|
|`dyrk3_v1_timeout_transfer.zip`|无|yes|
|`oracle_boundary_v0_transfer.zip`|无|yes|
|`task1_curation_agent_v1_transfer.zip`|无|yes|
|`task1_curation_agent_v2_1_transfer.zip`|task1_curation_agent_v2_1_transfer.sha256|no|
|`task1_curation_agent_v3_transfer.zip`|task1_curation_agent_v3_transfer.sha256|no|
|`task1_curation_agent_v4_transfer.zip`|无|yes|
|`task1_v5_stage0_transfer.zip`|task1_v5_stage0_transfer.sha256|no|

## 生成表格行数

- inventory_before.csv：2120
- duplicates.csv：1014
- hardcoded_paths.csv：220
- recorded_paths.csv：62

## 完整性说明

扫描不包含本目录 `s_restructure_20261018`，以避免盘点产物自身改变被比较对象；该排除规则将在 RUN_LOG 中说明。

> 公开版本已删除指向 Git 忽略文件的表格行；完整版本仅保存在本机 Git 忽略的私有 ledger。

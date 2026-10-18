# INDEX：当前 outputs 顶层文件与目录

本表依据当前目录自动生成，逐项列出顶层内容。历史路径与文件哈希见 `PATH_MIGRATION_20261018.csv`；本次整理的审计材料见 `s_restructure_20261018/`。

私有逐化合物标签不会提交到 Git。可复用代码包和测试保留在顶层，避免改变现有模块导入路径。

|条目|当前路径|类别|说明|
|---|---|---|---|
|`01_original_brief_from_chat.md`|`outputs/01_original_brief_from_chat.md`|Brief（兼容路径）|被现有 brief 复核脚本按旧路径读取，暂留顶层|
|`_archive`|`outputs/_archive`|分层目录|历史传输包和被取代文件|
|`a2_llm_input_audit_private_20261017`|`outputs/a2_llm_input_audit_private_20261017`|本机私有数据/分析|未纳入 Git；文件级状态见 S6 审计|
|`a3_dyrk3_supplement_private_20261017`|`outputs/a3_dyrk3_supplement_private_20261017`|本机私有数据/分析|未纳入 Git；文件级状态见 S6 审计|
|`acc2_patent_us8835472_sample_values.json`|`outputs/acc2_patent_us8835472_sample_values.json`|文件|具体用途见文件内容|
|`acly_source_value_review_20261017.md`|`outputs/acly_source_value_review_20261017.md`|文件|具体用途见文件内容|
|`assay_audit_v0`|`outputs/assay_audit_v0`|代码包|保留顶层以维持现有模块入口|
|`assay_edge_inspection_v0`|`outputs/assay_edge_inspection_v0`|代码包|保留顶层以维持现有模块入口|
|`audit_s1pr1_archived_assay.py`|`outputs/audit_s1pr1_archived_assay.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`audit_task1_finished_v1.py`|`outputs/audit_task1_finished_v1.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`audit_value_quantization_chembl37.py`|`outputs/audit_value_quantization_chembl37.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`b1_nonhit_limited_20261017`|`outputs/b1_nonhit_limited_20261017`|研究产物|状态和用途见目录内说明；检查 Git 忽略规则|
|`b1_nonhit_limited_private_20261017`|`outputs/b1_nonhit_limited_private_20261017`|本机私有数据/分析|未纳入 Git；文件级状态见 S6 审计|
|`b2_candidate_metrics_private_20261017`|`outputs/b2_candidate_metrics_private_20261017`|本机私有数据/分析|未纳入 Git；文件级状态见 S6 审计|
|`b3_pending_assay_private_20261017`|`outputs/b3_pending_assay_private_20261017`|本机私有数据/分析|未纳入 Git；文件级状态见 S6 审计|
|`brief`|`outputs/brief`|分层目录|原始 brief 与进度对照|
|`brief_gap_audit_private_20261018`|`outputs/brief_gap_audit_private_20261018`|本机私有数据/分析|未纳入 Git；文件级状态见 S6 审计|
|`build_task1_v2_1_transfer.py`|`outputs/build_task1_v2_1_transfer.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`build_task1_v2_transfer.py`|`outputs/build_task1_v2_transfer.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`build_task1_v3_transfer.py`|`outputs/build_task1_v3_transfer.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`build_task1_v5_stage0_transfer.py`|`outputs/build_task1_v5_stage0_transfer.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`campaign_v0`|`outputs/campaign_v0`|代码包|保留顶层以维持现有模块入口|
|`candidate_assay_reviews`|`outputs/candidate_assay_reviews`|历史数据/证据|本机保留；标签数据由 Git 忽略|
|`candidate_discovery_runs`|`outputs/candidate_discovery_runs`|历史数据/证据|本机保留；标签数据由 Git 忽略|
|`candidate_discovery_v0`|`outputs/candidate_discovery_v0`|代码包|保留顶层以维持现有模块入口|
|`check_project_sync.py`|`outputs/check_project_sync.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`chembl37_assay_prescreen.sql`|`outputs/chembl37_assay_prescreen.sql`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`chembl37_schema_documentation.txt`|`outputs/chembl37_schema_documentation.txt`|文件|具体用途见文件内容|
|`closeout_task1_v3.py`|`outputs/closeout_task1_v3.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`closeout_task1_v4.py`|`outputs/closeout_task1_v4.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`curate_chembl37_batch.py`|`outputs/curate_chembl37_batch.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`curate_remaining_chembl37.py`|`outputs/curate_remaining_chembl37.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`curate_selected_chembl37_assays.py`|`outputs/curate_selected_chembl37_assays.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`curation_agent_v1`|`outputs/curation_agent_v1`|代码包|保留顶层以维持现有模块入口|
|`curation_agent_v2`|`outputs/curation_agent_v2`|代码包|保留顶层以维持现有模块入口|
|`curation_agent_v2_1`|`outputs/curation_agent_v2_1`|代码包|保留顶层以维持现有模块入口|
|`curation_agent_v3`|`outputs/curation_agent_v3`|代码包|保留顶层以维持现有模块入口|
|`curation_agent_v4`|`outputs/curation_agent_v4`|代码包|保留顶层以维持现有模块入口|
|`deferred_moves.md`|`outputs/deferred_moves.md`|文件|具体用途见文件内容|
|`devlog`|`outputs/devlog`|分层目录|历史开发记录|
|`download_chembl37_parallel.py`|`outputs/download_chembl37_parallel.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`download_chembl37_sqlite.sh`|`outputs/download_chembl37_sqlite.sh`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`dyrk3_prefreeze_v0`|`outputs/dyrk3_prefreeze_v0`|代码包|保留顶层以维持现有模块入口|
|`enumerate_chembl37_assays.py`|`outputs/enumerate_chembl37_assays.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`env`|`outputs/env`|分层目录|本地环境配置；敏感文件被 Git 忽略|
|`extract_p1_p5_summaries.py`|`outputs/extract_p1_p5_summaries.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`first_sample_row_review`|`outputs/first_sample_row_review`|历史数据/证据|本机保留；标签数据由 Git 忽略|
|`freeze_v1`|`outputs/freeze_v1`|代码包|保留顶层以维持现有模块入口|
|`INDEX.md`|`outputs/INDEX.md`|导航|outputs 目录导航|
|`inspect_chembl_sample.py`|`outputs/inspect_chembl_sample.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`install_task1_v2.py`|`outputs/install_task1_v2.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`install_task1_v2_1.py`|`outputs/install_task1_v2_1.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`install_task1_v3.py`|`outputs/install_task1_v3.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`low_hit_fallback_design_private_20261017`|`outputs/low_hit_fallback_design_private_20261017`|本机私有数据/分析|未纳入 Git；文件级状态见 S6 审计|
|`monthly_prototype_guidance_v0_2_20261017.md`|`outputs/monthly_prototype_guidance_v0_2_20261017.md`|草案（兼容路径）|被现有复核和标准重建脚本按旧路径读取，暂留顶层|
|`monthly_prototype_guidance_v0_2_20261017.receipt.json`|`outputs/monthly_prototype_guidance_v0_2_20261017.receipt.json`|草案（兼容路径）|被现有复核和标准重建脚本按旧路径读取，暂留顶层|
|`oracle_boundary_v0`|`outputs/oracle_boundary_v0`|代码包|保留顶层以维持现有模块入口|
|`p1_negcoverage_private_20261018`|`outputs/p1_negcoverage_private_20261018`|本机私有数据/分析|未纳入 Git；文件级状态见 S6 审计|
|`p5_init_gate_private_20261018`|`outputs/p5_init_gate_private_20261018`|本机私有数据/分析|未纳入 Git；文件级状态见 S6 审计|
|`p5_standard_table_private_20261018`|`outputs/p5_standard_table_private_20261018`|本机私有数据/分析|未纳入 Git；文件级状态见 S6 审计|
|`package_task1_v4.py`|`outputs/package_task1_v4.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`PATH_MIGRATION_20261018.csv`|`outputs/PATH_MIGRATION_20261018.csv`|文件|具体用途见文件内容|
|`plan_local_cleanup.py`|`outputs/plan_local_cleanup.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`prepare_chembl37_sqlite.py`|`outputs/prepare_chembl37_sqlite.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`private`|`outputs/private`|分层目录|本机私有逐化合物数据；数据文件不进入 Git|
|`project_backup_v1.py`|`outputs/project_backup_v1.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`protocols`|`outputs/protocols`|分层目录|冻结协议和草案分层存放|
|`query_pubchem_sample_synonyms.py`|`outputs/query_pubchem_sample_synonyms.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`r0_integrity_20261018`|`outputs/r0_integrity_20261018`|研究产物|状态和用途见目录内说明；检查 Git 忽略规则|
|`r1_criteria_reconstruction_20261018`|`outputs/r1_criteria_reconstruction_20261018`|研究产物|状态和用途见目录内说明；检查 Git 忽略规则|
|`r2_threshold_counts_private_20261018`|`outputs/r2_threshold_counts_private_20261018`|本机私有数据/分析|未纳入 Git；文件级状态见 S6 审计|
|`r3_ranked_numeric_private_20261018_v2`|`outputs/r3_ranked_numeric_private_20261018_v2`|本机私有数据/分析|未纳入 Git；文件级状态见 S6 审计|
|`r5_cpu_controls_private_20261018`|`outputs/r5_cpu_controls_private_20261018`|本机私有数据/分析|未纳入 Git；文件级状态见 S6 审计|
|`r5_glm_response_private_20261018`|`outputs/r5_glm_response_private_20261018`|本机私有数据/分析|未纳入 Git；文件级状态见 S6 审计|
|`r5_matched_order_private_20261018`|`outputs/r5_matched_order_private_20261018`|本机私有数据/分析|未纳入 Git；文件级状态见 S6 审计|
|`r5_reveal_accounting_private_20261018`|`outputs/r5_reveal_accounting_private_20261018`|本机私有数据/分析|未纳入 Git；文件级状态见 S6 审计|
|`r7_oracle_service_private_20261018`|`outputs/r7_oracle_service_private_20261018`|本机私有数据/分析|未纳入 Git；文件级状态见 S6 审计|
|`r8_task1_failures_private_20261018`|`outputs/r8_task1_failures_private_20261018`|本机私有数据/分析|未纳入 Git；文件级状态见 S6 审计|
|`README.md`|`outputs/README.md`|导航|outputs 目录导航|
|`reconcile_acc2_patent_sample.py`|`outputs/reconcile_acc2_patent_sample.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`reconcile_tace_patent_sample.py`|`outputs/reconcile_tace_patent_sample.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`remote_30_candidate_review`|`outputs/remote_30_candidate_review`|研究产物|状态和用途见目录内说明；检查 Git 忽略规则|
|`remote_sync_20261014`|`outputs/remote_sync_20261014`|研究产物|状态和用途见目录内说明；检查 Git 忽略规则|
|`replay_task1_feedback_v3.py`|`outputs/replay_task1_feedback_v3.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`reporting_v1`|`outputs/reporting_v1`|代码包|保留顶层以维持现有模块入口|
|`results`|`outputs/results`|历史数据/证据|本机保留；标签数据由 Git 忽略|
|`review_candidate_assays.py`|`outputs/review_candidate_assays.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`review_task1_v3_archive.py`|`outputs/review_task1_v3_archive.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`run_chembl37_batch_after_prescreen.sh`|`outputs/run_chembl37_batch_after_prescreen.sh`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`run_chembl37_prescreen_after_download.sh`|`outputs/run_chembl37_prescreen_after_download.sh`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`s_restructure_20261018`|`outputs/s_restructure_20261018`|整理审计|本次 S1–S7 清单、报告和核验脚本|
|`scripts`|`outputs/scripts`|分层目录|一次性脚本按用途归类|
|`select_s1pr1_source_sample.py`|`outputs/select_s1pr1_source_sample.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`select_source_audit_samples.py`|`outputs/select_source_audit_samples.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`source_alignment_20261015`|`outputs/source_alignment_20261015`|历史数据/证据|本机保留；标签数据由 Git 忽略|
|`source_alignment_v1`|`outputs/source_alignment_v1`|代码包|保留顶层以维持现有模块入口|
|`source_context`|`outputs/source_context`|研究产物|目录内的运行状态和文件说明其用途|
|`source_review_20261014T101612Z_a227b5e7`|`outputs/source_review_20261014T101612Z_a227b5e7`|历史数据/证据|本机保留；标签数据由 Git 忽略|
|`src`|`outputs/src`|分层目录|代码包说明；可复用包仍在 outputs 顶层|
|`summarize_chembl37_curation.py`|`outputs/summarize_chembl37_curation.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`tace_patent_us9926281_sample_values.json`|`outputs/tace_patent_us9926281_sample_values.json`|文件|具体用途见文件内容|
|`tace_source_value_review_20261017.md`|`outputs/tace_source_value_review_20261017.md`|文件|具体用途见文件内容|
|`task1_curation_agent_v1_validation.json`|`outputs/task1_curation_agent_v1_validation.json`|文件|具体用途见文件内容|
|`task1_feedback_audit_validation`|`outputs/task1_feedback_audit_validation`|研究产物|状态和用途见目录内说明；检查 Git 忽略规则|
|`task1_feedback_replay_20261015`|`outputs/task1_feedback_replay_20261015`|研究产物|状态和用途见目录内说明；检查 Git 忽略规则|
|`task1_v1_review_20261015`|`outputs/task1_v1_review_20261015`|历史数据/证据|本机保留；标签数据由 Git 忽略|
|`task1_v2_1_delivery`|`outputs/task1_v2_1_delivery`|研究产物|状态和用途见目录内说明；检查 Git 忽略规则|
|`task1_v2_1_package_validation.json`|`outputs/task1_v2_1_package_validation.json`|文件|具体用途见文件内容|
|`task1_v2_1_validation`|`outputs/task1_v2_1_validation`|研究产物|状态和用途见目录内说明；检查 Git 忽略规则|
|`task1_v2_delivery`|`outputs/task1_v2_delivery`|历史数据/证据|本机保留；标签数据由 Git 忽略|
|`task1_v2_package_validation.json`|`outputs/task1_v2_package_validation.json`|文件|具体用途见文件内容|
|`task1_v2_validation`|`outputs/task1_v2_validation`|历史数据/证据|本机保留；标签数据由 Git 忽略|
|`task1_v3_archive_review_20261016`|`outputs/task1_v3_archive_review_20261016`|研究产物|状态和用途见目录内说明；检查 Git 忽略规则|
|`task1_v3_delivery`|`outputs/task1_v3_delivery`|研究产物|状态和用途见目录内说明；检查 Git 忽略规则|
|`task1_v3_final_checks`|`outputs/task1_v3_final_checks`|研究产物|状态和用途见目录内说明；检查 Git 忽略规则|
|`task1_v3_package_validation.json`|`outputs/task1_v3_package_validation.json`|文件|具体用途见文件内容|
|`task1_v3_replay_release_validation`|`outputs/task1_v3_replay_release_validation`|研究产物|状态和用途见目录内说明；检查 Git 忽略规则|
|`task1_v3_validation`|`outputs/task1_v3_validation`|研究产物|状态和用途见目录内说明；检查 Git 忽略规则|
|`task1_v4_delivery`|`outputs/task1_v4_delivery`|研究产物|状态和用途见目录内说明；检查 Git 忽略规则|
|`task1_v5_execution_plan_20261016.md`|`outputs/task1_v5_execution_plan_20261016.md`|协议（兼容路径）|被进度快照脚本按旧路径读取，暂留顶层|
|`task1_v5_protocol_lock_20261016.json`|`outputs/task1_v5_protocol_lock_20261016.json`|协议（兼容路径）|被进度快照脚本按旧路径读取，暂留顶层|
|`task1_v5_source_adjudication_rules_20261016.md`|`outputs/task1_v5_source_adjudication_rules_20261016.md`|协议（兼容路径）|被进度快照脚本按旧路径读取，暂留顶层|
|`test_audit_task1_finished_v1.py`|`outputs/test_audit_task1_finished_v1.py`|测试|测试仍在原位置以维持导入路径|
|`test_audit_value_quantization_chembl37.py`|`outputs/test_audit_value_quantization_chembl37.py`|测试|测试仍在原位置以维持导入路径|
|`test_check_project_sync.py`|`outputs/test_check_project_sync.py`|测试|测试仍在原位置以维持导入路径|
|`test_chembl37_assay_prescreen.py`|`outputs/test_chembl37_assay_prescreen.py`|测试|测试仍在原位置以维持导入路径|
|`test_chembl37_batch_curation.py`|`outputs/test_chembl37_batch_curation.py`|测试|测试仍在原位置以维持导入路径|
|`test_closeout_task1_v3.py`|`outputs/test_closeout_task1_v3.py`|测试|测试仍在原位置以维持导入路径|
|`test_closeout_task1_v4.py`|`outputs/test_closeout_task1_v4.py`|测试|测试仍在原位置以维持导入路径|
|`test_curate_remaining_chembl37.py`|`outputs/test_curate_remaining_chembl37.py`|测试|测试仍在原位置以维持导入路径|
|`test_project_backup_v1.py`|`outputs/test_project_backup_v1.py`|测试|测试仍在原位置以维持导入路径|
|`test_reconcile_acc2_patent_sample.py`|`outputs/test_reconcile_acc2_patent_sample.py`|测试|测试仍在原位置以维持导入路径|
|`test_reconcile_tace_patent_sample.py`|`outputs/test_reconcile_tace_patent_sample.py`|测试|测试仍在原位置以维持导入路径|
|`test_review_task1_v3_archive.py`|`outputs/test_review_task1_v3_archive.py`|测试|测试仍在原位置以维持导入路径|
|`test_select_s1pr1_source_sample.py`|`outputs/test_select_s1pr1_source_sample.py`|测试|测试仍在原位置以维持导入路径|
|`test_select_source_audit_samples.py`|`outputs/test_select_source_audit_samples.py`|测试|测试仍在原位置以维持导入路径|
|`test_summarize_chembl37_curation.py`|`outputs/test_summarize_chembl37_curation.py`|测试|测试仍在原位置以维持导入路径|
|`tests`|`outputs/tests`|分层目录|测试整理说明；测试本体暂留原位|
|`validate_task1_v2.py`|`outputs/validate_task1_v2.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|
|`verify_task1_v4_archive.py`|`outputs/verify_task1_v4_archive.py`|单次脚本|未移动脚本；原因见 deferred_moves.md 或 S5 分类表|

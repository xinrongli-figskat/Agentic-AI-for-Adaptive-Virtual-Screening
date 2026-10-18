# S5 延后移动清单

这些文件先留在原路径，避免在本卡中修改代码和测试。恢复移动前需单独改造并验证引用。

## 脚本

- `audit_s1pr1_archived_assay.py`：depends on sibling assay_audit_v0 via Path(__file__).parent; moving breaks lookup
- `audit_task1_finished_v1.py`：external code/path reference(s): test_audit_task1_finished_v1.py:7
- `audit_value_quantization_chembl37.py`：external code/path reference(s): test_audit_value_quantization_chembl37.py:3
- `build_task1_v2_1_transfer.py`：computes project root with Path(__file__).parent.parent; moving changes root
- `build_task1_v2_transfer.py`：computes project root with Path(__file__).parent.parent; moving changes root
- `build_task1_v3_transfer.py`：computes project root with Path(__file__).parent.parent; moving changes root
- `build_task1_v5_stage0_transfer.py`：uses current script directory as HERE; moving changes source location
- `check_project_sync.py`：external code/path reference(s): test_check_project_sync.py:7
- `chembl37_assay_prescreen.sql`：external code/path reference(s): b1_nonhit_limited_20261017/run_b1.py:25, b1_nonhit_limited_20261017/run_b1.py:31, b1_nonhit_limited_20261017/run_b1.py:43, b1_nonhit_limited_private_20261017/run_b1.py:25, b1_nonhit_limited_private_20261017/run_b1.py:31, b1_nonhit_limited_private_20261017/run_b1.py:43, run_chembl37_prescreen_after_download.sh:21, test_chembl37_assay_prescreen.py:100
- `closeout_task1_v3.py`：external code/path reference(s): test_closeout_task1_v3.py:9
- `closeout_task1_v4.py`：external code/path reference(s): build_task1_v5_stage0_transfer.py:12, build_task1_v5_stage0_transfer.py:13, test_closeout_task1_v4.py:12
- `curate_chembl37_batch.py`：external code/path reference(s): curate_remaining_chembl37.py:15, curate_selected_chembl37_assays.py:14, p1_negcoverage_private_20261018/closeout.py:57, p1_negcoverage_private_20261018/run_p1.py:66, run_chembl37_batch_after_prescreen.sh:34, summarize_chembl37_curation.py:13, test_chembl37_batch_curation.py:10
- `curate_remaining_chembl37.py`：external code/path reference(s): test_curate_remaining_chembl37.py:3
- `curate_selected_chembl37_assays.py`：uses Path(__file__).parent as project root; moving changes root
- `download_chembl37_parallel.py`：external code/path reference(s): switch_chembl37_to_parallel.sh:18
- `download_chembl37_sqlite.sh`：external code/path reference(s): start_chembl37_download.sh:11, switch_chembl37_to_parallel.sh:6
- `enumerate_chembl37_assays.py`：external code/path reference(s): b1_nonhit_limited_20261017/run_b1.py:25, b1_nonhit_limited_20261017/run_b1.py:32, b1_nonhit_limited_20261017/run_b1.py:34, b1_nonhit_limited_private_20261017/run_b1.py:25, b1_nonhit_limited_private_20261017/run_b1.py:32, b1_nonhit_limited_private_20261017/run_b1.py:34, reconcile_pubchem_tnap.py:13, run_chembl37_prescreen_after_download.sh:19
- `extract_p1_p5_summaries.py`：uses parents[1] as BASE; moving changes base
- `inspect_chembl_sample.py`：external code/path reference(s): check_remote_progress_20261015.py:30, remote_sync_20261014/tests/test_inspect_chembl_sample.py:11, remote_sync_20261014/tests/test_inspect_chembl_sample.py:13, source_review_20261014T101612Z_a227b5e7/work/fetch_selected_chembl_context.py:13, source_review_20261014T101612Z_a227b5e7/work/fetch_selected_chembl_context.py:27
- `install_task1_v2.py`：external code/path reference(s): build_task1_v2_transfer.py:16, build_task1_v2_transfer.py:29, build_task1_v2_transfer.py:41, build_task1_v2_transfer.py:72, build_task1_v2_transfer.py:78
- `install_task1_v2_1.py`：external code/path reference(s): build_task1_v2_1_transfer.py:16, build_task1_v2_1_transfer.py:34, build_task1_v2_1_transfer.py:52, build_task1_v2_1_transfer.py:81, build_task1_v2_1_transfer.py:85
- `install_task1_v3.py`：external code/path reference(s): build_task1_v3_transfer.py:17, build_task1_v3_transfer.py:33, build_task1_v3_transfer.py:51, build_task1_v3_transfer.py:72, build_task1_v3_transfer.py:75
- `package_task1_v4.py`：uses parents[1] as project root; moving changes root
- `plan_local_cleanup.py`：uses parent.parent as project root; moving changes root
- `prepare_chembl37_sqlite.py`：external code/path reference(s): run_chembl37_prescreen_after_download.sh:18
- `project_backup_v1.py`：external code/path reference(s): complete_project_backup.ps1:13, complete_project_backup.ps1:34, complete_project_backup.ps1:44, test_project_backup_v1.py:7
- `query_pubchem_sample_synonyms.py`：external code/path reference(s): query_s1pr1_all_source_names.py:14
- `reconcile_acc2_patent_sample.py`：external code/path reference(s): test_reconcile_acc2_patent_sample.py:7
- `reconcile_tace_patent_sample.py`：external code/path reference(s): test_reconcile_tace_patent_sample.py:6
- `replay_task1_feedback_v3.py`：external code/path reference(s): build_task1_v3_transfer.py:33, build_task1_v3_transfer.py:51
- `review_candidate_assays.py`：default path resolves candidate_discovery_v0 as sibling; moving breaks default
- `review_task1_v3_archive.py`：external code/path reference(s): test_review_task1_v3_archive.py:8
- `run_chembl37_batch_after_prescreen.sh`：external code/path reference(s): start_chembl37_batch.sh:9
- `run_chembl37_prescreen_after_download.sh`：external code/path reference(s): start_chembl37_pipeline.sh:8
- `select_s1pr1_source_sample.py`：external code/path reference(s): test_select_s1pr1_source_sample.py:4
- `select_source_audit_samples.py`：external code/path reference(s): test_select_source_audit_samples.py:4
- `summarize_chembl37_curation.py`：external code/path reference(s): test_summarize_chembl37_curation.py:3
- `validate_task1_v2.py`：uses parents[1] as project root; moving changes root
- `verify_task1_v4_archive.py`：external code/path reference(s): build_task1_v5_stage0_transfer.py:14, preview_s1pr1_structure.py:15, select_s1pr1_source_sample.py:17, test_closeout_task1_v4.py:14

## 测试

- `outputs/test_audit_task1_finished_v1.py`：导入被测模块，移动需要同步调整导入/路径：audit_task1_finished_v1@7
- `outputs/test_audit_value_quantization_chembl37.py`：导入被测模块，移动需要同步调整导入/路径：audit_value_quantization_chembl37@3
- `outputs/test_check_project_sync.py`：导入被测模块，移动需要同步调整导入/路径：check_project_sync@7
- `outputs/test_chembl37_assay_prescreen.py`：__file__ 相对路径锚点会随移动改变; 导入被测模块，移动需要同步调整导入/路径：__future__@2,enumerate_chembl37_assays@9
- `outputs/test_chembl37_batch_curation.py`：__file__ 相对路径锚点会随移动改变; 导入被测模块，移动需要同步调整导入/路径：assay_audit_v0@9,curate_chembl37_batch@10
- `outputs/test_closeout_task1_v3.py`：导入被测模块，移动需要同步调整导入/路径：closeout_task1_v3@9,curation_agent_v3.integrity@10
- `outputs/test_closeout_task1_v4.py`：__file__ 相对路径锚点会随移动改变; 导入被测模块，移动需要同步调整导入/路径：__future__@2,closeout_task1_v4@12,curation_agent_v4.run@13,verify_task1_v4_archive@14
- `outputs/test_curate_remaining_chembl37.py`：导入被测模块，移动需要同步调整导入/路径：curate_remaining_chembl37@3
- `outputs/test_project_backup_v1.py`：导入被测模块，移动需要同步调整导入/路径：project_backup_v1@7
- `outputs/test_reconcile_acc2_patent_sample.py`：__file__ 相对路径锚点会随移动改变; 导入被测模块，移动需要同步调整导入/路径：reconcile_acc2_patent_sample@7
- `outputs/test_reconcile_tace_patent_sample.py`：__file__ 相对路径锚点会随移动改变; 导入被测模块，移动需要同步调整导入/路径：reconcile_tace_patent_sample@6
- `outputs/test_review_task1_v3_archive.py`：导入被测模块，移动需要同步调整导入/路径：review_task1_v3_archive@8
- `outputs/test_select_s1pr1_source_sample.py`：导入被测模块，移动需要同步调整导入/路径：select_s1pr1_source_sample@4
- `outputs/test_select_source_audit_samples.py`：导入被测模块，移动需要同步调整导入/路径：select_source_audit_samples@4
- `outputs/test_summarize_chembl37_curation.py`：导入被测模块，移动需要同步调整导入/路径：summarize_chembl37_curation@3

## 可执行模块保留原位

- `outputs/freeze_v1/`：包含 Python 包和测试；移动后 `python -B -m unittest freeze_v1.test_create_version` 无法导入，已恢复。
- `outputs/dyrk3_prefreeze_v0/`：包含 Python 包和测试；保留现有模块入口及相对路径。

# D5 Task 1 自主审查运行日志

- 2026-10-20 11:31:37 UTC：本机从固定 R3 62 项队列重算六项数值门槛，核对 R3 输入哈希，封存不含人工裁决的六份事实包；`inputs_locked.json` SHA-256 为 `d90a5ad0c10e1a096621fb6ea15d44990993a9540099c5a3bdcd9e6bc018cdb3`。
- 11:33:20 UTC：动作屏蔽测试本机 6/6 通过；锁定 `agent_protocol.json`、事实包与实际执行的 `gates.py`/`run_agent.py` 等，`agent_lock.json` 早于首个模型请求。远端相同单测 6/6 通过、`run_agent.py check` 通过。
- 11:34–11:36 UTC：仅在远端独立 `outputs/d5_20261020/d_task1_auto/` 目录运行 GLM，模型 `glm-5.3-flash`；按 TNAP、ACC2、TACE、CPT2、ACLY、S1PR1 顺序各完成四阶段，共 24 次请求，全部有合法动作与回执。总预算 30，未用 6 次；没有第七候选、没有新 ChEMBL HTTP 请求、没有 campaign 查询。
- 六项模型判断完成后才在本机生成 `human_reference_postrun.json` 并运行 `evaluate.py`；正式 precision/recall 分母为 5，S1PR1 暂定状态排除。结果 TP=1、FP=1（TACE）、TN=3、FN=0。回执请求内容逐条检查，无 `human_reference_verdict` 或人类参考文件名。
- 远端只读重算 TNAP 私有 H5 化合物表的深度关联，汇总 AUC `0.8785348526`、r `0.4948945406`，没有导出化合物级标签；汇总收据为 `tnap_depth_recheck.json`。
- 运行后远端只读核对 DYRK3/TNAP 冻结物及两份旧 campaign 核心文件，哈希与 `outputs/d5_20261020/d5_baseline.json` 完全一致，详情见 `protected_hashes_after.json`。
- 发现 TACE 科学假阳性后未改写协议、证据包、模型回执或历史人工结论。下一版可能的结构身份凭证屏蔽写在 `source_identity_gate_proposal.md`，本轮不实施、不回放。

环境：本地 Windows 工作区；远端 `lab-4090` `/driveA/xinrong/agentic-screening` 的 Python 3.10 虚拟环境。智谱 API key 从远端受保护文件注入进程环境，仅用于调用，不写入回执或报告。

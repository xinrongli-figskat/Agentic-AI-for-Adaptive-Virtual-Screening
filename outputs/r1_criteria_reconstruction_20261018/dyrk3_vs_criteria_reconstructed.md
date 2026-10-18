post-exposure 的证据整理，不是新 benchmark、盲验证或新 campaign。

# DYRK3 v1 对现行 v2+ 门槛（重建）

B2 已保存的独立指标 outputs/b2_candidate_metrics_private_20261017/candidate_metrics.csv:64 与原审查设置 outputs/assay_audit_v0/audit_policy_v0.json:30、outputs/assay_audit_v0/audit_policy_v0.json:31、outputs/assay_audit_v0/audit_policy_v0.json:32、outputs/assay_audit_v0/audit_policy_v0.json:33 一致：Morgan r2、2048 bit、手性、Tanimoto 0.7 / Butina 距离 0.3。此处复核 B2 的同设置再计算结果，而非本次从 SMILES 新运行聚类。最大簇 72/231=31.17%；Murcko 桶 101。先前报告的约 31% 与之吻合。

三项例外：231<250；72/231=31.17%>25%；50/231=21.65%>20%。其余计数：116 hit≥30、115 measured nonhit≥100、单类别初始化概率 0.0015954≤0.5、骨架桶101≥10。原 v1 冻结原型不因 v2+ 门槛而撤销；它不是通用 benchmark。

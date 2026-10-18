post-exposure 的证据整理，不是新 benchmark、盲验证或新 campaign。

# 标准演变（仅据可见文件）

- candidate_scope_v0.1：1000 nM IC50、B 型、单蛋白、潜在重复剔除信号；500 来源分子 ID、30/100 支持 ID 为预筛优先条件。见 outputs/candidate_discovery_v0/criteria_v0.json:17。
- audit_v0：引入结构与删失/冲突核查及 Morgan/Butina 设置；尚未自动判资格。见 outputs/assay_audit_v0/audit_policy_v0.json:42。
- task1_agent_v1：整理后最低 500、30/100、置信度9、簇≤25%、骨架桶≥10、双侧初始化概率≤0.5、50次查询。见 outputs/curation_agent_v1/protocol.json:5–outputs/curation_agent_v1/protocol.json:13。双侧门槛的 0.5 数值来源未记录。
- task1_agent_v2：最低改为250，500改为优先层，增加 50/N≤20%；理由仅记录为控制查询占比并扩大有限可行性审查。见 outputs/curation_agent_v2/CRITERIA_REVIEW.md:5、outputs/curation_agent_v2/CRITERIA_REVIEW.md:14。其余保留。
- task1_agent_v3：在现有 protocol 中未见这些资格数值进一步改变；接口/工具反馈修订不算科学门槛变更。

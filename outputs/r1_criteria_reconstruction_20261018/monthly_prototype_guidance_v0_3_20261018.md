# 本月原型推进记录 v0.3（由 v0.2 复制并更正）

日期：2026-10-18。**状态：post-exposure 工作草案，未冻结；不是盲验证或新 benchmark 声明。**本文件在既有结果之后整理，不能回写 DYRK3 v1、Task 1 v1–v4 或 v5 来源判定规则。本版文件哈希与 UTC 生成时间见本目录 `MANIFEST.json` 和 `RUN_LOG.md`；v0.2 原件保留。

依据：`01_original_brief_from_chat.md`、`freeze_v1/protocol_decisions.md`、`benchmark_build_progress_20261017.md`、导师本月反馈及现存运行代码/证据。若与冻结协议冲突，以冻结协议为准；修改只能作为新版本或明确的偏离。

## 已核实的定位和门槛

- DYRK3 v1 是单 assay、同系列、已冻结且已运行的**可行性原型**。231 个可查询化合物、116 命中支持、115 非命中支持。相对于后来为新候选设定的 v2+ 操作性门槛，它有**三项例外**：231 < 250；最大 Butina 簇 72/231 = 31.17% > 25%；50/231 = 21.65% > 20%。这里比较的是同一 `assay_audit_v0/audit_policy_v0.json`：Morgan radius 2、2048-bit、含手性，Tanimoto 相似度阈值 0.7（Butina 距离阈值 0.3）。原审查代码与 v2 所带审查代码 SHA-256 相同。原先 500 门槛是优先审查规模，v2+ 的 500 是“更理想”，不是 brief 的硬标准。
- 类别最低数 30 hit、100 measured nonhit 是为两类覆盖和 10+40 查询反馈实验设定的操作性过滤器，**未经独立统计功效论证**，并非普适的生物学标准。缺测、阈值不确定或 decoy 都不能填入 measured nonhit。
- 当前 Task 1 离线漏斗：原始 IC50 记录不少于 250 的 assay 1,206 → type B 979 → 单蛋白且映射置信度至少 9 的 assay 512 → 来源分子 ID 数值预筛通过 81。81/81 完成 RDKit 整理；B3 补算后 62 个通过、19 个未过、0 个待补。没有第二个来源/端点批准且冻结的 benchmark。来源审查仍依赖逐条人工证据核实，不能把整个流程称为全自动。

## R1：实测非命中不足的补充统计（已完成，离线且无 GLM）

使用原 ChEMBL 37 SQLite 枚举器已经保存的**完整 512-assay 结果**重算，输入 `result.json` SHA-256 为 `f7ad0d2e45f0890f4833fafc99c1db2733bc70231875d51ac42f597052c218a5`，其 manifest 指向官方数据库 SHA-256 `4be13df3b68e25dcd0bff44bf094033b5aebe98f415acdc8c1cdf380e0c15142`、原 SQL SHA-256 `9e97d5efaaf7d3861af2ba765b8d1e30e8f70aeda39b268f9d92f2cfaacb7952`。本次未重新查询数据库；复用原枚举器按等值、删失界值、单位、重复及有效性标记产生的**来源分子 ID 预筛支持状态**。脚本和结果另存哈希，不修改原清单。

- 328 个 assay 达到 hit-support ID ≥30，但 nonhit-support ID <100；其中 102 个的两类支持总数仍 <250，不能称作“只差非命中”。
- **226 个**已达到两类支持总数 ≥250、hit-support ID ≥30，预筛数值三门槛中只有 nonhit-support ID <100；来源层级分别是 BindingDB 专利 191、直接专利 32、其他/未知 3、带 DOI/PubMed 的文献元数据 0。若补足实测非命中，它们在此三项**预筛计数**上可能通过；结构、实验端点、来源身份、多样性和真实 campaign 资格仍未审定。
- 因此导师 Q2 应回答“**确实遇到，而且在数值预筛层面并不少；但尚不能断言其中多少是科学审查后仅剩这一障碍**”。不应根据 226 直接生成 decoy 或改变既有 81-assay 漏斗。高 hit/低 nonhit 的专利记录还须检查数值分辨率、选择性报告和原始实验范围。
- 结果位于本机 `.sync_audit/chembl37_benchmark_20261017/nonhit_bottleneck_r1_e72cad5ea7902859/`，其中逐 assay CSV 留在本地审查区，不进入任何 campaign 公共路径；重算代码为 `outputs/audit_nonhit_bottleneck_chembl37.py`。

## 决策系统、证据边界与现有对照

- 代码核对了实际 GLM 请求：`campaign_v0/llm_controller.py` 仅从公共状态构造计数、已揭示结果、kNN 分数/相似度摘要和允许策略；`campaign_v0/glm_api.py` 将该摘要作为用户消息发出。**GLM 请求不含候选 SMILES、完整化学结构或未揭示标签**。表示由运行参数预先固定，不是 GLM 决策变量。GLM 每轮仅在 `knn_greedy`、`knn_diverse`、`uniform_random` 之间选择并说明理由。Python 以已揭示标签重新计算加权 kNN，并按策略挑选下一批。
- bit 主分析下 5 个同种子配对差：fixed greedy − random 为 `[3,14,8,11,1]`，均值 +7.4、样本标准差 5.41；LLM − fixed 为 `[-4,-4,-4,-1,3]`，均值 −2.0、样本标准差 3.08。只应称“在这五个种子中 fixed greedy 高于随机”，不能用边际标准差或小样本推断普遍显著收益。GLM 相对 fixed 没有额外收益证据。
- “反馈驱动流程已运行”可由每轮先揭示、再重算和更新下一批的轨迹证明；**“标签反馈本身造成性能提升”尚未由反事实对照证明**。Task 2 v2 增加按种子配对的标签置换/打乱对照，置换只能用于受控评估分支，不接触主 campaign；预先写明何时置换、保存随机种子及预算，比较差值分布，而不预设必然回落到随机水平。
- 随机 H@50 全池期望是 50×116/231 ≈25.11；五种子实测平均 22.4。差异本身不足以判采样器异常；另做 ≥10,000 种子的离线采样核对，保存均值、方差及采样器实现哈希。不得据此重抽原五个种子。

## 已见候选的当前状态

- p300：HAT 域与全长蛋白解释及多个 Isomer 的来源身份未完全解决，**hold**；不冻结。P2X：现有证据指向人 P2X2/3 异聚受体功能拮抗，不能当成孤立 P2X2；结构身份/跨专利重复仍待核，作为原孤立 P2X2 解释**不适用**，异聚体候选仍待审。
- S1PR1 `CHEMBL5734042`：暂定 293 可用、52/241；抽样专利值已对齐，但 `AA IC50` 的实验方法/构建体仍未解决，`campaign_ready=false`。这是**来源端点未解决的候选**，尚未保存最终 `resolved/hold/reject` 裁决。v5 的首次逐条匹配时间是 2026-10-16 15:22:39 UTC；两日上限为 2026-10-18 15:22:39 UTC，四小时实际人工工时是否已用完仍需核对。到点后按锁定规则正式记 `hold` 或其他有证据的裁决，不回写 v4。
- ACC2、TNAP、CPT2、TACE、ACLY 的缺口分别是结构/质谱疑点、蛋白构建体、原始捐赠数据方法、专利结构身份、跨阈值区间标签。均未 campaign-ready。v5 的三项未见候选封存及人工/GLM 同证据包独立判定**尚未完成**。

## v0.2 当时的后续顺序与尚未决定的参数（历史草案，现以 v0.3 补记为准）

1. R2：对 1,765 化合物的待补 assay 另记计算上限偏离，分块或提高成对多样性上限，保留原/新配置和资源用量。
2. R3：私有工作区内给 62 个数值通过 assay 补最大 Butina 簇、骨架数、前三簇和簇内命中率，并列随机 H@50 期望与十次初始化无命中概率；不导出到 campaign 公共池。
3. R4–R5：在继续看新候选前固定来源审查排序、时间盒和选取数量；优先收口现有五个待审来源，逐条记录 `resolved/hold/reject`。无来源结论不冻结数据集。
4. R6：仅对封存的同一来源证据包做人和 GLM 各自独立判定，GLM 不见人工结论；样本太小，不报准确率。
5. 兼容 assay 合并**允许但未实施**：须对齐蛋白/物种、构建体、端点、方法、单位和重叠化合物，并新建版本。Decoy **尚未生成**；只有来源、端点和结构已解决且实测非命中不足仍是主要障碍时，才考虑一个与实测池分开报告的 `decoy_assumed_inactive` 版本。未测类似物不充作 decoy。
6. Task 2 v2 仍是草案：先确定新池和冻结标签，再固定种子、同种子初始化、控制器、主比较、多重比较处理、标签置换对照和失败处理。运行前做合成 oracle 防泄漏检查。**不要**因 DYRK3 或新池的已见结果选择特征、阈值、种子或控制器。

仍待正式决策：decoy:hit 比例（仅在确实使用 decoy 时）、新候选命中率优先区间和审查数量、固定调度及规则自适应的精确定义、多个主比较的处理方式。这些未定项不应假装已预注册。


## v0.3 补记：已核实 A2–A3、B1–B3、P1、P5（post-exposure）

- A2: outputs/a2_llm_input_audit_private_20261017/llm_input_audit.md；SHA-256 f54adfb600a1f33c0747594eea3f4f006b662263c99c2f8be13ae958ebc6e647。
- A3: outputs/a3_dyrk3_supplement_private_20261017/group_H50.csv；SHA-256 d2133c7a40b116c98348bc21e14e4c8724be2f4ae8de434506788b4f11851991。
- B1（通过 P1 输入复核）: outputs/p1_negcoverage_private_20261018/p1_input_check.json；SHA-256 9f3dd012a238fddd862587ed3e27b28991944cccc0adf87245ccc93d59d1d064。
- B2: outputs/b2_candidate_metrics_private_20261017/candidate_metrics.csv；SHA-256 06fcdfd7d89d446fd956321c0a92a7eebfa4b727dd3f362ae6e23794adb5300d。
- B3: outputs/b3_pending_assay_private_20261017/qualification_addendum.json；SHA-256 e4ade73295fef5b602d590d4b14bea350ff633ed4879f3bc2afbbc6c5ace8ce1。
- P1: outputs/p1_negcoverage_private_20261018/p1_aggregate_totals.json；SHA-256 085d3ed14ca3d0876cb472bd44fed6f444f1759815caee2be842797fe935dac0。
- P5: outputs/p5_init_gate_private_20261018/init_gate_definition.md；SHA-256 16ccb81b8bf36b855b90d29b48a3bdf7126b5dd6d291c93dfb9746c668001a4b。

A2：GLM 仅见聚合状态与已揭示结果，未见候选结构/隐藏标签。A3：bit 的 5 种子固定贪心 H@50 均值 29.8；保留实际初始化后的算术上限均值 44.4（见 `outputs/brief_gap_audit_private_20261018/dyrk3_ceiling.json`）。不得写‘贪心已近上限’。B1：81 个预筛；B2：62 个数值通过；B3：1,765 池的初始化风险未过。P1：226 个非命中不足分支经整理为 A66/B94/C66；P5：门槛是双侧单类别概率≤0.5，数值 0.5 的来源未记录。这些均不构成来源审查通过。

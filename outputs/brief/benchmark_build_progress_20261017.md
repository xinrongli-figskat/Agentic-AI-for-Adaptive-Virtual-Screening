# Benchmark 构建进度与来源审查交接（2026-10-17）

本记录是 **post-exposure 的候选发现与证据整理**，不是新 benchmark 的冻结声明，也不是盲验证。沿用 [v5 来源判定规则](task1_v5_source_adjudication_rules_20261016.md)；不改变 DYRK3 v1、Task 1 v1–v4 或其历史决定。本轮 GLM 调用数为 **0**。

## 数据底座和资格漏斗

- 官方 ChEMBL 37 SQLite 压缩包在 4090 工作站的 `/driveA` 完整下载并按官方 SHA-256 校验；解压库 30,480,314,368 字节，SHA-256 为 `4be13df3b68e25dcd0bff44bf094033b5aebe98f415acdc8c1cdf380e0c15142`。没有放在系统启动盘，也没有复制到本机。
- 本地 SQL 扫描按单 assay 的 IC50、关系符号和来源分子 ID 做便宜的预筛。原始 IC50 记录数达到 250 的 assay 有 1,206 个；其中 type B 为 979 个；叠加单蛋白及映射置信度 ≥9 后为 512 个；满足两类预览支持和当前数值预筛的有 81 个。**预览数不是最终标准化分子数**。
- 这 81 个按元数据暂分：BindingDB 专利 55、直接专利 19、有 DOI/PubMed 的文献 3、其他/未知 4。这里“文献”只表示书目信息存在，不保证是原始实验文章；检查已发现抽中的三篇涉及综述、计算整理或二次汇编，须作为来源待审，不能据此宣布独立原始证据。
- 离线 RDKit 整理现已覆盖 **81/81** 个通过预筛的 assay（涉及 66 个目标）：**62 个通过当前数值/结构门槛，18 个未通过，1 个由于 1,765 个可用分子超出事先设置的精确成对多样性计算上限而待补算**。18 个失败项中有 17 个涉及最大化学簇超限；失败原因可重叠。按元数据来源层级，数值通过数分别为 BindingDB 专利 43、直接专利 13、文献元数据 3、其他来源 3。所有临时类别保存在 `data/curation_private`，**62 个数值通过不等于 62 个获准使用的 benchmark**。
- 追加的只读数值分辨率检查发现：81 个 assay 中 25 个仅有 ≤8 种 IC50 关系符号/数值/单位组合，其中 18 个原本数值通过。它们仅被标为**需要原始来源复核**，不是自动拒绝；见 [ACLY 具体案例](acly_source_value_review_20261017.md)。

## 优先候选（均未获 campaign-ready 资格）

| 候选 | 标准化可用化合物 | 命中/非命中支持 | 已核实内容 | 尚缺内容 |
| --- | ---: | ---: | --- | --- |
| ACC2 `CHEMBL3705476` | 662 | 384 / 278 | [US8835472B2](https://patents.google.com/patent/US8835472B2/en) 明确写出人 ACC2 去掉 N 端 128 氨基酸、昆虫细胞表达、NADH 耦联 ADP 读数；预设 6+6 样本的例号和 IC50 表值在 nM/µM 换算后 12/12 一致。 | 分子结构尚未与专利图逐个独立核对；例 4.28 的专利质谱标为 361 `[M+H]+`，而 ChEMBL 结构预期约 362.211，须查明是否为笔误、绘图/导入差异或身份错误。 |
| 人 TNAP `CHEMBL1738510` | 462 | 53 / 409 | [PubChem 原始 AID 1056](https://pubchem.ncbi.nlm.nih.gov/bioassay/1056) 记载 CDP-star 发光酶活抑制实验；ChEMBL 该 assay 的 485/485 条记录按 SID、IC50 关系符号和数值与 PubChem 原始表完全对齐。 | PubChem 记载蛋白由研究者提供、目标标注为人 TNAP，但蛋白制备/确切构建体未写清。需核实后再定端点可解释范围。PubChem “Active” 阈值为 100 µM，与本项目 1 µM 标签阈值不同，不得照搬。 |
| 人 CPT2 `CHEMBL3431931` | 475 | 32 / 443 | ChEMBL 37 离线结构、冲突、类别及多样性检查通过；来源标为 Roche 捐赠的补充筛选数据。 | 元数据仅写“抑制 CPT2”，缺具体蛋白制备、测量方法及原始逐条表格对齐；关联论文是 [2011 年 Perspective](https://pubs.acs.org/doi/10.1021/jm100809g)，不能自动当作这 476 条新实验的原始方法。 |
| ACLY `CHEMBL5738952` | 466（仅为数据库显示值下的临时数） | 106 / 360（**不能作正式标签**） | 专利写明重组人 ACLY 的 ADP-Glo 酶活实验。 | 专利按 IC50 区间报告；ChEMBL 出现区间中点式数值，其中一个原始区间跨过 1,000 nM 阈值。需逐分子重建区间标签，目前 hold。 |
| 人 TACE/ADAM17 `CHEMBL5733557` | 406 | 40 / 366 | [专利 Table VIII](https://patents.google.com/patent/US9926281B2/en) 给出重组人酶荧光底物实验和逐化合物 nM IC50；固定 6+6 样本的例号、关系符号和数值 12/12 对齐。 | 仍须独立核实 12 个专利结构与 ChEMBL SMILES，尤其三个“一分子对应两例号”条目；目前 hold，见 [单独审查记录](tace_source_value_review_20261017.md)。 |

TNAP 和 CPT2 的暂定命中比例约 11.5% 与 6.7%，比 DYRK3 v1 的近 50% 更适合在**来源核实以后**考察主动筛选策略，但低命中率也可能导致 10 次纯结构初始化没有正例。已锁定的规则要求这种情况按预定随机回退继续，不能依据隐藏标签重抽。

## 证据位置、判断边界与下一步

- 远端预筛：`data/candidate_discovery/chembl37_assay_prescreen_55e8f6d01fb9247d/`；首批结构审查：`data/curation_private/chembl37_batch_curations/chembl37_batch_curation_d1d3b87ef2b3ea4e/`；CPT2：`data/curation_private/chembl37_selected_curations/selected_curation_edbf9ed1bc5303a1/`。
- 其余 68 个 assay 的断点续跑结果：`data/curation_private/chembl37_remaining_curations/remaining_curation_d91b5805eb8ae2cd/`；完整 81-assay 汇总和带来源/资格状态的私有清单：`data/curation_private/chembl37_full_numeric_funnel_20261017/`。汇总程序检查 assay ID 不重复且恰好覆盖预筛集合。
- ACC2 来源样本和 12 项数值对齐：`data/curation_private/source_audits/source_sample_CHEMBL3705476_056b6facbeda4569/`。其 `patent_alignment_v1/` 明确保存 `source_endpoint_resolved=false`，因为结构身份差异尚待解释。
- ACC2 专利原 PDF 也已留在上述目录，SHA-256 为 `eda7c30f9f342f26d176e96a29a92b275ecee87ca89c493f1673557916a80703`。PDF 文本抽取未给出可独立确认例 4.28 图示结构的证据，因此没有用它消除该疑点。
- TNAP 原始 PubChem 文件和全记录对齐：`data/curation_private/source_audits/source_sample_CHEMBL1738510_cccc2760ddd56b29/`。其 `full_alignment_v1/` 同样保存 `campaign_ready=false`。
- 81-assay 数值分辨率复核：`data/curation_private/chembl37_full_numeric_funnel_20261017/value_resolution_audit.json`；发现 ACLY 的明确来源精度疑点后，已在本地和远端保存单独的 hold 说明，没有改写已有数值整理结果。
- 人 TACE/ADAM17 固定来源样本与专利 12/12 名称/值对齐：`data/curation_private/source_audits/source_sample_CHEMBL5733557_39a9c5c75f294b09/`；只证明样本数值与同一表相符，化学结构独立核对仍未完成。
- 下一轮优先核实 TACE 固定 12 个样本的专利结构与 ChEMBL SMILES，并复查三组双例号；同时解决 ACC2 例 4.28 的结构/质谱疑点、寻找 TNAP 蛋白来源的原始说明；CPT2 继续追 Roche 捐赠数据的逐条来源和实验方法。任何未解决项继续 `hold`，不降低阈值、不启动新 campaign。核实之后将同一证据包交由人独立判定，再按锁定规则做一次遮蔽人工结论的 GLM 判定；只在这一决策节点花模型 tokens。
- 4090 工作站本阶段承担大库下载、SQLite 扫描和 RDKit 结构整理，主要消耗磁盘与 CPU。GPU 留给来源已确认、数据集已冻结后的表示学习、非 LLM 自适应基线和 Task 2 实验；不会为了提高 GPU 占用率而提前跑无效训练。

## 当前交付判断

目前已经建立可重复的**全库枚举 → 低成本预筛 → 全部 81 个候选结构整理 → 原始来源核对**流程；62 个在当前数值规则下过关，其中 ACC2、TNAP、CPT2 已进入重点来源审查。**还没有第二个获准冻结的正式 benchmark**。最大阻碍从“找不到足量数据”转为“证明这些数值对应同一种可解释的蛋白实验，并逐条确证分子身份”。

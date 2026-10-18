# 七个化合物、20 条记录与来源关系审查

日期：2026-10-14。证据是用户在远程终端显示的 activity ID、化合物 ID、目标 ID、assay ID、文档 ID 和测量字段。此前显示表中的目标名称、物种和 assay 类别按行与公共字段核对后合并。两次显示的公共字段一致；这里保留的是聊天转录，未替代远程原始 API 快照。

本文及新增的本地复核文件尚未上传到远程。01–05 文档与离线测试的此前上传、远程测试通过状态已由用户确认。

## 核对结果

- 20 条记录的 activity ID 均不同。
- 七个不同 molecule_chembl_id；仍未进行结构标准化，不能直接当作标准化后的结构数。
- 13 条为超出各化合物首次出现的记录：20−7。
- 四个不同 document_chembl_id；未查询文献标题、DOI 或来源类别，不能直接宣称恰好对应四篇独立论文。
- 在本显示范围内，以“化合物 ID、目标 ID、assay ID、测量类型”为键，没有重复键。这不证明所有来源都不存在质量问题或重复引用。

## 化合物各自的记录

| 化合物 ID | 记录数 | 主要涉及内容 |
|---|---|---|
| CHEMBL113081 | 1 | DNA topoisomerase 2-alpha 的 IC50 |
| CHEMBL324340 | 2 | Heparanase IC50；NON-PROTEIN TARGET IC50 |
| CHEMBL109600 | 2 | Heparanase IC50；NON-PROTEIN TARGET 下缺数值的记录 |
| CHEMBL357278 | 2 | 氧化酶 IC50；ADMET 的 % remaining |
| CHEMBL357119 | 2 | 氧化酶 IC50；ADMET 的 % remaining |
| CHEMBL152968 | 8 | 氧化酶 IC50、ADMET 剩余百分比、三个 CYP 目标的 IC50、三个以物种为目标的变化量 |
| CHEMBL174698 | 3 | CCRF-CEM 的 EC50、CC50，以及 Unchecked 目标下的 Selectivity index |

CHEMBL152968 的八条结果不能计作八个不同化合物。也不能全表按化合物 ID 直接去重、只保留一条，否则会丢失不同实验和目标的信息。后续先定义目标、endpoint 和兼容范围，再作化合物层面的重复与冲突处理。

## 同一目标下数值不同的解释

Heparanase 的两条 IC50 是两个不同化合物，在同一 assay `CHEMBL872937` 中：

- CHEMBL324340：2500 nM。
- CHEMBL109600：9000 nM。

氧化酶的三条 IC50 是三个不同化合物，在同一 assay `CHEMBL760688` 中：

- CHEMBL357278：4000 nM。
- CHEMBL357119：17000 nM。
- CHEMBL152968：180 nM。

这些不同数值不是对同一个化合物的相互矛盾测量。此结论只针对当前显示的记录，不宣称完整目标数据已经没有冲突。若以后同一化合物在同一 endpoint 下有不同测量，则需继续检查条件、来源和测量边界。

## 来源记录的分布

| document_chembl_id | 记录数 |
|---|---|
| CHEMBL1137930 | 1 |
| CHEMBL1146658 | 4 |
| CHEMBL1148425 | 12 |
| CHEMBL1138695 | 3 |

同一个来源可能贡献多个化合物和多种结果，因此记录数不能当作独立来源数。当前 API 顺序页面存在明显的来源聚集，仍然不代表全库分布。

## 选择性指数的诊断线索

最后三条记录属于同一个化合物 CHEMBL174698 和同一个来源文档 ID CHEMBL1138695：

- EC50 <63.6 nM，assay CHEMBL651396。
- CC50 >1000000 nM，assay CHEMBL657398。
- Selectivity index >15723 uM，assay CHEMBL845142。

数值工具计算边界之比：1000000 / 63.6 = 15723.270440…。

这支持一个待核查的假设：来源中的指数可能定义为 CC50/EC50。只有确认这个定义和相关实验适用性后，才能采用该解释。若该定义适用于这里的正浓度，两个不等号给出的是指数的下界 >15723.27，而不是精确测得的指数值。

按该比值假设，同单位的浓度相除应抵消单位，因此显示的 uM 值得核查。当前未确认指数定义，未改动源记录单位，未将指数作为蛋白活性或安全性结论。

## 下一步行动及依据

1. 先读取已保存的原始 activity 31882，比较原始 `type/relation/value/units` 与 `standard_` 字段及注释。依据：指数数值可能来自前两条结果，但单位需要解释。
2. 随后查询 assay CHEMBL845142 及来源文档 CHEMBL1138695，核查指数定义与原始报道。这些查询是数据整理上下文中的动作。
3. 查询蛋白例子的 target 与 assay 元数据，确认目标映射、实验读出和条件；随后另外设计正式候选发现范围。
4. 不把这七个化合物当成正式 benchmark，不给缺失结果分配非活性标签，不因本页出现某个目标就将其列为最终候选。

本次仅完成证据复核和下一步工具选择；未实施 LLM 控制器、测量标准化或正式命中分类。

## 本地复核文件与依据

- `first_sample_row_review/displayed_rows_with_ids_transcribed.csv`：两次终端显示内容的核对合并转录。
- `first_sample_row_review/displayed_rows_with_ids_audit.json`：化合物计数、来源计数、重复键检查及指数假设；`labels_assigned=false`。
- [ChEMBL 官方数据接口说明](https://chembl.gitbook.io/chembl-interface-documentation/web-services/chembl-data-web-services)：activity、assay、document 等资源的含义。
- [ChEMBL 官方数据问答](https://chembl.gitbook.io/chembl-interface-documentation/frequently-asked-questions/chembl-data-questions)：数据质量、潜在重复引用与标准化。

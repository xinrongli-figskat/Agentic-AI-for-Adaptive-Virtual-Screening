# 30 个候选的详细计数与五个实验来源审查

日期：2026-10-14。来源：用户贴出的远程输出，以及本机随后读取的 ChEMBL_37 assay/document API。没有直接读取远程原始 activity 文件。本报告不是正式 benchmark 资格结论。

## 主要结果

| 目标 | 已读分子 ID | 命中支持 | 非命中支持 | 两类都有 | 单一 assay 支持数 | assay 命中/非命中 |
|---|---:|---:|---:|---:|---:|---:|
| CHEMBL4822 / BACE1 | 773 | 451 | 309 | 24 | 28 | 17 / 11 |
| CHEMBL204 / Prothrombin | 945 | 285 | 533 | 5 | 94 | 20 / 74 |
| CHEMBL3769299 / Npt2a | 538 | 478 | 57 | 1 | 521 | 470 / 51 |
| CHEMBL4575 / DYRK3 | 457 | 199 | 262 | 4 | 231 | 116 / 115 |
| CHEMBL4372 / Lethal factor | 447 | 57 | 396 | 17 | 50 | 28 / 22 |

前两个目标只读了按 activity_id 排序的前 1000 条 IC50 记录，不能外推整个目标的数据分布。其余三个是在当前 IC50 查询范围内完整获取，仍不等于完整覆盖该目标的所有来源或 endpoint。

这些都是分子 ID 和暂定证据支持计数，没有进行结构标准化或形成最终标签。全目标的两个证据集合可以重叠。例如 BACE1 的至少一类支持为 451+309-24=736 个 ID，另外 773-736=37 个 ID 没有这两类支持。不能把 451+309 当作互斥类别总数，也不能把其余 ID 标作非命中。

源字段 molecule_ids_with_both_supports_across_assays 的实现是全目标证据集合的交集，既可能包含同 assay 内分歧，也可能包含不同 assay 间分歧；字段名本身不能证明分歧一定来自不同 assay。需要追溯原记录和实验条件。

best_assay 的选择规则是先最大化较少一类的数量，再比较总支持数；它未必是最大 assay，也不是经过实验方法审查后的最佳 assay。该 assay 的计数已排除同 assay 内阈值两侧都有支持的 ID，但尚未处理结构层面的重复或全部来源问题。

## 来源审查

### CHEMBL4575 / CHEMBL5363961

- [官方 assay 记录](https://www.ebi.ac.uk/chembl/api/data/assay/CHEMBL5363961.json)：人源 DYRK3 的酶活抑制实验，放射性读数；single protein format；B 类；目标映射 confidence_score=9。
- [文献记录 CHEMBL5360622](https://www.ebi.ac.uk/chembl/api/data/document/CHEMBL5360622.json)：2023 年论文，DOI [10.1021/acs.jmedchem.3c00884](https://doi.org/10.1021/acs.jmedchem.3c00884)。题名和摘要描述 Leucettinib 系列化合物的合成与表征。
- 可解释为该实验条件下的 DYRK3 抑制证据。仅凭该 IC50 实验不能声称直接结合证据。
- 231 个支持 ID、116/115 的类别结构适合作为下一轮审查对象。但摘要提示同系列类似物集中的可能，必须实际计算结构骨架和相似度。未阅读论文全文或补充表，未断言全部 231 个分子的结构组成。

### CHEMBL3769299 / CHEMBL5737708

- [官方 assay 记录](https://www.ebi.ac.uk/chembl/api/data/assay/CHEMBL5737708.json)：尽管标为 B 类，文字描述和 BAO 格式显示是在表达 Npt2a 的细胞中用膜电位荧光变化衡量转运功能相关反应；cell-based format；confidence_score=8、relationship_type=H。
- [来源记录 CHEMBL5728896](https://www.ebi.ac.uk/chembl/api/data/document/CHEMBL5728896.json)：专利 US-11208400-B2，2021 年。
- 按功能实验读数解释，不能当作已证实的直接结合。描述提到人源表达构建，而映射元数据仍为 8/H、assay organism 为空；保留这一待审查事项，不自行断言物种错误或直接覆盖来源字段。
- 在当前支持计数中，470/521=90.21% 为命中支持。若整理后保持该组成，均匀随机、不放回地查询 100 个化合物，期望命中约 90.2 个。该数是 E[命中]=预算×H/N 的算术说明，不是运行结果。高背景命中率限制了策略可展示的绝对增益；不据此断言一定无法比较策略。

### 其他三个实验

- [CHEMBL816079](https://www.ebi.ac.uk/chembl/api/data/assay/CHEMBL816079.json)：描述是 thrombin (IIa) 抑制，而目标目录名为 Prothrombin；confidence_score=8，物种未明确。来源 [CHEMBL1145085](https://www.ebi.ac.uk/chembl/api/data/document/CHEMBL1145085.json) 是 TF/VIIa 抑制剂论文。需要核对具体蛋白形式、物种、测量用途和同系列构建偏差。当前单 assay 94 个支持 ID 不足以支撑 100 次不同化合物查询。
- [CHEMBL871431](https://www.ebi.ac.uk/chembl/api/data/assay/CHEMBL871431.json)：BACE1 抑制的 FRET 实验，映射分数 9；当前窗口中只有 28 个支持 ID。全目标范围尚未获取完整。
- [CHEMBL861854](https://www.ebi.ac.uk/chembl/api/data/assay/CHEMBL861854.json)：LF 抑制的 FRET 实验，映射分数 9；当前最佳平衡 assay 有 50 个支持 ID。不能因为全目标有 447 个 ID 就直接拼成一个兼容数据集。

ChEMBL 官方说明中，confidence_score 描述 assay 与 target 的映射；9 不是测量质量满分，也不是直接结合证明：[官方说明](https://chembl.gitbook.io/chembl-interface-documentation/frequently-asked-questions/chembl-data-questions)。

## 本轮决定与下一步

1. 把 DYRK3 的 CHEMBL5363961 提升为优先深入整理对象，仍不判为正式合格；先审查结构、类似物冗余、重复/冲突、删失测量和来源。
2. Npt2a 保留为具有明确解释限制的备选，不把规模较大或接近满足数量门槛当作优先采用理由。
3. BACE1 和 Prothrombin 保留进一步检索机会；当前窗口和单一推荐 assay 的结果不能替代全目标资格评估。
4. 不修改原 candidate_scope_v0.1 配置或已有结果。500/30/100 是初版优先审查门槛，需要结合科学可比性、结构多样性、类别覆盖与查询预算整体复核，不能仅为使某个目标通过而降低门槛。
5. 若 DYRK3 整理后规模仍接近 231，可以评估 50 次查询、其中 10 次初始化的技术原型方案。100/231=43.3%，50/231=21.6%；预算最终需在评价前确定并对所有对照一致。该提案尚未执行或冻结。
6. 公开结构和来源证据只能供整理阶段使用。后续 campaign 的隐藏结果和类别比例不能由整理工具泄漏给搜索智能体。当前分析没有运行任何 campaign 或 GLM 调用。

## 保存与验证范围

本机保留用户输出原文、源文件 SHA-256、计数核对 JSON、API 原始响应、URL、时间、响应 SHA-256、脚本快照和失败日志。未覆盖远程数据或生成正式标签。

第一次来源读取有一个 assay 请求连接中断；已在独立运行中重试成功，原失败记录保留。第一次结束打印时遇到 Windows GBK 不能编码作者名字符，之前已保存的 JSON 文件不受影响；交付脚本 v0.1.1 改用控制台 ASCII 转义输出。两个来源读取运行合起来提供五个目标对应的五份 assay 和五份 document 元数据。没有阅读五篇来源全文。

这些新增文件最初位于 Windows 本机；只有用户完成同步后，才能确认它们已保存到远程 /driveA。

# ACLY CHEMBL5738952：来源值精度审查（2026-10-17）

状态：**hold；不可进入 benchmark 或 campaign**。这是一项 post-exposure 来源核查，没有改写此前 81-assay 数值审查或降低资格门槛。本轮未调用 GLM。

## 已对齐的实验含义

- ChEMBL 37 将该单 assay 映射到人 ATP-citrate synthase/ACLY（`CHEMBL3720`，type B、confidence 9）；整理后暂有 466 个可用结构身份，106 命中支持、360 非命中支持，数值和结构层通过。
- [US11555012B2 专利 Example 330 与 Table 10](https://patents.google.com/patent/US11555012B2/en) 明确写出 ADP-Glo 酶反应，ACLY 试剂为 Sino Biological `11769-H07B`，反应浓度 3 nM，底物和发光读数也有说明。[生产商对应产品页](https://cdn.sinobiological.com/recombinant-proteins/human-atp-citrate-lyase-11769-h07b) 将该货号标为重组人 ACLY。这支持**酶活抑制端点**的解释，但不等于直接结合证据。

## 阻塞问题：原始活性是区间，ChEMBL 显示离散数值

- 专利 Table 11 把 ADP-Glo IC50 报为 A `<0.050 µM`、B `≥0.050–<0.50 µM`、C `≥0.50–<20.0 µM`、D `≥20 µM`，表中不是每个化合物的精确 IC50。
- ChEMBL 此 assay 的 477 条原始记录仅有四种关系符号/数值组合：`<50 nM` 50 条、`=275 nM` 59 条、`=10,250 nM` 281 条、`=5,500 nM` 87 条。275 是 B 区间 50–500 nM 的中点，10,250 是 C 区间 500–20,000 nM 的中点。这是**中点编码的强烈迹象**，尚未逐分子确认导入映射；5,500 的来源尤其需要查明。
- 项目阈值是 1,000 nM。C 区间同时包含阈值两侧，不能因为数据库显示 10,250 nM 就把这 281 条记录当成实验支持的非命中。原先 106/360 的类别数只是 ChEMBL 显示值下的临时计算，**不能作为正式标签使用**。
- 如逐分子来源对齐后确定原始表只有 A/B/C/D，必须改用**区间界限**重新判定，跨阈值的 C 保持 unknown；不得把专利类别中点当实测值。根据保守类别计数，非命中池可能低于目前 ≥100 的审查线，但在逐分子映射完成前不下最终结论。

远端经哈希核对的证据为 `data/curation_private/chembl37_remaining_curations/remaining_curation_d91b5805eb8ae2cd/CHEMBL5738952/`，其中 `source_records.json` 的 SHA-256 为 `85451bad9ca90a0ca9405ede743bd3bf1d469d2e6e4f94570eee6edb56f4b7f9`。本次检查属于来源分辨率审查；没有运行新的 campaign。

## 全库范围的检查

只读程序 `audit_value_quantization_chembl37.py` 对 81 个审查结果逐文件验哈希后统计 IC50 关系符号/数值/单位组合。25 个 assay 只有 ≤8 种不同组合，其中 18 个原本通过数值门槛。这是**复核标志，不是自动拒绝**；只有与原始来源表对齐后才能判断是否为区间编码、集中检测限或真实离散测量。优先处理没有此标志且来源可追溯的 ACC2、TNAP 等候选。

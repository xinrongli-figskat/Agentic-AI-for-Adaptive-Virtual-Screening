# 人 TACE/ADAM17 CHEMBL5733557：固定样本来源核查（2026-10-17）

状态：**数值与端点有较强来源支持，化合物结构身份仍待审；hold，不可进入新 benchmark/campaign**。这项核查是 post-exposure 候选审查，不是盲评估。本轮 GLM 调用数为 0。

- ChEMBL 37 单 assay 整理后的临时池为 406 个化合物，40 个命中支持、366 个非命中支持；当前数值和多样性检查通过，且不在“≤8 种 IC50 值”低分辨率复核名单。
- [US9926281B2 第 3.5 节与 Table VIII](https://patents.google.com/patent/US9926281B2/en) 写明：用人 TACE/ADAM17 酶、荧光标记肽底物和 10 点剂量反应测 IC50；表中按化合物编号提供具体 nM 数值与 `>` 下限。专利指定 R&D Systems `930-ADB`；[制造商产品说明](https://www.bio-techne.com/p/proteins-enzymes/recombinant-human-tace-adam17-protein-cf_930-adb) 指向重组人 TACE/ADAM17 的成熟形式，来源 Sf21 昆虫细胞。这里的端点应表述为**生化酶活抑制**，不声称直接结合。
- 在查看逐条来源值前，沿已锁定规则 `SHA256("task1-v5-source-audit|" + activity_id)` 冻结 6 个命中支持 + 6 个非命中支持的不同来源分子。固定样本的来源名称/专利编号及 IC50 数值、关系符号 **12/12 与 Table VIII 一致**。三个来源分子各连接两个专利例号：250/440（417 nM）、231/434（106 nM）、331/455（>4000 nM）；各对例号在专利同一 TACE 表中给出相同结果。详见远端 `data/curation_private/source_audits/source_sample_CHEMBL5733557_39a9c5c75f294b09/patent_alignment_v1/`。
- 仍缺：按专利化学结构与 ChEMBL SMILES 独立核对 12 个样本，特别是三组双例号的立体化学和是否确为同一分子；检查来源表中未抽样记录是否仍为同一端点。现有程序明确保存 `compound_structures_independently_verified=false`、`source_endpoint_resolved=false`、`campaign_ready=false`，不得把 12/12 的**值**匹配误写成来源完全解决。

固定样本清单的 SHA-256 为 `a8512a858b434ea1cafc70fe13f8541be87bbe32c2b13eca35604129f983dc18`。本次人工转录另保存为 `tace_patent_us9926281_sample_values.json`；校验程序逐条比较来源例号、单位、数值和关系符号，并保留 12 条审计记录与哈希收据。

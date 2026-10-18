# 选择性指数 31882：来源定义与单位审查

日期：2026-10-14。原始活动字段依据用户从远程保存的 `raw_activities.json` 读取并贴出的内容；实验和文档元数据已从 ChEMBL 官方 API 实际获取。没有编辑原始活动、生成命中标签或建立正式 benchmark。

## 用户确认的活动字段

activity 31882 的原始字段 `type/relation/value/units` 和标准字段分别都为：Selectivity index、>、15723.0、uM。`activity_comment` 与 `data_validity_comment` 均为 null。

这说明 uM 已存在于 ChEMBL API 的活动记录中，不是我们的 CSV 预览工具添加的单位。数据库的原始字段不等于我们已经核对原论文的原始表格；不能据此断定单位问题由论文作者造成。null 也只表示没有相应注释，不代表质量审查通过。

## 新取回的实验定义

官方 assay CHEMBL845142 的 description 为：

> Selectivity index expressed as the ratio of CC50 to EC50

因此，“ChEMBL 将该实验的指数定义为 CC50/EC50”已经有来源支持，不再只是数值相近的猜测。对应 assay 类型为 F，target 为 CHEMBL612545，confidence_score=0；描述为目标未知或尚未分配。这个分数是目标映射信息，不是数值准确性的评分，也不支持将此指数当作已验证的蛋白直接结合证据。

来源：[ChEMBL assay 官方 JSON](https://www.ebi.ac.uk/chembl/api/data/assay/CHEMBL845142.json)。

## 来源文档

官方 document CHEMBL1138695 返回：

- Sriram D, Yogeeswari P, Srichakravarthy N, Bal TR；2004；Bioorganic & Medicinal Chemistry Letters。
- 标题：Synthesis of stavudine amino acid ester prodrugs with broad-spectrum chemotherapeutic properties for the effective treatment of HIV/AIDS.
- DOI：10.1016/j.bmcl.2004.01.007；PubMed ID：14980640。
- ChEMBL 保存的文献摘要也提到选择性指数 >15,723，并说明相关抗 HIV-1 活性在 CEM 细胞中测定。

来源：[ChEMBL document 官方 JSON](https://www.ebi.ac.uk/chembl/api/data/document/CHEMBL1138695.json)。本次没有取得原论文全文或检查其中的表格；PubMed 网页访问返回了验证页面，因此不把该网页访问当作全文验证。

## 数值解释与限制

同一化合物和来源文档中的相关记录为 EC50 <63.6 nM 与 CC50 >1000000 nM。若该定义对应这两个正浓度结果，则：

```text
CC50 / EC50 > 1000000 / 63.6 ≈ 15723.27
```

这与报告的 >15723 在数值上相容，但给出的是下界，不是精确指数值。由相同浓度单位相除得到的比值没有浓度单位，因此活动记录中的 uM 与 assay 中的比值定义不一致。

仍需区分：指数定义由 ChEMBL 实验描述支持；两个相关记录是否完全对应原论文的指数计算、测量条件及舍入细节，未在全文表格中核实。不能推断临床安全性或真实靶点结合机制。

## 当前整理决定

1. 保留 activity 的原始字段和原始样本，不直接覆盖 uM。
2. 在独立审查记录中标记“记录单位与 assay 比值定义不一致”，留下活动、实验和文档 ID，以及原始响应和获取日志。
3. 若未来需要使用该指数，可另建整理字段，说明维度解释、边界和依据；当前没有实施这项转换。
4. 本条不作为当前蛋白筛选 benchmark 的命中或非活性标签。未来任何实际纳入或排除应在明确的 endpoint 和版本规则下执行。
5. 此案例的当前疑问已足以定位。后续工作转向候选蛋白的数据覆盖、assay 条件、实验非活性覆盖和化学多样性；它不是正式候选目标。

## 证据保存与验证范围

成功请求快照位于本机 `outputs/source_context/chembl_context_20261014T101612Z_a227b5e7/`，含 raw_status.json、assay_CHEMBL845142.json、document_CHEMBL1138695.json、run_metadata.json。状态、实验和文档请求均返回 HTTP 200，数据库版本为 ChEMBL_37。脚本核对了返回的 assay/document ID 与请求 ID 一致；元数据保留 URL、UTC 时间、响应 SHA-256、代码 SHA-256 与 completed=true。

此前一个网络受限的失败尝试只保存了失败元数据，不作为成功源数据。以上成功证据和本次文档目前在本机；等待补传到远程数据盘。本次没有调用 GLM，也未花费 GLM API 预算。

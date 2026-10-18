# 第一次样本的逐行证据审查

日期：2026-10-14。证据来自用户贴出的远程 `activity_preview.csv` 九列显示结果。此处没有重新下载 API 数据，也没有获得完整原始 JSON；本地转录表只用于复核显示内容，不能替代服务器的原始快照。

## 此前保存与测试状态

用户已确认远程 `docs/` 内存在 01–05 五份说明文档，`tests/` 内存在测试脚本。远程运行报告六项离线检查通过（`Ran 6 tests ... OK`）。这是对之前文档中“待补传、待远程验证”的后续状态更新。离线测试使用模拟响应，不能据此宣布科学 benchmark 合格。

本次新建的 06 审查文档和本地转录审查文件尚未上传；之前同步的文件保持为那次同步时的快照。

## 从逐行表新增确认的事实

本地数值工具按转录表重新统计，得到 20 行、11 个目标 ID、15 个 assay ID、19 个有限数值、五个不等号记录，测量类型、单位、关系和 assay 分类计数与先前摘要一致。

- 数值与关系符号都缺失的是同一行：显示表第五行，目标 `CHEMBL3879801`、assay `CHEMBL693238`。行号只表示这次显示顺序，不是 activity ID。
- 11 条 IC50 全部使用 nM；其中八条等号、两条大于号、一条缺关系和数值。
- 本表没有化合物 ID，因此不能从这九列独立核对七个化合物、13 条重复出现记录，也不能判断同一目标的多条测量是否来自不同化合物或构成测量冲突。
- `Delta H-V = 0 ms` 与 `Delta CPP = -4.3 mmHg` 均通过“有限数字”检查；是否合理取决于变化量的实验定义，不能仅因零或负数排除。

## 名称明确指向蛋白的目标

下面按显示名称作初步分组，尚未读取 `target_type`、蛋白组分、目标映射置信度或具体 assay 描述，不能将这些名称判断冒充正式数据库类型验证。

| 目标 ID | 名称 | 物种 | 记录数 | 显示的 IC50 结果（nM） | assay 类别 |
|---|---|---|---|---|---|
| CHEMBL1806 | DNA topoisomerase 2-alpha | Homo sapiens | 1 | >100000 | B |
| CHEMBL3921 | Heparanase | Homo sapiens | 2 | =2500；=9000 | B |
| CHEMBL4632 | Peroxisomal acyl-coenzyme A oxidase 1 | Rattus norvegicus | 3 | =4000；=17000；=180 | B |
| CHEMBL3356 | Cytochrome P450 1A2 | Homo sapiens | 1 | =6000 | A |
| CHEMBL340 | Cytochrome P450 3A4 | Homo sapiens | 1 | =37000 | A |
| CHEMBL3397 | Cytochrome P450 2C9 | Homo sapiens | 1 | =24000 | A |

共六个不同目标名称、九条记录，其中 B 六条、A 三条。CYP 的三个目标在这里属于 A 类，并不因此失去蛋白身份；是否纳入项目应由 endpoint、数据覆盖和实验兼容性决定。B 类或 IC50 字段也不能单独证明直接结合。

Heparanase 的两条记录共用 `CHEMBL872937`，氧化酶的三条共用 `CHEMBL760688`。同一 assay ID 提供了继续检查的一条线索，但缺化合物 ID 时不能声称有两个或三个不同化合物，也不能声称已解决冲突。

## 其余目标与结果

| 显示目标 | 记录数 | 结果 | 对当前构建工作的含义 |
|---|---|---|---|
| NON-PROTEIN TARGET | 2 | IC50 >50000 nM；另一条缺数值和关系 | 不能直接映射为明确蛋白 benchmark；缺失结果保持未知 |
| ADMET | 3 | % remaining =25、27、58 | 需要读出、浓度、条件和目标定义；不能把剩余百分比直接视为本项目活性标签 |
| Cavia porcellus | 3 | Delta S-H =3 ms；Delta H-V =0 ms；Delta CPP =−4.3 mmHg | 显示以物种名称作目标，不能直接当作单一蛋白活性；具体变化量含义需查来源 |
| CCRF-CEM | 2 | EC50 <63.6 nM；CC50 >1000000 nM | 名称对应人细胞系；细胞结果不自动确定某个蛋白的直接结合 |
| Unchecked | 1 | Selectivity index >15723 uM | 目标尚不明确，测量类型和浓度单位的组合需要核查；不自动纠正或当作 IC50 |

CCRF-CEM 的细胞系身份由 [ATCC 官方资料](https://www.atcc.org/products/ccl-119)支持；此处没有从该资料推断样本中实验的具体机制或条件。

## 对本项目的决定

1. 继续保留原始 20 条记录，不给它们批量生成命中标签。目标、测量和单位混杂，当前不能构成一个共同 endpoint。
2. 加回化合物 ID、activity ID 和文献 ID，确认记录之间的关系及来源。缺失结果不标成实验非活性。
3. 随后查询 target 与 assay 元数据，包括目标类型、组分、物种、映射置信度、实验描述及条件。对最后一行优先核查指数定义和单位；不能未经证据修改原始字段。
4. Heparanase 和氧化酶可用于说明“同一 assay 中的多条记录怎样审查”，不是正式 shortlist。它们在本样本中只有两条和三条记录，完整覆盖仍未知。
5. 正式候选发现另行声明检索范围，以可用化合物数、实验非活性覆盖、多样性、冗余、兼容性和预算可行性排序。不能因为某个目标在默认第一页出现就优先选为评价 benchmark。

## 本地复核文件

- `first_sample_row_review/displayed_rows_transcribed.csv`：用户显示的九列内容转录，非完整原始 API 响应。
- `first_sample_row_review/displayed_rows_audit.json`：数值工具复核的计数、来源说明和限制；`labels_assigned=false`。

科学解释参考 [ChEMBL 官方 assay 与 activity 问答](https://chembl.gitbook.io/chembl-interface-documentation/frequently-asked-questions/chembl-data-questions)。下一步查询方式参考 [ChEMBL 官方数据接口文档](https://chembl.gitbook.io/chembl-interface-documentation/web-services/chembl-data-web-services)。

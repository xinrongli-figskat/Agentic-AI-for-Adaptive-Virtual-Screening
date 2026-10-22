# D5-C｜目标通用零样本打分的可行性评估

日期：2026-10-20。性质：post-exposure 方法评估；GLM 调用 0；未生成新 benchmark，未接入 campaign。决策日期：[人填：决策日期]。

现有 `structure_prior` 是根据候选化合物之间的结构相似度进行的**无标签、无靶点排序**，不输入蛋白信息。它不能称为“目标通用零样本打分”或预测的结合证据（项目文件 `outputs/d_discrimination_20261018/d1_descriptor_spec.md`）。brief 对零样本起步使用的是 *may*，因此本评估以方法适用性和污染风险决定是否新增共享打分工具，而非为满足字面要求强行接入。

## 两个预定槽位的结果

| 槽位 | 方法及版本状态 | 输入和输出含义 | 两池适用性 | 训练污染/许可 | 决定 |
| --- | --- | --- | --- | --- | --- |
| 需要受体结构 | [Protenix-Dock](https://github.com/bytedance/Protenix-Dock)，官方 `main`，未能固定 commit/checkpoint | 受体 PDB、配体 SDF、预先定义的结合位点盒；输出对接姿势和经验/力场打分，**不是 IC50 或已校准亲和力**。官方称其为刚体经典对接；亲和力排序 checkpoint 与筛选效果评估仍列为 *work in progress*。 | 两个靶点均有实验结构，但 TNAP assay 所用蛋白构建体仍未核对；结构“存在”不等于实验兼容。 | GPL-3.0。经验参数/训练数据截止时间、具体打分文件与训练化合物重叠未核实。尚不能排除结构与化学污染。 | **暂缓**。不得把当前姿势分数当成可用零样本活性排名。 |
| 无需受体结构 | [PSICHIC](https://github.com/huankoh/PSICHIC) 的公开预训练多任务权重，官方 `main`，未能固定 commit/checkpoint | 输入蛋白序列与配体 SMILES，不用 3D 受体。公开 [配置](https://github.com/huankoh/PSICHIC/blob/main/trained_weights/multitask_PSICHIC/config.json)含亲和力回归和功能效应任务；它们是跨来源的预测值，**不是本项目同一 assay 的 IC50**。 | DYRK3 与 TNAP 均有 UniProt 序列，故输入形式上覆盖两池；仍须对齐所选 isoform/构建体。 | Apache-2.0。公开[数据说明](https://github.com/huankoh/PSICHIC/tree/main/dataset)含蛋白–配体监督样本；所选权重的准确训练清单和截止时间未核实。与两个 ChEMBL 池的同靶点、同分子或同系列重叠是**未排除的否决项**。 | **暂缓**，待训练清单审计。若审计无法完成，放弃作为无污染的 retrospective 零样本臂。 |

“版本状态”是本次评估实际核查到的边界；`main` 会变化，不能充当可复现实验版本。未来若进入实验，必须固定仓库 commit、模型/参数文件 SHA-256、依赖版本和受体 PDB ID。PSICHIC 官方 [`screening.py`](https://github.com/huankoh/PSICHIC/blob/main/screening.py)的默认权重不应被默认为上表多任务权重，调用时须明确记录实际权重。Protenix-Dock 官方示例将 `pscore-v7_and_bscore-fake.json` 复制为配置；文件名不能证明该分数已经过亲和力排序验证。

## 受体结构：确实有，但尚非可直接比较的 assay 构建体

- DYRK3 / `CHEMBL4575` 对应人 UniProt `O43781`，[实验结构 5Y86](https://www.rcsb.org/structure/5Y86)含抑制剂 harmine。仅部分区域有坐标，需审查结构片段与 assay 构建体、ATP 口袋和共晶配体；还须查 harmine/其近邻是否在 DYRK3 池内。
- TNAP / UniProt `P05186` 有[人源实验结构 7YIV](https://www.rcsb.org/structure/7YIV)和[含抑制剂的 9SH5](https://www.rcsb.org/structure/9SH5)。TNAP 池的蛋白来源/构建体问题在 `outputs/d3_tnap_20261019/freeze_tnap_v1/pool_card.md` 中仍被记为局限；不能凭 PDB ID 把它消除。9SH5 的共晶配体与测试池的重叠、结合位点选择的事后信息均须审计。

这里的结构可用性属于 *technical availability*，不是已验证的 assay 对齐；尤其不能把含测试化合物的共晶姿势当成无信息的零样本先验。

## 进入前的污染审计与硬门槛

1. 固定两套源码、打分参数和权重的 SHA-256，取得与这些**具体权重**对应的训练/校准记录及截止日期。公开论文对某种拆分的描述不能替代当前权重的训练清单；缺清单时写“未核实”，不宣称 clean zero-shot。
2. 从冻结池只读导出化合物身份供离线审计：保留立体信息的标准化 SMILES/InChIKey、母核和 Morgan 相似度；与训练/校准数据逐一比较 exact molecule、相同靶点–化合物对、同系列近邻以及共晶 PDB。靶点核对 `O43781` / `P05186`、蛋白序列和近同源序列。报告各重叠层的数量及排除/敏感性规则，不能以训练集“没有标签泄漏”替代污染审计。
3. 若任一方法的训练或参数拟合可能覆盖本项目池内化合物且无法澄清，**不能进入主比较**。即使只是靶点见过、化合物未见过，也要注明它不是严格的 target-cold 零样本；相似骨架重叠要单列敏感性分析。对接受体的配体、姿势与位点选择也受相同约束。
4. 先审查两池输入是否能用同一处理流程成功覆盖所有候选，保留失败分子数。对接还需固定受体选择、质子化、辅因子、二聚状态、位点盒；这些不能看隐藏标签后调参。PSICHIC 需选定一个输出通道及方向，且不能把功能效应概率/回归值称为 IC50。
5. 只有前四项通过才做三个**预先选定、与隐藏标签无关**的化合物 smoke，记录每个池的成功率、墙钟时间和峰值显存；再讨论全池预计算。不能用三个样本的好看排名替代污染或适用性审查。

## 4090 检查与公平性

对 `lab-4090` 只读检查发现 NVIDIA GeForce RTX 4090、约 24 GiB 显存；远端项目 `.venv` 可导入 RDKit，但未装 `pxdock`、`torch` 或 `Bio`。未下载大型权重、未改环境，也未准备经审核的受体/位点和跨池训练清单。故**三化合物 smoke 未运行**，耗时、峰值显存、预测输出均为“未测量”，不是 0。GPU 存在不构成方法可用或科学有效的证据。

若未来接入，零样本分数须成为随机、固定贪心、规则控制器及 GLM 控制器**共同可调用**的工具，并计入同样的计算成本；不可让 GLM 独享分数再把收益归因于“智能体控制”。在两个池上对齐化合物全集和分数缺失处理，预注册是否选 kNN、零样本或组合。任何新增菜单都属于新协议版本，不回写 DYRK3/TNAP 已冻结运行。

结论：**建议：暂缓**。两个槽位均有潜在研究价值，但当前缺少足以排除训练污染的证据；Protenix-Dock 的官方亲和力排序 checkpoint 还未作为可验证交付公布。下一步优先取得权重/训练清单与结构–assay 对齐证据，再考虑小规模无标签 smoke。决策日期：[人填：决策日期]。

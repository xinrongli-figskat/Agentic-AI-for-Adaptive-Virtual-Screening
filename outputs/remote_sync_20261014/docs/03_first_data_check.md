# 第一份真实数据的检查

日期：2026-10-13。ChEMBL 状态连接已由用户在远程服务器验证，返回 `HTTP: 200`、`status: UP`、`ChEMBL_37`。

## 这一步做什么

读取 20 条 ChEMBL 活性记录，保存原始 JSON、数据库版本、请求地址、响应文件的 SHA-256、时间及字段摘要。检查测量类型、单位、关系符号、缺失结构与数值、重复化合物及 assay 构成。

这批记录按 API 顺序取得，不是随机样本，不代表全库或任何靶点的分布。不会分配阳性、非活性或 decoy 标签，也不会将不等号转换为精确值。这个程序是后续数据构建智能体可用的初步工具；当前还没有接入 LLM，也没有产出合格 benchmark。

## 传到实验室电脑

在 Windows 本机新开一个 PowerShell 标签，提示符应是 `PS C:\Users\lixinrong>`。运行：

```powershell
scp -i "$env:USERPROFILE\.ssh\id_ed25519_lab" "C:\Users\lixinrong\Documents\Codex\2026-10-09\agentic-ai-for-adaptive-virtual-screening\outputs\inspect_chembl_sample.py" xinrong@100.92.205.88:/driveA/xinrong/agentic-screening/inspect_chembl_sample.py
```

若要求私钥口令，输入之前设置的私钥口令。

## 在远程 Ubuntu 终端运行

```bash
cd /driveA/xinrong/agentic-screening
source .venv/bin/activate
python inspect_chembl_sample.py --limit 20 --output-dir /driveA/xinrong/agentic-screening/data/exploration
```

每次运行创建一个新的带 UTC 时间和随机后缀的目录，保留原始数据快照：

- `raw_status.json`：数据库状态原始响应。
- `raw_activities.json`：活性记录原始响应。
- `activity_preview.csv`：方便查看的字段表。
- `summary.json`：字段和数据构成摘要。
- `run_metadata.json`：版本、请求、时间、哈希和完成状态。

首次不指定靶点，是为了理解字段；后续可以通过 `--target CHEMBL_ID` 检查候选目标。工具限制每次 1–200 条，不自动翻页，不自动重试。

把屏幕输出中的摘要贴回对话。若失败，把错误与输出目录贴回；请求日志和已经得到的响应仍会保留。失败请求不要当成成功的数据集。

## 接下来根据什么作决定

- 是否混合了不同测量类型、单位、靶点或 assay？
- 缺失结构或测量值是否需要追加结构查询或排除规则？
- 有没有不等号记录，后续该如何解释测量边界？
- 重复化合物是否来自不同 assay，是否需要检查可比性和冲突？
- 需要进一步检索哪些目标及其 assay 条件？

这个小样本不能估计一个候选靶点的有效类别数或资格，也不能据此确定命中阈值。下一阶段需要完整或有明确采样设计的候选数据审查。

官方接口依据：https://chembl.gitbook.io/chembl-interface-documentation/web-services/chembl-data-web-services

## 验证范围

6 项本地离线检查已通过，覆盖了原始响应字节与 SHA-256 保留、缺失与不等号记录、单位和重复记录保留、异常响应拒绝、独立运行目录，以及请求失败后保留状态和完成标记。离线检查使用模拟响应，没有在本地下载真实活性记录。实际活性接口的远程运行已由用户确认，见下一节；实际源文件尚未传入本地检查。

## 首次远程运行与证据审查

用户已在远程服务器运行成功，返回 ChEMBL_37 和 20 条活动记录。运行目录为：

`/driveA/xinrong/agentic-screening/data/exploration/chembl_sample_20261013T154424Z_bf4ac0ff`

以下分析依据用户贴出的摘要；尚未读取实际原始 JSON、预览表或请求日志。该远程运行的结果已确认，上一节的本地离线验证范围保持不变。

| 观察到的证据 | 可得出的结论 | 后续行动 |
|---|---|---|
| 20 条记录、7 个化合物 ID、11 个靶点、15 个 assay | 一条测量记录不是一个独立化合物；多 assay / 多靶点重复不自动意味着数据错误 | 保留原始记录，在确定目标与 endpoint 后再按合适的键处理重复和冲突 |
| 11 条 IC50，另有 EC50、CC50、百分比、时间、压力和其他测量 | 当前样本包含多种科学含义，不适合直接合并成一个活性 endpoint | 逐行查看靶点、实验与测量类型，再制定可解释的检索范围 |
| nM 13 条、uM 1 条，其他为百分比、mmHg、ms | 不能把所有单位转换成 nM；IC50 数量和 nM 数量是边际计数，不能推断它们的交集 | 只在同一测量含义和兼容实验下考虑摩尔浓度单位换算 |
| 5 条不等号记录（4 条 >、1 条 <） | 这些是边界信息；25% 仅描述这个小样本，不能外推全库 | 保留关系符号，在 endpoint 和阈值确定后用区间逻辑处理 |
| 测量值和关系符号各有 1 条缺失 | 缺测量或缺关系不能自动当作已测非活性；两项是否来自同一行仍需看预览表 | 保留未知状态，审查记录后决定可用性 |
| assay 类型 A=6、B=6、F=8 | 记录混合了 ADME、结合类和功能类实验 | 进一步检查 assay 描述、方法、目标类型和映射置信度 |
| 20 条都没有 data_validity_comment | 没有出现该注释字段的标记 | 不能仅据此认定所有记录可靠、兼容或已经解决所有质量问题 |

ChEMBL 的 B、F、A 分别是结合、功能与 ADME 类别；confidence score 描述 assay 与目标的映射置信度。类别字母或较高映射分数不能替代具体方法的审查，也不能单独证明物理结合机制。官方依据：https://chembl.gitbook.io/chembl-interface-documentation/frequently-asked-questions/chembl-data-questions

当前决定：继续查看同一批记录的靶点名称、物种、assay ID 和逐行测量，而不对本样本分配命中标签。这个阅读练习不把 API 顺序得到的 11 个靶点作为正式候选 shortlist；正式发现阶段需要另外说明检索范围，并按数据资格排序。

后续若优先探索单一蛋白的生化测量，应明确限定目标、endpoint 和 assay 兼容性，并检查足够的实验非活性覆盖；不能仅凭 IC50、nM 或 B 类型筛选后就宣布 benchmark 合格。数据不充分时再查询其他来源或拒绝目标。

探索目录包含原始活性信息，属于数据构建上下文；以后搜索智能体不能获得该目录的一般文件访问权限。

## 文件保存状态补充（2026-10-14）

用户贴出的远程文件清单确认：项目根目录已有 `requirements.lock.txt` 和 `inspect_chembl_sample.py`，首次运行目录内的五个输出文件均存在。这确认了文件存在；尚未逐行读取实际原始数据，也未核对依赖清单的内容。说明文档和离线测试仍需补传。

详细的逐项统计解释见同目录 `04_chembl_sample_explained.md`。离线测试已调整为同时支持本地 `outputs/` 下的读取脚本和远程项目根目录下的读取脚本；临时测试数据放在各自项目的 `.cache/inspection-tests/`，测试使用模拟响应。

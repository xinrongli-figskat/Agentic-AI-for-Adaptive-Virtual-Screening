# 候选靶点摸底工具 v0.1.1

这是 Task 1 的初步数据工具：保存完整单蛋白目标目录，按预先声明的规则选取候选，读取有上限的 IC50 数据，并形成下一步审查表。当前没有接入 GLM，没有构建合格 benchmark。

## 第一版选择与理由

- 第一来源为 ChEMBL；目标范围为 SINGLE PROTEIN，各物种均可进入目录，目标 ID 分别统计。
- 为减少目录传输，只请求目标 ID、名称、类型和物种。对应的 API 原始响应及请求参数会保存；这不是完整蛋白组分审查。
- 全部目录分页成功后，按 `SHA256(seed|target_id)` 固定排序选取第一批目标。选择不使用活性结果，也不依据疾病重要性；仅代表声明范围中的一批，不是全库排名。
- 记录检索 endpoint 为 IC50；初步统计只使用 B 类中满足有限质量条件的记录。其他 assay 类型保留并另列，不自动合并。
- 暂定记录统计阈值为 IC50 ≤1000 nM 支持命中，>1000 nM 支持非命中。uM 等已识别浓度单位换算后比较。不等号仅在整个允许范围位于阈值一侧时支持分类；否则为未知。
- 非命中只针对此暂定 IC50 规则，不表示任何情境下都无活性。缺结果、不支持的单位、来源质量或潜在重复标记保留审查原因，不转成非命中。
- 尚未检查 assay 描述、置信度和条件，也没有完成结构解析、标准化、多样性或全部冲突处理，因此统计的是记录证据和化合物 ID，不是正式 benchmark 标签。

## 草案数值

`criteria_v0.json` 暂设 campaign 预算 100，其中 20 用于初始化，每批反馈 10。它们是设计选择，与当前数据库 HTTP 请求数不同。

单个 assay 若在窗口中支持至少 500 个化合物 ID、其中至少 30 个命中支持 ID 和 100 个非命中支持 ID，则提高后续方法与结构审查优先级。500 是暂按五倍查询预算设置的池规模起点；30/100 是类别覆盖的初步工程门槛，不是统计效力证明，也不是 brief 指定数字。

同一 assay 中同一分子同时获得两类支持时，初步优先级统计排除该冲突 ID。不同 assay 的两类支持不会拼成满足单一 assay 门槛的结果。跨 assay 集合可能重叠，其数字不能直接相加当作标签池。

更少但质量更好的数据也可能适合不同预算；这些门槛须随数据条件审查。任何正式评价前都需重新论证规则，并冻结实际 benchmark 的化合物池和标签版本。

## 在远程项目目录运行

```bash
cd /driveA/xinrong/agentic-screening
source .venv/bin/activate
python candidate_discovery_v0/tests/test_discovery.py
python candidate_discovery_v0/discover_chembl_candidates.py --candidate-count 30 --output-dir /driveA/xinrong/agentic-screening/data/candidate_discovery
```

脚本只依赖 Python 标准库。初版每个目标最多读取 1000 条活动记录，全次最多 300 个 HTTP 请求；每次保存独立目录。按 activity_id 顺序得到的截断窗口不是随机样本。目录必须完整才能选取候选；活动覆盖是否完整在每个目标结果中分别标记。

配置中 socket 超时为 30 秒，响应读取的墙钟期限为 60 秒。程序在读取分块之间检查期限，因此阻塞读取可能延迟至 socket 超时后才停止。达到限额或发生失败时保存不完整状态；请求开始和结束有日志检查点。没有自动重试或自动断点续跑。

## 主要结果

- `criteria_snapshot.json`：该次实际配置，包括命令行覆盖值。
- `target_catalog.json`：声明范围内的完整目标目录（初步四字段）。
- `selected_candidates.json`：候选及选择规则。
- `candidate_profiles.csv`：便于查看的初步审查顺序及下一步状态。
- `profiles/目标ID.json`：记录原因计数、每个 assay 的证据支持、边界和限制。
- `raw/`：每次 API 返回的原始字节；不完整响应另标 `.incomplete`。
- `run_metadata.json`：数据库版本、HTTP 请求、时间、SHA-256、成本计数和完成标记。
- `tool_source.py`：本次运行代码快照。

run 的 `completed=true` 表示声明的目录与候选窗口任务成功，不意味着所有目标活动已完整下载，更不意味着 benchmark 合格。所有初步 profile 的 `benchmark_qualified` 与 `benchmark_labels_assigned` 都为 false。

优先级按单 assay 的初步类别覆盖排列，仅决定先审查什么；不能用它宣称科学资格通过或预测 agent 表现。

## 对 brief 的贡献与后续

本工具推进候选识别、计数摸底、边界处理、来源保存和资格草案。后续须补齐 assay 兼容性、完整数据获取、结构整理与多样性、初始化可行性等审查，并让 GLM 根据证据选择进一步查询或拒绝动作。完整 Task 1 还包括实际构建智能体与版本化 benchmark；Task 2 尚未实施。

数据输出属于 curation 上下文。后续 campaign 只能通过受控接口访问已查询结果，其正常状态与工具不能访问这里的全部活动。

官方依据：[ChEMBL 数据接口](https://chembl.gitbook.io/chembl-interface-documentation/web-services/chembl-data-web-services)、[assay 与 activity 问答](https://chembl.gitbook.io/chembl-interface-documentation/frequently-asked-questions/chembl-data-questions)。

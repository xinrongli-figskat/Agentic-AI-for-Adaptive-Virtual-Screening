# Task 1：证据驱动的数据整理智能体 v1

本工具补充 brief 中“LLM 根据中间证据选择后续工具和动作”的第一条工作流。
它独立于 DYRK3 v1，不修改旧 campaign、模型提示词、冻结版本或结果。

## 工作方式

1. 从已有 discovery 目录的原始响应及哈希重建完整 SINGLE PROTEIN 目录，并重新计算之前检索的目标摘要。不会把旧摘要里的结论当作已合格数据集。
2. GLM 看到协议、目标摘要、实验描述和已经获得的整理证据，选择下一项允许的动作。
3. 程序执行该工具，将结果和失败保存，再交给 GLM 决定下一步。
4. 数据符合预先写下的数值条件、且 GLM 选择 shortlist 时，导出有版本号和哈希的候选池草稿。也允许本次没有任何候选合格。

可选择的工具：`discover_batch`（再查 1–3 个目标）、`profile_target`、`inspect_assay`（同时获取关联文献的书目信息）、`fetch_assay`（完整单实验 IC50 范围）、`curate_assay`（RDKit、测量冲突、不等号、类别、骨架、聚类、预算）、`decide_assay`（拒绝或列入候选）、`finish`。

这是由 LLM 选择工具、程序执行工具的 JSON 动作接口，不需要额外 agent 框架。
LLM 不获得终端、任意文件路径、任意网络地址或修改资格条件的工具。
程序限定允许动作、输入范围和硬性数值门槛；科学文字解释仍需检查，不能由这些约束保证正确。

## 本次预先声明的范围与取舍

- 仅 ChEMBL、单蛋白目标、单 assay、IC50、记录类型 B；不跨实验混合，不分配 decoy 标签。不是所有 ChEMBL 蛋白和所有实验类型的全面搜索。
- 命中为 IC50 <=1000 nM。严格保留不等号，跨阈值或证据不足保留 unknown；重复、冲突、标记为 potential_duplicate 等处理复用之前已测试的数值工具。
- 实验定义的抑制/未达命中阈值，与直接物理结合证据分开。B 类型和映射置信度 9 本身都不证明直接结合。
- 保留 500 个可用标准化化合物、至少 30 hit 和 100 nonhit 的工程门槛；这些不是 brief 指定的数字。
- 对新目标增加保守的初筛条件：Morgan r2/2048/chirality、Butina 相似度 0.7 下最大簇占比 <=25%，Murcko 骨架桶 >=10（无环结构共用一个桶）。这些数字是寻求比既有同系列原型更宽化学覆盖的操作性选择，并非已验证的科学标准。它们可能排除有价值的数据集，不保证通过者有泛化能力。
- 上述新条件是在看过 DYRK3 v1 数据和结果之后制定，只用于后续新整理任务，不追溯修改 v1；不能声称它们与既有结果完全独立。未来改变条件须创建新运行并记录原因。
- 拟议 campaign 总查询 50，包含 10 次无标签均匀随机初始化，之后每批 10；初始化单类别概率 <=0.5。计算超几何概率、随机预期命中及方差。这里仅论证可行性，不实际评价 campaign，也不要求 LLM 能证明性能更优。
- 目标预览最多 1000 条，单实验最多 2000 条；超过上限明确不完整。精确两两结构分析最多 1500 个可用化合物，超过时失败并报告限制，不暗中下采样。
- 仅获取 ChEMBL 实验描述及文献书目信息，没有论文全文核查。因此 shortlist 是待协议审查的候选，不是自动完成最终科学资格认可。

完整机器可读规则见本目录 `protocol.json`。运行开始保存副本、哈希和源码快照；继续运行时检查它们。哈希帮助发现变更，不证明来源或科学结论正确。

## 远端安装与离线检查

压缩包应先通过 Windows PowerShell 传到服务器的项目目录。之后在远端 Ubuntu、已经激活的 `.venv` 内运行：

```bash
cd /driveA/xinrong/agentic-screening
python3 -m zipfile -e task1_curation_agent_v1_transfer.zip .
source .venv/bin/activate
python -B -m unittest curation_agent_v1.test_agent

python -B -m curation_agent_v1.run prepare \
  --discovery-run /driveA/xinrong/agentic-screening/data/candidate_discovery/discovery_20261014T122202Z_5a03ac52 \
  --output-root /driveA/xinrong/agentic-screening/data/curation_private/task1_agent_v1

TASK1_RUN=$(python -c 'import json; print(json.load(open("/driveA/xinrong/agentic-screening/data/curation_private/task1_agent_v1/latest_prepared.json"))["run_dir"])')
python -B -m curation_agent_v1.run status --run-dir "$TASK1_RUN"
```

`prepare` 只读取和验证旧证据、保存新运行，不调用 GLM 或联网，不改变旧目录。
测试全部使用合成数据，不把真实标签提交给 API。测试通过不代表找到了合格真实数据集。
不需要新装 Python 依赖；使用已有 RDKit 和标准库即可。

## 首次真实执行，以及继续运行

先用最多 8 次 LLM 决策检查实际行为：

```bash
read -rsp 'Zhipu API key: ' ZAI_API_KEY; echo
export ZAI_API_KEY
python -B -m curation_agent_v1.run execute --run-dir "$TASK1_RUN" --steps 8
unset ZAI_API_KEY
python -B -m curation_agent_v1.run status --run-dir "$TASK1_RUN"
```

执行会向官方智谱接口发送当前整理证据，包括实验描述和类别统计。全部数据来自公开 ChEMBL；它与 campaign 的标签隔离上下文不同。
API 调用可能消耗账号额度。本原型不假定特定实时价格，也不自动更换模型。

达到 8 步时状态 `paused_at_step_limit` 是正常暂停。检查动作后，用同一条 `execute` 命令继续同一个目录。
本次运行总共最多 30 次 LLM 请求尝试和 180 次新的 ChEMBL HTTP 请求尝试，失败也计数。
一条 discover_batch 动作可能触发多个 HTTP 请求，所以“一步”并不等于“一次联网”。

若 SSH 重连，先恢复环境并从 `latest_prepared.json` 读回 `TASK1_RUN`，再执行同一个目录。
不要再次 prepare 以冒充对失败运行的继续；再次 prepare 会创建新版本。
同一运行由操作系统文件锁防止并行写入。

429、超时、JSON 错误会保留请求记录并暂停，不伪造回复、不偷偷改成固定控制器。
手动再次 execute 会保留已完成工具结果并发起新的决策请求，失败消耗的尝试额度仍保留。
中断发生在一个工具内部时，恢复可能重算未提交的本地计算；成功的相同 HTTP 请求通过哈希缓存复用。
若 ChEMBL release 与旧 discovery 不同，应重新构造同一新 release 的 discovery 快照，不能混用。

## 输出与安全边界

运行全部放在 `data/curation_private/task1_agent_v1/curation_.../`：

- `state.json`：协议、累计状态、每步动作/理由/结果/失败、计数、待继续动作。
- `raw/`：ChEMBL 原始响应；state 中的请求日志保存 URL、时间和哈希。
- `evidence/`：导入的原始测量窗口、重新计算的目标摘要、实验元数据、标准化结果、逐化合物证据与决定。
- `llm/0001.json` 等：实际发送的系统提示词、当时可见状态、原始返回、request ID、token 用量及耗时。回复在动作格式校验之前保存，覆盖无效回复；不会保存 Authorization 请求头或 API key。
- `source_snapshot/`：独立源码快照；复用数值工具的原始副本在 `vendor/`。
- `report.json`：排序、门槛失败项、候选、成本及局限。排序先看数值资格，再按最大簇占比从小到大、少数类别数量从多到少、assay ID。
- `drafts/`：只有 shortlist 成功时才出现。包含 `public/candidates.json`（无标签、无来源 ID）、`private/labels.json`、带两者哈希的 `manifest.json`。未知和排除结果继续保留在 curation evidence 中。

“public/private”仅是候选草稿的文件拆分，不是操作系统权限隔离。本工具没有部署新 oracle，也没有授权 campaign 读取整个整理目录。
后续必须为新池审查协议、建立独立 campaign 可见状态、通过 oracle 隔离标签，再单独冻结。现在的状态始终不是 campaign_ready。

Token 统计包括保存下来的无效回复；超时后供应商未返回用量时仍可能有费用。只报告已返回用量，并明确缺失。
整理工具的计算耗时和 HTTP 时间单独记录，不占未来 campaign 的 50 次结果查询预算。

## 与 brief 的对应

本版本补上 Task 1 的 LLM 工具选择、证据响应、候选审查/拒绝和可检查决策，并把可用候选整理为可接入 Task 2 的版本化草稿。
它复用此前 Task 1 的数值整理工作；Task 2 的 DYRK3 v1 结果保持原状。
它没有完成多数据源整合、论文全文核查、泛化验证、正式新 benchmark 冻结或新 campaign。
这些尚未完成的部分及此次搜索范围，应如实写入最终交付。

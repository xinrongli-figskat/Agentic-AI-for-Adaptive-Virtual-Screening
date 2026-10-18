# Task 1 v2：数量预筛与证据驱动审查

这是独立的新包，不修改 curation_agent_v1、旧运行或 DYRK3 v1。它改进数据发现和 GLM 上下文管理；没有生成已获科学批准的新 benchmark，也不直接启动 campaign。

## 工作方式

1. `prepare` 离线验证并读取已完成的 Task 1 v1 证据，复制目标目录和此前画像，写明已见数据，固定新版代码、运行环境、规则和来源限制。旧运行只读。
2. `prescreen` 不调用 GLM。程序先逐个请求总记录数，低于数量下限的目标不抓取活动窗口；优先复查旧画像中数据较多的目标。其他目标仍按固定哈希顺序进入计数，在已计数范围内按数量排序。计数使用 `limit=1`，仍然需要一次 HTTP 请求，并不是免费的全库统计。
3. 对有足够记录的目标，只抓取必要字段做初步画像。按 assay 统计命中/非命中支持来源 ID，供进一步排序；这是预筛信号，不是最终标准化的化合物标签。部分窗口明确标记，不可据此拒绝整个目标。
4. GLM 看精简摘要后选择下一步：继续数量搜索、查询 assay 目录、读元数据/完整实验说明、检查来源别名、完整抓取、调用数值整理、记录端点与构建体含义，或拒绝/保留/列入待审草稿。
5. 需要细节时分页读取证据，默认不重复发送全部实验说明、原始记录和历史。单次证据正文最多 4000 字符，状态 JSON 最多 24000 字符；字符上限不是 token 上限或费用保证。
6. JSON 或工具参数格式错误会保存原响应和校验原因，最多额外纠正两次，期间不执行科学工具。纠正请求也计入总预算和返回 token；HTTP/超时不冒充格式错误，不自动重试、不改模型。暂停后手动续跑会留痕。

GLM 有实际工具选择和实验解释权限；数值门槛、来源限制和未知标签规则由程序执行，不能被模型理由覆盖。实际可调用工具清单在 efficient.py 的 TOOLS 中；engine.py 是本包复制的数值与证据基础，未向模型开放的旧辅助方法不属于新工具清单。

## 先看资格与限制

阅读 CRITERIA_REVIEW.md 和 protocol.json。500 是优先层，250–499 是有限可行性层；两层均须通过类别、多样性、预算和来源检查。规则是在已见旧结果后确定的探索性规则。p300/P2X 的来源限制仍生效。

所有 `review_shortlist` 都只是待原文身份核验和新 campaign 协议审查的草稿。包内没有原文全量审查或自动来源批准工具，`campaign_ready` 始终为 false。不能把新草稿直接送入旧 DYRK3 campaign。

## 远端 Ubuntu 安装与检查

将整个交付 ZIP 上传到 `/driveA/xinrong/agentic-screening`，在已连接的远端 Ubuntu 终端运行。不要在 Windows 本地终端直接执行以下 Linux 命令。

```bash
cd /driveA/xinrong/agentic-screening
source .venv/bin/activate
sha256sum task1_curation_agent_v2_transfer.zip
# 与本次交付的 .sha256 文件核对；安装器还会校验每个文件。
python -B install_task1_v2.py --archive task1_curation_agent_v2_transfer.zip --root .
python -B -m unittest curation_agent_v2.test_agent
```

`install_task1_v2.py` 随交付 ZIP 单独提供。安装器只写 `curation_agent_v2/` 和 `task1_v2_delivery/` 两个新目录，拒绝覆盖已有目录；不会改旧包、数据或配置。

## 准备新运行（不联网、不用 API Key）

```bash
python -B -m curation_agent_v2.run prepare \
  --prior-run /driveA/xinrong/agentic-screening/data/curation_private/task1_agent_v1/curation_20261015T034434Z_d2828e13 \
  --output-root /driveA/xinrong/agentic-screening/data/curation_private/task1_agent_v2

TASK1_V2_RUN=$(python -c 'import json; print(json.load(open("/driveA/xinrong/agentic-screening/data/curation_private/task1_agent_v2/latest_prepared.json"))["run_dir"])')
printf '%s\n' "$TASK1_V2_RUN"
```

新运行目录会保存 prior_exposure.json、protocol 哈希、代码快照、环境版本。旧运行必须完整；缺文件或哈希不一致时应解决原因，不跳过校验。代码/规则/科学运行环境变化后须新建运行，不续写原版本。

## 数量预筛（联网，但不调用 GLM）

```bash
python -B -m curation_agent_v2.run prescreen \
  --run-dir "$TASK1_V2_RUN" --targets 32 --profiles 3
python -B -m curation_agent_v2.run status --run-dir "$TASK1_V2_RUN"
```

每完成一个计数都会显示进度；网络慢时可能需要数分钟。`32` 表示新做至多 32 个精确 IC50/B 目标计数，不包含复用的旧画像上限；`3` 表示至多整理三个精简目标窗口。这个阶段还没有最终池、标签冻结或 campaign。开始 GLM 后如需扩展，应由其工具继续，不能回到程序预筛改写运行状态。

## GLM 审查（先运行 8 个有效工具动作）

```bash
export ZAI_API_KEY="$(cat /driveA/xinrong/.config/agentic-screening/zhipu_api_key)"
python -B -m curation_agent_v2.run execute --run-dir "$TASK1_V2_RUN" --steps 8
unset ZAI_API_KEY
python -B -m curation_agent_v2.run status --run-dir "$TASK1_V2_RUN"
```

以后在同一运行上用相同 execute 命令续跑；不要重复 prepare 来挑选有利结果。重新 SSH 后可用上述 latest_prepared.json 命令恢复变量，确认打印的目录是要继续的运行。finished 表示本次搜索已结束，不是已完成 benchmark。

`--steps 8` 限制本次有效工具尝试，格式纠正会增加 LLM 请求。整次运行上限是 40 个 LLM 请求尝试、300 个 ChEMBL 请求尝试，包含失败请求。断点保存已完成证据与待执行动作；网络失败可能有供应商未返回的用量，报告会明确列出，不能按零成本算。

## 文件和结果怎么读

- `report.json`：新计数数目、复用上限数目、新画像、候选排序、类别/多样性门槛、去留理由和返回用量。
- `state.json`、`evidence/`、`raw/`：状态、带哈希的科学证据、请求原响应。`llm/`：每次模型请求正文、原响应、校验错误、用量与耗时，授权请求头不保存。
- `drafts/`：只有待审入选项才导出。public/candidates.json 不含标签和来源 ID；private/labels.json 保留 assay 测量支持和溯源。整个运行目录仍含标签，不能挂到 campaign。
- `paused_at_step_limit`：本批动作完成，可查看后续再续跑。`paused_after_format_limit`：连续三次无效格式，已停且没有执行其工具。`paused_after_api_failure`：读取模型回执查网络/供应商原因。`tool_error` 会进入下一步摘要，由模型据证据选后续动作，不伪造成功。

## 验证与尚未完成的功能

离线测试使用合成化合物和假的 API/控制器，验证动作随已得到的证据变化、数值整理到草稿、门槛、哈希、格式纠正和续跑。测试里的小池/放宽规则仅为测试夹具，不是实际资格配置，也不证明真实 GLM 能找到合适数据。

2026-10-15 对此前已见 p300 assay 做了 3 次公开 GET：总数一致，精简/完整页面的 ID 一致；3 条精简记录约为完整响应字节数的 21.4%。这是接口检查，不能当作新版检索成功率或 GLM 效果比较。没有通过本包调用真实 GLM 或运行新 campaign。

尚未支持 PubChem/BindingDB、跨 assay 合并、自动原文全池样品核对、decoy 生成、异聚受体目标目录、全库按数据量排序。数值阈值与多样性依赖表示，单 assay 可能过度集中于药化系列。源数据版本变化会阻止续跑；如需扩范围或改规则，另建版本并说明理由。

ChEMBL 官方接口文档：https://chembl.gitbook.io/chembl-interface-documentation/web-services/chembl-data-web-services

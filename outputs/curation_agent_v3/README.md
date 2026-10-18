# Task 1 v3：让工具结果真正进入下一轮决策

这是在 v2/v2.1 结束后开发的软件修订。科学阈值与来源限制沿用旧值；新旧运行分开，旧 40 次请求、原始模型理由和失败记录保留。本包不代表已找到新 benchmark，也不代表已证明搜索成功率提高。

## 已核实的问题与修复

下载的闭环证据包共 340 个文件，包内逐项哈希与本机审计通过。旧报告中的 809 实为 known_assays 编号数；CHEMBL816079 的完整实验说明没有读取覆盖记录，其类别预览来自 CHEMBL204 的 2000/3321 部分窗口。因此旧理由不能原样作为完整科学核验结论；原始文字不回写。

v3 作以下改变：

1. 下一轮输入直接包含 last_tool_result：工具名称、参数、成功/错误、缓存标记及带大小限制的结果。20 条 assay 列表必须全部送达，不再只给一个证据编号。
2. 元数据摘要直接带 confidence_score、assay_type、来源文档；实验说明预览明确标记是否截断。完整说明仍由分页工具读取。
3. 每条证据标明 kind、assay、target、可读视图；活动候选单独固定显示，旧文本不会无标记地被当作另一候选的说明。
4. 目标计数、旧范围上限、已知 assay 编号数明确区分单位。显示已计数但尚无画像的数据较多目标，让模型知道还有哪些可进一步分析。
5. decide_assay 新增 basis，程序核对真实依据：count_upper_bound、metadata_gate、curation_gate、source_problem、resource_limit。部分目标窗口的类别数不能冒充完整 assay 上界。
6. 保留单一外层 reason、严格格式、最多两次纠正、记录全部失败与用量。建议下一步动作只是提示，LLM 仍选择搜索对象、工具、来源解释和去留。

元数据失败（例如置信度 8<9）可以作为拒绝依据，不要求无必要地读完整来源后才排除；但不能虚称已经读过。程序核验结构化依据，不保证自由文字中的每句陈述都正确，仍须检查原理由。已知来源限制不能被模型解除。通过数值层级也只是 review_shortlist 草稿，campaign_ready 始终 false。

## 资格和科学范围没有改变

单蛋白目录、单 assay、IC50/B；≥500 优先审查、250–499 有限可行性、至少 30 命中和 100 非命中、目标映射置信度≥9、骨架/簇和查询可行性门槛保持原值。详见 CRITERIA_REVIEW.md。没有新增合并、decoy、全文身份自动批准或异聚受体范围。50 次 campaign 查询提议与这里的模型请求预算不是一回事。

新增 basis 改变了决定的校验方式，须作为软件方法修订披露，不能把新旧运行当作只有一个变量不同的性能对照。

## 离线验证解释

对真实历史 40 次模型输入逐步重建科学状态，核对每次的目标/assay 数和元数据出现时点，再用新上下文重新呈现。11 次元数据检查后直接置信度可见性由 0/11 变为 11/11；列表案例由 0/20 个编号送达变为 20/20；最大状态 JSON 低于 24000 字符。没有调用新模型，也没有执行新的科学工具，原 334 个输入文件哈希未改变。

这仅验证信息可用性，不证明模型会正确利用它，也不证明能发现合格数据。27 项离线检查包含原 15 项、9 项反馈/决定依据检查、3 项新实验预算与历史保留检查。实际远端测试结果另行记录。

## 安装检查（远端 Ubuntu）

先将 task1_curation_agent_v3_transfer.zip 和 install_task1_v3.py 上传到项目根目录，核对交付 SHA256，再运行：

```bash
cd /driveA/xinrong/agentic-screening
source .venv/bin/activate
python -B install_task1_v3.py --archive task1_curation_agent_v3_transfer.zip --root .
python -B -m unittest curation_agent_v3.test_agent curation_agent_v3.test_feedback curation_agent_v3.test_revision
```

测试沿用已安装的 v2/v2.1 来生成合成父状态；没有真实联网或 GLM 调用。安装只写 curation_agent_v3/、task1_v3_delivery/ 新目录，不覆盖旧版本。

## 显式准备新的修订实验，不重置旧用量

这不是继续旧 40 次预算的同一轮，也不是独立或盲态复现。下面明确声明额外 20 次模型请求、100 次 ChEMBL 请求。旧已用 40/103 保留，累计上限变为 60/203；旧 131475 返回 tokens 继续保留并另报新增用量。仅准备不联网、不扣模型用量。

```bash
python -B -m curation_agent_v3.run prepare-revision \
  --parent-run /driveA/xinrong/agentic-screening/data/curation_private/task1_agent_v2_1/continuation_v2_1_78389671c15ef4ab \
  --output-root /driveA/xinrong/agentic-screening/data/curation_private/task1_agent_v3 \
  --additional-llm-budget 20 \
  --additional-http-budget 100

TASK1_V3_RUN=$(python -c 'import json; print(json.load(open("/driveA/xinrong/agentic-screening/data/curation_private/task1_agent_v3/latest_revision.json"))["run_dir"])')
python -B -m curation_agent_v3.run status --run-dir "$TASK1_V3_RUN"
```

父运行必须已关闭且无入选导出，环境与原科学运行一致；所有原证据、回执、去留决定和来源限制保留。旧状态/报告/快照放在 history_v21/，新协议、代码和先前暴露关系写 revision.json。重复准备同一父状态、代码与预算返回已有子目录，不回退已执行进度。不要为了挑结果开多个新目录，也不要继续调用旧运行。

## 小批真实验证（会调用 GLM）

先确认离线准备继承的是 40 次模型请求、103 次数据请求、131475 tokens，再在新目录运行：

```bash
export ZAI_API_KEY="$(cat /driveA/xinrong/.config/agentic-screening/zhipu_api_key)"
python -B -m curation_agent_v3.run execute --run-dir "$TASK1_V3_RUN" --steps 4
unset ZAI_API_KEY
python -B -m curation_agent_v3.run status --run-dir "$TASK1_V3_RUN"
```

模型仍可能出格式或科学错误；全部记入新预算。status 中 llm_attempts/http_attempts 是累计值，new_llm_attempts/new_http_attempts/new_returned_usage 在 report.json 中区分新增部分。候选数包含继承历史，不能把旧整理当作新发现。

达到新预算后保持结果，不临时调门槛或延长上限。零候选不等于数据库没有合适数据。新候选仍需原文样品/立体结构/构建体和端点审查、新冻结与受控 oracle，才能启动新的 campaign。

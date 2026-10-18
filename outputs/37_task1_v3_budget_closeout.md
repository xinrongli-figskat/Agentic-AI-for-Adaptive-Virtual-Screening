# Task1 v3 本轮收尾

2026-10-16，Asia/Shanghai。当前事实依据为用户粘贴的远端输出，完整v3证据包尚未下载；以下统计待 closeout_task1_v3.py 在远端回执上重算确认。

## 本轮结果

新增20次GLM请求、10次ChEMBL HTTP尝试、113471返回tokens。累计60次GLM、113次HTTP、244946返回tokens。根据动作轨迹，新增14次工具成功、6次工具错误。新增完成1个assay整理（CHEMBL861854，50个可用化合物，28/22类），未通过本轮资格规则并已拒绝。CHEMBL5629827被模型暂缓，但跨assay来源问题推断仍需审查。CHEMBL832832仅完成元数据、描述阅读与来源评估，未计数/获取/整理，不得作为合格候选。review_shortlist为空，不能启动新campaign。

这支持v3已能执行获取、整理、拒绝的反馈路径，但没有证明发现效率或科学判断质量提高。目标数64、画像3、已检查assay8均包含继承历史；不能全部算作v3新增覆盖。LF查全50个化合物的事实不代表目标级596条记录属于同一实验。

## 预算与状态

原始状态paused_at_step_limit保留；实际GLM预算60/60已经耗尽。收尾报告另记effective_closure_reason=llm_budget_exhausted。不要追加预算或再调用execute仅为改变状态。API返回tokens与现金费用不同，实际资源包抵扣尚未核实。

## 离线收尾工具

本机outputs/closeout_task1_v3.py，SHA256 cf2bee0ed47cc6a0222bb3b56afe3f2cf93c9eb626120ae60e20cdd973543713。仅依赖标准库与已安装的curation_agent_v3.integrity，无GLM、无HTTP请求。读取原运行及其范围内归档，拒绝未关闭预算、待执行动作、哈希或用量不一致的状态。在独立新目录写summary.json、new_tool_events.json、assays.json、integrity.json、EXPORT_MANIFEST.json、task1_v3_evidence.zip、archive_receipt.json。逐项核验ZIP内容哈希及原运行前后不变。

4项本机离线测试通过（原运行保持不变、ZIP逐项校验及范围限制、回执用量不符阻止导出、未关闭运行或嵌套输出拒绝、原始证据被改动时拒绝；部分检查合并于同一测试）。Python3.10语法检查通过，本机运行环境Python3.12；不等于远端完整运行已核验。

远端Ubuntu执行（上传脚本后）：

```bash
cd /driveA/xinrong/agentic-screening
source .venv/bin/activate
sha256sum closeout_task1_v3.py
TASK1_V3_RUN=$(python -c 'import json; print(json.load(open("/driveA/xinrong/agentic-screening/data/curation_private/task1_agent_v3/latest_revision.json"))["run_dir"])')
python -B closeout_task1_v3.py --run-dir "$TASK1_V3_RUN" --output-root /driveA/xinrong/agentic-screening/data/curation_private/task1_run_reviews
```

输出的archive路径与archive_sha256用于下载后本机核验；归档文件含curation证据，不向campaign agent提供。

## 后续开发重点

取得收尾证据后先审查全部新增决定、数据范围和错误，不直接以新模型或更多请求作为解决方案。优先考虑assay级便宜数量预筛，以及随证据状态更新的可用动作/必要引用提示。LLM保留目标/assay选择和来源解释等需要判断的权限；确定的资格门槛和前提由程序执行。任何代码或预算修订另立实验，并记录已知结果与继承关系。旧v3、v2.1和DYRK3结果保持原记录。

## 远端收尾输出已收到

用户随后提供远端结果：status=verified_offline_closeout，399个原运行文件归档前后内容保持不变。source_run=/driveA/xinrong/agentic-screening/data/curation_private/task1_agent_v3/revision_v3_d91bb3b1f7c5535c。

归档目录：/driveA/xinrong/agentic-screening/data/curation_private/task1_run_reviews/task1_v3_closeout_20261015T164249Z_bc2ecdd0。目录时间戳按UTC命名，折合Asia/Shanghai为2026-10-16 00:42:49；目录名中的20261015不代表本地日期仍是10月15日。

ZIP：该目录下task1_v3_evidence.zip；1801923字节；SHA256 f3c68276c985082729b194ef6cedf6f864b99a4993eb9237798beef87d5a8792。此时仅收到用户贴出的远端核验结果，本机尚未取得或独立验证ZIP。

远端回执重算确认新增20次模型请求均为valid_decision（通过格式校验，不等于科学正确）；工具14次成功、6次错误；新增动作inspect_assay=3、read_evidence=3、assess_source=4、decide_assay=7、fetch_assay=2、curate_assay=1。无缺失返回用量的请求。新增用量113471 tokens、新增HTTP尝试10，均与前述轨迹统计一致。remaining_llm_attempts=0、remaining_http_attempts=90；应保留原预算终止点，不因HTTP余额尚存而续开模型请求。

已在本机准备下载位置：.sync_audit/task1_v3_closeout/task1_v3_evidence.zip。待用户从Windows本机PowerShell下载后，独立校验ZIP哈希、逐项清单和原始决策轨迹，再提出后续实现。

## 本机下载与独立核验完成

已实际读取上述本机ZIP：外层SHA256匹配；403个清单声明文件哈希全部通过，加清单自身共404个文件。安全解压到outputs/results/task1_v3_closed_20261016。逐次回执用量与远端报告一致，归档v3源代码与本机源代码一致，继承/原始响应/证据/代码快照共862次声明哈希检查通过；原运行399个文件内容保持不变。

后续原始轨迹分析见outputs/task1_v3_archive_review_20261016/REPORT.md与outputs/38_task1_v3_archive_verified_and_next_design.md。已确认新调用均用glm-5.3-flash、无格式失败、无新目标画像或assay专用计数。完整p300窗口内CHEMBL5629827仅49条记录，来源评估先于数量排除造成低效。不能将此观察夸大为新策略已验证的收益。

新增离线导入/审查脚本review_task1_v3_archive.py与4项归档边界检查：正确归档可导入且不覆盖已有目录、路径穿越拒绝、大小写冲突拒绝、外层与成员哈希分别校验。4项检查通过。本次所有新审查输出在本机，未同步到远端、未开启新版本实验或新增API预算。

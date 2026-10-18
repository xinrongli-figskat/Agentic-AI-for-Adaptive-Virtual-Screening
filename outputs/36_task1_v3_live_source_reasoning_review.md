# Task 1 v3：真实运行中的来源判断审查

日期：2026-10-16（Asia/Shanghai）。依据：用户粘贴的远端执行输出与第 45、46 次模型回答；尚未取得本轮远端完整证据包，不能声称已独立核验全部原始文件。此记录仅保存于本机，不表示已同步远端。

## 已观察结果

v3 新增第 41–48 次请求。累计 GLM 请求 48、HTTP 尝试 105、返回 prompt tokens 165007、completion tokens 11851、总 tokens 176858。相对继承历史 40/103/131475，新增 8 次 GLM、2 次 HTTP、45383 tokens。按累计上限 60/203，尚余 12 次 GLM、98 次 HTTP。review_shortlist 为空，campaign_ready=false。

第 44 次以 source_problem 暂缓 CHEMBL5629827 被拦截：来源评估当时为 primary_review_required，而该依据要求固定来源限制或 blocked 评估。通用错误中的“partial-window class count”是所有 basis 失败共用的尾句，不能据此认定本次错误由类别计数造成。

第 45 次模型未获取新的科学来源，将同一实验的来源评估改为 blocked；理由既包含其自身描述仅为“Inhibition of p300 (unknown origin)”的不足，也引用另一实验 CHEMBL5737918 的构建体、异构体身份限制。第 46 次随后成功记录 hold。

## 解释与局限

该轨迹证明状态条件满足后校验会通过，不证明来源问题已被独立证实。模型指定的 blocked 状态仍依赖模型对证据的解释；目前程序未充分检验证据与该状态的实质关联。这是软件与判断的共同限制，不能称模型已成功纠正科学错误。

不同 assay 属于同一蛋白，不足以传递样品/异构体/构建体的具体问题。CHEMBL5737918 的固定限制并非整个 p300 目标的禁用规则。CHEMBL5629827 当前应解释为“模型暂缓、依据仍需人工复核”，不能据此证明其数据不适用。说明缺失可支持暂不进入最终 campaign，但不自动证明数据存在已确认冲突。

第 43 次保存理由中的 1118 条来自 p300 目标级画像，尚不能作为 CHEMBL5629827 单 assay 的总量；源 ID 计数亦不是整理后化合物数。此统计范围混用必须在结果分析中披露。

## 当前候选

第 47–48 次检查并读取 CHEMBL861854：target CHEMBL4372、assay_type B、confidence_score 9、Bacillus anthracis、single protein format；描述“Inhibition of LF by FRET assay”（终端报告 30 字符，显示未截断）。来源文档 CHEMBL1138106，题名“The discovery of a potent and selective lethal factor inhibitor for adjunct therapy of anthrax infection.”，DOI 10.1016/j.bmcl.2005.10.088，PMID 16338135，2006 年。

数据库摘要与题名不足以确认直接结合、全部实验条件或最终资格。本轮尚无该 assay 完整获取、整理和类别覆盖的新结果。短描述本身不是排除依据；应按该 assay 自身的证据和数量检查继续决定。来源全文及其内容未在本轮独立查阅。

## 后续执行原则

保留原运行和决定，不改写第 45–46 次理由，不将其他 assay 的限制扩展为整个目标限制，不临时降低科学门槛。保持当前 v3 代码与声明预算，建议再观察 4 个工具动作，检查是否获取自身数量/测量证据或转向其他候选。新的 review_shortlist 仍只是待审草案，不能直接冻结或进入 campaign。

最后一条用户提供的调用回执请求模型为 glm-5.3-flash、状态 valid_decision、5554 tokens；这确认调用型号和格式通过，不确认科学正确性或现金扣费。平台资源包抵扣尚未核实。

## 第 49–52 次更新：暂停新增请求，先取具体错误

用户提供终端输出：第 49 次为 CHEMBL861854 记录 primary_review_required；第 50 次 fetch_assay 工具错误；第 51 次尝试 count_upper_bound/reject，第 52 次尝试 source_problem/hold，均为工具错误。终端未展示具体错误消息，不能断言是网络、范围不符、数量不足或证据引用问题。

累计 52 次 GLM、108 次 HTTP 尝试、199382 返回 tokens；相对本修订起点新增 12 次 GLM、5 次 HTTP、67907 tokens。声明预算剩余 8 次 GLM、95 次 HTTP。第 49–52 次新增 22524 tokens。

当前 shortlist 仍为空。获取失败不能作为数据规模不足或来源冲突的证据。代码 count_upper_bound 要求 state.assay_counts 中该 assay 的 below_raw_count_floor=true；source_problem 要求固定限制或该 assay 的 blocked 来源评估。获取结果和专用计数工具证据目前分开保存，若完整获取已显示小样本但专用计数未登记，则此规则可能对有效数量证据过窄；必须查看实际记录后判断，不能先改代码或手写状态绕过。

下一步仅从已保存 state.events 提取第 49–52 次完整动作理由与错误、该 assay 的计数/获取状态、最近 ChEMBL 请求错误。暂停新的 execute 直到知道第 50 次根因。此诊断不改变协议、模型输入或运行记录。

用户随后提供上述只读诊断结果，已确认：第 50 次 `fetch_assay` 为 `TimeoutError: The read operation timed out`。最近请求中 activity offset=0 返回 HTTP 200，紧接着的 ChEMBL `status.json` 版本复核超时。故 fetch 调用整体失败，`assay_counts[CHEMBL861854]` 与 `assays[CHEMBL861854].acquisition` 仍为空；不能说已完整获取或已证明该 assay 数量不足。成功 activity 页有可能留在 raw 请求归档中，需看其 `page_meta.total_count` 才知道页覆盖范围。

第 51 次 `count_upper_bound` 被拒是正确的：当前 assay 专用 `count_probe` 为 null；596 条与 28/22 类计数出现在第49次理由，来自已知目标画像/预览，不能替代该 assay 的计数。第 52 次 `source_problem` 被拒也正确：CHEMBL861854 当前来源状态为 `primary_review_required`，而不是 `blocked`，且该 assay 不在固定来源限制表中。需要审查不等于已确认来源存在冲突。

这轮新请求合计 12 次 GLM、5 次 HTTP、67907 tokens；余额为 8 次 GLM、95 次 HTTP。下一步先检查成功保存的 activity page 原始响应总数和记录数，再由受控 agent 重试 assay 专用计数/获取；除非出现该 assay 自身的来源冲突证据，否则不接受来源问题 hold。未改运行状态、数据、门槛或代码。

## 第 53–54 次：获取重试与整理成功

用户提供执行输出：第 53 次 `fetch_assay(CHEMBL861854)` 成功，第 54 次 `curate_assay(CHEMBL861854)` 成功；review_shortlist 仍为空。按现有代码，整理拒绝不完整 acquisition，因此该轨迹支持本次已越过版本复核超时，并完成声明 IC50 单 assay 范围内的数据获取与整理；具体记录数、标准化合并数、类别数、资格失败项尚未在输出中展示。不能据工具成功断言资格通过或来源已获批准。

累计 54 次 GLM、110 次 HTTP、210417 返回 tokens（prompt 196765、completion 13652）。相对修订起点新增 14 次 GLM、7 次 HTTP、78942 tokens；声明预算剩余 6 次 GLM、93 次 HTTP。第 53–54 次新增 11035 tokens。后续先只读 acquisition、budget、diversity、qualification 摘要，保留原失败与成功记录，不根据结果调整阈值。

## CHEMBL861854 完整整理摘要

用户提供只读摘要：acquisition E0154，IC50 范围内 records_received=50、source_total=50、complete=true。标准化整理后可用化合物 50，其中 hit_support=28、nonhit_support=22；摘要列出的标准化身份状态仅此两类。最大簇占比 0.18、骨架桶数 23。映射置信度、单蛋白格式、B 类、范围完整性与多样性门槛通过；失败项为 usable_compounds、hits、nonhits、campaign_query_fraction。未保存正式 decision。

对照当前规则：50<250 最低可用化合物，28<30 最低命中数，22<100 最低非命中数；50 次查询/50 个化合物=100%，超过20%查询比例门槛。campaign_pool_size=true 仅指池容量足够支付50次不重复查询，并不代表仍有未查询池供选择策略比较。这是数据充分支持的当前协议不合格，不依赖来源问题推断。

先前596条来自目标级画像，不能当作本 assay 的 IC50 记录数；本次 assay 完整获取明确为50条。应让模型在原运行中依据 curation_gate 记录拒绝，随后在剩余6次模型请求内继续其他候选或结束。此处人工审查结论不等于已经写入远端 decision；不改原失败理由、数值门槛或预算。

## 第 55–60 次：模型请求预算耗尽

用户提供终端轨迹：55 次仅引用 E0155 尝试 curation_gate/reject，被拦截；56 次补入元数据、来源评估及获取证据后，CHEMBL861854 正式拒绝。按代码，55 次缺少 required evidence citations，具体错误仍待原始事件核验。

57–59 次检查 CHEMBL832832、阅读 E0158 实验说明并记录来源评估（描述为 human alpha thrombin，IC50/type B/confidence 9）。60 次未先完成该 assay 的计数、获取、整理，直接尝试以 source_problem 为 basis 的 review_shortlist，被拦截。按代码，source_problem 仅支持已建立来源问题的 reject/hold，本次 verdict/basis 组合不成立；且 review_shortlist 仍须通过 curation 数值门槛。不能据此称凝血酶候选合格或不合格，当前应记为未完成审查。

累计 60 次 GLM、113 次 HTTP、244946 返回 tokens（prompt 229683、completion 15263）；新增 20 次 GLM、10 次 HTTP、113471 tokens（prompt 108171、completion 5300）。依据已贴轨迹，v3 新增工具动作14次成功、6次错误，无新入选、1次成功整理（LF，已拒绝）。这些统计尚待远端收尾脚本按回执独立核验。

保存状态仍为 paused_at_step_limit，但 llm_attempts=maximum_llm_attempts=60，实际已耗尽本次模型预算。原因是 run_steps 在第6个动作后因步数到限离开循环，没有回到循环顶部设置 llm_budget_exhausted。保留该状态字面值，在独立收尾报告中注明 effective_closure_reason=llm_budget_exhausted。不要再调用 execute 来改变状态，因为其起始版本检查仍会产生HTTP请求。

下一步离线归档：本机新增 closeout_task1_v3.py，只读取原运行，在外部新目录写审查文件和证据ZIP，核对继承哈希及逐次回执用量，归档前后检查原文件未改变。科学判断与费用均不由该脚本自动确认。4项离线测试及Python3.10语法检查通过；远端实际执行待用户完成。脚本 SHA256 cf2bee0ed47cc6a0222bb3b56afe3f2cf93c9eb626120ae60e20cdd973543713。

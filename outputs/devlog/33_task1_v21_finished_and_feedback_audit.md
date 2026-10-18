# Task 1 v2 / v2.1 有界运行结束及工具结果反馈诊断

日期：2026-10-15。远端状态依据用户提供的终端输出，本机尚未直接取得远端完整最终回执。

## 本轮真实运行结果

v2.1 延续目录：`/driveA/xinrong/agentic-screening/data/curation_private/task1_agent_v2_1/continuation_v2_1_78389671c15ef4ab`。

第 40 次请求执行 finish，状态 finished。累计 40 次模型请求、103 次 ChEMBL 请求；返回 prompt 121512、completion 9963、total 131475 tokens。fresh_target_count_probes=64、imported_target_upper_bounds=50、新生成画像 3、检查 assay 元数据 7、shortlist 为空、campaign_ready=false。64 个计数包含此前目标的重新计数，不是 64 个完全未见目标；两种计数范围不同，不能混成完整目标画像。

v2.1 第 20–40 次共 21 次请求未在输出中出现格式错误，第 39 次有工具证据视图错误。单一 reason 接口的实际遵守情况改善，但阶段和证据不同，不是配对模型能力评估。

NPT2a 的 reject 和较早 P2X assay 的 hold 已有终端记录。第 37 次还拒绝 CHEMBL816079，理由需从已保存的 decision 读取，不能猜测。部分其他 assay 仅 inspect，不代表已完成整理或资格失败。没有入选不能解释为 ChEMBL 不存在合适数据，也不能宣布 brief 的新 benchmark 构建任务完成。

## 观察到的效率问题

第 34 次重复检查 CHEMBL816079，第 35–36 次再次检查 CHEMBL5629827。缓存可能减少重复 HTTP 请求，但每次模型决策仍消耗预算。第 39 次请求对 E0098 读取 assay_description 返回 tool_error；具体证据类型及模型理由由审计读取，不能把它简单归因于模型能力。

代码检查发现：最近动作仅保留 action、status、error、evidence_id；缺少动作参数和刚返回的实际结果。assay_preview 仅前六项，且未直接提供每个 assay 的 confidence_score 和完整元数据。list_assays 的返回列表也未直接作为 last_tool_result 传入后续模型请求。按需读证据仍可取得详细内容，但默认反馈缺口可能促成重复读取或错用旧证据。

这属于此前压缩上下文实现中的问题。应与模型选择、检索覆盖和数据自身的限制分别检查，不能把全部零产出归因于单一原因。

## 针对性离线检查

使用已经交付的 v2.1 代码和合成 FakeChEMBL，调用 inspect_assay 返回 confidence_score=8 和唯一实验说明文本，再构造下一次实际 context。结果：assay_preview 行中没有置信度或说明字段；recent_actions 仅显示动作状态和证据 ID，唯一实验说明文本不在下一次输入中。

该实验没有调用真实 GLM、没有 HTTP 请求。它证明一个具体状态存在直接反馈遗漏，不证明该遗漏导致本轮整体失败。记录位于 `task1_feedback_audit_validation/synthetic_feedback_probe.json`。

## 只读审计交付

独立脚本 `audit_task1_finished_v1.py` 仅用标准库，不导入 agent、不访问网络、不读取密钥。它验证当前运行声明的协议/目录/代码/证据/来源哈希、继承历史副本和累计返回用量，在运行目录之外另存 summary.json、assays.json、actions.csv、tool_result_visibility.csv、integrity.json、REPORT.md。

6 项离线测试覆盖：原目录不变；重复动作与可见性统计；证据损坏拒绝；用量不一致拒绝；活动运行或写入原目录拒绝；延续历史验证与不重复计数。仅在远端执行后才能报告实际的可见性缺口数和最终去留理由。

当前 v2 和 v2.1 源码与交付哈希一致；新审计工具在包外保存，不改变已固定运行的代码。

下一版应优先补充带大小限制的最新工具结果、活动候选和证据类型，进行完整反馈与压缩反馈的针对性实验，再考虑扩大搜索或其他公开数据源。任何新运行或规则变化都要另留版本，不对本轮增加预算或回写拒绝决定。

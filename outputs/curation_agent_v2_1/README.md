# Task 1 v2.1：单一理由接口与保留预算的延续

2026-10-15。此版本修复 v2 的两层 reason 歧义。没有更换模型、修改科学门槛或建立新 benchmark。

## 已确认的问题

用户提供的第 11、12、17、18、19 次回执均 HTTP 200、finish_reason=stop。模型在外层 reason 与 arguments.reason 之间反复移动文字，而旧接口要求两处都存在。不是本次回执被截断的情形。新接口统一为：

```json
{"action":"finish","arguments":{},"reason":"本次有界搜索已结束；这不代表数据库中没有合适数据，也不代表已生成可运行 campaign 的数据集。"}
```

所有工具只用最外层的 reason。assess_source、decide_assay、finish 由程序将这处理由传入其内部记录。模型不可再提供 arguments.reason。严格校验仍保留：不自动搬移字段、不放宽缺失 verdict、不执行旧的无效回复。错误反馈指出具体 JSON 路径，提示词提供完整布局示例；连续无效仍最多纠正两次。

## 延续的边界

continue-v2 在独立目录中延续当前 v2 运行，而不是重启实验或清零预算：

- 旧 v2 目录与其拒绝决定保持原样；迁移期间使用既有写锁，校验来源快照、科学证据、原响应、目录与旧协议哈希。
- 历史请求、原始 LLM 回执、返回用量、已整理 assay 和证据 ID 原样保留。当前 19 次模型请求、71 次 ChEMBL 请求、64063 返回 tokens 均继续计入上限；剩余模型请求是 21 次。
- 旧状态、旧报告和旧代码快照存入新目录的 history_v2/，其余证据保留原相对路径。continuation.json 固定父运行文件清单及版本改变原因；清单仅排除操作系统锁文件。
- 数量门槛 250/500、类别 30/100、映射置信度 9、多样性、来源限制及 40/300 请求上限不变。源模型与科学运行环境不变。迁移不联网、不调用模型。
- 同一父状态、同一代码、同一输出根下，重复准备会返回已有延续目录；即使它已经向前运行，也不会把进度和用量退回 19 次。
- 只支持状态为 paused_after_format_limit、无待执行动作且无导出 shortlist 的已知 v2.0 运行。其他情况会拒绝迁移。
- 原文身份审查尚未完成，campaign_ready 仍为 false。v2.1 是已见证据上的软件修复延续，不是独立或盲态试验。

## 远端安装

在 Windows 上传 task1_curation_agent_v2_1_transfer.zip 和 install_task1_v2_1.py 后，进入远端 Ubuntu：

```bash
cd /driveA/xinrong/agentic-screening
source .venv/bin/activate
sha256sum task1_curation_agent_v2_1_transfer.zip
python -B install_task1_v2_1.py --archive task1_curation_agent_v2_1_transfer.zip --root .
python -B -m unittest curation_agent_v2_1.test_agent curation_agent_v2_1.test_continuation
```

安装器只写 curation_agent_v2_1/ 和 task1_v2_1_delivery/ 两个新目录，不覆盖 v2。延续测试需要已有的 curation_agent_v2/，因为它测试真实的 v2 到 v2.1 格式转换。

## 准备延续，先检查继承的进度

```bash
python -B -m curation_agent_v2_1.run continue-v2 \
  --parent-run /driveA/xinrong/agentic-screening/data/curation_private/task1_agent_v2/curation_v2_20261015T141733Z_df707611 \
  --output-root /driveA/xinrong/agentic-screening/data/curation_private/task1_agent_v2_1

TASK1_V21_RUN=$(python -c 'import json; print(json.load(open("/driveA/xinrong/agentic-screening/data/curation_private/task1_agent_v2_1/latest_continuation.json"))["run_dir"])')
python -B -m curation_agent_v2_1.run status --run-dir "$TASK1_V21_RUN"
```

预期继承 llm_attempts=19、http_attempts=71、total_tokens=64063，NPT2a 拒绝决定仍在。若父运行已被继续执行，继承数字可能变化，应先核对；不要改文件来跳过哈希校验。延续后只在新目录继续，不同时运行父目录。

## 小批检查新的真实模型输出

```bash
export ZAI_API_KEY="$(cat /driveA/xinrong/.config/agentic-screening/zhipu_api_key)"
python -B -m curation_agent_v2_1.run execute --run-dir "$TASK1_V21_RUN" --steps 3
unset ZAI_API_KEY
python -B -m curation_agent_v2_1.run status --run-dir "$TASK1_V21_RUN"
```

先做三个工具动作，观察单一 reason 是否被遵守，再继续。总预算仍从原运行累计，失败也计入；格式问题没有被保证完全消除。不应重开运行挑选有利输出。

## 科学解释与未完成事项

当前 NPT2a 已正式拒绝：521 可用、470 命中、51 非命中，映射置信度 8，后两项不满足规则。其他 assay 的 inspect_assay 成功仅代表读到元数据。

本轮模型还重新查看了 DYRK3 的 CHEMBL5363961，以及此前 P2X 重复来源追溯涉及的 CHEMBL5732176。不能把旧目标或较早专利当作新的独立发现；P2X2/3 受体身份与跨专利重叠仍需来源审查。此修复没有扩大 source_holds registry 或改变候选排序；来源科学判断仍是待检验的能力。

资格规则原文见 CRITERIA_REVIEW.md。旧 500 门槛是自主设计，250 是已见旧数据后确定的探索性层级，不是 brief 规定或盲态预注册。

## 验证范围

测试由继承的 15 项核心检查和新增 7 项接口/延续检查组成。新增检查包含用量与历史继承、父目录不变、重复准备不重置、协议或证据被改后拒绝、耗尽预算不再调用模型、五种实际回复布局及单一理由写入科学记录。

failure_layout_fixtures.json 只保存用户提供的五种布局作解析回归。测试中显式构造合法布局仅用于测试解析器，不代表在真实运行中自动修复并执行历史回复。原 12、18 次布局现在本来就符合新接口，但迁移仍不会重新执行它们。

本地离线验证不调用真实 GLM；新接口的实际遵守率须在远端续跑后报告。没有新增 campaign 查询。数值、来源和标签隔离的既有局限继续适用。

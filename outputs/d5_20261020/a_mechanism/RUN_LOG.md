# D5-A 运行日志

- 2026-10-20 UTC：阅读 D5 任务卡、冻结数值工具、D3 冷启动规格与 D4 报告；确认无适用的项目级额外 AGENTS 指令。
- 2026-10-20 UTC：运行 D4 本机私有镜像验证程序；原清单 117 个文件哈希通过，清单 SHA-256 为 `1eb690658a062d959aa52750d849529a0a557bcdb1371ac86a41b7de3bb3af37`。
- 2026-10-20 UTC：`analyze_trajectories.py` 逐条检查 40 个 D4 GLM run 哈希、轨迹与标签累计，读取 D3 的 12 个 `fixed` 和 12 个 `forced_random_coldstart` 零命中种子 run；输出四轮序列表和逐种子配对表。无 GLM 调用。
- 2026-10-20 UTC：本机未安装 RDKit，因此将 `recalculate_selection_zero6_remote.py` 通过标准输入送入已授权的 `lab-4090` Python，在远端只读使用冻结 TNAP 池与现有 RDKit；远端没有新建或修改文件。标准输出仅写入本目录下 Git 忽略的 `selection_private/selection_zero6.json`。另一次单种子验证保存在同一私有目录。
- 2026-10-20 UTC：`summarize_selection.py` 校验本机公开池与私有标签的哈希、重算选择与 12 个 GLM 首批和 12 个规定回退首批完全一致，输出不含单分子标签的汇总 CSV。
- 2026-10-20 UTC：完成机制报告；结论是全负例 kNN 分数单调性成立，但 `diverse > greedy` 的孤立排序不成立。未改旧策略、冻结池、私有标签或 D3/D4 产物；未作 Tier B/C 决定。

执行次数：GLM **0**；远端只读 RDKit 核验 **2**；Tier A 修复 **0/2**；Tier B/C **0**。

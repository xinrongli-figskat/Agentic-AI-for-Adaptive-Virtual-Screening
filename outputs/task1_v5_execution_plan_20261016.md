# Task 1 v5 执行方案：固定判定规则后审 S1PR1，再扩大枚举

日期：2026-10-16。依据已见 v2–v4 结果制定，属于 **post-exposure 后续方案**；不能作为盲验证。此文件不修改任何历史运行、资格门槛或 DYRK3 campaign。

**执行顺序的硬边界：** 在继续 S1PR1 逐条来源核对或完整整理之前，先保存 [来源与端点判定记录](task1_v5_source_adjudication_rules_20261016.md) 的 SHA-256 与 UTC 时间。该规则是在已看到 v4 预览和专利元数据后拟定，只对后续证据收集和决定生效；不能倒称为 S1PR1 的盲预注册。新数据集 campaign 的完整协议仍须在任何新 campaign 查询之前另行冻结。

## 事实和待核实项

- v4 实际新增 12 次 GLM 调用（累计 72），31 次 HTTP 尝试，返回 86,043 tokens；`review_shortlist=[]`。最后检查了 S1PR1 `CHEMBL5734042` 元数据，尚未作去留决定。
- 用户从 v4 画像读出的预览为 294 个有类别支持的来源分子 ID：52 hit、242 nonhit；assay 映射置信度 9。这只是单实验预筛，不是标准化后池。池大小至 250 的余量为 44 个 ID；命中类别至 30 的余量为 22 个 ID。
- v4 已存元数据经证据文件 SHA-256 核验：`description="TBD: TBD"`，`doc_type=PATENT`，`patent_id=US-10323029-B2`，assay 和 document 的 `src_id` 均为 37，`confidence_score=9`，`bao_label=single protein format`，文献无 DOI/PubMed。ChEMBL 官方说明 `src_id=37` 是 BindingDB 来源的专利数据。[原始专利](https://patents.google.com/patent/US10323029B2/en)的表 2/3 有 S1P1 等受体的 `AA IC50` 列，也在文字中讨论激动/拮抗作用；尚不能把其中某一表格或实验方法逐行对齐到 `CHEMBL5734042` 的数值。`confidence_score=9` 是靶标映射置信度，不证明直接结合。结构系列与 assay 端点仍待核查。
- 50 次查询对 294 个预览 ID 占 17.0%；只有整理后仍不少于 250 个且其他门槛通过，才能满足现有 ≤20% 的方案。

## 阶段 0：将 v4 按预算耗尽归档

1. 将远端 v4 运行目录作为独立证据包复制到本机；核对远端与本机清单哈希、证据引用、模型回执、协议与代码快照。保留原 `state.status=paused_at_step_limit`，另在收尾报告写 `effective_closure_reason=llm_budget_exhausted`，列明待审的 `CHEMBL5734042`。
2. 统计本轮动作及成本，以新增 12 次为主要 denominator，同时保留累计 72 次总账。把工具报错、重复动作和状态提示缺陷独立记录。
3. 归档前后的 v4 文件哈希一致；不回写 v2–v4 的拒绝/暂缓决定。

本周先完成此阶段及规则文件哈希，再继续阶段 1。归档同时输出未决队列（至少包含 `CHEMBL5734042`）和 `budget_exhausted` 交接记录；不要把未作决定的候选记成通过或拒绝。

## 阶段 1：S1PR1 只读证据核查，随后做人工/GLM 独立判定

原始证据整理阶段不调用 GLM，也不新增 ChEMBL 请求。`assay_metadata` 已完成哈希验证和来源类型提取。继续从 v4 的哈希验证 `thin_target_window` 和目标画像提取：目标/物种/受体构建信息、预览计数、缺结构/冲突/删失记录，以及与专利例号或 BindingDB 记录相连的分子标识。用 RDKit 对画像窗口中该 assay 的结构做**初步**骨架/类似物分布；它不替代正式标准化和多样性审查。

按已保存的判定记录，从 6 个预览 hit-support 与 6 个 nonhit-support 来源 ID 构成固定主样本，核对 [原始专利 US10323029B2](https://patents.google.com/patent/US10323029B2/en) 与 BindingDB 源条目。逐条对齐 ChEMBL `activity_id`/分子标识/IC50、专利例号、受体列和测量方法；专利若涉及两张数据表，按固定规则补足表覆盖。区分结合置换、功能激动/拮抗及下游信号。来源核查限 4 个实际人工工时、开始匹配后最多 2 个日历日；到点按既定规则记 `resolved`、`hold` 或 `reject`，不放宽门槛。专利来源本身不自动否决。

将不含人工结论的证据包封存后，人工先独立写来源/端点判定并保存哈希；GLM 再在新上下文中读取**同一证据包**，不接触人工结论，输出自己的判定和证据。两者分开报告、再公开仲裁。S1PR1 是智能体在既有搜索中浮出的候选，经人工核实后可用于判断智能体审查表现；它不是完全陌生数据的盲评估。

## 阶段 2：无模型的便宜门槛与正式整理

1. 对 `CHEMBL5734042` 查**精确 assay IC50 记录数**。若原始记录数 <250，按照当前单实验规则可直接停止；若 ≥250，再核对其 type B、confidence 9、单蛋白目标及来源状态。这是低成本形式门槛；预览已有 294 个受支持 ID，不值得在此耗费 GLM 预算。
2. 完整获取该 assay 的 ChEMBL_37 活性记录，保存原始响应、请求参数和哈希。复用已验证的结构与测量整理规则：盐/片段、立体化学、重复来源、相反测量、`<`/`>` 等界值、有效性标记和 unknown 单独处理。
3. 报告整理后 usable/hit/nonhit/unknown/excluded、最大 Butina 簇、骨架数、50 次查询占比、10 次初始化两类抽到的风险。不要根据结果改 1000 nM 阈值或资格门槛。只读预览的 294/52/242 不作为最终类别。
4. 若数值门槛过关但来源/端点仍无法核实，只保留待审草稿，不导出 campaign 标签。

## 阶段 3：全库候选枚举（并行于来源核查，不能阻碍阶段 1–2）

先检查 `/driveA` 或 `/driveB` 是否已有 **ChEMBL_37 SQLite**。若没有，再从 ChEMBL 官方发布目录取得与已保存 API 版本一致的 SQLite、校验发布方校验值，并放在数据盘；不占用 Ubuntu 启动盘。读 `PRAGMA table_info` 核实 `activities`、`assays`、`target_dictionary`、`docs`、`source` 的字段，再运行有界查询并记录 SQL 文件哈希、数据库文件哈希/发布版本、耗时和行数。

枚举单位是 `(assay_id, molregno)`，先对每条活性判定 `hit_support`、`nonhit_support` 或 `unknown`，再把同一分子在同一 assay 的双向支持标为 `conflict`，不能两边各计一次。现行管线支持：`=` 且 IC50≤1000 nM 为 hit，`=` 且 >1000 为 nonhit；`<`/`<=` 上界≤1000 为 hit；`>` 下界≥1000 与 `>=` 下界>1000 为 nonhit；其余删失界值为 unknown。仅 `=` 的用户示例 SQL 可用于**发现候选的保守下界**，不能作为排除其他 assay 的依据。对结构、有效性标记、潜在重复和单位使用与现行管线相同的处理；SQL 结果仍只是来源分子 ID 预筛，后续必须用 RDKit 正式整理。

候选队列先分 `research_article`（可定位原始论文）、`patent_via_bindingdb`（`src_id=37`）、`direct_patent`（`src_id=38`）和 `other_or_unknown`，**每层内部**再按少数类支持、总支持、来源可解释性与获取成本排序。层级只决定所需证据和报告口径，不预设论文质量高于专利；论文需定位测定方法及表/补充材料，专利需核对例号、受体列、方法与家族重复导入。输出可重现 SQL、过滤阶段数量、冲突/unknown 数、数据版本，以及每层的 assay 总数、各门槛通过数、hold/reject/可冻结数。以 assay 为漏斗分母，另列目标数与去重分子数。先对少数高位候选做 API/SQLite 计数交叉核对，再交给 GLM 审查科学含义。

为保留真正未见的候选判断，按固定哈希规则从 v1–v4 未触及的 assay 中另封存 3 个候选，来源层级尽量覆盖论文和专利。它们不用于调整 S1PR1 的规则；在后续人工/GLM 各自审查前，不向任一方展示对方结论。若清单不足，报告实际数量。这与已暴露的 S1PR1 独立判断是两种不同的评估。

## 阶段 4：v5 控制器和固定预算

- **状态与队列：** 先处理继承的待审 `CHEMBL5734042`。队列项记录已完成阶段、证据 ID、当前 blocker、下一项合法动作与成本；完成/拒绝/暂缓后才取新目标。新版本继承历史只作审计，不改写 v4。
- **动作屏蔽：** 模型只看到当前合法动作。例如未有完整 curation 时不提供 `curation_gate`；元数据未通过时不提供 full fetch；原始 assay 记录数不足 250 时不提供 curation。系统仍对错误动作留痕并拒绝执行。源解释不足可保留 `hold`，不能误写为数值拒绝。
- **输入压缩：** 默认送目标/assay ID、阶段、关键计数、少量证据摘要、最新工具结果、合法动作；长说明和原始记录通过按需只读工具获取。保存每次完整输入哈希、字符/token 用量，以相同任务做一次压缩前后离线回放。减少 prompt token 不等于减少总耗时或保证科学决策更好。
- **预算草案：** S1PR1 只读来源核查 0 次 GLM、0 次新 ChEMBL HTTP；精确计数/整理最多 12 次新 HTTP；独立 GLM 来源判定最多 4 次，必要的深度证据阅读预留 4 次，最终去留及下一候选选择最多 4 次，格式/网络纠错预留 4 次。**本次新增上限 16 次 GLM、40 次 HTTP**，其中先为 S1PR1 保留至少 8 次可用决策，不让新目标画像耗尽这部分预算。按阶段和运行分别计数，另列跨版本累计总账。达到上限时自动生成 `budget_exhausted` 交接记录，列出未决候选与最后证据。若先做全库下载，其传输与本地 SQL 成本另计，不占 ChEMBL API 请求预算。

## 进入 Task 2 的停点

只有 S1PR1（或另一个候选）通过结构/测量、来源/端点和资格检查后，才另建带哈希的 benchmark 版本、公开候选池与私有标签文件；先用合成标签检查 oracle 防泄漏。新 campaign 前固定：50 次预算（含 10 次无放回、只依赖公开结构的初始化），**10 个配对种子 0–9**及同种子共用的初始化清单；随机化合物选择、随机选择三种策略的控制器、固定调度、非 LLM 反馈自适应控制器、GLM 控制器；主/敏感性表示、H@50、累计命中曲线和同种子配对差值。若初始化 10 次没有 hit，不重抽、不按隐藏标签分层，按预定随机回退继续至首个 hit，并记录该情形。若未通过，报告具体 blocker 并继续候选队列，不把 unknown 或 decoy 当实测 nonhit。

## 一周内可核查的交付

**核心交付（按优先级）：**

1. v4 完整证据包、本机哈希核验报告和预算耗尽交接记录。
2. 固定规则下的 S1PR1 来源/端点核查表、人工与 GLM 独立判定对照、整理后池统计；若 hold/reject，写明具体 blocker 与已查范围。
3. ChEMBL_37 SQLite 是否可用、版本/字段核验、可重现枚举 SQL、按来源层级的候选队列与资格漏斗。即使没有新合格池，也报告队列长度、已评估 assay 数和每道门槛的去留数；不称 benchmark 已建成。

**后续工程：** 在核心证据交付后完成 v5 控制器的输入压缩离线回放与完整合成边界测试。若时间紧，先保留已有安全边界，不启动在线 v5 运行；不能为了赶进度跳过新 campaign 的冻结检查。

官方资料：ChEMBL [SQLite 下载说明](https://chembl.gitbook.io/chembl-interface-documentation/frequently-asked-questions/chembl-download-questions)、[数据库 SQL 示例](https://chembl.gitbook.io/chembl-interface-documentation/frequently-asked-questions/schema-questions-and-sql-examples)、[测量与置信度说明](https://chembl.gitbook.io/chembl-interface-documentation/frequently-asked-questions/chembl-data-questions)、[来源 ID 说明](https://chembl.gitbook.io/chembl-interface-documentation/frequently-asked-questions/document-and-data-source-questions)。

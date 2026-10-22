# S-1：授权 D 部分的来源测量修订（采纳 option 1，含六条具体裁决）

`BLOCKED_uncovered_measurement_definitions.md` 的三项观测与推荐均成立。授权 option 1，按以下**逐条裁决**实施，锁哈希为**规则 v3**。D6 A-2 的 G1/G2 阈值数值**仍不变**。

### 裁决 1：`single_source_frac` 重新定义（**使通过更容易**，须声明）

新定义：`n_src = 1` **且** 该身份的替代连接性键来源**全部落在其自身来源并集之内**。

即把那 2,526 个「仅同一来源存在替代完整键」的身份归入 `single_source`，而非 `skeleton_only`。

**理由：** `skeleton_only` 的语义是"连接性已被**独立**来源证实、立体化学未证实"。若替代键来自同一来源，则任何层面都没有独立证实，归入 `skeleton_only` 会**高估**佐证强度。

**方向声明（按 D7 卡的不对称原则，必须写入偏离记录）：** 本次修订降低 `skeleton_only_frac`，因此 G1（`skeleton_only_frac ≥ 0.25` 阻断）更不容易触发，**使受影响候选更容易通过**。补偿性门槛是 G2 的 `full_match_frac` 要求 —— 这些身份在任何定义下都不计入 `full_match`，仍须由 G2 拦截。

### 裁决 2：src_id 37 归入 **T2 专利**分支

锁定的 ChEMBL 37 `source` 表将 37 记为 **BindingDB Patent Bioactivity Data**，与 38 **SureChEMBL Patent Bioactivity Data** 并列。其风险剖面是**专利结构与立体化学抽取**，正是 D5 TACE 的失败模式。因此归 T2（`full_match_frac ≥ 0.50`），不归 T3 文献。这是四个分支中较严的一支，取舍从严。

须在产出中记录：**62 个候选中有 43 个的 assay 支持记录来自 src_id 37**，即本候选池主体为专利来源。该事实须作为漏斗层面的结论报告，不得仅作脚注。

### 裁决 3：聚合来源的伪独立性（**使通过更困难**，须声明）

`full_match_frac` 原按"不同 `src_id` 个数 ≥ 2"计独立佐证。但 37 与 38 均为**专利聚合库**，同一化合物同时出现在两者，很可能是**同一份专利**被两个聚合库分别收录，不构成独立实验确认。

因此独立性改按**来源分组**计数，`n_src_groups` 取代 `n_src`：

| 组 | 成员 src_id |
| --- | --- |
| `G_patent_agg` | **{37, 38}** 合并为一组 |
| `G_deposited` | {7, 21} |
| `G_lit` | {1} |
| 其余 | 每个 src_id 各自成组 |

`full_match` 要求 `n_src_groups ≥ 2`。**方向声明：本条使通过更困难**，属合法收紧。

### 裁决 4：来源范围二分（解除 scope 歧义）

两个问题不同，分别用不同范围：

- **来源层级（T1–T4）** 取自**该 assay 支持记录的活性来源**（assay-supporting activity provenance）—— 它决定这份标签是怎么产生的。
- **凭证计数（`n_src_groups`、替代键来源）** 取自**全部 `compound_records`** —— 它决定该结构在任何地方是否被独立记载。

全局范围中那 34 个未在来源映射内的 src_id：**仅用于凭证计数，各自成独立组，不需要层级映射**。层级只从 assay 来源取，因此不存在未覆盖分支。

### 裁决 5：T4 重新定义（取代"最严分支"）

原文"取最严的一条执行"预设了不同指标之间存在内在严格序，而 T1 用 `structure_resolvable_frac ≥ 0.95`、T2/T3 用 `full_match_frac` 阈值，两者不可比。

新定义：**T4 候选须逐项通过其支持集涉及的每一个层级的对应门槛，全部通过才算 pass。** 任一不过即 fail，并记录是哪一项不过。

### 裁决 6：分割必须穷尽，并增设第四类

四个类别须互斥且和为 1：`full_match_frac`、`skeleton_only_frac`、`single_source_frac`、`unresolvable_frac`（`standard_inchi_key` 为空，或 `n_src_groups = 0`）。

**分母始终为完整支持集**（即 R3 原支持计数），不得改为可解析子集 —— 这样 `unresolvable` 自动计入不利侧，G1/G2 阈值含义不变。逐候选报告 `unresolvable_frac` 分布。

### S-1 的验证条件（与 D6 相同，不是调参）

应用规则 v3 后重跑验证：

1. **TACE `CHEMBL5733557` 的 `shortlist_permitted` 必须为 `false`。**
2. **TNAP `CHEMBL1738510` 的 `shortlist_permitted` 必须为 `true`。**

任一不成立 → **Tier B 停止**，写明实测三/四个比例值与触发分支，**不得改判定表或裁决再试一版**。

**特别预警：** 裁决 2 把 37 归入 T2。若 TNAP 的 assay 支持来源中含 37，TNAP 将落入 T2 专利分支并可能因此 fail。若出现此情形，**停止并报告**，不要为放过 TNAP 调整任何裁决。

### S-1 之后恢复执行

验证通过后，按 D7 卡 D-2 原文继续：产出 `credential_62.csv`（62 行，四个比例每行和为 1）、`gate_decisions_62.csv`，然后 A-4 在 8 个未暴露候选上运行，GLM ≤ 40，名单调用前锁哈希，不计算 precision/recall，草案仍带 `campaign_ready=false`。

---


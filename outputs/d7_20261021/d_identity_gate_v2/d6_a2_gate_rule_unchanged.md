## A-2：预锁判定表（本卡已锁定，不得修改）

以下判定表在**未看到 A-1 分布的情况下**写定。Codex 按表执行，不得增删分支、不得调整数值。

**门槛 G1（全层级通用，立体化学）**
- `skeleton_only_frac ≥ 0.25` → 记 `stereochemistry_unresolved = true`，**`review_shortlist` 阻断**。
- 否则 `stereochemistry_unresolved = false`。

**门槛 G2（按来源层级）**

| 层级 | 条件 | 判定 |
| --- | --- | --- |
| T1 投递筛选数据集 | `structure_resolvable_frac ≥ 0.95` | `pass_t1`；否则 `fail` |
| T2 专利 | `full_match_frac ≥ 0.50` | `pass_t2`；否则 `fail_patent_identity` |
| T3 文献 | `full_match_frac ≥ 0.33` | `pass_t3`；否则 `fail_literature_identity` |
| T4 混合 | 取其支持集涉及的各层级中**最严**的一条执行 | 按该层级记 |

**T1 不要求独立来源互证的理由（设计时已知、须原样记入产出）：** 投递型筛选数据集由投递方提交显式的、机器可读的结构（PubChem CID → ChEMBL 映射），其结构身份风险低于专利/文献的结构抽取；T1 的主导风险是**测量深度与标签的关联**，已由 D3 的 H7a–H7d 门槛独立把关（TNAP 实测 AUC 0.8785、r 0.4949）。此分支是在**已知 TNAP 为单一投递来源**的情况下写定的，理由是上述实质性分工，而非为使 TNAP 通过。若评审认为 T1 仍需来源互证，那是另一个版本的规则，本轮不自行改动。

**最终凭证** `identity_credential ∈ {pass_t1, pass_t2, pass_t3, fail, fail_patent_identity, fail_literature_identity}`，并与 G1 的 `stereochemistry_unresolved` 共同决定 `shortlist_permitted = (G2 为 pass_*) AND (stereochemistry_unresolved == false)`。


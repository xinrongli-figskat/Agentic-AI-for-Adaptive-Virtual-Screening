# D2-2 power declaration, locked before real seed 5–19 calls

The post-exposure DYRK3 v1 feasibility pool has 231 compounds and 116 measured hits. These proxy dispersion values come from the pre-existing D1 paired comparisons, not from the upcoming GLM outcomes.

| Quantity | bit | count |
|---|---:|---:|
| Paired-difference SD, `matched_proportion − structure_prior` proxy | 3.27 | 3.31 |
| Paired SE with n=20 | 0.73 | 0.74 |
| Approximate two-sided detectable difference, 1.96 SE | 1.43 | 1.45 |
| Entire `structure_prior` to `fixed` space | +1.70 | +0.30 |

在 DYRK3 冻结池上，正确地板 `structure_prior` 之上的可测量空间（bit +1.70、count +0.30）与 20 个种子的可检测差值（约 1.43–1.45）同量级，count 上更是远小于检测门限。因此 **"配对区间包含 0"是本次的预期结果，且是一个有效结果**，不得解释为运行失败、实现缺陷或需要调参的信号。本池的区分力上限由数据决定，不由控制器决定。

The bit representation is primary; count is a separate sensitivity analysis. The primary H@50 paired comparisons are GLM minus `structure_prior` and GLM minus fixed greedy. Use 10,000 paired bootstrap resamples, seed 20261018. A paired interval containing zero does not establish extra agent benefit. These retrospective comparisons do not establish performance on another target.

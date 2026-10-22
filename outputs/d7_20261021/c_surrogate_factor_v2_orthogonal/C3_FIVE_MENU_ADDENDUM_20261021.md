# C3 five-menu audit addendum — tied ranks and fixed-versus-meta gaps

2026-10-21 UTC. This additive record supersedes two interpretations in `C3_FIVE_MENU_REPORT.md`; the original report, public JSON, manifest, and 720 private trajectories remain unchanged.

## Spearman tie correction

The six TNAP adaptive gaps in ascending AUC order are 2.15, 4.70, 3.50, 2.15, 1.95, and 2.20 H@50. Means are based on 20 integer-hit runs, so each arm mean is a multiple of 0.05; two mathematically equal gaps printed as 2.15 carry different binary floating-point residues (`2.1500000000000004` and `2.150000000000002`). Applying Spearman directly to these unrounded floats treated them as distinct and produced **−0.20**. The scientifically intended values are exact hundredths. Ranking the values rounded to 0.01 H@50, with **average ranks for the tied 2.15 values**, gives **−0.2898855**, reported as **−0.29**. The average ranks for the six gaps are 2.5, 6, 5, 2.5, 1, 4. The originally reported −0.20 is a numerical tie-handling artifact, not a different dataset.

For the fixed-policy spread, no value is tied; AUC-versus-spread Spearman remains −0.543. Both six-point relationships are descriptive, post-exposure, noncausal and nonmonotonic. Across the measured AUC interval 0.771–0.897, **no systematic relationship was observed**. These results neither establish nor refute the mentor's broader prediction.

## An additional fixed-versus-meta reading

`adaptive_gap` is best fixed mean minus best meta-controller mean. If this exceeds the spread between the best and worst common fixed means, the best meta mean is below **every** common fixed mean. At displayed precision:

| Proxy | Fixed spread | Gap | Gap − spread |
|---|---:|---:|---:|
| S_weak | 2.15 | 2.15 | 0.00 |
| S_morgan_gbdt | 4.15 | 4.70 | +0.55 |
| S_strong | 7.00 | 3.50 | −3.50 |
| S_morgan_logreg | 0.05 | 2.15 | +2.10 |
| S_maccs | 0.55 | 1.95 | +1.40 |
| S_incumbent | 1.75 | 2.20 | +0.45 |

Thus, in four of six TNAP cells, even the best of the three five-menu CPU meta-controllers has lower mean H@50 than all four common fixed arms; `S_weak` is approximately level with the worst fixed arm, and `S_strong` is the exception. The sharpest descriptive case is Morgan logistic regression: the common fixed arms span only 0.05 hit, yet the best meta-controller trails the best fixed arm by 2.15 hits.

These inequalities show that the measured meta-controller loss cannot be explained *only* as choosing a consistently inferior fixed arm. They do **not** prove that switching itself caused the loss; delayed feedback, four decision rounds, menu duplication, seed-specific selections, and the controller update rules are possible contributors. The older D5 seven-menu comparison (best fixed minus Thompson 5.25; best fixed minus five-repeat GLM 0.48) uses a different proxy/menu and is historical context, **not a directly matched comparison** with these six C3 cells. The C4 single-cell experiment is separately versioned for that reason.

The Morgan feature comparison is also descriptive: TNAP AUC was 0.8971 for weighted kNN, 0.8438 for logistic regression, and 0.8034 for GBDT. In this measured setup, the weaker GBDT result is attributable at least partly to model class rather than the Morgan representation alone.

# TNAP v1 D3 CPU controls

Protocol SHA-256 `8384797c0348b51e0b0bb2547b77520b36981d81af4b1320be4e6adb49b17943`; frozen pool receipt `f8801efbe28f73ddbcf9c5a2d493d862cbf124f311b6659e9224f2161b5bf662`. 280 completed campaigns, 0 GLM calls.

Unlabeled 10-query initialization had zero hits in 6/20 seeds: [5, 6, 15, 17, 18, 19]. Random expected H@50: 5.736.

| Representation | Arm | Mean H@50 | SD | First-hit censored (>50) |
|---|---|---:|---:|---:|
| bit | random | 6.00 | 2.47 | 0/20 |
| bit | structure_prior | 11.85 | 0.81 | 0/20 |
| bit | label_shuffle | 3.85 | 3.39 | 0/20 |
| bit | fixed | 20.35 | 12.04 | 1/20 |
| bit | fixed_schedule | 19.30 | 12.80 | 2/20 |
| bit | rule_adaptive_v2 | 18.75 | 11.24 | 1/20 |
| bit | forced_random_coldstart | 25.80 | 6.60 | 0/20 |
| count | random | 6.00 | 2.47 | 0/20 |
| count | structure_prior | 7.00 | 0.86 | 0/20 |
| count | label_shuffle | 3.70 | 2.90 | 0/20 |
| count | fixed | 21.05 | 11.58 | 0/20 |
| count | fixed_schedule | 21.10 | 11.21 | 0/20 |
| count | rule_adaptive_v2 | 20.20 | 11.16 | 0/20 |
| count | forced_random_coldstart | 24.95 | 7.80 | 0/20 |

Main paired bit contrasts (10,000 paired bootstrap resamples, seed 20261018):

| Contrast | Mean difference | 95% percentile interval | Paired SD |
|---|---:|---:|---:|
| fixed-structure_prior | 8.50 | [3.40, 13.25] | 11.54 |
| fixed-label_shuffle | 16.50 | [11.05, 21.70] | 12.45 |

A missing first hit by query 50 is right-censored, not zero or an observed query 51. The aggregate reports conditional means among observed first hits and a separately labeled 51-coded restricted mean.

Zero-hit seed details, forced fallback versus fixed, adaptive trigger rounds, curves, costs, and secondary contrasts are in `aggregate.json`. Bit adaptive trigger: {'seeds_with_trigger': 10, 'total_trigger_rounds': 13, 'round_counts': {4: 9, 2: 1, 3: 3}}; count: {'seeds_with_trigger': 11, 'total_trigger_rounds': 17, 'round_counts': {4: 9, 2: 1, 3: 7}}.

**Scientific limit:** TNAP remains `limited`: the protein construct is unspecified; characterization depth varies by compound (1–21 fitted curves, median 1) and is strongly associated with the assay-defined label (AUC 0.879, r 0.495). This is not direct-binding evidence or a uniform-effort screen. Results cannot be generalized to other targets. GLM was not evaluated in D3.

The original locked runner completed all 280 trajectories but failed while averaging a right-censored first-hit field. `DEVIATION_20261019_D3_REPORTING_CENSOR.md` records the offline-only repair. No campaign was rerun.

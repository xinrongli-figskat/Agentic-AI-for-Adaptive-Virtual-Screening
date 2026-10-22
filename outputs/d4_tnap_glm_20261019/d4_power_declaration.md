# D4-1 power and interpretability declaration

Locked before the first real TNAP GLM campaign call. These are descriptive proxy calculations from D3 bit-representation paired differences, with 20 paired seeds. The detectable column is 1.96 × sd / sqrt(20); it is not a prospective power guarantee.

| Proxy contrast | Paired sd | SE (n=20) | Two-sided detectable scale |
|---|---:|---:|---:|
| fixed − forced_random_coldstart | 9.17 | 2.05 | 4.02 |
| fixed − structure_prior | 11.54 | 2.58 | 5.06 |
| fixed − label_shuffle | 12.45 | 2.78 | 5.45 |
| rule_adaptive_v2 − fixed | 2.28 | 0.51 | 1.00 |

本池的配对差分布因零命中初始化而**双峰**，故"可检测效应"只是量级参考，区间一律以配对 bootstrap 百分位为准。与 DYRK3 不同，本池随机之上的空间约 44.3 个命中（DYRK3 约 24.9），最强 CPU 臂为 25.80，因此**存在真实的可测量余量**；但余量存在不等于 GLM 必然占据它，"区间包含 0"仍是可接受的有效结果。

Primary bit contrasts: GLM − forced_random_coldstart and GLM − structure_prior, each paired by seed. Count is a prespecified sensitivity representation. Intervals use 10,000 paired bootstrap resamples with seed 20261018. No multiple-comparison adjustment is planned; interpretation remains pool-specific.

# D7-A A1 results and A2/A3 status

All results are post-exposure reanalysis of D5. Zero new campaigns; zero GLM calls. The immutable D5 ZIP has the task-card SHA-256 and 760 members. All seven required fixed-arm means and the complete 20-seed GLM H50 vector reproduce exactly.

| Pool / representation | All-arm mean range | Nonrandom mean range | Mean within-seed range [95% bootstrap CI] | Oracle ceiling | Ceiling minus best fixed | Uniform observed / analytic |
|---|---:|---:|---:|---:|---:|---:|
| TNAP bit | 19.80 | 7.35 | 10.55 [6.75, 14.60] | 41.05 | 15.25 | 6.00 / 5.7359 |
| TNAP count | 18.95 | 6.15 | 11.05 [7.15, 15.15] | 41.05 | 16.10 | 6.00 / 5.7359 |
| DYRK3 bit | 5.80 | 2.85 | 5.55 [4.55, 6.55] | 44.65 | 14.05 | 24.80 / 25.1082 |
| DYRK3 count | 6.05 | 2.10 | 4.50 [3.60, 5.45125] | 44.65 | 13.80 | 24.80 / 25.1082 |

The main mean-range comparison is larger on TNAP. The mean within-seed ranges are also larger on TNAP, but DYRK3 has nonzero within-seed differences. The within-seed maximum and minimum can come from different arms for each seed; their range is a retrospective descriptive measure and does not show that a feasible controller can select the better arm in advance. Likewise the oracle ceiling uses known retrospective totals only during evaluation, not as a campaign input.

Uniform deviates from its analytic expectation by +0.2641 on TNAP and -0.3082 on DYRK3. These are descriptive deviations; no new significance claim is made.

Bootstrap uses 10,000 paired-seed resamples, NumPy default_rng seed 20261018, as locked before computation. D5 used 20261020; this reanalysis restores the project seed. All 20 per-seed ranges remain in the JSON for reproducibility.

A2/A3 have not run because the card requires both an exact match to the actual D5 seven-menu GLM interface and equality with a different frozen 14-field interface. Actual synthetic production captures confirm the difference. See BLOCKED_information_set.md. No assertion of bandit determinism, bandit advantage, decision-granularity effects or a new campaign-ready pool is made.

# D7-A approved 11-field revision: CPU results

All analyses are post-exposure. This revision completes A2/A3 after explicit approval of the D5 seven-policy, 11-field interface. Earlier A1, blocker and manifest remain unchanged. New GLM calls: **0**. Unique configurations: **1,160**; physical runs: **1,480**, including independent repeated execution of all **320 bandit configurations**.

## Main g4 comparison (50 queries, 10 initialization, four feedback batches)

| Pool / representation | Thompson H50 | UCB1 H50 | Best fixed mean | D5 GLM mean |
|---|---:|---:|---:|---:|
| TNAP bit | 20.55 | 17.00 | 25.80 | 24.80 |
| TNAP count | 20.40 | 17.35 | 24.95 | 23.35 |
| DYRK3 bit | 28.05 | 27.90 | 30.60 | not run with this menu |
| DYRK3 count | 28.30 | 28.70 | 30.85 | not run with this menu |

TNAP bit's three tied best fixed policies are persistent random until first hit, logistic greedy and ENS proxy. The output reports paired intervals against all three; it does not choose an arbitrary tie winner. Thompson minus these fixed policies has mean -5.25, with intervals [-8.50,-2.20], [-8.25,-2.50] and [-7.85,-2.75], respectively. UCB's corresponding mean is -8.80. Count's best is persistent random until first hit. DYRK3's best is logistic greedy in both representations.

Against the single saved D5 GLM run per seed, TNAP bit Thompson differs by -4.25 [-7.50,-1.30], and UCB by -7.80 [-11.85,-3.70]. These comparisons exclude model-output variance and therefore **do not establish GLM benefit**. D7-B is needed before any such claim; this report does not launch or imply approval for it.

At four decisions the UCB rule spends its time trying the first four untried menu items in the locked order. Seven policies cannot all be tried within four batches. Thompson uses explicit Beta(1,1) priors and fractional reward updates, so its conclusions also concern this specific prior and four-decision design. Inferiority to the hindsight best fixed arm is consistent with limited adaptation opportunities; it does not, by itself, establish a universal impossibility or prove that decision count is the sole cause.

## Decision granularity

| Pool | Decisions | Nonrandom fixed mean range | Mean within-seed range | Thompson | UCB1 | Best fixed |
|---|---:|---:|---:|---:|---:|---:|
| TNAP | 2 | 9.25 | 10.95 | 18.25 | 17.15 | 23.80 |
| TNAP | 4 | 7.35 | 10.55 | 20.55 | 17.00 | 25.80 |
| TNAP | 8 | 5.70 | 10.25 | 22.75 | 22.55 | 26.20 |
| DYRK3 | 2 | 2.00 | 5.60 | 26.95 | 27.70 | 29.90 |
| DYRK3 | 4 | 2.85 | 5.55 | 28.05 | 27.90 | 30.60 |
| DYRK3 | 8 | 1.85 | 4.90 | 29.35 | 29.35 | 31.05 |

Increasing decisions from four to eight did **not** increase the measured within-seed strategy spread: TNAP paired change -0.30 [-1.85,1.30], DYRK3 -0.65 [-1.65,0.50]. Thus this scan does not support the proposed explanation that the four-point design suppressed a larger measurable fixed-arm spread. Bandit means improve at eight decisions, but the best fixed arm improves too; spread and achievable adaptive advantage are distinct quantities. At TNAP g8 Thompson minus logistic greedy is -3.45 [-7.85,1.00]; this includes zero and does not demonstrate superiority. All interval calculations use 10,000 paired-seed bootstrap resamples, seed 20261018, and are descriptive without multiplicity correction.

The unchanged ENS implementation keeps its top-10 fantasy utility at all three granularities. This preserves the locked policy, but means the scan changes decision batch size while holding that policy's planning horizon constant. No new pool or qualification threshold is produced.

## Verification

- Actual production D5 summary construction, no-network stub: exactly 11 fields; every g4 summary matches all original D5 values. g2/g8 modify only batch-size wording.
- Synthetic hidden-measurement perturbation leaves summaries and controller decisions unchanged. Rewards use only changes in cumulative already revealed hit/query counts, including variable batch sizes.
- All 320 bandit configurations were run twice with fresh state; complete timing-free trajectories and terminal posteriors match exactly. No posterior crosses a seed or campaign.
- The 280 g4 fixed-policy runs (two pools, **bit only**, seven policies, 20 seeds) exactly match D5 selections, observations and cumulative counts. All initializations use and are checked against D5's seeded rule.
- Known-good D5 ZIP means and exact 20-element GLM vector passed before and after execution. Frozen sources and D5 numerical code are imported unchanged.
- Parent independently recomputed 1,480 transcripts, 5,360 summary checks and 1,440 reward updates; its record resides at the root output directory, outside this child manifest.

Specification/code locked at **2026-10-21T10:19:12.013032+00:00**; last CPU job completed at **10:19:37.487413+00:00**, approximately 25.10 wall seconds with eight CPU workers and one BLAS/OpenMP thread per worker. API calls and GPU use were both zero. Public outputs contain H50 and aggregate data; per-compound transcripts are in the gitignored `runs_private/` directory.

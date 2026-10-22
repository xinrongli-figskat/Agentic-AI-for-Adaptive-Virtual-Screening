# C3 orthogonal factor experiment — audited interim report

Date: 2026-10-21. Post-exposure, CPU-only analysis; no new benchmark, no pool
or label change, no GLM call. Full matrix: 1,880 completed campaigns, each
with 50 distinct queries and the same ten-query label-blind initialization
within each pool/seed. The integrity audit passed; private details have a
combined SHA-256 of
`5e646c289355a43ef81926a112035f6eb7f002dd7b573e734892ba9ab2de2b62`.
The DYRK3 input is the hash-verified backup copy. The local CPU matrix took
968 s; the remote 4090 and GPU were not used.

The six proxy AUC values were locked before C3. On TNAP, the four common
fixed-policy H@50 spreads and paired 95% bootstrap intervals were:

| Proxy | OOF AUC | Fixed spread | Paired 95% interval |
| --- | ---: | ---: | ---: |
| S_weak | 0.771 | 2.15 | [1.25, 3.15] |
| S_morgan_gbdt | 0.803 | 4.15 | [1.50, 7.00] |
| S_strong | 0.821 | 7.00 | [4.70, 9.35] |
| S_morgan_logreg | 0.844 | 0.05 | [0.00, 0.60] |
| S_maccs | 0.864 | 0.55 | [0.05, 1.80] |
| S_incumbent | 0.897 | 1.75 | [0.10, 3.95] |

The fixed spread does not shrink monotonically with AUC. Its six-point
Spearman correlation is −0.543, a descriptive statistic from only six
post-exposure proxy choices, not evidence of a general law. The largest gap
is under `S_strong`: greedy finds 16.65 hits at query 50 on average, while
diverse finds 9.65. TNAP pure random is 6.00 versus the analytic 5.736.

DYRK3 pure random is 24.80 versus analytic 25.108. It remains the CPU
negative-control pool and fails the pre-existing pool-level LLM signal gate;
no DYRK3 C4 GLM run is planned. In the current fixed-spread gate, only TNAP
`S_strong` has a bootstrap lower bound at least 2.0. This is a **candidate
for CP-2 consideration**, not authorization to call GLM.

An important interface consequence: the locked C1 one-class random fallback
makes greedy and persistent-random identical in every measured pool/proxy
seed, and likewise makes diverse and diverse-random-coldstart identical.
TNAP logged 208 one-class fallback batches; DYRK3 logged none. Thus four
named common policies have only two distinct trajectories at fixed proxy.
The D5 original kNN means 20.35/18.45 remain historical; under C1 fallback,
the revised incumbent means are 25.80/24.05. All seven versioned regressions
passed, with `S_morgan_logreg` matching D5 `logreg_greedy` at 25.80 and the
modified incumbent ENS mean at 26.15.

The D5 menu had mixed a predictor switch (`logreg_greedy`) with acquisition
rules; this factorization makes Morgan logistic regression a proxy and leaves
the acquisition rules model-agnostic. D7-A bandits used D5's seven-item
menu and remain historical comparisons. C3 bandits use the new menu, so they
do not replace D7-A results. A future `llm_policy_only` controller would also
be distinct from D5 `glm_extended`; direct performance attribution between
them would be invalid.

**Open consistency issue:** fixed GBDT ENS was skipped for equal-compute
feasibility, but six-menu GBDT meta controllers chose full-size ENS 116 times.
Their adaptive gaps and the six-point AUC–adaptive-gap trend are provisional;
see `DEVIATION_C3_GBDT_META_ENS.md`. The fixed-policy table above is unaffected.
No C4 GLM calls will be made until this menu is resolved and CP-2 is granted.

# D9 report — preset-library-visible policy controller

**Date:** 2026-10-22. **Status:** complete, post-exposure. D9 used the local CPU and the authorised Zhipu API only. It did not use Git or the remote workstation, freeze a new pool, change the 1000 nM threshold, or modify any D3–D8 artifact. The historical C4 analysis and its private trajectories remain byte-for-byte unchanged.

## What was tested

The one new controller arm used the existing TNAP pool (462 compounds), S_strong prediction method, bit representation, five named selection rules, 20 seeds, and the same 10 initial compounds per seed as C4. It selected 50 distinct compounds per run in four feedback rounds. The new information was the full preset candidate list with compound keys, standardised SMILES and current predicted probabilities. Experimental results remained hidden until selection. The controller still chose a rule, not individual compounds. Its system instruction was adapted to describe the visible library; therefore the prompt text did not differ *solely* by added rows, a limitation on causal attribution.

The protocol and run code were hashed in `D9_LOCK.json` before the first D9 provider request. A 20-seed, zero-provider-call preflight confirmed identical C4 initialisations, equivalent S_strong scores, and all four information-boundary conditions. Seeds 0–9 formed a mandatory checkpoint; `CHECKPOINT_0_9.json` passed before seeds 10–19 began. The full 20-run audit passed: each run made 50 unique selections and completed four feedback batches.

## Reconciliation of C4 behavior counts

The D9 task card identified a seeming inconsistency between C4's named-policy counts and its executed-behavior counts. Direct recount of all 40 C4 private trajectories showed **both original tables were correct**. Named policies counted 102 `diverse`, 5 `diverse_random_coldstart`, 38 `greedy`, 14 `persistent_random_until_first_hit`, and 1 `random`. Executed behavior counted **104 diversity-like, 42 greedy-like, and 14 random** among 160 batches. Thirteen cold-start batches were random because no active compound had yet been revealed; one batch used explicit random. One of the 13 was an automatic zero-hit commitment without a new GLM call, but it still consumed ten queries and counted as one executed batch. There were no one-class random fallbacks. The nominal 107/52/1 mapping in the task card omitted the cold-start condition. No C4 table needs correction; `C4_BEHAVIOUR_COUNT_RECONCILIATION.json` preserves both original values, the recount, source hashes, and the explanation. The C4 active count mean reproduced **11.325** exactly.

## Frequency-matched CPU comparisons

For each seed and feedback round, a fixed SHA-256 stream drew one of three behavior classes at the model's observed overall frequencies. Each 20-seed configuration was run twice, with exact equality of every full trajectory. Intervals use 10,000 same-seed paired bootstrap resamples with seed 20261018. A one-class state still invokes the locked random fallback, so realised frequencies can differ from the draw weights.

| Prediction method | Observed LLM behavior weights, greedy/diverse/random | CPU mix mean actives in 50 selections | LLM mean | LLM − mix | Paired 95% interval |
|---|---:|---:|---:|---:|---:|
| S_strong, five-rule C4 | 42 / 104 / 14 | 11.20 | 11.325 | +0.125 | [−0.650, 0.975] |
| S_incumbent, original seven-rule D5 bit arm | 37 / 36 / 7 | 24.90 | 24.80 | −0.10 | [−2.25, 1.80] |

The S_strong interval includes zero, so selection timing has no detectable contribution beyond the observed rule preference in this comparison. The S_incumbent contrast is **descriptive**: seven-menu ENS and logistic-regression choices were coarsened to model-ranked/greedy-like, though neither executes the same selections as the five-menu S_incumbent greedy rule. D5 bit-only nominal counts were 20 nearest-neighbour greedy, 35 nearest-neighbour diverse, 15 one-step lookahead, 2 logistic-regression greedy, 5 cold-start diverse, and 3 random; the zero-hit state was applied before coarsening. The intervals do not support the task card's rough arithmetic expectations of +0.16 and +2.4 as general conclusions: the S_strong estimate is close (+0.125), whereas the S_incumbent observed estimate is −0.10, 2.50 actives below its +2.4 estimate. This difference and the menu coarsening rule are recorded rather than adjusted after seeing outcomes.

## Library-visible controller result

| Arm or comparison | Mean actives in 50 selections | Difference, library-visible minus reference | Paired seed-bootstrap 95% interval |
|---|---:|---:|---:|
| Library-visible GLM, one run × 20 seeds | **14.25** | — | — |
| C4 policy-only GLM, two runs × 20 seeds | 11.325 | **+2.925** | **[+0.424, +5.550]** |
| Fixed greedy | 16.65 | −2.40 | [−4.30, −0.80] |
| Five-menu Thompson sampling | 13.15 | +1.10 | [−1.55, +3.65] |
| C4-frequency-matched CPU mix | 11.20 | +3.05 | [+0.40, +5.75] |

The primary interval remains above zero when the B-line between-run model SD of 2.1943108257491692 is incorporated as an additional approximate model-noise term: model SE = 0.601 and interval **[+0.191, +5.798]**. This is a sensitivity calculation on top of seed resampling, not a claim of independent prospective validation. The fixed-rule regression checks reproduced greedy **16.65** and diverse **9.65**.

The model's named choices in D9 were 54 greedy, 17 diverse, 6 diverse-with-random-cold-start, and 3 random (80 total). Their **executed** behaviors were 54 greedy-like, 17 diversity-like, and 9 random. Thus diversity-like batches fell to **17/80 = 21.25%**, from **104/160 = 65.0%** in C4. This is the central mechanism observation: with a visible library, the model used the diversity penalty much less often. D9 outperformed the old C4-frequency mix, but that comparator matches C4's frequencies, not D9's; this contrast alone cannot distinguish a new static preference from superior decision timing.

Under the pre-registered interpretation, the library-visible controller is **clearly better than the policy-only C4 arm in this cell and moves toward the fixed greedy result**, while still falling short of fixed greedy. The former information restriction plausibly mattered. This is one post-exposure pool, one surrogate, one five-rule menu and one model run per seed. It does not establish a general advantage over a prescribed controller and does not answer whether the benefit changes with surrogate predictive strength. D5's expanded-menu controller and D7-A bandits use different menus and/or predictors and are not direct head-to-head comparisons with D9.

## Boundary, reliability and cost

All 80 planned decisions yielded strict valid JSON with exactly `policy` and `reason`; **0/81 physical requests** yielded a format-invalid response. One additional physical request timed out during TLS handshake before an assay selection; the run paused, retained the receipt and resumed from the same public state. In total, **81 physical API requests** were made, below the D9 maximum 88. Starting from the task-card project baseline 683, the recorded cumulative physical count is **764**, below 1,000. There was no parser relaxation or fallback policy.

For **every physical request**, the saved pre-network receipt confirms four passed assertions: the prompt carried exactly all 462 candidate keys; candidate rows had no outcome field; no hidden pool-level label aggregate, near-threshold measurement or measurement-effort field was present; and revealed active/inactive keys matched only compounds already selected. The same payload was checked against the actual serialized request body. The full-run trajectory audit rechecked all saved model calls. These checks establish the encoded information boundary for this run; the Python process still holds the oracle internally and is not a separate operating-system security boundary.

The provider returned usage on all 80 valid responses: **3,916,491 prompt tokens**, 18,718 completion tokens, and 3,935,209 total, or **48,956 prompt tokens per valid decision**. The 23,413-token/card estimate derived from payload bytes substantially understated provider-reported usage. The timed-out call returned no usage, so its billable token amount is unknown; token counts are not cash charges.

## Files and scope

Public D9 protocol, lock, reconciliation, checkpoint, analysis, report and advisor summary live in this directory. The full frequency-control trajectories, D9 assay-result trajectories, response content and per-call HTTP receipts live under `d9_private/`; they must stay out of any public repository or disclosure package. Source hashes and the D9 file manifest allow local verification. No new pool or campaign version was frozen.

# C4 five-policy GLM arm: completed TNAP × S_strong cell

**Date:** 2026-10-21. **Status:** complete, post-exposure retrospective experiment; no new benchmark. This arm tests one TNAP × `S_strong` × bit cell. It does **not** answer whether LLM benefit systematically changes with surrogate strength. The [original protocol](C4_PROTOCOL_v1.md) and the [single-decision extension](C4_EXTENSION_PROTOCOL_v1.md) were locked before their respective calls. The original 160-call ceiling was reached at 39/40 campaigns; the user then approved at most four additional physical calls solely for the last decision. One was used. Existing locked files and the 160-call checkpoint were not rewritten.

## Outcome

Forty campaigns completed: two GLM repeats for each of 20 matched seeds, with 10 label-blind initialization queries plus four batches of 10 per campaign. The GLM arm averaged **11.325 H@50**. The preselected primary CPU comparator, five-menu Thompson sampling, averaged **13.15 H@50**. The seed-paired difference (GLM minus Thompson) was **−1.825** hits; its 10,000-resample paired seed bootstrap 95% interval was **[−4.10, 0.275]**. A sensitivity interval adding the previously measured B-line model SD of 2.1943 was **[−4.197, 0.365]**. Both cross zero: this cell provides **no evidence that the GLM outperformed the selected CPU meta-controller**, nor a conclusive primary-test finding that it underperformed it.

| Comparator | Mean H@50 | GLM minus comparator | Paired 95% interval |
| --- | ---: | ---: | ---: |
| Thompson (preselected primary) | 13.15 | −1.825 | [−4.10, 0.275] |
| UCB1 | 11.60 | −0.275 | [−2.00, 1.325] |
| Uniform five-name mixture | 13.00 | −1.675 | [−4.325, 0.700] |
| Greedy (post-hoc best common fixed arm) | 16.65 | −5.325 | [−7.825, −2.925] |

The greedy contrast is secondary and exploratory: its interval excludes zero, but the best fixed arm was selected after observing the fixed-arm outcomes, no multiple-comparison correction was applied, and this is one chosen cell. Under this C4 menu/proxy the GLM did **not** reproduce the earlier D5 description of being nearly tied with the best fixed arm. D5 and C4 cannot be directly compared because their menus and/or proxy differ. These observations also do not isolate a causal “switching cost”; poor choices, the information summary, stochastic outputs, and the chosen proxy can all contribute.

The two GLM repeat means were 11.15 and 11.50; 10/20 seed pairs had identical H@50 and 51/80 same-seed feedback positions had the same named policy. The GLM selected `diverse` 102 times, `greedy` 38, `persistent_random_until_first_hit` 14, `diverse_random_coldstart` 5, and `random` once. After mapping names to actual selection behavior, there were **104 diverse-like, 42 greedy-like, and 14 random batches**. The name count alone would misstate the actual action mix. The five-name uniform mixture is not uniform over these three behaviors.

## Reliability and budget

The 40 campaigns made **2,000 unique within-campaign oracle queries** in total. There were 160 feedback batches: 159 strict-format GLM decisions and one automatic continuation of an earlier persistent-random choice. Exactly **161 physical provider attempts** were used, including the one-call approved extension. Of these, 159 returned valid decisions and two failed during transport; there were **zero** model-format failures in 159 returned decision responses. Returned usage was **89,970 prompt + 12,018 completion = 101,988 tokens**; usage for the two transport failures was not returned, and token usage is not a cash-billing figure. The initial 160-call halt is preserved in [its report](C4_BUDGET_HALT_REPORT.md).

The [full audit](C4_AUDIT.json) passed: 40 complete trajectories, exactly 50 unique selections each, correct frozen-label observations, no ENS, and no out-of-menu decision. The synthetic-label prompt/oracle boundary check passed before calls. Raw provider responses, trajectories, and labels are in the Git-ignored private directory `outputs/d7_20261021/c4_five_private`; the public aggregate contains no individual labels. A local scan of 362 private JSON files found no occurrence of the API key. The private evidence-tree digest and all aggregate results are recorded in [C4_AUDIT.json](C4_AUDIT.json) and [C4_PUBLIC_ANALYSIS.json](C4_PUBLIC_ANALYSIS.json).

## Interpretation and limits

This is a single, post-exposure TNAP cell chosen because its fixed-policy spread was large. It asks whether GLM can recover policy headroom left by three CPU meta-controllers; the answer here is **not demonstrated**. It is not a cross-proxy trend test, a blind prospective evaluation, a new protein pool, or a new benchmark. The comparison to greedy shows that the GLM also fell well short of the strongest fixed arm in this cell. It does not establish that GLM control always loses, or that a different prompt, summary, or surrogate would behave the same way. The frozen pool and labels were unchanged.

The separate C3 rank-correlation correction is additive: rounded two-decimal adaptive gaps with average ranks for the tied 2.15 values give Spearman **−0.29**, while unrounded floating residues yielded the earlier −0.20. See [C3_FIVE_MENU_ADDENDUM_20261021.md](../c_surrogate_factor_v2_orthogonal/C3_FIVE_MENU_ADDENDUM_20261021.md). The six post-exposure cells show no systematic monotone relationship over their observed AUC range; this C4 experiment adds no second cell to that trend analysis.

# D11 report

D11 is a post-exposure ablation of policy-instruction framing, using the same aggregate-only information surface as C4. The point estimate is consistent with an instruction-framing contribution, while the remaining D9–D11 difference is uncertain. This experiment does not isolate the information surface from D9’s field-dependent wording.

No Git operation was performed; no new pool was frozen; no D3–D10 artifact was modified.

D11 found a mean of **13.00 hits in 50 queries**. Against C4’s seed-matched two-run mean of 11.325, the difference was **+1.675** (paired seed-bootstrap 95% interval **+0.10 to +3.65**). After adding the prespecified model-noise component, the sensitivity interval was **−0.294 to +3.949**, which includes zero. Against D9, D11 was **1.25 lower** (D11−D9: **−1.25**, 95% interval **−3.35 to +0.75**). Thus the point estimates partition the earlier D9−C4 difference of +2.925 into +1.675 for the instruction-framing contrast and +1.25 for the remaining information-plus-field-dependent-wording contrast. These intervals are not additive, and the single D11 repeat per seed limits resolution.

The executed diversity-penalized behavior share was **43/80 (53.8%)**, between C4’s **104/160 (65.0%)** and D9’s **17/80 (21.3%)**. Under the prespecified descriptive bands, the result is **intermediate**: it is neither C4-like (the primary interval excludes zero) nor D9-like (the behavior share is outside the registered D9-like band). The descriptive bands are not equivalence margins. This intermediate outcome does not support attributing D9’s entire gain to either information access or instruction wording alone.

Secondary comparisons: D11 minus fixed greedy was **−3.65** (95% interval **−5.90 to −1.50**); D11 minus Thompson sampling was **−0.15** (**−2.45 to +1.95**). These are exploratory and unadjusted.

All four information-boundary assertions passed for **all 82 physical attempts**. A receipt audit reconstructed the C4 public summary at each decision and confirmed the exact request-body hash and assertions for every attempt. Seed initializations matched C4 and D9 for all 20 seeds. There were **79 valid GLM decisions**; one later batch followed C4’s automatic zero-hit commitment. The 82 physical attempts comprised **81 provider responses**, two invalid-format responses (2/82, **2.44% per physical attempt**) and one DNS/transport failure. Invalid responses were retried once with the identical request body; there was no parser relaxation or policy fallback. Returned usage was **48,141 prompt tokens**, **6,614 completion tokens**, **54,755 total tokens**. Starting from the stated project baseline of 764, cumulative physical attempts are **846/1,000**.

The conclusion is limited to one TNAP pool, one S_strong model, one policy menu, 20 seeds with one D11 repeat per seed, and a post-exposure design. No multiplicity adjustment was applied. The result does not generalize to other targets or information surfaces.

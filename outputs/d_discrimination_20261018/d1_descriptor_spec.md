# D1 descriptor and comparison specification

Locked before any descriptor–label association or `structure_prior` result is computed. This is a **post-exposure descriptive analysis** of frozen DYRK3 v1, not a new benchmark, blind validation, or campaign. The original protocol and 30 runs remain unchanged. Brief: compare simple reference strategies with a prescribed controller using the same information and query budget; use targeted analyses to examine consequential modeling choices.

## Structural input and descriptors

Use only `candidates.jsonl` from the frozen public pool (231 unique `compound_key`, `standardized_smiles`). Sort by `compound_key` for all pairwise and Butina calculations. Morgan radius 2, 2048 bits, chirality enabled. Main representation is bit; sensitivity representation is sparse count with the same radius and chirality. Similarity is RDKit Tanimoto. Butina uses the complete lower-triangle distance vector `1 - similarity`, distance cutoff `1 - 0.7`, `isDistData=True`, `reordering=True`. These settings agree with `outputs/b3_pending_assay_private_20261017/build_metrics.py:62-75` and `outputs/p1_negcoverage_private_20261018/DEVIATION_20261018_P1.md`; any actual-code difference must be logged before calculation.

The **primary descriptor** `mean_tanimoto_k5` is each compound's average Tanimoto to its five nearest *other* pool compounds. Five matches the campaign's kNN neighbor count and proxies attraction to a dense analogue region. Ties among neighbors are ordered by compound key. Separate sensitivity descriptors are: `butina_cluster_size` (number of members in the assigned Butina cluster); `cluster_centrality` (mean similarity to other members in that cluster, 0 for a singleton); and `degree_t07` (number of other compounds with Tanimoto >= 0.7). Descriptor calculation never loads labels.

## Evaluation only

Only after descriptors have been saved, load the private frozen `oracle_labels.jsonl` in a separate evaluation stage. For each descriptor and representation, report ROC-AUC against true hits, point-biserial correlation, and H@50 from descending descriptor rank; ties use `SHA256("structprior|seed|round|compound_key")` only in the strategy, while descriptive H@50 uses ascending `compound_key` for a fixed, disclosed tie rule. Save compound-level labels and cluster hit rates only under a directory whose name contains `_private_`.

For mechanism interpretation, define the dense group as the top 25% of compounds by Butina cluster size (ties broken by compound key), and compare its true hit fraction with 116/231. The mechanism is supported only if primary AUC is above 0.5 with a compound-bootstrap descriptive 95% interval entirely above 0.5 **and** dense-group hit rate exceeds 116/231. If primary AUC is near 0.5 (interval includes 0.5), abandon the proposed density explanation; do not swap primary descriptors after seeing results. Compound bootstrap uses 10,000 resamples, seed 20261018, and is descriptive because related molecules are dependent.

## Label-blind structural reference and decomposition

`structure_prior` has the same seed-specific 10-compound *unlabeled* initialization as the frozen control arms. Four following batches of 10 select the highest remaining `mean_tanimoto_k5`; ties sort by `SHA256("structprior|seed|round|compound_key")`, then compound key. Initialization counts toward the 50-query budget. The reference selector receives no `revealed` records or outcomes. Replacing all oracle outcomes must leave its complete selection sequence unchanged for a given seed. Seeds 0–19 and bit/count are separate.

**Prediction fixed before results:** If the density mechanism holds, `label_shuffle − structure_prior` should be near zero (paired bootstrap interval contains zero). Report the result even if it contradicts this prediction.

On each representation separately, use 20 paired seeds and 10,000 bootstrap resamples of seed pairs (seed 20261018) for mean H@50 differences and percentile 95% intervals: `structure_prior − random`, `label_shuffle − structure_prior`, **`fixed − label_shuffle` (primary estimate of correct-label feedback value)**, `fixed − structure_prior`, and `fixed − random` (legacy secondary comparison). Also report `random_mixture`, `matched_proportion`, `fixed_schedule`, and the existing `rule_adaptive_v1` against each of random, structure_prior, and label_shuffle. Existing GLM seeds 0–4 may be reported separately with low-power caveat; do not impute GLM seeds 5–19. The new `rule_adaptive_v2` belongs to D2 and is not a D1 result.

`structure_prior` is a simple reference floor, not a new shared tool offered to GLM. If a later version offers structural scores to GLM, the same score must enter every arm's shared tool menu. No GLM calls in D1.

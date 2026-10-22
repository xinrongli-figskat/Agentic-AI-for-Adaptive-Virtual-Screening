# D7-C6 v2 — corrections to prior records

This is an additive post-exposure correction. It preserves D6 and D7-C v1 artifacts and does not change frozen pools, labels, thresholds, or prior decisions.

1. **Model-SD definition.** D6's `4.20` is the standard deviation of the difference between two runs, not the SD of a single run. D7 planning used it as if it were a single-run SD, making variance corrections about `sqrt(2)` too wide. D7-B measured single-run `SD_model = 2.1943108257491692`. Use the D7-B re-expression for affected comparisons; leave the original D6/interim text intact as historical record.
2. **First-round reproducibility.** D6's 10-seed summary described 60% disagreement. D7-B compared 200 pairs with identical within-seed first-round public summaries and measured agreement `0.615`, hence disagreement `0.385`. Later-round agreement `0.3583` is contaminated by diverging states and must retain that caveat.
3. **C v1 design fault.** C v1 preregistered an assumed model-strength order and made failure to match it a hard stop. C v2 replaces that with observed ROC-AUC ranking and a preregistered trend analysis. The C v1 stop and refusal to relabel after seeing the outcome were correct; the design error was in the C v1 task card, not in execution.

## Substantive, limited finding

On this congeneric, assay-derived pool, under the C2 v1 label characterization, Morgan-fingerprint kNN had ROC-AUC `0.8971`, compared with MACCS + logistic regression `0.8642`, 2D descriptors + gradient boosting `0.8206`, and physicochemical descriptors + logistic regression `0.7711`. Greater model complexity did not imply better ranking in this example. This is a post-exposure, pool-specific observation, not evidence that simpler models generally outperform more complex ones.

Sources: `outputs/d7_20261021/b_model_variance/B_REPORT.md`, `B_ANALYSIS.json`, and the unchanged historical D6/D7-C v1 records.

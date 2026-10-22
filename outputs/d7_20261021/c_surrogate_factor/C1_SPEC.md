# D7-C1 proxy definitions — pre-result code lock

Date: 2026-10-21. Status: post-exposure implementation specification. This file and
`c1_surrogates.py` are fixed before any D7-C2 strength scores or D7-C3 campaigns.
The D7 original task card and its 2026-10-21 addendum govern all decisions.

Only the two existing human-target pools, TNAP and DYRK3, are in scope. The
candidate interface is exactly `compound_key` plus `standardized_smiles`.
Features are built from these public structures alone. A campaign score call
receives only previously queried `(compound_key, outcome)` pairs. The code has
no private-file, oracle, network, or model-weight reader.

The four preregistered models, in expected weak-to-strong order, are:

1. `S_weak`: eight RDKit physical descriptors, in the order `MolWt`, `MolLogP`,
   `TPSA`, `HBD`, `HBA`, `RotBonds`, `Rings`, `AromaticRings`; logistic regression
   `C=1`, `liblinear`, `random_state=0`, `max_iter=200`. Missing/nonfinite values
   are imputed from training medians, then centered/scaled from training only.
2. `S_maccs`: MACCS bits 1–166 (bit 0 omitted), same logistic model; median
   imputation from training only, no scaling.
3. `S_incumbent`: unchanged `campaign_v0.numerical_tools.NumericalTools`
   Morgan bit r2/2048/chirality and its original weighted 5-neighbor `score_knn`.
   The D7 code calls that function and does not copy or modify its scoring rule.
4. `S_strong`: RDKit 2D descriptor functions from the complete
   `Descriptors._descList`, sorted by descriptor name, with nonfinite values
   imputed from training medians; `GradientBoostingClassifier` with 200 trees,
   depth 3, learning rate 0.1, random state 0. No scaling.

The RDKit version is pinned in code to `2026.09.1`, the version recorded in
the DYRK3 frozen manifest. At first execution, record installed RDKit,
scikit-learn and NumPy versions and the exact sorted descriptor-name list with
its SHA-256 *before* reading any C2 labels. A different version or descriptor
set is a hard stop requiring a new, pre-result version, not an implicit update.

C2 is an offline private characterization only. Use sorted compound keys and
`StratifiedKFold(n_splits=5, shuffle=True, random_state=0)`. Fit preprocessing
within each training fold, collect one out-of-fold score per compound, then
compute pooled ROC-AUC and EF1%. EF1 selects the top `ceil(0.01*N)` scores,
ties by compound key, and divides the selected hit fraction by full-pool hit
fraction. The expected **strict** ROC-AUC ordering is
`S_weak < S_maccs < S_incumbent < S_strong` separately for each pool. EF1 is
reported but does not override that preregistered ordering. If either pool
violates the order, stop C after C2 under the original Tier B rule; do not
rename models to fit outcomes.

C3, if admitted, uses only the bit representation, 20 fixed seeds, 50 oracle
queries including 10 initialization, and the ten arms in the D7 card. At
each feedback point, refit the chosen surrogate from revealed outcomes only.
If observations contain one class, use the frozen `uniform_random` policy for
that batch, record the fallback, and charge every query to the 50 budget.
Store individual outcomes and trajectories only in a gitignored private path.
Public output may contain pool-level and proxy-level aggregates only.

This local implementation has passed syntax compilation only. It cannot be
executed here because RDKit, scikit-learn and SciPy are absent. Local DYRK3
data are available only inside an independently hash-verified backup archive;
the live frozen directory and ChEMBL SQLite are absent. The eleven-input D7
preflight was passed on the remote host, not on this local environment. Thus
the C2 and C3 gates remain closed in this local work package.

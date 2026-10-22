# C1 v2 additive proxy specification — 2026-10-21

Status: post-exposure; lock before new six-proxy scoring. The original four
proxies in `../c_surrogate_factor/C1_SPEC.md` and their measured metrics remain
unchanged. The fifth proxy, `S_morgan_gbdt`, was already scored in C2-v2; its
pre-score lock and result remain unchanged. This additive specification defines
only the two new proxy implementations for the orthogonal C3 design.

Both use the incumbent Morgan bit fingerprints (radius 2, size 2048,
chirality). `S_morgan_logreg` uses the D5 `ExpandedTools._feature_matrix`
construction: active bit columns in sorted order and a float64 CSR matrix.
Its estimator is **the actual D5 code**:
`LogisticRegression(C=1.0, solver="liblinear", random_state=0, max_iter=200)`.
The task-card sentence saying D5 omitted `max_iter=200` conflicts with the
frozen source. Exact D5 behavior takes precedence for the seven required
regressions; this discrepancy is recorded rather than silently repaired.
`S_morgan_gbdt` uses 2048 dense binary columns and
`GradientBoostingClassifier(n_estimators=200, max_depth=3,
learning_rate=0.1, random_state=0)` as already locked in C2-v2.

Each score call accepts only already revealed `(compound_key, outcome)` pairs.
Each feedback stage refits the proxy. With only one observed class, selection
uses the frozen uniform-random policy for that batch and charges all ten
queries. Labels are never used to build features or choose model definitions.

For the new logistic proxy, characterize both frozen pools with five-fold
`StratifiedKFold(shuffle=True, random_state=0)`, pooled ROC-AUC, and EF1 at
the top `ceil(0.01*N)` compounds, ties by compound key. Keep per-compound
scores and outcomes in the ignored private directory; publish aggregates only.
Reuse existing C2 measurements for the other five proxies. Sort all six by
observed TNAP AUC before any C3 run. Tier B: TNAP AUC span at least 0.05,
and each new proxy within 0.15 of the existing five-proxy AUC range.

No C4 GLM call is authorized by this specification. CP-2 approval remains
mandatory before any C4 LLM cell.

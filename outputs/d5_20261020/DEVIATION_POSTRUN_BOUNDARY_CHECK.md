# D5 preflight timing deviation

The locked D5 menu spec requested a synthetic outcome-permutation check before real campaigns. The preflight on 2026-10-20 completed 28 synthetic full campaigns, public-field checks, common initialization checks, three unit tests, and a synthetic GLM request. It did **not** explicitly compare numerical scores after permuting revealed synthetic outcomes. This was noticed after 760 real runs had completed. The preflight receipt is preserved unchanged.

The separate `e_menu_postrun_boundary_check.json` was run later using synthetic outcomes only. Across both pools and both representations, seeded uniform selection was unchanged under a permutation of revealed labels, while weighted-kNN scores changed. This late check verifies those limited properties but does not retroactively satisfy the pre-run timing requirement. No frozen data, labels, threshold, legacy policy or campaign trajectory was changed.

The spec also mentioned a `structure_prior` permutation check. D5's seven policies and GLM prompt do not consume a `structure_prior` field. Its value-permutation check is therefore inapplicable to this version; the public candidate rows still contain only `compound_key` and `standardized_smiles`.

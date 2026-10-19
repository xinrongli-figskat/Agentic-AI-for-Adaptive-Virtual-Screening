# D2-1 second attempt: test entry-point repair

User authorization was given on 2026-10-19 after the first D2-1 attempt stopped with `ModuleNotFoundError: No module named 'oracle_boundary'`. The first blocked attempt and its hashes remain unchanged at `outputs/d2_controls_20261019/d2_rule_adaptive_private_20261019/` and `outputs/d2_controls_20261019/BLOCKER.md`.

This new attempt changes only the **test invocation**: the existing `oracle_boundary_v0/test_oracle_boundary.py` is run with `cwd=oracle_boundary_v0` and module name `test_oracle_boundary`, matching its own top-level import of `oracle_boundary`. The script's output path and self-check paths were also redirected to this new attempt directory so it cannot overwrite the first attempt. The scientific rule, budget, seed set, frozen pool, old controls, labels, thresholds, and the oracle test file are unchanged.

The D2-1 rule remains the previously locked `d2_rule_adaptive_spec.md` with SHA-256 `6d7d54a8ae84a53916f151c74249451d486993ccd6e7814818c1d18df126951a` (locked 2026-10-19 10:21:33 UTC). The first attempt's D2-4 result remains **failed**; this second attempt must rerun every D2-1 and D2-4 acceptance check. Any new failure is another hard stop, not a reason to silently alter the rule or test.

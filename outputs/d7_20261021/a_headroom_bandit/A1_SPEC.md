# D7-A independent A1 reanalysis specification

Post-exposure. New campaign runs: 0. GLM calls: 0. This specification applies only to A1 and the synthetic information-field inspection; A2/A3 await resolution of the literal information-set conflict.

Source: D5 locked e_menu_results.json and authoritative private ZIP; require their task-card SHA-256 values before using any result. Read ZIP in place, do not extract or alter old files. Require 760 members. Verify all seven TNAP bit fixed means and the exact 20-element GLM H50 vector in the D7 card.

For each pool and representation, use 20 paired seed results for seven fixed menu items. Nontrivial set means six items, resolving the card's explicit corrected footnote over the earlier word 'five'. Report the seven-mean range, six-mean range, and mean of per-seed six-arm ranges. For the latter use NumPy default_rng(20261018), 10,000 paired seed bootstrap resamples and linear 2.5/97.5 percentiles. The RNG restarts for each cell so resampling indices are common across cells.

Oracle ceiling conditional on each saved initialization is initial_hits + min(40, total_pool_hits - initial_hits). It describes an unattainable perfect-information retrospective bound, never a predictive input. Subtract the best fixed-arm mean. Validate shared initialization across arms, compare uniform mean with 50 K/N (TNAP N=462 K=53; DYRK3 N=231 K=116). Public outputs contain only aggregate or per-seed H50/range statistics, no per-compound measurements.

Before any A2 outcomes, the following D7 interpretation must remain in any future bandit specification: four decisions versus seven arms make adaptation prior-dominated. Failure to exceed best fixed is evidence about this limited decision budget, not evidence that LLMs alone are weak. A bandit matching or exceeding GLM would indicate no extra value relative to that baseline; GLM exceeding bandit cannot support a benefit claim before D7-B variance measurement.

Synthetic information check invokes both actual frozen campaign_v0.llm_controller.ToolChoiceLLMController and D5 seven-menu run_extended.Controller using synthetic data and no-network capture stubs. Compare emitted field sets exactly. A2/A3 cannot be represented as accepted if they cannot meet both D7's same-LLM-information and frozen-field-set-equality requirements. No bandit determinism success is claimed before an actual replay.

For future A3, preserve D5 ENS's fixed top-10 future utility horizon and all existing numerical policy code; only next_batch_size changes. This note authorizes no A2/A3 execution.

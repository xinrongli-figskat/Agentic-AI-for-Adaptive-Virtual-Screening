# GLM probe result after repairing synthetic state

Recorded 2026-10-15 from user-supplied terminal output. The repaired probe used six synthetic candidates, one revealed nonhit, five unqueried candidates and a next batch of one. It did not load or query any DYRK3 outcome.

Official `glm-4.7-flash` returned valid JSON with policy `uniform_random`. It cited 0 hits from 1 revealed query as the reason to explore. Prompt usage was 335 tokens, completion 57 tokens, reasoning 0, total 392; request ID `202610142357362b606de10138457f`. This confirms that the specific JSON/disabled-thinking settings worked at least once and were much cheaper in tokens than the first malformed-state probe (2,662 total, 2,283 reasoning). A transient HTTP 429 occurred between the two successes; its business code was unavailable, so no cause was inferred.

The policy is responsive to the synthetic feedback, but the phrase “no predictive signal for kNN” is too strong: even one observed nonhit can inform similarity-based ranking. One synthetic decision does not establish scientific quality or robust API availability. Before freezing, the controller was enhanced to receive all revealed outcomes and numerical score/similarity diagnostics computed only from those outcomes. This revised prompt still needs a final synthetic connection check on the remote machine. No real-label campaign has run.

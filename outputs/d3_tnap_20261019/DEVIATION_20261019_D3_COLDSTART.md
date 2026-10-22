# Deviation from the 2026-10-17 low-hit fallback proposal

Original design: when all revealed outcomes are nonhits, every new control would temporarily use `uniform_random` until the first hit, consuming normal queries. The previously frozen `fixed` controller did not follow this rule. The original file `outputs/low_hit_fallback_design_private_20261017/protocol_proposal.md` remains unchanged.

New D3 design: no implicit fallback for primary comparison arms; preserve the former behavior as the separate secondary arm `forced_random_coldstart`. All arms share the same initialization, tools, and 50-query budget.

Reasons: **comparability** with prescribed `fixed` under the brief's same-tools/same-information/same-budget condition; **the premise was disproven** because all-negative feedback drives the existing weighted kNN toward structural novelty; **auditability** because no undisclosed override masks the declared policy. The prospective impact is about 5.8 of 20 TNAP seeds starting with zero hits (N=462, K=53, initialization=10). This is a protocol deviation recorded before D3 data results, not a rewrite of earlier runs. The forced fallback's value will be measured directly against `fixed`.

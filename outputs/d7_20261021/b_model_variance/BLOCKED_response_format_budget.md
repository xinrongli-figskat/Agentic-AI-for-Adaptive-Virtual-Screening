# D7-B Tier B stop: one invalid GLM response exhausts the exact 360-call design

Date: 2026-10-21 UTC. Post-exposure measurement, not a benchmark or efficacy result.

## Locked rule and observed trigger

The D7 task card requires TNAP bit/D5 V0, 20 seeds × 5 repeats, reusing D6 seeds 0–9 as first repeats, with **at most 360 new GLM decision calls**. It requires the unchanged D5 controller and a receipt for every call. The D5 controller requires the response JSON to have exactly `policy` and `reason` keys.

The new pilot (seed 0, repeat 2) passed, with four decisions and four HTTP requests. The batch then completed all ten new first repeats (seeds 10–19) and 13 second repeats (seeds 0–12). At second repeat, seed 13, initialization and one feedback batch were saved (20 unique queries, one successful GLM decision). The next GLM request returned HTTP 200 and a syntactically valid JSON object with `policy` and `reason` **plus one empty-string key**. The unchanged D5 strict parser raised `ValueError: Invalid D5 GLM policy JSON`; it did not execute that selection or query the oracle. The raw provider response, request ID, usage and timing remain in the private `decision_002.json` and `http_002.json`; the failure event remains next to the partial run. No API key is serialized.

At the stop: 33/100 planned campaigns are complete (10 pre-existing D6 + 23 new). There are 94 new model-decision receipts and 94 physical HTTP receipts: 93 valid decisions (92 from completed new campaigns, one in seed 13 repeat 2), one invalid decision, zero HTTP retries. Completing all planned repeats needs 267 further valid decisions (three in the partial campaign plus 66 entire campaigns × four). The remaining 360-call budget is 266. Therefore the preregistered complete matrix is **mathematically impossible under the current cap**, even if every future model response is valid. No additional GLM calls have been made after this determination.

## Options requiring a new explicit decision

1. **Increase the D7-B new-decision cap from 360 to at least 361 and keep the 20×5 design.** This preserves the intended balanced repetition but is a post-trigger budget deviation. If D7-C later uses 240 calls, the whole-project 600-call reporting checkpoint must be re-planned before C begins; one cannot silently pass 600. This is the preferred scientifically clean repair if more calls are authorized. The invalid request and its cost remain in the ledger.
2. **Keep the 360 cap and end with an incomplete matrix**, reporting only 99 complete campaigns or an explicitly unbalanced set. This preserves the budget but violates the locked 20×5 and changes variance precision. A revised missing-data analysis and a new protocol must precede any resumed calls.
3. **Reuse a historical D5 seed-13 run as the missing repeat**, with explicit contamination/correlation caveats. This avoids a call but changes the predeclared provenance (which specified only D6 replay reuse), and that D5 run is also the historical comparator being reinterpreted. It is not recommended.

The parser will not be relaxed, the failed response will not be removed from the budget, and the frozen D5 run/labels/policies remain untouched. D7-B2 and B3 cannot be finalized from this incomplete data under the original design; D7-C LLM work remains stopped pending the Tier B disposition. Independent CPU work is unaffected.

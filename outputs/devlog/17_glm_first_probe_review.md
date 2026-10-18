# First real GLM connection probe review

Date: 2026-10-14. The user ran `python -m campaign_v0.probe_glm --model glm-4.7-flash` on the remote Ubuntu desktop. This was a synthetic-feedback request; no DYRK3 labels or private files were loaded.

The API responded with a valid JSON policy choice, so the official endpoint, account, model name and authentication worked. Returned usage was 298 prompt tokens, 2,364 completion tokens (including 2,283 reasoning tokens), 2,662 total tokens; request ID `202610142346326880734ea2794c9e`.

**Probe defect:** the synthetic state claimed one candidate in total, one already queried, and one more query to make. These values are inconsistent. The model's explanation then asserted that one candidate remained. The JSON format success is valid evidence of connection, but the policy rationale from this request is **not evidence of decision quality**.

Before another probe or campaign, the public-state controller now rejects inconsistent counts and IDs before calling GLM. The new probe has six synthetic candidates, one revealed nonhit, five unqueried candidates and a batch size of one. The adapter requests `thinking: disabled` and a 256-token output limit; this should reduce the large reasoning-token cost observed above, but whether the chosen model honors these settings requires a second real synthetic probe. Offline tests cover the corrected state and request payload. The first result is retained as a failed prompt-quality check, not silently overwritten.

The DYRK3 data remains pre-freeze. No real-label query has yet occurred.

# D7 A2/A3: Tier B information-set specification conflict

Post-exposure. Recorded after the synthetic capture at 2026-10-21T09:52:00.293491+00:00; document timestamp is its filesystem write time. No bandit campaign or GLM request has been run.

Trigger: D7 A2 requires "在与 LLM 完全相同的信息面" on the same seven-item menu. Its acceptance criterion separately requires "bandit 的信息面与 llm_controller.py 的 public_summary 字段集一致；用程序化断言核对字段集合".

Observed: the frozen `campaign_v0/llm_controller.py` emits **14** summary fields. D5's actual seven-menu `outputs/d5_20261020/e_menu/run_extended.py::Controller` emits **11**. `information_set_conflict.json` captures both actual production methods using the same synthetic state and no-network clients. Their intersection has nine fields. Frozen-only fields are `next_batch_size`, `recent_observations`, `recent_revealed_count`, `revealed_observations`, `unqueried_count`. D5-only fields are `task`, `commitment_note`. Thus adopting either exact field set cannot satisfy both literal requirements. This is not evidence of exposed private data; the additional frozen fields contain only already revealed observations.

Possible resolutions, none applied:

1. **Recommended:** explicitly replace the acceptance comparator with the D5 seven-menu production summary (11 fields). This preserves the actual comparison with D5 GLM. Bandit computes previous-batch reward from differences in cumulative revealed_hits, supporting g2/g8 without assuming recent_revealed_hits covers the whole batch. Lock the amended comparator before new CPU outcomes. Cost: a narrow task-card amendment and then full A2/A3 work.
2. Use the 14-field frozen controller contract for bandits, accepting that this is a larger information interface than D5 GLM (though counts suffice for these bandits). Cost: expressly relax equal-information wording, document the extra fields and restrict actual use; this weakens the clean interface comparison.
3. Define a common new information adapter and give both bandits and new GLM runs that same adapter. Cost: a new comparison version and additional GLM budget; historical D5 GLM remains a contextual reference, not an exact matched-interface comparator.

A1 is independent and complete. A2/A3 are stopped; deterministic replay and bandit field equality are **not performed/not passed**, not silently waived. ENS's fixed top-10 lookahead horizon would remain unchanged under any proposed granularity scan.

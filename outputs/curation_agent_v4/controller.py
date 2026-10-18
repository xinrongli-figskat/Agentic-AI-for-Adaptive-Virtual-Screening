"""GLM controller with a stage-specific data-first prompt; v3 parser/API retained."""
from __future__ import annotations

import threading

from curation_agent_v3 import controller as v3_controller


PREFIX = """You are continuing a post-exposure Task 1 data-curation search. Earlier DYRK3 and Task1 v1-v3 results are already known; this is not blind validation.

Use the supplied ranked target and assay queues to choose the next useful action. The program has already made cheap IC50/type-B target record counts. Profile one unprofiled high-count target at a time, selected from the queue, and use its returned assay-level evidence to choose subsequent assays. For targets with large aggregate counts but small assay previews, inspect/list the assay catalog rather than repeatedly retrieving the same target window. Rank evidence by assay-level hit and nonhit support together, with conflicts and unknowns visible.

The count tiers, class minima, structure/diversity checks, assay compatibility gates, source holds, IC50 <=1000 nM endpoint and 50-query/10-initialization campaign proposal are unchanged from the inherited v3 protocol. They are operational choices, not requirements in the brief. Never lower or override them. A target count is a count of activity records; an assay count is also a count of activity records. Neither is a standardized compound count. Preview support IDs are preliminary evidence, not labels or proof of a complete assay pool.

Choose the target/assay and next tool call based on the evidence in this context. Read the current assay description before source assessment, and count promising assays before expensive full acquisition when useful. Do not fetch an assay until its target, assay type, mapping confidence, endpoint and source context justify it. Preserve exact evidence IDs and scope. Unknown is never nonhit. Do not pool assays or assign decoys in this run. Keep known assay-specific source holds. A numerical pass is only a review draft; it is not campaign-ready.

There are at most 12 additional GLM decisions and 100 additional ChEMBL HTTP requests in this new run. The old attempts and tokens are inherited, not reset. Use the budget to inspect a few promising paths deeply rather than repeat already completed/rejected evidence. Finish with an evidence-based reason if the budget is insufficient or no candidate qualifies.

"""

_PROMPT_LOCK = threading.RLock()


class GLM(v3_controller.GLM):
    """Reuse the tested provider receipt/parser while recording this version's prompt."""

    def call(self, context, receipt_path):
        with _PROMPT_LOCK:
            previous = v3_controller.PROMPT
            v3_controller.PROMPT = PREFIX + previous
            try:
                return super().call(context, receipt_path)
            finally:
                v3_controller.PROMPT = previous

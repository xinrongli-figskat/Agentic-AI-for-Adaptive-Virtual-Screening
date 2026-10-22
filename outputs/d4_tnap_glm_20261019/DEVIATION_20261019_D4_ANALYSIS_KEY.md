# D4 Tier A mechanical repair, analysis attempt 2

Attempt 1 stopped before writing analysis outputs. Its unmodified script and error are preserved in `attempt1_20261019/`; the script SHA-256 is `6ecdb8b7bad5a57f9e53640fc4def6bfc317447b17744e5116345b8806c8d4af`.

The reader used `d3['arm_summaries']`, while the already frozen D3 aggregate uses `d3['arm_stats']`. The correction changes only the key used to read the same D3 mean H@50 values. It does not change any source data, treatment assignment, label, threshold, comparison, test statistic, or pass criterion. New results go to `attempt2_20261019/`; attempt 1 stays intact.

Known-good regression before retry: recompute D3 bit fixed and forced-random-coldstart means from all 20 unmodified per-run summaries, require 20.35 and 25.80, and require equality to the original aggregate's `arm_stats`. Also recheck one GLM seed's 50 unique queried compounds and outcome sum against its saved H@50. Then rerun the **entire** D4 analysis, not just the failed assertion. This is Tier A repair 1/2. If the retry fails, retain its output and classify the new fault independently under the task-card rules.

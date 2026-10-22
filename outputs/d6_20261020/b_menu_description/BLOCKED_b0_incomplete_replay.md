# B-0 blocked: incomplete replay receipt

## Trigger

D6-B0 requires ten TNAP-bit seeds and 40 provider decisions before its
determinism rule can be applied. The assigned private output contains exactly
one completed seed (seed 0, four decisions), and no receipt for seeds 1–9.

## Observed state

The saved seed-0 sequence is:

`ens_one_step_proxy, knn_greedy, logreg_greedy, ens_one_step_proxy`.

The corresponding D5 reference sequence is:

`knn_diverse, knn_greedy, knn_greedy, knn_greedy`.

This is one differing sequence, which is insufficient to invoke the D6-B0
rule for two or more differences. The D6 card instead requires an independent
rerun of that one seed if exactly one difference is found. The replay process
ended before the other nine planned seeds and left no exception record, so the
intended 40-decision experiment has not been completed.

## Candidate next actions

1. Add execution-only exception capture and a durable per-seed progress log,
   then resume seeds 1–9 and, if appropriate, independently rerun seed 0.
   This preserves the locked D5 request construction and consumes the
   remaining authorized B-0 calls.
2. Treat the missing process-level diagnostic as an infrastructure failure and
   halt D6-B permanently. This preserves budget but leaves the description
   ablation untested.

The recommended action is option 1, because it changes only D6-B orchestration
and is needed to distinguish a provider/transport interruption from a
deterministic policy difference. It must be authorized and logged before any
additional provider request.

# Mechanical regression-checker repair — 2026-10-21

The locked v3 checker completed six of seven cases, then raised
`RuntimeError: ENS cold-start fallback missing`. Its validation loop paired
`responses[0]` (initialization) with `modes[1]` (the first feedback decision)
and then appended initialization observations again. At the next check it
still saw one class even when the first feedback batch had revealed a hit.
This is a test-index error. It did not alter C1, C3 selection, labels, budget,
the original v3 script, or any historical D5 record.

The v3.1 checker pairs `responses[1:]` with `modes[1:]`, so each policy mode
is evaluated against observations *before* that feedback batch. The first
six completed v3 comparisons remain valid. The original checker and lock
remain unchanged. This additive repair is separately hashed and locked before
rerun; no C3 full matrix or C4 GLM calls occurred before the repair.

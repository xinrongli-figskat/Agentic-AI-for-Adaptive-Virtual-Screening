# D6 controlled-experiment closeout

**Status:** Tier B stopped.  **Nature:** post-exposure evidence and harness
checks; this run created no new benchmark, no campaign-ready pool, and did not
modify frozen pools, labels, thresholds, old policies, or historical results.

## Immutable inputs

The D6 task card and all eight required preflight hashes were verified before
work.  The required legacy-code and frozen-artifact hashes were checked again
afterwards and remained unchanged.  The preflight record is
`d6_preflight_baseline.json`.

## A. Identity credential gate

A-1 stopped before calculating a 62-row credential table.  Five saved,
standardized support identities correspond to two distinct original ChEMBL
`molregno` values (parent/salt forms).  The locked A-1 rule defines its source
measure for a singular `molregno` but supplies no aggregation rule for this
one-to-many mapping.  Choosing an aggregation would change the measurement
unit, so it is a specification issue rather than a permissible implementation
choice.  `a_identity_gate/BLOCKED_support_identity_mapping.md` preserves the
observations and alternative resolutions.  A-2 through A-4 were not started;
therefore no new Task 1 review decision or GLM call was made by A.

## B. Menu-description reproducibility gate

B0 made exactly 40 authorized GLM decisions: TNAP, bit representation, seeds
0--9, four feedback decisions each.  The first seed completed before a
path-only post-run inspection error.  The repair added the runner's existing
`runs/` directory to the inspection path and reused that completed seed, so no
extra call was made.  All 40 receipts are in the gitignored
`b_menu_description_private/` directory.

All ten replayed policy sequences differ from their corresponding D5 records,
despite the locked model settings, source hashes, pool, seed, and V0 menu.
This triggers the task card's Tier B nondeterminism stop.  B1--B4 were not
started: there are no synthetic-menu results and no new campaign runs.  The
result means the planned single-call description ablation has no valid
deterministic basis.  It is not evidence that a different menu makes the model
more capable.

## C. D5 report addendum

The D5 report hash was confirmed before a separate, immutable addendum was
written.  It records that the forced cold-start and persistent fixed controls
are the same arm; restores the omitted uniform-random reference; documents the
three-way finite-resolution tie; and records the bootstrap-seed comparison.
No GLM call or campaign run occurred in C.

## Consequence

The first-wave verification forbids D6's second wave.  The next version must
first resolve A's identity-unit definition and redesign B as a stochastic,
replicated experiment; neither change is made in this run.  D6 remains a
useful negative result: its gates prevented a false claim that a prompt/menu
effect or source credential had been demonstrated.

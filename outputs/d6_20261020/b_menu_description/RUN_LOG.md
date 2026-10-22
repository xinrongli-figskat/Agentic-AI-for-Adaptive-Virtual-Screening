# D6-B run log

- **Scope:** post-exposure D6-B menu-description experiment.  No frozen pool,
  label, threshold, or pre-existing policy implementation was changed.
- **Preflight:** all eight required D6 hashes, including the ChEMBL 37 SQLite
  hash, matched before B0.
- **B0:** 40 TNAP-bit decisions for seeds 0--9 were run with the D5 V0
  configuration.  A path-layer error after seed 0 was repaired without
  rerunning seed 0; the repair is documented in
  `DEVIATION_TIER_A_B0_PATH_REPAIR.md`.  Exactly 40 private decision receipts
  were saved.
- **Result:** all 10 four-round policy sequences differed from the corresponding
  D5 records.  This triggers the D6 Tier B nondeterminism stop.  B1--B4 were
  not started, so no synthetic probes or additional campaign calls were made.
- **Budget:** 40 GLM decision calls used; 350 of the D6-B allocation remain
  unused.  This is not evidence that a menu description improves model choice.

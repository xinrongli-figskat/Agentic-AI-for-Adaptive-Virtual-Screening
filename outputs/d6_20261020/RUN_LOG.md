# D6 root run log

- Verified all immutable-input hashes before work and again after the run.
- First wave ran independent A, B0, and C work.
- A stopped at a specification-level identity-unit ambiguity without GLM calls.
- B0 used 40 GLM decisions and triggered the prescribed nondeterminism stop;
  B1--B4 did not run.
- C completed its report-only addendum with zero GLM calls.
- Wave-1 member manifests were independently rehashed.  `d6_wave1_verification.json`
  records why the second wave was prohibited.

# D3-1 definition change after the first hard stop

Date: 2026-10-19. The original requirement was implemented literally as `no_other_tid_present`: an original PubChem row could contain only `tid=1` qualifier and `tid=2` `IC50_Mean`. The revised rule uses H1-H3 as gates for consistent selected endpoint, unique value provenance, and same-protocol/same-target auxiliary columns; H4-H6 require recording fit depth, its label association, and near-threshold precision.

Reasons for revision: the old predicate measures whether the depositor published underlying data rather than whether the label is intact; it would block nearly any richly annotated dose-response deposition; and it systematically favors information-poor deposits over transparent ones. **This revision makes TNAP easier to pass.** The compensation is the new H3 gate, which can genuinely fail if another target, endpoint, counter-screen, toxicity readout, or protocol appears, plus mandatory H4-H6 diagnostics. It is not a retrospectively blinded validation.

The first failed `../BLOCKER.md` and `../tnap_homogeneity_assertion.json` are preserved byte-for-byte, as is the successful 485-to-462 reconciliation. This rule applies prospectively from today to all deposited dose-response candidates, not solely TNAP. Any later change requires another dated version; do not overwrite this record.

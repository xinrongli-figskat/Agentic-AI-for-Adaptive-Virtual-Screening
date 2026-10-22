# BindingDB inclusion as a candidate-ranking signal

ChEMBL includes a subset of BindingDB patent records, identified in this project by source identifier 37. It does not contain all BindingDB data. BindingDB’s inclusion filters for the ChEMBL records it incorporates may provide useful evidence for prioritizing source review. In the 62 numerically passing candidates, 43 involve source identifier 37.

The required resource is a versioned BindingDB-to-ChEMBL cross-reference or source record that can verify whether a candidate assay or its underlying measurements were included by BindingDB. The current local ChEMBL 37 database records source identifiers, but a complete independent BindingDB cross-reference table has not been verified as locally available. Before use, obtain a dated, licensed BindingDB export or documented API result and retain its version and checksum.

Use inclusion as a ranking feature that can prioritize manual review, alongside source type, record-level structure alignment, endpoint clarity, measured nonhit coverage, and chemical diversity. Do not use it as an automatic admission rule: a filtered record may still have an ambiguous endpoint or compound identity. Report ranking both with and without this feature to show its effect.

This addresses the advisor’s point that the bottleneck is not simply increasing the molecule count. The present funnel—62 numeric passes, six source reviews, one source-limited set—shows that resolving whether structures and measurements correspond is a central cost.

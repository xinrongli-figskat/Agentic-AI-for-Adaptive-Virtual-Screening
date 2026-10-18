# TNAP CHEMBL1738510 source-gap adjudication

Date: 2026-10-18. Post-exposure draft applying [the general rule](source_gap_adjudication_rule_20261018.md). The original numerical criteria, labels and previous ranking remain unchanged. This case is **not campaign-ready**.

| Item | Finding | Evidence |
|---|---|---|
| Classification | `limited`, conditional on the two pre-freeze checks below | General rule, locked before this case; source alignment summary |
| Target identity | RefSeq `NP_000469.3`, tissue-nonspecific alkaline phosphatase precursor, *Homo sapiens*, taxon 9606 | `outputs/private/r4_source_review_private_20261018/source_inputs/tnap_alignment_summary.json` → `source_target` |
| Experimental method | Cell-free TNAP enzyme activity, CDP-star substrate, luminescent readout, fitted `IC50_Mean` | Same → `source_method` |
| Readout columns | `ic50_mean_tid=2`; `qualifier_tid=1` | Same → `source_readout_columns` |
| Record alignment | PubChem AID 1056: 485 source rows; ChEMBL: 485 records; 485 matched; fixed main sample 12/12 matched | Same → `pubchem_substance_rows`, `chEMBL_records`, `alignment_counts.matched`, `fixed_main_sample_matched` |
| Source gap | AID identifies a human TNAP accession and names the protein supplier, but does not describe the exact expression construct or protein preparation | Same → `source_protein_preparation_note` |
| Question 1: label wrong or ambiguous? | No evidence of an alignment or readout-column ambiguity in the reviewed records. The complete 485-row readout assertion is still required before freezing. | Same → alignment and readout fields; pre-freeze check 1 below |
| Question 2: compound-dependent heterogeneity? | No evidence in the reviewed source: one AID, one described method, one readout-column pair and the same protein supplier. The unresolved preparation is treated as a pool-wide constant **conditional on** the full homogeneity check, not as proven molecular identity. | Same → `pubchem_aid`, `source_method`, `source_readout_columns`, `source_protein_preparation_note` |
| Question 3: external interpretation only? | Yes, if the two checks below pass. The unresolved construct limits the biological interpretation beyond this assay. | General rule and preceding evidence |
| Claims excluded | These IC50 labels are assay-defined inhibition, not proof of direct binding. PubChem Active/Inactive is not reused: its roughly 100 µM convention differs from this project's 1 µM IC50 threshold. | Same → `source_activity_threshold_note` |

Before any freeze, two tasks remain:

1. Assert across **all 485 rows** that the measurement uses `tid=2` `IC50_Mean` and `tid=1` qualifier, with no second readout mixed in.
2. Account by qualifier, censoring, deduplication and conflict rules for every record between 485 raw observations and 462 usable curated compounds (difference: 23). The difference is a count to reconcile, not 23 presumed nonhits or 23 presumed exclusions.

If either check fails or cannot be verified, reclassify as `blocker` or `unverifiable` under the general rule. Until both pass, `campaign_ready=false`; this record does not authorize a campaign.

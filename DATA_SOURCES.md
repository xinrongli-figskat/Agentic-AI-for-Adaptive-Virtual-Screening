# Data sources and attribution

## ChEMBL

- **Release:** ChEMBL 37, SQLite distribution.
- **File checksum (SHA-256):** `4be13df3b68e25dcd0bff44bf094033b5aebe98f415acdc8c1cdf380e0c15142`
- **Size:** 30,480,314,368 bytes.
- **Licence:** CC-BY-SA 3.0. ChEMBL must be cited in any work derived from this repository,
  and the share-alike condition propagates to derived data.
- The database copy itself is **not** distributed here.

## Primary evaluation set

- **Assay:** human tissue-nonspecific alkaline phosphatase, `CHEMBL1738510`.
- **Upstream deposition:** PubChem BioAssay **AID 1056**.
- 485 source records reduced to 462 usable standardised compounds; 53 measured actives and
  409 measured inactives under a fixed 1,000 nM activity threshold.

## Secondary set (negative control only)

- A DYRK3 assay set, 231 compounds, 116 measured actives and 115 measured inactives.
- Admitted with three recorded qualification exceptions and subsequently shown to carry no
  detectable signal. Reported as a negative control, not as a benchmark.

## Source provenance of candidates

`src_id` values in ChEMBL that supplied the activity records behind the 62 numerically
qualifying candidates:

| `src_id` | Source | Role here |
| --- | --- | --- |
| 7, 21 | PubChem BioAssay and deposited supplementary data | Depositor-supplied screening data; supplies the primary evaluation set |
| 37 | BindingDB **patent** bioactivity data | Supplies activity records behind **43 of the 62** candidates |
| 38 | SureChEMBL patent bioactivity data | Patent-derived |
| 1 | Literature-curated | Literature-derived |

Note that ChEMBL carries BindingDB's **patent** subset rather than BindingDB in full. For the
purpose of counting independent attestation of a structure, sources 37 and 38 are treated as
one patent-aggregator group, because a compound appearing in both is likely the same patent
read by two aggregators.

Because 43 of 62 candidates are patent-derived, unverifiable patent structure identity is the
dominant admission risk across this candidate pool rather than an isolated case.

## Citation

Underlying assay data must be cited to their original sources. The hashes recorded in this
repository establish only which analysis file produced which reported figure.

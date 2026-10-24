# Agentic Active Search for Virtual Screening

**Does a language model add value when it steers compound selection in an iterative screening loop?**
This project builds the apparatus needed to answer that, and reports what the apparatus found.

`One-month research prototype` · `Python` · `ChEMBL 37` · `846 Task 2 API attempts, including post-exposure experiments` · [Manuscript draft](#manuscript)

---

## The short version

A language model placed in control of an active-search loop was asked to pick a compound-selection
rule at each feedback round. Three things came out of testing it:

| | Finding | Evidence |
|---|---|---|
| **1** | **No distinct benefit from switching timing was detected** | The model matched a static mixture drawn at its own observed rule frequencies in all 3 settings tested (differences +0.13, −0.10, +1.40; all intervals span zero) |
| **2** | **Controller information and instructions matter in this setting** | Making the library visible while revising its explanatory prompt moved performance by **+2.93 actives** (95% CI 0.42–5.55); an instruction-only ablation had a +1.68 point estimate, with a model-noise sensitivity interval spanning zero. The two effects are not fully separable. |
| **3** | **A fixed rule still wins in the library-visible test** | Committing to ranking-by-predicted-activity beat the library-visible language-model controller by **2.40 actives** (CI 0.80–4.30) |

The honest summary is mixed-to-negative — and the most useful part of the project is the
measurement apparatus that makes a negative result *interpretable* rather than ambiguous.

---

## Why the apparatus was the hard part

**A benchmark can carry strong signal and still leave a controller nothing to do.** The standard
check — true labels beat permuted labels — proves the labels are learnable, not that the *choice of
rule* matters. I measured settings where the available rules differ by **0.05 actives** out of a
50-compound budget. No controller can gain more than 0.05 there, so a null result describes the
dataset, not the controller. I made the between-rule range an admission criterion.

**Suitable public assay data are scarce.** A funnel over ChEMBL 37 ran 1,206 candidate assays →
62 passing numerical and structural screens → 6 surviving source review → **1 usable evaluation
set** (462 compounds, 53 measured actives, 409 measured inactives). Relaxing documentation
requirements changed nothing: 59 of 62 are blocked on *compound identity*, not paperwork.

**Controller variability matters.** Under deterministic decoding
with byte-identical prompts, the model chose a different rule in **38.5% of 200 paired decisions**.
Repeated runs at a fixed seed varied with a standard deviation of **2.19 actives** — larger than
most effects under study. Structured-output failures ran 0.7% overall (3/418), unevenly distributed.
The library-visible and instruction-only arms each had one model run per seed; their intervals have
limited resolution despite the 20 paired seeds.

---

## Three data-quality criteria public bioactivity data commonly violate

Each was added because a candidate failed it, and each is cheap to check.

1. **Measurement-effort bias.** A proxy for how much follow-up testing a compound received predicted
   its label at **0.879 ROC-AUC**, against **0.598** for the strongest structural descriptor. The
   depositor measured promising compounds more; the "signal" is the data-collection process.
2. **Unverifiable compound identity.** 59 of 62 candidates could not have their supporting structures
   independently attested. 43 of 62 draw on patent-derived depositions, making this the dominant risk.
3. **No headroom between rules.** Computable only after a set is frozen, and it bounds any controller
   claim the set can support.

---

## Methodology

- **Pre-specified comparisons.** For the locked experimental arms, primary and secondary contrasts,
  resampling seeds, and interpretations for possible outcomes were recorded before their model calls.
  The choice of some settings was post-exposure and is labelled as such.
- **A hash-locked protocol chain.** Protocol, analysis, and evidence files trace the reported
  comparisons and distinguish rules fixed in advance from post-exposure analyses.
- **Repeated evaluation where available.** The main TNAP comparisons use 20 paired seeds and 10,000 bootstrap
  resamples at a fixed seed. Some arms have multiple model runs per seed; for single-run arms,
  separate sensitivity intervals incorporate measured run-to-run variance.
- **Deviations published, not tidied away.** Including analyses that were stopped on a specification
  gap, corrected after a variance-estimation error of my own, and two of my own hypotheses that later
  measurements refuted.

---

## Repository layout

```
data/benchmarks/        frozen evaluation sets — compound keys and structures (results withheld)
outputs/campaign_v0/    active-search harness, selection rules, controller interface
outputs/d3…d11/         each experimental round: protocol, locks, analyses, reports, deviations
PROTOCOL_INDEX.md       what was fixed before which run — and what was not
MANUSCRIPT_EVIDENCE_INDEX.md   every reported number → its source file, hash, pre-registration status
DATA_SOURCES.md         ChEMBL 37 attribution and source provenance
PRE_PUBLIC_CHECKLIST.md audit gate for any change in repository visibility
```

**Reproducible, not blinded.** The source assay is public and named, so the measured results can be
re-derived from the cited records. They are withheld here so derived label sets are not
redistributed — not because they are secret. The record of when results were used rests on the
protocol chain, not on secrecy.

---

## Manuscript

A manuscript is in preparation, targeting a computational-methods venue. Its three claims are the
findings above; its contributions are the admission protocol, the reliability measurements, and the
frequency-matched control that separates rule choice from switching timing.

*Link to be added.*

---

## Limitations

One evaluation set carries the main controller comparisons. Most analyses are post-exposure and
labelled as such. The strongest fixed rule is identified retrospectively, making it an optimistic comparator. No correction
for multiple comparisons is applied. The data-construction agent produced no usable evaluation set
autonomously — reported as a finding, not hidden. The library-visible frequency-matched control
matches draw weights rather than exact realised behavior counts, so it does not isolate a causal
switching-timing effect.

## Data and licence

ChEMBL 37 (CC-BY-SA 3.0) and PubChem BioAssay AID 1056; see `DATA_SOURCES.md` for attribution and
checksums. Licence for this repository is **not yet determined** — default copyright applies and no
reuse permission is granted until a `LICENSE` file is added.

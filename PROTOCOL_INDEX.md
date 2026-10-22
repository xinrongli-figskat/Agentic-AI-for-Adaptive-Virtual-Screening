# Protocol and lock chain

This file records **what was fixed before which run**, in order. It is the basis for any claim
that a comparison was specified in advance. It complements the evidence index, which maps each
reported number to the file that produced it.

**Hashes in the table below must be regenerated from the actual files at publication time, not
copied from prose elsewhere in the project.** Replace each table placeholder with the recomputed
SHA-256.

## Immutable inputs

| Artifact | SHA-256 | Note |
| --- | --- | --- |
| ChEMBL 37 SQLite | `4be13df3b68e25dcd0bff44bf094033b5aebe98f415acdc8c1cdf380e0c15142` | 30,480,314,368 bytes; not distributed |
| `campaign_v0/llm_controller.py` | `30c1c75da16636518d947b1eecb7207c922034ce1863adc0417f9fa676dde2b7` | Unchanged from the first controller run onward |
| `campaign_v0/campaign_core.py` | `3044fb6b5f61bb435eb50a04dd8dcd23ed89abd314c420799c9dc4079d40f0a1` | Unchanged |
| Evaluation-set freeze receipt | `f8801efbe28f73ddbcf9c5a2d493d862cbf124f311b6659e9224f2161b5bf662` | Fixes compounds, results and the 1,000 nM threshold |
| Evaluation-set pool manifest | `c4206075c51db7c9fc14a9ab910b87c91adb82f5fd468dba74edba244d27feb1` | |
| DYRK3 negative-control manifest | `3866c7bfc99e92b8e0d6f92b98955d5e68a7ae202f609eac90d0e7a201f98235` | |

## Chronological chain

For each entry: what the lock fixed, when it was written, and whether the runs it governs came
after it.

| Order | Lock | What it fixed in advance | Governs |
| --- | --- | --- | --- |
| 1 | Evaluation-set freeze receipt | Compounds, measured results, activity threshold | Every search against that set |
| 2 | Expanded-menu specification | The rule menu, controller information interface, primary and secondary comparisons, resampling seed, and the sentence to be written for each possible outcome | The expanded-menu controller runs |
| 3 | Controller code lock | Implementation of every selection rule | The same runs |
| 4 | Repeated-run design | Twenty seeds, five repeats, the precision threshold for continuing | The variance measurement |
| 5 | Prediction-method roster | Six methods and their hyperparameters, recorded before any method was scored | The method comparison |
| 6 | Admission-criterion rule, version 3 | Four mutually exclusive provenance classes, source-tier mapping, aggregator grouping, and the two validation conditions | The 62-candidate credential table |
| 7 | Library-visible protocol and lock | Primary and secondary comparisons, repeat count, four runtime information-boundary assertions, interpretation of each outcome | The library-visible arm |
| 8 | Frequency-matched control protocol | Draw weights, pseudorandom stream, resampling seed, interpretation of an interval containing zero | The frequency-matched arms |
| 9 | Instruction-ablation protocol | The clause-by-clause instruction comparison, the arm's information interface, interpretation of each of three outcomes | The instruction-only arm |

## What was not fixed in advance

This list matters more than the hashes.

- The choice of which prediction-method setting to run the library-visible controller in was
  made after seeing where the rules differed most.
- The strongest fixed rule is identified retrospectively wherever it is used as a reference,
  which makes it an optimistic comparator.
- The three data-quality admission criteria were added after candidates failed them.
- No correction for multiple comparisons is applied anywhere; all intervals are descriptive.

## Deviation and blocking records

Published alongside the locks, and part of the account rather than an appendix: records of
analyses that were stopped on a specification gap, corrected after a counting or variance error,
or withdrawn after a later measurement contradicted them.

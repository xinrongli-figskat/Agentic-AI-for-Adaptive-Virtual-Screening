# Agentic active search on retrospective virtual-screening benchmarks

A prototype study of whether a language model can usefully steer compound selection in
retrospective active search, together with the apparatus built to evaluate that question.

**Status:** research prototype, pedagogical in intent, not a production system.
**Licence:** not yet determined — see *Licence* below before reusing anything here.

## What this repository contains

- An **admission protocol** for retrospective active-search benchmarks, with three
  data-quality criteria that public bioactivity data commonly violate.
- One **fixed evaluation set** (human TNAP assay `CHEMBL1738510`): 462 compounds,
  53 measured actives, 409 measured inactives, released as compound keys and
  standardised structures.
- A **controller harness** with every selection rule compared: ranking by predicted
  activity, ranking with a batch-diversity penalty, uniform random, random-until-first-active,
  diversity-with-random-cold-start, plus Thompson sampling, UCB1, uniform and
  frequency-matched mixtures, and the language-model controllers.
- Six **prediction methods** fitted only on results revealed so far.
- **Protocol and lock files** recording what was fixed before each run, and
  **deviation and blocking records** for analyses that were stopped, corrected or withdrawn.

## Reproducible, not blinded

The source assay is public and named. Anyone can re-derive the measured results from the
cited source records. Measured results are withheld from this repository so that derived
label sets are not redistributed and so the published artifacts stay clean — **not because
they are secret.**

The claim that results were not consulted while the controllers were being developed rests
on the hash-locked protocol chain in `PROTOCOL_INDEX.md`, not on secrecy. Read that file
before treating any number here as pre-registered: a substantial part of the analysis is
post-exposure and is labelled as such.

## Re-deriving the measured results

The evaluation set is defined by its freeze receipt, which records the source assay, the
activity threshold applied, the compound set and the hash of each artifact. ChEMBL 37 is
identified by release and checksum in `DATA_SOURCES.md`. Together these are sufficient to
reconstruct the labels from the public source.

## Public and private split

Published: compound keys and standardised structures; protocol, specification and lock
files; aggregate analyses behind every reported number; reports, run logs and manifests;
deviation and blocking records.

Not published: measured per-compound results; full selection trajectories; raw model
responses; the ChEMBL database copy.

Everything withheld lives in directories excluded from version control. `PRE_PUBLIC_CHECKLIST.md`
must be re-run and passed before this repository's visibility is changed, because changing
visibility exposes the whole commit history at once.

## Licence

Undetermined. Derived data inherit share-alike terms from ChEMBL (CC-BY-SA 3.0), which has to
be reconciled with whatever licence covers the code. Until a `LICENSE` file is added, default
copyright applies and no reuse permission is granted. This is a practical statement, not legal
advice; the licence decision rests with the authors and their institution.

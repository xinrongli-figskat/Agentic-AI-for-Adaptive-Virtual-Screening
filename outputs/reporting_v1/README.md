# DYRK3 v1 post-campaign report

Run from the Ubuntu project root after all 30 campaigns are complete:

```bash
python -B -m unittest reporting_v1.test_report
python -B -m reporting_v1.build_report \
  --frozen-dir /driveA/xinrong/agentic-screening/data/curation_private/frozen_dyrk3_v1
```

This separate reporting tool verifies the recorded frozen-manifest hash,
pool, code/snapshots, 30 run identities, 50 unique queries per run, deterministic
initializations, observed outcomes against the fixed private source, and LLM
feedback/decision records. It calls the frozen evaluator without changing
its metrics. It makes no API requests or oracle queries, and never edits
campaign code, labels, frozen files or run checkpoints.

New timestamped reports go under `data/curation_private/reports_dyrk3_v1/`:
`evaluation.json`, `summary.md`, two PNG/PDF figures, generator source, and
`REPORT_SHA256.json`. Matplotlib cache stays under the project's `.cache`.
The report includes private provenance and belongs in curation context.

Bit remains the primary analysis; count is separate sensitivity. Bands show
sample standard deviations over five fixed seeds, not confidence intervals.
The frozen logs omit raw format-invalid responses and their token/latency
metadata; those costs are explicitly unknown rather than zero. Existing
evaluator fields that sum only known failed durations must not be interpreted
as complete elapsed costs. Probe costs and monetary charges are excluded.

The four offline tests use wholly synthetic records, make no network calls,
and do not evaluate real DYRK3 performance. Their temporary files are removed.

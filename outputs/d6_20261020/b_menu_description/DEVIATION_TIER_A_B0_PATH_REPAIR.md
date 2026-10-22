# Tier A repair: D6-B0 output-path inspection

**UTC:** 2026-10-20T13:45:00Z

The first B0 execution completed the four decision calls for seed 0, then
failed while reading its output.  The replay script expected
`runs_v0_replay/tnap/...`; the locked D5 runner writes beneath
`runs_v0_replay/runs/tnap/...`.  This is a path-layer error after the model
calls, not a change to the task-card specification, any selection algorithm,
or a frozen input.

The one-line path repair adds that `runs/` directory.  The loop also reuses a
completed `run.json`, so seed 0 is not called again.  Seeds 1--9 therefore
provide the remaining 36 decisions and the B0 total remains 40.  The known
good regression is the four-policy sequence for seed 0 compared with D5;
the repaired run checks it together with all nine resumed seeds before it
creates a passing summary.

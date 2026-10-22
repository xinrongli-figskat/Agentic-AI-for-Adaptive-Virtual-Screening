# D7-A execution log

All work is post-exposure and CPU only. GLM calls 0; new campaigns 0.

- Read complete D7 card and D5 numerical menu/runner; parent confirmed prerequisite hashes. Root owns the full 11-file preflight.
- A read-only remote Python one-liner intended to inspect ZIP member shape failed during command-line parsing because SSH/PowerShell quoting left backslashes in Python. It made no data writes and emitted no private records. Event wall time was not separately recorded. Replaced that invocation with a versioned script copied via SCP; this is a path/invocation-layer repair, not a scientific algorithm change. No failed campaign attempt occurred. Both required known-good regressions passed afterward.
- 2026-10-21T09:51:59.910492+00:00: locked A1_SPEC.md and run_a1.py with live UTC before any A1 numbers were generated.
- The subsequent same-process reanalysis verified archive and e_menu_results hashes, 760 members, seven exact TNAP bit means, and exact 20-element GLM H50 vector. It read archived trajectories in place; no extraction or modified legacy files.
- 2026-10-21T09:52:00.293491+00:00: actual production summary captures with synthetic state confirmed unequal sets (14 vs 11 fields). Tier B applies to A2/A3. No determinism replay is claimed.
- Downloaded JSON outputs to this directory. BLOCKED_information_set.md and A1_REPORT.md written after the captured observation. Their filesystem creation/write times document record creation, not a backdated event claim.
- Only this subtask directory was written, locally and remotely. No private trajectories were produced. Parent will independently verify MANIFEST and prerequisite hashes.

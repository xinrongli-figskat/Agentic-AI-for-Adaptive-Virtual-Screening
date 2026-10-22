# Approved D7-A revision run log

Post-exposure, CPU only, GLM 0. Earlier parent-directory snapshots were not overwritten.

1. User explicitly approved replacing the interface comparator with the D5 seven-policy controller's 11-field summary. Parent approval was recorded at 2026-10-21T10:12:17 UTC; SHA-256 ae6dfd39b6f1e2f8e38b3bea56216890ec7315137b7965a384aafcee2043fc9a.
2. Wrote A2_A3_SPEC.md and run_cpu.py in this new revision directory. Parent reviewed reward updates, variable batch handling, persistent commitment semantics, and full-repeat requirements before results.
3. 2026-10-21T10:19:00.755123+00:00: synthetic tests passed, with no real campaign execution: exact production fields, g4 value equality, hidden-measurement perturbation invariance, UCB order and commitment reward accounting.
4. 2026-10-21T10:19:12.013032+00:00: execution_lock.json sealed specification and code with live UTC. The prior frozen-source checks and explicit approval hash passed.
5. Executed eight-worker CPU job matrix; all 1,160 unique configurations completed at 10:19:37.487413+00:00. Each of 320 bandit configurations was physically repeated using fresh controller/oracle, resulting in 1,480 total runs. No resumptions or failed jobs occurred. No GPU or API calls.
6. 2026-10-21T10:19:37.592340+00:00: aggregate analysis written; validation and repeated known-good source regression followed at 10:19:37.608266+00:00. Public JSON copied locally for review.
7. Parent performed an independent transcript/reward/source verification and reported no discrepancies. The parent artifact is outside this subtask's ownership and is referenced, not added as a manifest member.
8. REPORT.md and this log were written after those results; filesystem write times record document creation. Private archive and per-member manifest are generated afterward. They cover only this revision directory.
9. Before sealing, remote git check-ignore reported that the remote project is not a Git repository. Checked the actual local repository instead; at 10:23:16 UTC the private path was ignored and .gitignore SHA was recorded in local_gitignore_check.json. No remote Git exclusion is asserted. This inspection did not run or modify any campaign.

No runtime repairs or deviations were needed in this approved revision. The earlier information-interface Tier B stop remains preserved in the parent subdirectory as historical evidence; this user-approved revision supersedes that stop for A2/A3 only.

"""Render the D7-E record-only addendum from independently checked evidence."""
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path

base=Path(__file__).resolve().parent
now=datetime.now(timezone.utc).isoformat()
e=json.loads((base/'corrected_baseline_checks.json').read_text(encoding='utf-8'))
h=json.loads((base/'historical_record_checks.json').read_text(encoding='utf-8'))
report_hash=h['d6_report_sha256']
times=h['historical_file_metadata']
repair_time=times['DEVIATION_TIER_A_B0_PATH_REPAIR.md']['observed_local_mtime_utc']
block_time=times['BLOCKED_b0_incomplete_replay.md']['observed_local_mtime_utc']
summary_time=times['b0_replay_summary.json']['observed_local_mtime_utc']
text=f'''# D6 report addendum — D7-E

Written UTC: {now}

Post-exposure, offline record correction. New campaigns: 0. New GLM calls: 0.
The original `outputs/d6_20261020/d6_report.md` is preserved byte for byte;
its SHA-256 is `{report_hash}`. This addendum supersedes only the
baseline attribution and sequence-count evidence, plus the unsupported
historical event-time claim. It does not erase the original record.

## 1. The D6-B0 reference was D4, despite residing under D5

The original reference `outputs/d5_20261020/a_mechanism/all_glm_policy_sequences.csv`
contains 160 decisions: knn_diverse 84, knn_greedy 59, uniform_random 17.
Its H@50 entries equal the locked D5 `glm_basic` entries for all 20 seeds
in each representation (bit and count). Those entries are the earlier D4 arm.
The D6 replay used the seven-item D5 menu: 16 of its 40 choices were
`ens_one_step_proxy`, an unavailable option in the earlier three-item menu.
Thus all ten alleged D5 reference sequences in D6-B0 were misattributed.
The root cause is the D6 task card's reference-file specification, not an
unauthorized execution change.

## 2. Correct baseline, independently recomputed

The authoritative D5 records were read directly from the locked private ZIP,
SHA-256 `{e['archive_sha256']}`, {e['archive_bytes']:,} bytes and
{e['archive_members']} members. The member path is
`outputs/d5_20261020/e_menu_private/runs/tnap/bit/glm_extended_seed*/run.json`.
No new run was used to reconstruct the baseline. Seven fixed-arm means and
the full 20-seed GLM H@50 vector exactly matched the task-card regression.

For D5 seeds 0–9 the 40 choices are coldstart 2, greedy 10, diverse 17,
logreg 1, ENS 9 and uniform 1, matching the locked checkpoint.

| Comparison to D6 saved replay | Matches |
| --- | ---: |
| Ordered initialization of ten compounds | 10/10 |
| All 11 first-round public_summary fields | 10/10 |
| First-round information_available | 10/10 |
| First-round policy | 4/10 |
| Complete four-round policy sequence | 1/10 (seed 5) |

The public-summary objects have equal canonical JSON bytes and hashes.
The saved evidence establishes equality of the full recorded input state;
it does not independently attest raw HTTP request bytes. Response content,
latency and request IDs are response-side records, not evidence of different
input states. Later-round states may diverge after the first policy choice,
so the first-round 60% disagreement is the clean reproducibility observation.

The correct sequence-disagreement count is **9/10**, not 10/10. Therefore
the original sentence “All ten replayed policy sequences differ from their
corresponding D5 records” is false as a statement about D5. Its comparison
was actually to D4. The original evidence was invalid for the intended D5
reproducibility claim, but the corrected evidence still meets the specified
Tier B condition (at least two differing sequences). The Tier B stop and
the decision not to start B1–B4 remain valid.

## 3. Historical timestamp correction

The original `DEVIATION_TIER_A_B0_PATH_REPAIR.md` asserts
`2026-10-20T13:45:00Z`. This is not a supported repair-event timestamp.
Its saved local file mtime is `{repair_time}`, after the incomplete-replay
record's `{block_time}`. For record attribution, replace the asserted event
time with **2026-10-20T14:07:43Z (deviation-record write time)**.
The actual code-repair event time was not separately recorded and remains
unknown. File mtime is not proof of the repair event itself; transport can
also change file metadata. Here the observed saved-file metadata corroborates
the supplied D7 card. The old file remains untouched.

The completed B0 summary internally records
`2026-10-20T14:10:14.880869+00:00`; its currently observed local mtime is
`{summary_time}`. The result was recorded after the incomplete-replay
observation and correction record. This check finds no basis for alleging
backdating of that result; it corrects the earlier unsupported event time.
This addendum's own UTC above is generated from the live clock at file creation.

## 4. Valid D6 safeguards retained

- The incomplete-replay record correctly declined to treat one observed
  differing seed as meeting the at-least-two condition and recognized the
  rule for an independent rerun if a completed comparison has exactly one
  difference. It also recognized that nine seeds were still missing.
- The first-wave gate explicitly prohibited the second wave.
- All three public subtask manifests were independently rehashed: A 4/4,
  B 8/8 and C 5/5 members matched.
- All 40 D6 decision receipts have request IDs, raw response content, usage,
  elapsed decision time and a returned HTTP-attempt record. Budget usage
  remained 40/450, with no new model call in this correction.

Machine-checkable evidence: `corrected_baseline_checks.json` and
`historical_record_checks.json`. This record correction creates no new
campaign-ready pool and makes no claim of agentic performance improvement.
'''
(base/'d6_report_addendum.md').write_text(text,encoding='utf-8')
(base/'DEVIATION_TIER_A_E_EXECUTION.md').write_text(f'''# D7-E execution-only repairs

Recorded UTC: {now}. This is the write time of this record; exact event
timestamps for the earlier failed inspection commands were not recorded.

During read-only schema discovery, a remote inline Python command failed
because Windows/SSH quoting changed escaped quote characters. Replaced the
inline invocation with a transferred Python file. The first transfer failed
because the assigned remote E directory did not yet exist; created that
directory and repeated the transfer. A schema-inspection script then found
that the D6-A manifest was present locally but absent at the assumed remote
path; the historical public-manifest check was run against the preserved
local artifacts, while private archive/replay checks ran on the workstation.

Invocation/path deltas only:
1. `ssh ... python -c <quoted code>` -> `scp inspect_schema.py; ssh ... python inspect_schema.py`.
2. Missing remote E destination -> create that same assigned destination,
   then repeat the same transfer.
3. Historical manifests assumed remote -> local preserved public artifacts;
   authoritative private D5/D6 run paths remain remote.

No experiment specification, frozen input, selection rule or threshold was
changed. No campaign or API call occurred. The final verifier passed all
seven known-good fixed-arm means and the exact 20-seed GLM H@50 regression,
and independently matched all 17 historical manifest members.
''',encoding='utf-8')
(base/'RUN_LOG.md').write_text(f'''# D7-E run log

Post-exposure. Recorded UTC: {now}.

1. Read D7-E and preserved D6 records; initial schema discovery had the
   invocation/path failures documented in DEVIATION_TIER_A_E_EXECUTION.md.
2. Workstation offline verification started {e['started_utc']} and ended
   {e['finished_utc']}. Verified the locked D5 archive hash, byte count,
   760 members, seven fixed-arm means and complete GLM H@50 vector.
3. Compared the authoritative ten D5 seven-menu records to the existing
   ten D6 replay files. Retained their hashes and only public aggregates.
4. Local historical verification at {h['checked_utc']}: three manifests,
   17 members, and original report SHA-256 preserved; observed timestamps
   recorded without inventing the original repair-event time.
5. Wrote this new addendum. No original D6 file was edited.

New campaigns 0; new GLM calls 0; all findings are post-exposure.
''',encoding='utf-8')
(base/'STATUS').write_text('complete_offline_record_correction\n',encoding='utf-8')
files=[]
for p in sorted(base.rglob('*')):
    if p.is_file() and p.name!='MANIFEST.json':
        b=p.read_bytes();files.append({'path':p.relative_to(base).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
manifest={'task':'D7-E','post_exposure':True,'created_utc':now,'status':'complete_offline_record_correction',
          'new_glm_calls':0,'new_campaigns':0,'self_excluded':True,'files':files}
(base/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'manifest_sha256':hashlib.sha256((base/'MANIFEST.json').read_bytes()).hexdigest(),'files':len(files),'created_utc':now}))

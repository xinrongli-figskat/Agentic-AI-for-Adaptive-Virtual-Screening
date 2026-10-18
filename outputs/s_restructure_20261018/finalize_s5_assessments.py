import csv
from pathlib import Path
p=Path('outputs/s_restructure_20261018/script_classification.csv')
rows=list(csv.DictReader(p.open(encoding='utf-8-sig')))
path_sensitive={'audit_s1pr1_archived_assay.py':'depends on sibling assay_audit_v0 via Path(__file__).parent; moving breaks lookup','build_task1_v2_1_transfer.py':'computes project root with Path(__file__).parent.parent; moving changes root','build_task1_v2_transfer.py':'computes project root with Path(__file__).parent.parent; moving changes root','build_task1_v3_transfer.py':'computes project root with Path(__file__).parent.parent; moving changes root','build_task1_v5_stage0_transfer.py':'uses current script directory as HERE; moving changes source location','curate_selected_chembl37_assays.py':'uses Path(__file__).parent as project root; moving changes root','extract_p1_p5_summaries.py':'uses parents[1] as BASE; moving changes base','package_task1_v4.py':'uses parents[1] as project root; moving changes root','plan_local_cleanup.py':'uses parent.parent as project root; moving changes root','review_candidate_assays.py':'default path resolves candidate_discovery_v0 as sibling; moving breaks default','validate_task1_v2.py':'uses parents[1] as project root; moving changes root'}
for r in rows:
 n=Path(r['source']).name
 if n in path_sensitive:
  r['move_decision']='defer'; r['reason']=path_sensitive[n]
with p.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
tests=list(csv.DictReader(Path('outputs/s_restructure_20261018/test_movement_assessment.csv').open(encoding='utf-8-sig')))
# All current tests import top-level tested modules or use __file__ as a path anchor.
for r in tests:
 if r['move_decision']!='defer': r['move_decision']='defer'; r['reason']='tests import top-level project modules; keeping source/test relationship intact without editing tests'
with Path('outputs/s_restructure_20261018/test_movement_assessment.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(tests[0]));w.writeheader();w.writerows(tests)
print('scripts',len(rows),'script_moves',sum(r['move_decision']=='move_candidate' for r in rows),'script_defers',sum(r['move_decision']=='defer' for r in rows),'tests',len(tests),'tests_deferred',sum(r['move_decision']=='defer' for r in tests))

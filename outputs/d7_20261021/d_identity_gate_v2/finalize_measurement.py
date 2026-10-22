"""Retain first diagnostic snapshot and resolve invariant empty-set cases only."""
import csv
import hashlib
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
now=datetime.now(timezone.utc).isoformat()
records=json.loads((ROOT/'identity_private/per_identity_measurement.json').read_text())
changed=[]
for rec in records:
    if rec['measurement_category']=='undefined_multi_key_single_source':
        # The stored union is empty, which proves each constituent alternate set
        # is empty. No choice of representative key or aggregation changes this.
        assert len(rec['global_src_ids'])==1 and rec['alternate_key_src_ids']==[]
        rec['measurement_category']='single_source'
        changed.append({'assay_id':rec['assay_id'],'reason':'Every constituent alternate-key source set is empty; classification is invariant.'})
source=list(csv.DictReader((ROOT/'credential_62_measurement_partial.csv').open()))
for row in source:
    counts=Counter(r['measurement_category'] for r in records if r['assay_id']==row['assay_id'])
    n=int(row['support_identity_count'])
    for kind in ['full_match','skeleton_only','single_source']:
        row[kind+'_frac']=counts[kind]/n
    row['defined_ratio_sum']=sum(counts[k] for k in ['full_match','skeleton_only','single_source'])/n
    row['unclassified_identity_count']=sum(v for k,v in counts.items() if k.startswith('undefined'))
    row['unclassified_categories']=json.dumps({k:v for k,v in counts.items() if k.startswith('undefined')},sort_keys=True)
dest=ROOT/'credential_62_measurement_partial_v2.csv'
assert not dest.exists()
with dest.open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(source[0]));w.writeheader();w.writerows(source)
def save(name,data):
    p=ROOT/name
    assert not p.exists()
    p.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
save('identity_private/per_identity_measurement_v2.json',records)
summary=json.loads((ROOT/'credential_summary_partial.json').read_text())
summary.update({'finalized_utc':now,'ratio_sum_pass_rows':sum(abs(r['defined_ratio_sum']-1)<1e-9 for r in source),
    'unclassified_identity_total':sum(r['unclassified_identity_count'] for r in source),
    'category_counts':dict(Counter(r['measurement_category'] for r in records)),
    'invariant_multi_cases_resolved':changed,
    'measurement_table':'credential_62_measurement_partial_v2.csv',
    'status':'blocked_tier_b_uncovered_measurement_definitions',
    'first_snapshot_preserved':True})
save('credential_summary_partial_v2.json',summary)
assert summary['multi_molregno_total']==5
assert summary['all_multi_fractions_de_minimis']
assert summary['unclassified_identity_total']==2526
save('measurement_resolution_record.json',{
    'recorded_utc':now,'post_exposure':True,
    'first_snapshot':'credential_62_measurement_partial.csv',
    'final_partial_snapshot':dest.name,
    'change':'Three multi-molregno cases have n_src=1 and an empty union of all per-key alternate-source sets. Each per-key set must therefore be empty; every representative and union rule agrees on single_source. No new aggregation rule is needed and de minimis does not block.',
    'changed_identity_occurrences':3,'remaining_unclassified_single_molregno_identities':2526,
    'gate_application_performed':False,'glm_calls':0})
ignored=subprocess.run(['git','check-ignore','--quiet',str(ROOT/'identity_private/per_identity_measurement_v2.json')],check=False).returncode==0
assert ignored
save('private_ignore_verification.json',{'recorded_utc':now,'private_paths_gitignored':ignored})
print(json.dumps(summary,indent=2))

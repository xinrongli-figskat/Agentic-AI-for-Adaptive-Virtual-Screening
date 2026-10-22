"""Verify final tables and gate boundary/conjunction behavior without GLM."""
import csv
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def b(x):return str(x).lower()=='true'
def permit(skeleton,full,resolvable,tiers):
    tests={'T1':resolvable>=.95,'T2':full>=.50,'T3':full>=.33}
    return skeleton<.25 and all(tests[t] for t in tiers)

tests=[
    (permit(.25,1,1,['T2']),False),
    (permit(.249, .50,1,['T2']),True),
    (permit(0,.499999,1,['T2']),False),
    (permit(0,.33,1,['T3']),True),
    (permit(0,0,.95,['T1']),True),
    (permit(0,1,.949999,['T1','T2']),False),
    (permit(0,.49,1,['T1','T2']),False),
    (permit(0,.50,.95,['T1','T2','T3']),True),
]
assert all(a==e for a,e in tests)
creds=list(csv.DictReader((ROOT/'credential_62.csv').open()))
decisions=list(csv.DictReader((ROOT/'gate_decisions_62.csv').open()))
assert len(creds)==len(decisions)==62
for r,d in zip(creds,decisions):
    assert r['assay_id']==d['assay_id']
    assert abs(sum(float(r[k+'_frac']) for k in ['full_match','skeleton_only','single_source','unresolvable'])-1)<1e-9
    assert permit(float(r['skeleton_only_frac']),float(r['full_match_frac']),float(r['structure_resolvable_frac']),json.loads(r['involved_source_tiers']))==b(d['shortlist_permitted'])
    assert not b(r['campaign_ready']) and not b(d['campaign_ready'])
assert sum(int(r['multi_molregno_count']) for r in creds)==5
lookup={d['assay_id']:d for d in decisions}
assert not b(lookup['CHEMBL5733557']['shortlist_permitted'])
assert b(lookup['CHEMBL1738510']['shortlist_permitted'])
unseen=json.loads((ROOT/'unseen_set_lock.json').read_text())
assert len(unseen['assay_ids'])==8
assert not set(unseen['assay_ids'])&set(unseen['excluded_reference_assays'])
assert unseen['assay_ids']==[r['assay_id'] for r in creds if r['assay_id'] not in unseen['excluded_reference_assays']][:8]
old=json.loads((ROOT.parent/'MANIFEST.json').read_text())
for item in old['files']:
    assert hashlib.sha256((ROOT.parent/item['path']).read_bytes()).hexdigest()==item['sha256']
receipt={'checked_utc':datetime.now(timezone.utc).isoformat(),'post_exposure':True,'gate_boundary_cases':len(tests),
 'all_cases_passed':True,'credential_rows':62,'four_ratio_sum_rows':62,'gate_recompute_rows':62,
 'TACE_false':True,'TNAP_true':True,'multi_total':5,'all_campaign_ready_false':True,
 'old_manifest_24_members_unchanged':True,'unseen_top8_rule_verified':True,'glm_calls':0}
p=ROOT/'independent_verification.json'
assert not p.exists()
p.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps(receipt,indent=2))

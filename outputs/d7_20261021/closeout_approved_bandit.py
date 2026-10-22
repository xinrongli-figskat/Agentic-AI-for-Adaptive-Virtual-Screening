"""Additive D7 closeout after the approved eleven-field amendment."""
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path

B=Path(__file__).resolve().parent
R=B/'a_headroom_bandit/revision_11field'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,value):
    assert not p.exists(), str(p)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def keys(x):
    if isinstance(x,dict):
        for k,v in x.items():
            yield k
            yield from keys(v)
    elif isinstance(x,list):
        for v in x: yield from keys(v)

def main():
    totals={}
    for manifest in (B/'MANIFEST.json',R/'MANIFEST.json'):
        m=load(manifest); members=m.get('files',m.get('members'))
        for row in members:
            p=(manifest.parent/row['path']).resolve()
            assert p.is_relative_to(manifest.parent)
            assert sha(p)==row['sha256'],str(p)
        totals[manifest.relative_to(B).as_posix()]=len(members)
    findings=[]
    for p in B.rglob('*.json'):
        if any('private' in part.lower() for part in p.relative_to(B).parts):continue
        forbidden={'outcome','label','is_hit'} & set(keys(load(p)))
        if forbidden:findings.append({'path':p.relative_to(B).as_posix(),'fields':sorted(forbidden)})
    assert not findings
    v=load(B/'approved_bandit_root_verification.json')
    assert v['deterministic_repeated_configurations']==320 and v['g4_bit_fixed_D5_regressions']==280
    assert load(B/'preflight_20261021T102149Z.json')['passed']
    now=datetime.now(timezone.utc).isoformat()
    write(B/'d7_wave1_verification_after_bandit_approval.json',dict(recorded_utc=now,post_exposure=True,
        status='A_COMPLETE_D_DEFINITION_GATE_PENDING',previous_delivery_members_unchanged=totals,
        approved_interface='D5 eleven fields',bandit_and_granularity_completed=True,
        public_forbidden_fields=findings,independent_root_verification_sha256=sha(B/'approved_bandit_root_verification.json'),
        new_glm_calls=0,new_campaign_unique_configurations=1160,physical_runs_including_repeats=1480,
        D_rule_amendments_authorized=False,second_wave_authorized=False,
        report_sha256=sha(B/'d7_report_after_bandit_approval.md')))
    target=B/'MANIFEST_AFTER_BANDIT_APPROVAL.json'
    members=[dict(path=p.relative_to(B).as_posix(),sha256=sha(p)) for p in sorted(B.rglob('*')) if p.is_file() and p!=target]
    write(target,dict(recorded_utc=now,post_exposure=True,status='PARTIAL_D_TIER_B',files=members))
    print(json.dumps({'manifest_members':len(members),'manifest_sha256':sha(target),'historical_and_revision_members_verified':totals,'second_wave_authorized':False}))

if __name__=='__main__':main()

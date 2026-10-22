"""Independently verify D7 local manifests and record the wave gate."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
PARTS = ('a_headroom_bandit', 'd_identity_gate_v2', 'e_record_fixes')

def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()

def pairs(manifest):
    members = manifest.get('files', manifest.get('members', []))
    if isinstance(members, dict):
        return [(p, h if isinstance(h,str) else h['sha256']) for p,h in members.items()]
    return [(r.get('path',r.get('relative_path')),r['sha256']) for r in members]

def walk_keys(data):
    if isinstance(data, dict):
        for k,v in data.items():
            yield k
            yield from walk_keys(v)
    elif isinstance(data,list):
        for v in data:
            yield from walk_keys(v)

if __name__=='__main__':
    reports=[]
    for name in PARTS:
        folder=BASE/name
        mp=folder/'MANIFEST.json'
        if not mp.exists():
            reports.append(dict(directory=name, complete=False, error='manifest missing'))
            continue
        data=json.loads(mp.read_text(encoding='utf-8-sig'))
        records=[]
        for relative,expected in pairs(data):
            p=(folder/relative).resolve()
            assert p.is_relative_to(folder), (name,relative,'cross-directory manifest member')
            actual=sha(p) if p.is_file() else None
            records.append(dict(path=relative,expected=expected,actual=actual,match=expected==actual))
        reports.append(dict(directory=name, manifest_sha256=sha(mp), member_count=len(records),
                            all_members_match=bool(records) and all(r['match'] for r in records),
                            status=(folder/'STATUS').read_text().strip(), members=records))
    findings=[]
    for p in BASE.rglob('*.json'):
        if any('private' in part.lower() for part in p.relative_to(BASE).parts):
            continue
        try:
            forbidden={'outcome','label','is_hit'} & set(walk_keys(json.loads(p.read_text(encoding='utf-8-sig'))))
        except (ValueError,UnicodeError):
            continue
        if forbidden:
            findings.append(dict(path=str(p.relative_to(BASE)),fields=sorted(forbidden)))
    result=dict(utc=datetime.now(timezone.utc).isoformat(),post_exposure=True,
                manifest_checks=reports,public_forbidden_field_findings=findings,
                second_wave_authorized=False,
                gate_note='Structural verification only; scientific/field-contract/measurement gates must separately pass before authorization.')
    out=BASE/'wave1_manifest_verification.json'
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    assert not findings, 'Public forbidden field found'
    assert all(r.get('all_members_match') for r in reports), 'Manifest verification incomplete or failed'

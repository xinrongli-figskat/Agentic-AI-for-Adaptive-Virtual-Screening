"""Verify the self-contained D7-E delivery; read only."""
import hashlib
import json
from pathlib import Path

base=Path(__file__).resolve().parent
m=json.loads((base/'MANIFEST.json').read_text(encoding='utf-8'))
for item in m['files']:
    p=(base/item['path']).resolve()
    assert p.is_relative_to(base)
    b=p.read_bytes()
    assert len(b)==item['bytes']
    assert hashlib.sha256(b).hexdigest()==item['sha256'],p

def scan(x):
    if isinstance(x,dict):
        assert not {'outcome','label','is_hit'}.intersection(x)
        for v in x.values():scan(v)
    elif isinstance(x,list):
        for v in x:scan(v)
for p in base.glob('*.json'):
    scan(json.loads(p.read_text(encoding='utf-8')))
historical=json.loads((base/'historical_record_checks.json').read_text(encoding='utf-8'))
old_report=base.parents[1]/'d6_20261020/d6_report.md'
if old_report.exists():
    assert hashlib.sha256(old_report.read_bytes()).hexdigest()==historical['d6_report_sha256']
print(json.dumps({'verified_members':len(m['files']),'public_forbidden_fields':0,'manifest_sha256':hashlib.sha256((base/'MANIFEST.json').read_bytes()).hexdigest()}))

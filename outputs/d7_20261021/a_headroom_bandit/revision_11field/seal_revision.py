"""Validate private repeats, scan public JSON, archive, and seal this revision only."""
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

base=Path(__file__).resolve().parent
root=base.parents[3]
private=base/'runs_private'
assert not (base/'MANIFEST.json').exists()
runs=sorted(private.rglob('*.json'))
assert len(runs)==1480
repeats=[p for p in runs if p.stem.endswith('_repeat')]
assert len(repeats)==320
for path in repeats:
    other=path.with_name(path.name.replace('_repeat.json','.json'))
    assert path.read_bytes()==other.read_bytes()
ignore_proof=json.loads((base/'local_gitignore_check.json').read_text())
assert ignore_proof['exit_code']==0 and ignore_proof['private_path_ignored']
forbidden={'outcome','label','is_hit'}
def scan(obj):
    if isinstance(obj,dict):
        assert not (set(obj)&forbidden)
        for value in obj.values():scan(value)
    elif isinstance(obj,list):
        for value in obj:scan(value)
for path in base.glob('*.json'):
    scan(json.loads(path.read_text()))
archive=private/'cpu_trajectories.zip'
assert not archive.exists()
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for path in runs:z.write(path,path.relative_to(base).as_posix())
validation={'post_exposure':True,'utc':datetime.now(timezone.utc).isoformat(),'private_transcripts':1480,'independent_byte_identical_repeat_pairs':320,'private_paths_gitignored_in_local_repository':True,'remote_has_git_repository':False,'public_structured_field_scan_pass':True,'archive_path':archive.relative_to(base).as_posix(),'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'archive_bytes':archive.stat().st_size,'glm_calls':0}
(base/'archive_receipt.json').write_text(json.dumps(validation,indent=2,sort_keys=True)+'\n',encoding='utf-8')
members=[]
for path in sorted(base.rglob('*')):
    if path.is_file() and '__pycache__' not in path.parts:
        relative=path.relative_to(base).as_posix()
        assert not relative.startswith('../')
        members.append({'path':relative,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
manifest={'post_exposure':True,'utc':datetime.now(timezone.utc).isoformat(),'status':'COMPLETE_CPU_ONLY_A2_A3_APPROVED_11_FIELD_REVISION','members':members,'glm_calls':0}
(base/'MANIFEST.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps({'archive_receipt':validation,'manifest_sha256':hashlib.sha256((base/'MANIFEST.json').read_bytes()).hexdigest(),'members':len(members)}))

"""Read-only D7-B final inventory and private backup, after analysis."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path('/driveA/xinrong/agentic-screening')
sys.path.insert(0,str(ROOT))
from outputs.d7_20261021.b_model_variance import b_repeat as old
from outputs.d7_20261021.b_model_variance import b_resume_v2 as resume

BASE=old.BASE
PRIVATE=old.PRIVATE


def write_new(path,value):
    assert not path.exists(),f'Will not overwrite {path}'
    path.write_text(json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False)+'\n',encoding='utf-8')
    if 'private' in str(path): os.chmod(path,0o600)


def main():
    resume.verify_lock()
    analysis=json.loads((BASE/'B_ANALYSIS.json').read_text())
    assert analysis['campaigns_total']==100
    assert analysis['new_physical_http_requests']==resume.physical_count()<=380
    old_snapshot=json.loads((PRIVATE/'PRIVATE_MANIFEST_TIER_B.json').read_text())
    old_partial_name='rep2/runs/tnap/bit/glm_extended_seed13/run.json'
    old_partial_archive=PRIVATE/'partial_evidence_tier_b.zip'
    assert old.sha(old_partial_archive)==json.loads((BASE/'MANIFEST_TIER_B.json').read_text())['private_archive_sha256']
    for name,digest in old_snapshot['files'].items():
        if name==old_partial_name:
            # The authorized resume appends batches to this checkpoint. Its
            # exact old bytes are retained in the Tier B sealed archive.
            with zipfile.ZipFile(old_partial_archive) as z:
                original=z.read(name)
            assert hashlib.sha256(original).hexdigest()==digest
            previous=json.loads(original)
            current=json.loads((PRIVATE/name).read_text())
            assert not previous['complete'] and current['complete']
            assert current['trajectory'][:len(previous['trajectory'])]==previous['trajectory']
        else:
            assert old.sha(PRIVATE/name)==digest,f'Old receipt changed: {name}'
    private_files=sorted(p for p in PRIVATE.rglob('*') if p.is_file())
    private_manifest={'generated_utc':old.utc(),'post_exposure':True,
        'files':{str(p.relative_to(PRIVATE)).replace('\\','/'):old.sha(p) for p in private_files}}
    write_new(PRIVATE/'PRIVATE_MANIFEST_B_FINAL.json',private_manifest)
    archive=PRIVATE/'b_full_evidence.zip'
    assert not archive.exists()
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(PRIVATE.rglob('*')):
            if p.is_file() and p!=archive:
                z.write(p,arcname=str(p.relative_to(PRIVATE)).replace('\\','/'))
    os.chmod(archive,0o600)
    files=sorted(p for p in BASE.iterdir() if p.is_file() and p.name!='MANIFEST_B_FINAL.json')
    public_manifest={'generated_utc':old.utc(),'post_exposure':True,
        'status':analysis['status'],'public_files':{p.name:old.sha(p) for p in files},
        'private_manifest_sha256':old.sha(PRIVATE/'PRIVATE_MANIFEST_B_FINAL.json'),
        'private_archive_sha256':old.sha(archive),'private_archive_bytes':archive.stat().st_size,
        'private_files':len(private_files),'new_physical_http_requests':resume.physical_count()}
    write_new(BASE/'MANIFEST_B_FINAL.json',public_manifest)
    print(json.dumps({'status':analysis['status'],'public_manifest_sha256':old.sha(BASE/'MANIFEST_B_FINAL.json'),
        'private_archive_sha256':public_manifest['private_archive_sha256'],
        'private_files':len(private_files),'new_physical_http_requests':resume.physical_count()},
        ensure_ascii=False))


if __name__=='__main__':main()

"""Verify remote manifests and inventory local supplementary files."""
import hashlib,json,platform
from datetime import datetime,timezone
from pathlib import Path
root=Path(__file__).resolve().parents[2]
out=Path(__file__).resolve().parent
names=['r1_criteria_reconstruction_20261018','r2_threshold_counts_private_20261018',
       'r3_ranked_numeric_private_20261018','r3_ranked_numeric_private_20261018_v2',
       'r4_source_review_private_20261018','r5_cpu_controls_private_20261018',
       'r5_matched_order_private_20261018',
       'r5_glm_response_private_20261018','r5_reveal_accounting_private_20261018',
       'q2_decision_draft_20261018','r7_oracle_service_private_20261018',
       'r8_task1_failures_private_20261018']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
report=[]
for name in names:
    folder=root/'outputs'/name
    manifest=folder/'MANIFEST.json'
    assert manifest.is_file(),name
    data=json.loads(manifest.read_text(encoding='utf-8'))
    problems=[]
    for row in data['files']:
        p=folder/row['path']
        if not p.is_file() or p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:
            problems.append(row['path'])
    assert not problems,(name,problems)
    # Remote result manifests intentionally exclude new local source/verification helpers.
    if name in ('r2_threshold_counts_private_20261018','r4_source_review_private_20261018','r5_cpu_controls_private_20261018','r5_matched_order_private_20261018'):
        listed={row['path'] for row in data['files']}
        supplements=[]
        for p in sorted(folder.rglob('*')):
            if p.is_file() and p.name not in ('MANIFEST.json','LOCAL_MANIFEST.json') and p.relative_to(folder).as_posix() not in listed:
                supplements.append({'path':p.relative_to(folder).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
        (folder/'LOCAL_MANIFEST.json').write_text(json.dumps({'remote_manifest_sha256':sha(manifest),
            'local_supplemental_files':supplements},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report.append({'output':name,'manifest_sha256':sha(manifest),'verified_files':len(data['files']),
                   'status':(folder/'STATUS').read_text(encoding='utf-8').strip()})
(out/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(out/'STATUS').write_text('done\n')
(out/'RUN_LOG.md').write_text('post-exposure 的证据整理，不是新 benchmark、盲验证或新 campaign。\n\n'
    f'UTC: {datetime.now(timezone.utc).isoformat()}\nCommand: python -B outputs/r0_integrity_20261018/audit_new_outputs.py\n'
    f'Python: {platform.python_version()}\nNumPy/SciPy/RDKit: not used\nRandom seed: none\nGLM calls: 0\n'
    f'Code SHA-256: {sha(Path(__file__))}\n',encoding='utf-8')
items=[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(out.iterdir()) if p.is_file() and p.name!='MANIFEST.json']
(out/'MANIFEST.json').write_text(json.dumps({'files':items,'self_excluded':True},indent=2)+'\n')
print({'verified_outputs':len(report),'statuses':{r['output']:r['status'] for r in report}})

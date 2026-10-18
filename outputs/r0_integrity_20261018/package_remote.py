"""Make a compact, path-safe transfer archive of this round's outputs."""
import hashlib,json,tarfile
from datetime import datetime,timezone
from pathlib import Path
root=Path(__file__).resolve().parents[2]
audit=root/'.sync_audit/round_20261018'
audit.mkdir(parents=True,exist_ok=True)
archive=audit/'round_outputs_20261018_v3.tar.gz'
names=['r0_integrity_20261018','r1_criteria_reconstruction_20261018','r2_threshold_counts_private_20261018',
       'r3_ranked_numeric_private_20261018','r3_ranked_numeric_private_20261018_v2',
       'r4_source_review_private_20261018','r5_cpu_controls_private_20261018',
       'r5_matched_order_private_20261018',
       'r5_glm_response_private_20261018','r5_reveal_accounting_private_20261018',
       'q2_decision_draft_20261018','r7_oracle_service_private_20261018',
       'r8_task1_failures_private_20261018']
paths=[root/'config/task_params_20261018.json']
for name in names:
    paths.extend(p for p in (root/'outputs'/name).rglob('*') if p.is_file())
with tarfile.open(archive,'w:gz') as tar:
    for p in sorted(paths):
        rel=p.relative_to(root).as_posix()
        assert not p.is_symlink() and not rel.startswith('/') and '..' not in Path(rel).parts
        tar.add(p,arcname=rel,recursive=False)
h=hashlib.sha256(archive.read_bytes()).hexdigest()
receipt={'utc':datetime.now(timezone.utc).isoformat(),'archive':str(archive),'sha256':h,
         'files':len(paths),'bytes':archive.stat().st_size,'destination_intended':'/driveA/xinrong/agentic-screening/deliveries_20261018_v3',
         'note':'Private data are included; keep archive under the project private permissions.'}
(audit/'transfer_receipt_v3.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(receipt)

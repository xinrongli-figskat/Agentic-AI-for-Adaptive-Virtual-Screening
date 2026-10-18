import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

out=Path(__file__).resolve().parent
root=out.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
sources=[root/'outputs/p1_negcoverage_private_20261018/p1_aggregate_totals.json',
         root/'outputs/p1_negcoverage_private_20261018/gate_matrix.csv',
         root/'outputs/p1_negcoverage_private_20261018/hypothetical_negatives_needed.csv',
         root/'outputs/r2_threshold_counts_private_20261018/aggregate_counts.csv']
assert all(p.exists() for p in sources)
(out/'STATUS').write_text('done_artifact_pending_scientific_approval\n',encoding='utf-8')
(out/'RUN_LOG.md').write_text('post-exposure 的证据整理，不是新 benchmark、盲验证或新 campaign。\n\n'
    f'UTC: {datetime.now(timezone.utc).isoformat()}\nCommand: python -B outputs/q2_decision_draft_20261018/seal_q2.py\n'
    f'Python: {platform.python_version()}\nNumPy/SciPy/RDKit: not used\nRandom seed: none\nGLM calls: 0\n'
    f'Code SHA-256: {sha(Path(__file__))}\nInputs:\n'+
    ''.join(f'- {p.relative_to(root)} SHA-256 {sha(p)}\n' for p in sources),encoding='utf-8')
files=[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(out.iterdir()) if p.is_file() and p.name!='MANIFEST.json']
(out/'MANIFEST.json').write_text(json.dumps({'files':files,'self_excluded':True},indent=2)+'\n')
print(json.dumps({'status':'done_artifact_pending_scientific_approval','manifest_sha256':sha(out/'MANIFEST.json')}))

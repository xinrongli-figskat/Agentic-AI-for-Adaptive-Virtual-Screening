import json
import zipfile
from pathlib import Path

root=Path('/driveA/xinrong/agentic-screening')
z=zipfile.ZipFile(root/'data/curation_private/d5_backups/d5_e_menu_private_20261020.zip')
n=next(n for n in z.namelist() if n.endswith('tnap/bit/glm_extended_seed0/run.json'))
r=json.loads(z.read(n))
print(n, list(r))
print('arms', sorted({json.loads(z.read(n)).get('arm','') for n in z.namelist() if n.endswith('/run.json')}))
print('first call keys', list(r['trajectory'][1]['glm_call']))
print('RESULTS', list(json.loads((root/'outputs/d5_20261020/e_menu_results.json').read_text())))
print(json.dumps(json.loads((root/'outputs/d5_20261020/e_menu_results.json').read_text())['metrics'])[:2500])
for d in ('a_identity_gate','c_d5_addendum'):
    m=json.loads((root/'outputs/d6_20261020'/d/'MANIFEST.json').read_text())
    print(d, list(m),str(m)[:500])
for n in ('DEVIATION_TIER_A_B0_PATH_REPAIR.md','BLOCKED_b0_incomplete_replay.md','b0_replay_summary.json'):
    from datetime import datetime,timezone
    p=root/'outputs/d6_20261020/b_menu_description'/n
    print(n,datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat())

"""Verify the Git-ignored local mirror against the final remote D4 manifest."""
import hashlib
import json
from pathlib import Path

base = Path(__file__).resolve().parent
mirror = base / 'remote_backup_private_20261019/d4_tnap_glm_20261019'
manifest = mirror / 'MANIFEST.json'
expected = '1eb690658a062d959aa52750d849529a0a557bcdb1371ac86a41b7de3bb3af37'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(manifest) == expected
rows = json.loads(manifest.read_text())['files']
for row in rows:
    path = mirror / row['path']
    assert path.is_file() and path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], row['path']
assert len(rows) == 117
assert (mirror / 'STATUS').read_text().strip() == 'done'
addendum = json.loads((mirror / 'd4_postfinal_addendum_lock.json').read_text(encoding='utf-8-sig'))
assert addendum['previous_root_manifest_sha256'] == expected
assert sha(mirror / 'd4_cross_version_cost_ledger.md') == addendum['ledger_sha256']
for name in ('d4_report.md', 'd4_cross_pool_synthesis.md', 'd4_floor_decision_spec.md'):
    assert sha(base / name) == sha(mirror / name), name
print(json.dumps({'status': 'pass', 'manifest_sha256': expected,
                  'files_verified': len(rows), 'local_mirror': str(mirror)}, ensure_ascii=False))

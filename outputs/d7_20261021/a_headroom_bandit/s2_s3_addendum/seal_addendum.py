"""Seal only additive S2/S3 artifacts; verify old manifests unchanged."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

NEW = Path(__file__).resolve().parent
BASE = NEW.parent
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
old = {'MANIFEST.json': '4b73316852001cd93de3e5e707ae5ffbe6d6d02b73e9ab7e226b1afbd0ae29fb',
       'revision_11field/MANIFEST.json': '2e76b72620b8437d3d13aabf5c661c58ff5af23105b4fb5f9f341275596caf42'}
for rel, expected in old.items():
    assert sha(BASE / rel) == expected, rel
    data = json.loads((BASE / rel).read_text(encoding='utf-8'))
    parent = (BASE / rel).parent
    for row in data.get('members', data.get('files', [])):
        assert sha(parent / row['path']) == row['sha256'], row['path']
paths = sorted(p for p in NEW.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
paths.append(BASE / 'PREREGISTRATION_OUTCOMES.md')
members = [{'path': p.relative_to(BASE).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in paths]
out = BASE / 'MANIFEST_S2_S3.json'
assert not out.exists()
out.write_text(json.dumps({'utc': datetime.now(timezone.utc).isoformat(),
                          'scope': 'additive S2/S3 files only; old A1/A3 snapshots retained',
                          'old_manifests_and_members_verified_unchanged': old,
                          'members': members, 'glm_calls': 0, 'new_campaigns': 0},
                         indent=2, sort_keys=True) + '\n', encoding='utf-8')
print(json.dumps({'path': str(out), 'sha256': sha(out), 'members': len(members)}))

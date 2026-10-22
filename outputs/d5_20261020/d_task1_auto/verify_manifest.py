"""Read-only verification of this D5 subagent deliverable and scope."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
manifest = json.loads((HERE/'MANIFEST.json').read_text(encoding='utf-8'))
seen = set()
for row in manifest['files']:
    path = (HERE/row['path']).resolve()
    if not path.is_relative_to(HERE):
        raise ValueError('Manifest path escaped subagent directory')
    assert path.is_file(), row['path']
    assert path.stat().st_size == row['bytes'], row['path']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256'], row['path']
    seen.add(row['path'])
actual = {p.relative_to(HERE).as_posix() for p in HERE.rglob('*')
          if p.is_file() and p.name != 'MANIFEST.json' and '__pycache__' not in p.parts}
assert actual == seen, sorted(actual ^ seen)
progress = json.loads((HERE/'progress.json').read_text(encoding='utf-8'))
assert progress['api_attempts'] == 24
assert len(progress['candidates']) == 6
assert not any(c['decision']['campaign_ready'] for c in progress['candidates'])
assert all(e['status'] == 'action_executed' for e in progress['events'])
print(json.dumps({'verified': True, 'file_count': len(seen), 'api_attempts': 24,
                  'manifest_sha256': hashlib.sha256((HERE/'MANIFEST.json').read_bytes()).hexdigest()}))

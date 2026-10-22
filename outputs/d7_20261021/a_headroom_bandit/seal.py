"""Seal this directory after post-exposure A1 reanalysis and Tier B stop."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

base = Path(__file__).resolve().parent
assert not (base / 'MANIFEST.json').exists()
files = []
for path in sorted(base.rglob('*')):
    if path.is_file() and '__pycache__' not in path.parts:
        relative = path.relative_to(base).as_posix()
        assert not relative.startswith('../')
        files.append({'path': relative, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size})
obj = {'post_exposure': True, 'utc': datetime.now(timezone.utc).isoformat(), 'status': 'A1_COMPLETE_A2_A3_BLOCKED_TIER_B_INFORMATION_SET', 'glm_calls': 0, 'new_campaigns': 0, 'members': files}
(base / 'MANIFEST.json').write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)+'\n', encoding='utf-8')
print(hashlib.sha256((base/'MANIFEST.json').read_bytes()).hexdigest())

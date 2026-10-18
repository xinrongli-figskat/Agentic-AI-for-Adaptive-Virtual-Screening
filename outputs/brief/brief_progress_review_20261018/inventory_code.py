"""Read-only code inventory; never reads credentials or data records."""
import hashlib
import json
import os
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
skip = {'.git', '.venv', '.venv-curation-check', '.cache', '__pycache__', '.sync_audit',
        'node_modules', 'github_snapshot_20261018', 'brief_progress_review_20261018'}
rows = []
for parent, dirs, files in os.walk(root):
    dirs[:] = sorted(d for d in dirs if d not in skip and not d.startswith('deliveries_'))
    for name in sorted(files):
        p = Path(parent) / name
        if p.suffix.lower() not in {'.py', '.sql', '.sh', '.ps1'} or p.is_symlink():
            continue
        rows.append({'path': p.relative_to(root).as_posix(), 'bytes': p.stat().st_size,
                     'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
print(json.dumps({'root': str(root), 'files': rows}, ensure_ascii=False, indent=2))

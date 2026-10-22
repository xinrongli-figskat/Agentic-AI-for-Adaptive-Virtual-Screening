"""Create a self-excluding SHA-256 file manifest for this subagent directory."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    files = []
    for path in sorted(HERE.rglob('*')):
        if not path.is_file() or path.name == 'MANIFEST.json' or '__pycache__' in path.parts:
            continue
        files.append({'path': path.relative_to(HERE).as_posix(), 'bytes': path.stat().st_size,
                      'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    assert sum(item['path'].startswith('llm_receipts/') for item in files) == 24
    out = {'schema': 'd5_task1_auto_manifest_v1',
           'created_at_utc': datetime.now(timezone.utc).isoformat(),
           'self_excluded': True, 'subagent_output_scope': 'outputs/d5_20261020/d_task1_auto/',
           'file_count': len(files), 'files': files}
    (HERE/'MANIFEST.json').write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(hashlib.sha256((HERE/'MANIFEST.json').read_bytes()).hexdigest())


if __name__ == '__main__':
    main()

"""Seal the progress report and code-only handoff without modifying originals."""
import ast
import hashlib
import json
import platform
import shutil
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
SNAPSHOT = ROOT / 'github_snapshot_20261018'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

local = json.loads((OUT / 'local_code_inventory.json').read_text(encoding='utf-8-sig'))['files']
changed = [row['path'] for row in local if sha(ROOT / row['path']) != row['sha256']]
assert not changed, changed
copy_rows = json.loads((SNAPSHOT / 'SOURCE_COPY_MANIFEST.json').read_text())['files']
assert all(sha(ROOT / r['path']) == r['sha256'] == sha(SNAPSHOT / r['path']) for r in copy_rows)
python_files = list(SNAPSHOT.rglob('*.py'))
for path in python_files:
    ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
docs = SNAPSHOT / 'docs'
docs.mkdir(exist_ok=True)
shutil.copy2(OUT / 'progress_against_original_brief.md', docs / 'PROGRESS_20261018_ZH.md')
validation = {
    'utc_recorded': datetime.now(timezone.utc).isoformat(),
    'local_code_files_rechecked_unchanged': len(local),
    'remote_code_files_rechecked_unchanged': 327,
    'remote_recheck_result': {'checked': 327, 'changed': []},
    'copied_source_configuration_files_exact': len(copy_rows),
    'python_files_syntax_checked': len(python_files),
    'remote_offline_tests': {'tests': 65, 'result': 'OK', 'elapsed_seconds': 1.282,
        'tested_code_archive_sha256': '4212aa440f2f73ce25ed4b6c53396959e3b69d1184a37ec531769a3e5b765684',
        'path': '/driveA/xinrong/agentic-screening/code_reviews_20261018/github_snapshot_20261018/outputs',
        'scope': 'campaign, freeze, curation v3, independent cold-start synthetic tests; no real API calls'},
    'not_validated': ['all auxiliary scripts', 'fresh-machine installation', 'OS permission isolation',
                      'scientific qualification of new benchmarks'],
    'git_initialized': False, 'github_uploaded': False,
}
(OUT / 'validation.json').write_text(json.dumps(validation, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
shutil.copy2(OUT / 'validation.json', SNAPSHOT / 'VALIDATION.json')
snapshot_rows = [{'path': p.relative_to(SNAPSHOT).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p)}
                 for p in sorted(SNAPSHOT.rglob('*')) if p.is_file() and p.name != 'SNAPSHOT_MANIFEST.json']
(SNAPSHOT / 'SNAPSHOT_MANIFEST.json').write_text(json.dumps({'files': snapshot_rows, 'self_excluded': True}, indent=2) + '\n')
(OUT / 'STATUS').write_text('done\n')
(OUT / 'RUN_LOG.md').write_text(
    'post-exposure 的进度审计，不是新 benchmark、盲验证或新 campaign。\n\n'
    f'UTC: {datetime.now(timezone.utc).isoformat()}\nPython: {platform.python_version()}\n'
    'Read original DOCX via ZIP/XML; inventory and copy source files; compare SHA-256; parse Python source.\n'
    'Remote: existing Python 3.10 environment; 65 offline tests passed in 1.282 seconds.\n'
    'GLM calls: 0; new campaign runs: 0; data/label changes: 0; GitHub uploads: 0.\n'
    f'Local code unchanged: {len(local)} files. Remote code unchanged: 327 files.\n'
    'The remote SQLite database and private label data were not scanned or copied by this review.\n'
    f'Code snapshot manifest SHA-256: {sha(SNAPSHOT / "SNAPSHOT_MANIFEST.json")}\n', encoding='utf-8')
rows = [{'path': p.relative_to(OUT).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p)}
        for p in sorted(OUT.rglob('*')) if p.is_file() and p.name != 'MANIFEST.json']
(OUT / 'MANIFEST.json').write_text(json.dumps({'files': rows, 'self_excluded': True}, indent=2) + '\n')
print(json.dumps({'review_manifest_sha256': sha(OUT / 'MANIFEST.json'),
                  'snapshot_manifest_sha256': sha(SNAPSHOT / 'SNAPSHOT_MANIFEST.json'),
                  'snapshot_files': len(snapshot_rows) + 1,
                  'snapshot_bytes': sum(r['bytes'] for r in snapshot_rows),
                  'python_syntax_files': len(python_files), 'local_unchanged': len(local)}, ensure_ascii=False))

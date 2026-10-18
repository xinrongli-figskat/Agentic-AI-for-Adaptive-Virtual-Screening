from __future__ import annotations
import csv,hashlib,re,shutil
from datetime import datetime,timezone
from pathlib import Path
OUT=Path(r'C:\Users\lixinrong\Documents\Codex\2026-10-09\agentic-ai-for-adaptive-virtual-screening\outputs').resolve()
archive=(OUT/'_archive').resolve(); transfer=(archive/'transfer_packages').resolve(); superseded=(archive/'superseded').resolve(); devlog=(OUT/'devlog').resolve()
for d in (transfer,superseded,devlog):
 if not d.is_relative_to(OUT): raise SystemExit('Destination escapes outputs')
 d.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
moves=[]
# Transfer archives and their checksum/receipt sidecars.
for p in sorted(OUT.iterdir()):
 if not p.is_file(): continue
 name=p.name.lower()
 if name.endswith('_transfer.zip') or name=='research_notes_06_21_20261015.zip' or ('transfer' in name and p.suffix.lower()=='.sha256') or ('transfer' in name and 'receipt' in name and p.suffix.lower()=='.json'):
  dest=transfer/p.name
  if dest.exists(): raise SystemExit(f'Destination exists: {dest.name}')
  moves.append((p,dest))
# Numbered notes 02 through 39; preserve the original brief 01 at the root.
for p in sorted(OUT.iterdir()):
 if p.is_file() and re.match(r'^(?:0[2-9]|[12]\d|3[0-9])_.*\.md$',p.name,re.I):
  moves.append((p,devlog/p.name))
# Explicit superseded artifacts from S3 index.
old_r3=OUT/'r3_ranked_numeric_private_20261018'
if old_r3.exists(): moves.append((old_r3,superseded/old_r3.name))
old_summary=OUT/'results'/'task1_v4_terminal_summary_20261016.md'
if old_summary.exists(): moves.append((old_summary,superseded/old_summary.name))
rows=[]; now=datetime.now(timezone.utc).isoformat()
for src,dst in moves:
 src=src.resolve(); dst=dst.resolve()
 if not src.is_relative_to(OUT) or not dst.is_relative_to(OUT): raise SystemExit('Move path escapes outputs')
 if not src.exists(): raise SystemExit(f'Missing source: {src}')
 files=[src] if src.is_file() else sorted(x for x in src.rglob('*') if x.is_file())
 hashes={f:sha(f) for f in files}
 dst.parent.mkdir(parents=True,exist_ok=True)
 shutil.move(str(src),str(dst))
 for f,expected in hashes.items():
  new=dst if src.is_file() else dst/f.relative_to(src)
  if sha(new)!=expected: raise SystemExit(f'SHA mismatch after move: {f.relative_to(OUT)}')
  rows.append({'old_relative_path':f.relative_to(OUT).as_posix(),'new_relative_path':new.relative_to(OUT).as_posix(),'sha256':expected,'moved_utc':now,'task_card':'S4'})
# Rewrite path map with original header and all S4 rows.
map_path=OUT/'PATH_MIGRATION_20261018.csv'
existing=list(csv.DictReader(map_path.open(encoding='utf-8-sig',newline='')))
with map_path.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['old_relative_path','new_relative_path','sha256','moved_utc','task_card']); w.writeheader(); w.writerows(existing+rows)
print({'status':'S4_files_moved','move_operations':len(moves),'moved_file_rows':len(rows),'transfer_files':sum(1 for r in rows if '/_archive/transfer_packages/' in r['new_relative_path']),'devlog_files':sum(1 for r in rows if '/devlog/' in r['new_relative_path']),'superseded_files':sum(1 for r in rows if '/_archive/superseded/' in r['new_relative_path']),'sha_all_match':True})

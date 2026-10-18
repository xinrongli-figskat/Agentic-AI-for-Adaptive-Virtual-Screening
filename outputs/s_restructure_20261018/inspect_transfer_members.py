from zipfile import ZipFile
from pathlib import Path
for z in sorted(Path('outputs').glob('*transfer*.zip')):
 try:
  with ZipFile(z) as f:
   names=f.namelist()
   sensitive=[n for n in names if any(s in n.lower() for s in ('label','activity','hit','nonhit','private','run.json','oracle'))]
   print(z.name,'members',len(names),'bytes',z.stat().st_size,'sensitive_name_members',len(sensitive),'; '.join(sensitive[:12]))
 except Exception as e: print(z.name,'ERROR',type(e).__name__)

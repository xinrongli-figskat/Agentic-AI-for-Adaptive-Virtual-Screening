from pathlib import Path
from collections import defaultdict
root=Path('outputs')
for d in sorted((p for p in root.iterdir() if p.is_dir()), key=lambda p:p.name.lower()):
 if d.name=='s_restructure_20261018': continue
 fs=[p for p in d.rglob('*') if p.is_file()]
 size=sum(p.stat().st_size for p in fs)
 interesting=[p.relative_to(d).as_posix() for p in fs if any(x in p.name.lower() for x in ('label','activity','compound','class','private','hit','nonhit','oracle'))]
 if fs: print(f'{d.name}\tfiles={len(fs)}\tbytes={size}\tdata_named={len(interesting)}\t'+'; '.join(interesting[:8]))

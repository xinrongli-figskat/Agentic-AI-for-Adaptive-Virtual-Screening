import re
from pathlib import Path
idx=Path('outputs/INDEX.md').read_text(encoding='utf-8-sig').splitlines()
old=set()
for line in idx:
 m=re.match(r'^\|`([^`]+)`\|',line)
 if m: old.add(m.group(1))
new={p.name for p in Path('outputs').iterdir()}
print('index_old_rows',len(old),'current_top',len(new),'removed_from_index',len(old-new),'added_since_index',len(new-old))
print('removed_names',sorted(old-new))
print('added_names',sorted(new-old))

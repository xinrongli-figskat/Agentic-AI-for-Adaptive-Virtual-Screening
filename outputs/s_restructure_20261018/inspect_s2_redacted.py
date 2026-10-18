import re
from pathlib import Path
root=Path('outputs')
refs=[('brief_progress_review_20261018/progress_against_original_brief.md',165),('download_chembl37_parallel.py',15),('download_chembl37_sqlite.sh',5)]
rx=re.compile(r'(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{32,}[+/=][A-Za-z0-9+/=]{0,}(?![A-Za-z0-9+/])')
for name,n in refs:
 line=(root/name).read_text(encoding='utf-8',errors='replace').splitlines()[n-1]
 safe=rx.sub('<REDACTED_LONG_TOKENLIKE>',line)
 print(name,n,repr(safe[:400]))

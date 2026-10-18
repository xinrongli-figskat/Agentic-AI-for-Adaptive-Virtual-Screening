import csv
from pathlib import Path
rows=list(csv.DictReader(open('outputs/s_restructure_20261018/inventory_before.csv',encoding='utf-8-sig')))
for key in ('.cache','__pycache__'):
 a=[r for r in rows if r['relative_path'].split('/')[0]==key]
 print(key,'inventory_paths',len(a),'bytes',sum(int(r['size_bytes']) for r in a),'examples',[r['relative_path'] for r in a[:3]])

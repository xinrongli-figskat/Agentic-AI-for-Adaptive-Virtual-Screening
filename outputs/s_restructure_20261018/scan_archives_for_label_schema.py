import zipfile,json,csv,io,re
from pathlib import Path
root=Path('outputs')
compound=re.compile(r'(molecule_chembl_id|compound_chembl_id|molregno|canonical_smiles|compound_id)',re.I)
label=re.compile(r'(standard_value|standard_relation|standard_type|activity_comment|label|provisional_state|class_state)',re.I)
def scan_json(b):
 try: obj=json.loads(b.decode('utf-8',errors='replace'))
 except: return False
 found=False
 def walk(x):
  nonlocal found
  if isinstance(x,dict):
   ks=' '.join(map(str,x.keys()))
   if compound.search(ks) and label.search(ks): found=True
   for v in x.values(): walk(v)
  elif isinstance(x,list):
   for v in x[:5000]: walk(v)
 walk(obj); return found
for z in sorted(root.glob('*transfer*.zip')):
 try:
  with zipfile.ZipFile(z) as f:
   files=[]
   for n in f.namelist():
    if n.endswith('/') or f.getinfo(n).file_size>20_000_000: continue
    b=f.read(n); hit=False
    if n.lower().endswith('.json'): hit=scan_json(b)
    elif n.lower().endswith('.csv'):
     try:
      h=next(csv.reader(io.StringIO(b.decode('utf-8-sig',errors='replace'))),[]); hit=bool(compound.search(' '.join(h)) and label.search(' '.join(h)))
     except: pass
    if hit: files.append(n)
   if files: print(z.name,'compound_label_schemas',len(files),'; '.join(files[:10]))
 except Exception as e: print(z.name,'scan_error',type(e).__name__)

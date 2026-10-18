import csv,json,re,zipfile
from pathlib import Path
ROOT=Path('outputs'); SELF=ROOT/'s_restructure_20261018'
results=[]
compound=re.compile(r'(molecule_chembl_id|compound_chembl_id|molregno|canonical_smiles|compound_id)',re.I)
label=re.compile(r'(standard_value|standard_relation|standard_type|label|hit_support|nonhit_support|provisional_state|class_state|activity_comment)',re.I)
def inspect_obj(obj,keys,path):
 if isinstance(obj,dict):
  ks=set(map(str,obj.keys())); flat=' '.join(ks)
  if compound.search(flat) and label.search(flat): keys.add('compound_and_measurement_or_label_fields')
  for v in obj.values(): inspect_obj(v,keys,path)
 elif isinstance(obj,list):
  for v in obj[:1000]: inspect_obj(v,keys,path)
for p in sorted(ROOT.rglob('*')):
 if not p.is_file() or SELF in p.parents or 'private' in p.as_posix().lower(): continue
 name=p.name.lower(); flags=set()
 try:
  if p.suffix.lower()=='.csv':
   with p.open(encoding='utf-8-sig',errors='replace',newline='') as f:
    reader=csv.reader(f); header=next(reader,[])
   h=' '.join(header)
   if compound.search(h) and label.search(h): flags.add('compound_level_label_or_measurement_columns')
  elif p.suffix.lower() in ('.json','.jsonl'):
   text=p.read_text(encoding='utf-8',errors='replace')
   try: obj=json.loads(text)
   except Exception: obj=None
   if obj is not None: inspect_obj(obj,flags,p)
   # Key names can be split across nested arrays; raw activity structure and a molecule ID are sufficient to inspect privately.
   if compound.search(text) and label.search(text): flags.add('compound_and_measurement_or_label_tokens')
  elif p.suffix.lower()=='.zip':
   with zipfile.ZipFile(p) as z:
    members=[]
    for n in z.namelist():
     nl=n.lower()
     if any(k in nl for k in ('label','activity','hit','nonhit','compound','private')): members.append(n)
    if members: flags.add('archive_member_names_suggest_label_or_activity_data:'+str(len(members)))
 except Exception: flags.add('scan_error:'+type(Exception).__name__)
 if flags: results.append((p.relative_to(ROOT).as_posix(),sorted(flags)))
bydir={}
for path,flags in results:
 top=path.split('/')[0]; bydir.setdefault(top,[]).append((path,flags))
for d,rows in sorted(bydir.items()):
 print(f'[{d}] {len(rows)} flagged files')
 for path,flags in rows[:30]: print(' ',path,'|',';'.join(flags))
print('TOTAL',len(results),'TOP_DIRS',len(bydir))

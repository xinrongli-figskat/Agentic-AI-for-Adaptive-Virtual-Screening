import csv,re
from pathlib import Path
OUT=Path('outputs'); AUD=OUT/'s_restructure_20261018'; hard=list(csv.DictReader((AUD/'hardcoded_paths.csv').open(encoding='utf-8-sig')))
script_files=[p for p in OUT.iterdir() if p.is_file() and p.suffix.lower() in ('.py','.sh','.ps1','.sql') and not (p.name.startswith('test_') and p.suffix.lower()=='.py')]

def classify(n):
 low=n.lower()
 # Exact task-card exceptions before broad prefixes.
 if low in ('archive_s1pr1_source_review.py','check_project_sync.py','check_remote_progress_20261015.py','complete_project_backup.ps1','execute_local_cleanup.ps1','plan_local_cleanup.py','project_backup_v1.py','package_task1_v4.py') or low.startswith(('install_task1_v','build_task1_v','closeout_task1_v')): return ('ops','explicit ops exception/prefix in S5')
 if low in ('extract_p1_p5_summaries.py','review_task1_v3_archive.py','audit_task1_finished_v1.py'): return ('verification','explicit filename rule in S5')
 if low.startswith(('enumerate_chembl37_','download_chembl37_','prepare_chembl37_','repair_chembl37_','start_chembl37_','switch_chembl37_','run_chembl37_')) or low=='chembl37_assay_prescreen.sql' or low=='inspect_chembl_sample.py': return ('discovery','prefix/filename rule in S5')
 if low.startswith('curate_') or low=='summarize_chembl37_curation.py' or low.startswith(('audit_value_quantization_','audit_nonhit_bottleneck_')): return ('curation','prefix/filename rule in S5')
 if 's1pr1' in low or low.startswith(('reconcile_','compare_','fetch_pubchem_','query_pubchem_','extract_','map_')) or low in ('select_source_audit_samples.py','build_s1pr1_patent_crosswalk.py','review_candidate_assays.py'): return ('source_audit','prefix/filename rule in S5')
 if low.startswith(('verify_','check_','validate_','replay_')): return ('verification','prefix rule in S5')
 if low.startswith(('install_task1_v','build_task1_v','closeout_task1_v','check_remote_progress_')): return ('ops','prefix rule in S5')
 return ('unclassified','no S5 rule matched')
hard_by={}
for r in hard: hard_by.setdefault(Path(r['file']).name,[]).append((r['line'],r['matches']))
codepaths=[p for p in OUT.rglob('*') if p.is_file() and p.suffix.lower() in ('.py','.sh','.ps1','.sql') and AUD not in p.parents]
rows=[]
for p in sorted(script_files,key=lambda x:x.name.lower()):
 cls,rule=classify(p.name); own=hard_by.get(p.name,[]); refs=[]
 stem=p.stem
 for q in codepaths:
  if q.resolve()==p.resolve(): continue
  try: lines=q.read_text(encoding='utf-8',errors='replace').splitlines()
  except: continue
  for ln,line in enumerate(lines,1):
   # Consider literal relative/absolute paths or module imports, not prose mentions in docs.
   pathref=bool(re.search(r'(?i)(?:outputs[\\/]|[A-Z]:[\\/]|/drive[A-B]/)[^\"\'\s]*'+re.escape(p.name),line))
   modref=bool(re.search(r'(?i)(?:from\s+'+re.escape(stem)+r'\s+import|import\s+'+re.escape(stem)+r'(?:\s|$|,))',line))
   explicit= p.name.lower() in line.lower() and ('.py' in line.lower() or '.sh' in line.lower() or '.ps1' in line.lower() or '.sql' in line.lower())
   if pathref or modref or explicit: refs.append((q.relative_to(OUT).as_posix(),ln))
 refs=sorted(set(refs))
 decision='defer' if refs or cls=='unclassified' else 'move_candidate'
 reason=('external code/path reference(s): '+', '.join(f'{a}:{b}' for a,b in refs[:8])) if refs else ('unclassified by task rules' if cls=='unclassified' else 'no exact path/module reference in other code')
 dest=f'outputs/scripts/{cls}/{p.name}' if cls!='unclassified' else f'outputs/scripts/unclassified/{p.name}'
 rows.append({'source':p.relative_to(OUT).as_posix(),'category':cls,'destination':dest,'rule':rule,'own_hardcoded_matches':';'.join(f'{n}:{m}' for n,m in own),'referenced_by_code':';'.join(f'{a}:{b}' for a,b in refs),'move_decision':decision,'reason':reason})
with (AUD/'script_classification.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
tests=[p for p in OUT.iterdir() if p.is_file() and p.name.startswith('test_') and p.suffix.lower()=='.py']; tr=[]
for p in sorted(tests,key=lambda x:x.name.lower()):
 text=p.read_text(encoding='utf-8',errors='replace'); imports=[]
 for ln,line in enumerate(text.splitlines(),1):
  m=re.search(r'(?i)(?:from|import)\s+([A-Za-z_][\w.]*)',line)
  if m and not m.group(1).split('.')[0] in {'copy','json','hashlib','pathlib','tempfile','unittest','zipfile','sqlite3','sys','os','re','csv','decimal','subprocess','shutil','collections','typing','datetime','math'}: imports.append((m.group(1),ln))
 anchor='__file__' in text
 reasons=[]
 if anchor: reasons.append('__file__ 相对路径锚点会随移动改变')
 if imports: reasons.append('导入被测模块，移动需要同步调整导入/路径：'+','.join(f'{m}@{ln}' for m,ln in imports[:6]))
 tr.append({'test':p.name,'uses_file_anchor':'yes' if anchor else 'no','project_module_imports':';'.join(f'{m}@{ln}' for m,ln in imports),'move_decision':'defer' if reasons else 'move_candidate','reason':'; '.join(reasons) if reasons else '未发现相对路径锚点或项目模块导入'})
with (AUD/'test_movement_assessment.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(tr[0]));w.writeheader();w.writerows(tr)
print('SCRIPTS',len(rows),'MOVE',sum(r['move_decision']=='move_candidate' for r in rows),'DEFER',sum(r['move_decision']=='defer' for r in rows),'UNCLASSIFIED',sum(r['category']=='unclassified' for r in rows))
for r in rows:
 if r['move_decision']=='move_candidate': print('MOVE',r['source'],r['destination'])
print('TESTS',len(tr),'MOVE',sum(r['move_decision']=='move_candidate' for r in tr),'DEFER',sum(r['move_decision']=='defer' for r in tr))
for r in rows:
 if r['category']=='unclassified': print('UNCLEAR',r['source'])

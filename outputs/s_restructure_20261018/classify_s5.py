import csv,re
from pathlib import Path
OUT=Path('outputs'); AUD=OUT/'s_restructure_20261018'; hard=list(csv.DictReader((AUD/'hardcoded_paths.csv').open(encoding='utf-8-sig')))
script_files=[p for p in OUT.iterdir() if p.is_file() and p.suffix.lower() in ('.py','.sh','.ps1','.sql')]
# Class order follows task card exactly.
def classify(n):
 low=n.lower()
 if low.startswith(('enumerate_chembl37_','download_chembl37_','prepare_chembl37_','repair_chembl37_','start_chembl37_','switch_chembl37_','run_chembl37_')) or low=='chembl37_assay_prescreen.sql' or low=='inspect_chembl_sample.py': return ('discovery','prefix/filename rule in S5')
 if low.startswith('curate_') or low in ('summarize_chembl37_curation.py',) or low.startswith(('audit_value_quantization_','audit_nonhit_bottleneck_')): return ('curation','prefix/filename rule in S5')
 if 's1pr1' in low or low.startswith(('reconcile_','compare_','fetch_pubchem_','query_pubchem_','extract_','map_')) or low in ('select_source_audit_samples.py','build_s1pr1_patent_crosswalk.py','review_candidate_assays.py'): return ('source_audit','prefix/filename rule in S5')
 if low.startswith(('verify_','check_','validate_','replay_')) or low in ('review_task1_v3_archive.py','audit_task1_finished_v1.py','extract_p1_p5_summaries.py'): return ('verification','prefix/filename rule in S5')
 if low.startswith(('install_task1_v','build_task1_v','closeout_task1_v','check_remote_progress_')) or low in ('package_task1_v4.py','project_backup_v1.py','complete_project_backup.ps1','plan_local_cleanup.py','execute_local_cleanup.ps1','check_project_sync.py','archive_s1pr1_source_review.py'): return ('ops','prefix/filename rule in S5')
 return ('unclassified','no S5 rule matched')
hard_by={}
for r in hard: hard_by.setdefault(Path(r['file']).name,[]).append((r['line'],r['matches']))
refs={}
codepaths=[p for p in OUT.rglob('*') if p.is_file() and p.suffix.lower() in ('.py','.sh','.ps1','.sql') and AUD not in p.parents]
for target in script_files:
 hits=[]
 for q in codepaths:
  if q.resolve()==target.resolve(): continue
  try: lines=q.read_text(encoding='utf-8',errors='replace').splitlines()
  except: continue
  for ln,line in enumerate(lines,1):
   if target.name.lower() in line.lower(): hits.append((q.relative_to(OUT).as_posix(),ln,line.strip()[:180]))
 refs[target.name]=hits
rows=[]
for p in sorted(script_files,key=lambda x:x.name.lower()):
 cls,rule=classify(p.name); own=hard_by.get(p.name,[]); ext=refs[p.name]
 hardrefs=[]
 for path,ln,text in ext:
  if re.search(r'(?i)(?:outputs[\\/]|[A-Z]:[\\/].*'+re.escape(p.name)+r'|/drive[A-B]/.*'+re.escape(p.name)+r')',text): hardrefs.append((path,ln))
 move='defer' if ext or cls=='unclassified' else 'move_candidate'
 why='external code reference(s): '+','.join(f'{x[0]}:{x[1]}' for x in ext[:8]) if ext else ('unclassified by task rules' if cls=='unclassified' else 'no other-code filename reference found; path-safe candidate')
 rows.append({'source':p.relative_to(OUT).as_posix(),'category':cls,'destination':('outputs/scripts/'+cls+'/'+p.name if cls not in ('unclassified','verification') else 'outputs/scripts/unclassified/'+p.name if cls=='unclassified' else 'outputs/scripts/verification/'+p.name),'rule':rule,'own_hardcoded_matches':';'.join(f'{n}:{m}' for n,m in own),'referenced_by_code':';'.join(f'{x[0]}:{x[1]}' for x in ext),'move_decision':move,'reason':why})
with (AUD/'script_classification.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
# Test relocation audit. Examine __file__, parent path assumptions, and test imports using sibling/top-level modules.
tests=[p for p in OUT.iterdir() if p.is_file() and p.name.startswith('test_') and p.suffix.lower()=='.py']
tr=[]
for p in sorted(tests,key=lambda x:x.name.lower()):
 text=p.read_text(encoding='utf-8',errors='replace'); lines=text.splitlines()
 reasons=[]
 if '__file__' in text: reasons.append('__file__ path anchor; relocating changes relative base')
 imports=[]
 for ln,line in enumerate(lines,1):
  if re.search(r'(?i)(?:from|import)\s+[A-Za-z_][\w.]*',line):
   m=re.search(r'(?i)(?:from|import)\s+([A-Za-z_][\w.]*)',line)
   if m: imports.append(f'{m.group(1)}@{ln}')
 if imports: reasons.append('imports modules whose resolution may depend on current location: '+';'.join(imports[:10]))
 tr.append({'test':p.name,'uses_file_anchor':'yes' if '__file__' in text else 'no','imports':';'.join(imports),'move_decision':'defer' if reasons else 'move_candidate','reason':'; '.join(reasons) if reasons else 'no file-relative or import assumptions detected'})
with (AUD/'test_movement_assessment.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(tr[0]));w.writeheader();w.writerows(tr)
print('SCRIPTS',len(rows),'CANDIDATE',sum(x['move_decision']=='move_candidate' for x in rows),'DEFER',sum(x['move_decision']=='defer' for x in rows),'UNCLASSIFIED',sum(x['category']=='unclassified' for x in rows))
for x in rows:
 if x['move_decision']=='move_candidate': print('MOVE',x['source'],'->',x['destination'])
print('TESTS',len(tr),'CANDIDATE',sum(x['move_decision']=='move_candidate' for x in tr),'DEFER',sum(x['move_decision']=='defer' for x in tr))
for x in tr:
 if x['move_decision']=='defer': print('TEST_DEFER',x['test'],x['reason'][:200])

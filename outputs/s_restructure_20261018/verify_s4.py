import csv,hashlib,json
from pathlib import Path
OUT=Path('outputs'); audit=OUT/'s_restructure_20261018'
inv={r['relative_path']:r['sha256'] for r in csv.DictReader((audit/'inventory_before.csv').open(encoding='utf-8-sig'))}
rows=list(csv.DictReader((OUT/'PATH_MIGRATION_20261018.csv').open(encoding='utf-8-sig')))
problems=[]
for r in rows:
 old=r['old_relative_path']; new=r['new_relative_path']; p=OUT/new
 if old not in inv: problems.append(('missing_from_inventory',old))
 elif inv[old]!=r['sha256']: problems.append(('inventory_hash_mismatch',old))
 elif not p.is_file(): problems.append(('missing_destination',new))
 elif hashlib.sha256(p.read_bytes()).hexdigest()!=r['sha256']: problems.append(('destination_hash_mismatch',new))
if problems: raise SystemExit(json.dumps(problems[:20]))
summary={'task':'S4','status':'verified','migration_rows':len(rows),'move_operations':69,'transfer_package_files':sum('/_archive/transfer_packages/' in '/'+r['new_relative_path'] for r in rows),'devlog_files':sum('/devlog/' in '/'+r['new_relative_path'] for r in rows),'superseded_files':sum('/_archive/superseded/' in '/'+r['new_relative_path'] for r in rows),'all_sha256_match_inventory_and_destination':True,'cache_deletion':{'outputs/.cache':{'files_removed':0,'directory_removed':True,'note':'empty/reparse view under outputs; project-root .cache remains outside S4 scope'},'outputs/__pycache__':{'files_removed':1,'directory_removed':True}},'top_level_reconciliation':{'inventory_summary_before':229,'added_after_s1':['INDEX.md','PATH_MIGRATION_20261018.csv','_archive','devlog'],'removed_after_s1':['68 moved top-level entries','outputs/.cache','outputs/__pycache__'],'current':len(list(OUT.iterdir()))}}
(audit/'s4_verification.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))

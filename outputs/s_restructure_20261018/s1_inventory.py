from __future__ import annotations
import csv, hashlib, json, os, re, sys
from collections import defaultdict, Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(r'C:\Users\lixinrong\Documents\Codex\2026-10-09\agentic-ai-for-adaptive-virtual-screening')
OUT=ROOT/'outputs'; SELF=OUT/'s_restructure_20261018'

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def files():
    return sorted((p for p in OUT.rglob('*') if p.is_file() and SELF not in p.parents), key=lambda p:p.as_posix().lower())
def tree_digest(entries):
    h=hashlib.sha256()
    for p in entries:
        rel=p.relative_to(OUT).as_posix(); h.update(rel.encode()); h.update(b'\0'); h.update(sha(p).encode()); h.update(b'\n')
    return h.hexdigest()
def write_csv(path, fields, rows):
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
start=datetime.now(timezone.utc)
before=files(); before_digest=tree_digest(before)
rows=[]; byhash=defaultdict(list); bytes_total=0
for p in before:
    st=p.stat(); rel=p.relative_to(OUT).as_posix(); digest=sha(p); bytes_total+=st.st_size
    rows.append({'relative_path':rel,'size_bytes':st.st_size,'mtime_local':datetime.fromtimestamp(st.st_mtime).astimezone().isoformat(),'sha256':digest})
    byhash[digest].append((rel,st.st_size))
write_csv(SELF/'inventory_before.csv',['relative_path','size_bytes','mtime_local','sha256'],rows)
dups=[]
for digest,items in sorted(byhash.items()):
    if len(items)>1:
        for rel,size in items: dups.append({'sha256':digest,'group_size':len(items),'size_bytes':size,'relative_path':rel})
write_csv(SELF/'duplicates.csv',['sha256','group_size','size_bytes','relative_path'],dups)
# top-level inventory categories
cats=Counter(); top=list(OUT.iterdir())
for p in top:
    if p.is_dir(): cats['directory']+=1
    elif p.name.startswith('test_') and p.suffix.lower()=='.py': cats['test_*.py']+=1
    elif p.suffix.lower()=='.py': cats['.py']+=1
    elif p.suffix.lower() in ('.sh','.ps1','.md','.zip','.json','.sql'): cats[p.suffix.lower()]+=1
    else: cats['other']+=1
# private-named dirs and transfer packages
private=[]
for p in OUT.rglob('*'):
    if p.is_dir() and 'private' in p.name.lower() and SELF not in p.parents:
        private.append({'directory':p.relative_to(OUT).as_posix(),'file_count':sum(1 for x in p.rglob('*') if x.is_file())})
transfer=[]
for p in OUT.rglob('*'):
    if p.is_file() and p.name.lower().endswith('_transfer.zip'):
        stem=p.name[:-4]
        companions=[x for x in (p.with_suffix(p.suffix+'.sha256'),p.with_name(stem+'.sha256'),p.with_name(stem+'_receipt.json'),p.with_name(stem+'.receipt.json')) if x.exists()]
        transfer.append({'zip':p.relative_to(OUT).as_posix(),'companions':';'.join(x.relative_to(OUT).as_posix() for x in companions),'missing_companion':'yes' if not companions else 'no'})
# scripts path literals
hard=[]
for p in before:
    if p.suffix.lower() in ('.py','.sh','.ps1'):
        try: lines=p.read_text(encoding='utf-8',errors='replace').splitlines()
        except OSError: continue
        for n,line in enumerate(lines,1):
            hits=[needle for needle in ('outputs','C:\\Users','/driveA','.sync_audit') if needle.lower() in line.lower()]
            if hits: hard.append({'file':p.relative_to(OUT).as_posix(),'line':n,'matches':';'.join(hits),'line_excerpt':line.strip()[:300]})
write_csv(SELF/'hardcoded_paths.csv',['file','line','matches','line_excerpt'],hard)
# paths in run logs/manifests/receipts
recorded=[]; abs_rx=re.compile(r'(?:(?:[A-Za-z]:\\)[^\s"\'<>|]+|/(?:drive[A-B]|home|tmp|mnt|Users)/[^\s"\'<>|]+)')
for p in before:
    name=p.name.lower()
    if name=='run_log.md' or name=='manifest.json' or 'receipt' in name and p.suffix.lower()=='.json':
        try: lines=p.read_text(encoding='utf-8',errors='replace').splitlines()
        except OSError: continue
        for n,line in enumerate(lines,1):
            for m in abs_rx.findall(line): recorded.append({'file':p.relative_to(OUT).as_posix(),'line':n,'absolute_path':m[:500]})
write_csv(SELF/'recorded_paths.csv',['file','line','absolute_path'],recorded)
# largest and summary
largest=sorted(rows,key=lambda x:x['size_bytes'],reverse=True)[:20]
summary=['# S1 只读盘点摘要','',f'- 扫描开始（UTC）：{start.isoformat()}',f'- outputs 顶层条目：{len(top)}',f'- 顶层分类：{json.dumps(dict(cats),ensure_ascii=False,sort_keys=True)}',f'- 文件数：{len(rows)}',f'- 文件总字节数：{bytes_total}',f'- 扫描树 SHA-256（路径与内容哈希序列）：`{before_digest}`','', '## 最大 20 个文件','', '|相对路径|字节数|SHA-256|','|---|---:|---|']
summary += [f'|`{r["relative_path"]}`|{r["size_bytes"]}|`{r["sha256"]}`|' for r in largest]
summary += ['', '## 名称含 private 的目录','', '|目录|文件数|','|---|---:|']+[f'|`{x["directory"]}`|{x["file_count"]}|' for x in private]
summary += ['', '## transfer zip 清单','', '|zip|配套校验/收据|缺配套|','|---|---|---|']+[f'|`{x["zip"]}`|{x["companions"] or "无"}|{x["missing_companion"]}|' for x in transfer]
summary += ['', '## 生成表格行数','',f'- inventory_before.csv：{len(rows)}',f'- duplicates.csv：{len(dups)}',f'- hardcoded_paths.csv：{len(hard)}',f'- recorded_paths.csv：{len(recorded)}','', '## 完整性说明','', '扫描不包含本目录 `s_restructure_20261018`，以避免盘点产物自身改变被比较对象；该排除规则将在 RUN_LOG 中说明。']
(SELF/'inventory_summary.md').write_text('\n'.join(summary)+'\n',encoding='utf-8')
after=files(); after_digest=tree_digest(after)
end=datetime.now(timezone.utc)
if before_digest != after_digest: raise SystemExit('S1 read-only validation failed: outputs changed during scan')
# query git and powershell versions as metadata
(SELF/'s1_digest_check.json').write_text(json.dumps({'start_utc':start.isoformat(),'end_utc':end.isoformat(),'files_before':len(before),'files_after':len(after),'tree_sha256_before':before_digest,'tree_sha256_after':after_digest,'unchanged':before_digest==after_digest},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':'S1_read_only_done','files':len(rows),'bytes':bytes_total,'top_level':len(top),'duplicates_rows':len(dups),'hardcoded_rows':len(hard),'recorded_path_rows':len(recorded),'tree_unchanged':before_digest==after_digest,'tree_sha256':before_digest},indent=2))

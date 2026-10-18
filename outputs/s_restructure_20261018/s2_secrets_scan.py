from __future__ import annotations
import re, math, json
from pathlib import Path
ROOT=Path(r'C:\Users\lixinrong\Documents\Codex\2026-10-09\agentic-ai-for-adaptive-virtual-screening'); OUT=ROOT/'outputs'; SELF=OUT/'s_restructure_20261018'
EXT={'.txt','.md','.py','.sh','.ps1','.json','.csv','.sql','.yaml','.yml','.toml','.ini','.conf','.log','.tsv'}
patterns=[('api_key',r'api[_-]?key'),('apikey',r'apikey'),('secret',r'secret'),('token',r'token'),('password',r'password'),('Bearer',r'Bearer\s+'),('ZHIPU',r'zhipu'),('BIGMODEL',r'bigmodel')]
kw=[]; suspect=[]; nfiles=0
literal_field=re.compile(r'''(?i)\b(?:zai_api_key|(?:api[_-]?key)|apikey|secret|password|access[_-]?token|auth[_-]?token)\b\s*[:=]\s*(["'])([^"'\r\n]{20,})\1''')
bearer_rx=re.compile(r'(?i)\bBearer\s+([A-Za-z0-9._~+/=-]{24,})')
hex_rx=re.compile(r'(?<![A-Fa-f0-9])[A-Fa-f0-9]{32,}(?![A-Fa-f0-9])')
# Base64-ish literals must use non-alphanumeric base64 markers or occur next to credential field names.
b64_rx=re.compile(r'(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{32,}[+/=][A-Za-z0-9+/=]{0,}(?![A-Za-z0-9+/])')
placeholder=('your_api_key','api_key_here','test_api_key','example_key','<redacted>','<your-api-key>','changeme','none','null','dummy')
def ent(s):
 from collections import Counter
 n=len(s); return -sum((c/n)*math.log2(c/n) for c in Counter(s).values()) if n else 0
def possible(v):
 v=v.strip(); low=v.lower()
 return len(v)>=32 and not low.startswith(('$','<','your_','test_','example','dummy','changeme')) and low not in placeholder and ent(v)>=3.6
for p in sorted(OUT.rglob('*')):
 if not p.is_file() or SELF in p.parents or p.suffix.lower() not in EXT: continue
 try: lines=p.read_text(encoding='utf-8',errors='replace').splitlines()
 except OSError: continue
 nfiles+=1
 for i,line in enumerate(lines):
  line_no=i+1
  hits=[name for name,rx in patterns if re.search(rx,line,re.I)]
  if hits: kw.append((p.relative_to(OUT).as_posix(),line_no,hits))
  is_hash_context=bool(re.search(r'(?i)(sha-?256|sha256|digest|fingerprint|manifest_hash|database_hash)',line)) or any(re.search(r'(?i)(sha-?256|sha256|digest|fingerprint|manifest_hash|database_hash)',x) for x in lines[max(0,i-2):i])
  is_structure=bool(re.search(r'(?i)(smiles|canonical_smiles|structure|sequence|molregno|chembl_id)',line))
  kinds=[]
  for m in literal_field.finditer(line):
   if possible(m.group(2)): kinds.append('credential_literal')
  for m in bearer_rx.finditer(line):
   if possible(m.group(1)): kinds.append('bearer_value')
  if not is_hash_context and not is_structure:
   # Bare hex strings are tested but checksum-shaped values are excluded from the report as hash material.
   for m in hex_rx.finditer(line):
    if possible(m.group(0)) and not re.fullmatch(r'[A-Fa-f0-9]{40,}',m.group(0)): kinds.append('long_hex_candidate')
   for m in b64_rx.finditer(line):
    if possible(m.group(0)): kinds.append('base64_candidate')
  if kinds: suspect.append((p.relative_to(OUT).as_posix(),line_no,sorted(set(kinds))))
ssh=OUT/'env'/'lab-4090.ssh_config'
if not ssh.exists(): ssh=OUT/'lab-4090.ssh_config'
fields={k:'absent' for k in ('hostname','username','port','identity_file')}
if ssh.exists():
 t=ssh.read_text(encoding='utf-8',errors='replace')
 for k,rx in [('hostname',r'(?im)^\s*HostName\s+\S+'),('username',r'(?im)^\s*User\s+\S+'),('port',r'(?im)^\s*Port\s+\S+'),('identity_file',r'(?im)^\s*IdentityFile\s+\S+')]: fields[k]='present' if re.search(rx,t) else 'absent'
report=['# S2 密钥与隐私扫描','',f'- 扫描文本文件数：{nfiles}',f'- 敏感词模式命中行数：{len(kw)}（只表示提及相关术语）',f'- 长随机凭据样式候选行数：{len(suspect)}','','## SSH 配置字段（只记录存在性）','','|字段|状态|','|---|---|']+[f'|{k}|{v}|' for k,v in fields.items()]
report+=['','## 敏感词命中位置（不含文本内容）','','|文件|行号|模式|','|---|---:|---|']+[f'|`{p}`|{ln}|{", ".join(h)}|' for p,ln,h in kw]
report+=['','## 凭据样式候选位置（不含具体字符串）','','|文件|行号|模式|','|---|---:|---|']+[f'|`{p}`|{ln}|{", ".join(k)}|' for p,ln,k in suspect]
report+=['','## 初步状态','',('存在严格规则检测到的候选，需核实后才能通过 S2。' if suspect else '严格的值模式扫描没有发现明显凭据；常见 SHA-256 字段和结构/序列类字段按任务卡排除。')]
(SELF/'secrets_scan.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
ignore='''__pycache__/\n*.pyc\n.cache/\n.venv/\n.venv-*/\n*.ssh_config\n.env\n*.sqlite\n*.db\n# Private compound-level labels; exact private directories audited in S6\noutputs/**/*private*/\noutputs/private/\n'''
(SELF/'.gitignore.draft').write_text(ignore,encoding='utf-8')
print(json.dumps({'status':'S2_scan_complete','text_files':nfiles,'keyword_hit_lines':len(kw),'credential_style_candidate_lines':len(suspect),'candidate_locations':suspect[:100],'ssh_fields':fields},ensure_ascii=False,indent=2))

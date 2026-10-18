from pathlib import Path
import hashlib
root=Path('outputs')
known_code={'campaign_v0','oracle_boundary_v0','curation_agent_v1','curation_agent_v2','curation_agent_v2_1','curation_agent_v3','curation_agent_v4','assay_audit_v0','candidate_discovery_v0','assay_edge_inspection_v0','reporting_v1','source_alignment_v1'}
rows=[]
for p in sorted(root.iterdir(),key=lambda x:x.name.lower()):
 n=p.name; low=n.lower(); superseded=''; status=''
 if n=='r3_ranked_numeric_private_20261018': superseded='被 r3_ranked_numeric_private_20261018_v2 取代；旧版保留'
 elif n=='r3_ranked_numeric_private_20261018_v2': superseded='当前修订版；取代 r3_ranked_numeric_private_20261018'
 elif n=='b1_nonhit_limited_20261017': superseded='经核对为公开统计/结果包；不是私有目录的新版替代品'
 elif n=='b1_nonhit_limited_private_20261017': superseded='含同一 run_b1.py（SHA一致）；公开结果与私有目录代码副本并存，不是版本替代'
 elif n=='monthly_prototype_guidance_v0_2_20261017.md': superseded='当前有效复盘文档'
 elif n=='task1_v4_terminal_summary_20261016.md': superseded='已过期，保留备查；证据包已下载并核验'
 if p.is_dir():
  sts=list(p.rglob('STATUS'))
  status=sts[0].read_text(encoding='utf-8',errors='replace').strip() if sts else '无 STATUS 文件'
 else: status='—'
 if n=='01_original_brief_from_chat.md': cat='brief'; purpose='原始 brief 对话备份'
 elif n=='lab-4090.ssh_config': cat='env'; purpose='远端 SSH 配置（不纳入版本控制）'
 elif n in ('__pycache__','.cache'): cat='cache'; purpose='可重建缓存'
 elif n in known_code: cat='code'; purpose='可复用代码包；保持顶层以维持 import 路径'
 elif n.startswith('test_') and p.suffix.lower()=='.py': cat='test'; purpose='测试文件'
 elif p.suffix.lower() in ('.py','.sh','.ps1','.sql'): cat='script'; purpose='一次性脚本/查询'
 elif 'private' in low: cat='result_private'; purpose='私有分析结果/待核对私有数据'
 elif p.suffix.lower()=='.zip' or 'transfer' in low and p.suffix.lower() in ('.json','.sha256'): cat='archive'; purpose='历史传输包或校验回执'
 elif n.startswith(('task1_v5','monthly_prototype_guidance')) or 'protocol' in low or 'criteria' in low: cat='protocol'; purpose='协议、标准或资格说明'
 elif p.is_dir() and any((x.is_file() and x.name=='STATUS') for x in p.rglob('*')): cat='result_public'; purpose='有状态文件的运行或结果目录（标签内容按 S6 审计）'
 elif n[:2].isdigit() and p.suffix.lower()=='.md': cat='devlog'; purpose='编号开发记录'
 elif p.suffix.lower()=='.md': cat='devlog'; purpose='项目说明或进度记录'
 elif p.is_dir() and (n.startswith(('results','candidate','source','task1','remote','brief','r','p','b'))): cat='result_public'; purpose='结果、审查或交付目录；精确用途见文件内容'
 else: cat='unclear'; purpose='自动分类不确定，交人复核'
 rows.append((n,cat,status,purpose,superseded))
# B1 relation evidence is a same-content comparison.
a=root/'b1_nonhit_limited_20261017'/'run_b1.py'; b=root/'b1_nonhit_limited_private_20261017'/'run_b1.py'
b1='同一脚本 SHA-256 相同' if a.exists() and b.exists() and hashlib.sha256(a.read_bytes()).digest()==hashlib.sha256(b.read_bytes()).digest() else '脚本哈希不相同，关系待人工复核'
lines=['# INDEX：项目交付物索引','','本索引按当前工作区路径列出 outputs 顶层所有条目；重组前后的路径映射见 `PATH_MIGRATION_20261018.csv`（S4 后生成）。代码包留在顶层以保持现有导入和记录路径。','',f'B1 两目录关系核验：{b1}；前者保存统计/结果，后者仅有重复的运行脚本，故按公开结果包与私有代码副本并列记录，不判为新旧替代。','', '|单元/条目|当前路径|分类|STATUS|说明/取代关系|','|---|---|---|---|---|']
for n,cat,status,purpose,sup in rows:
 path=f'outputs/{n}'
 lines.append(f'|`{n}`|`{path}`|{cat}|{status.replace("|","/")}|{purpose}。{sup}|' if sup else f'|`{n}`|`{path}`|{cat}|{status.replace("|","/")}|{purpose}。|')
lines+=['','## 需要人工复核的 unclear 项','','']
unclear=[r[0] for r in rows if r[1]=='unclear']
lines += [f'- `{x}`' for x in unclear] if unclear else ['本次初分未产生 unclear 项；此分类由名称规则生成，后续可人工调整。']
(root/'INDEX.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('index_rows',len(rows),'unclear',len(unclear),'b1',b1)

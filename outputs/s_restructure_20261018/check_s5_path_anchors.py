import csv,re
from pathlib import Path
OUT=Path('outputs')
rows=list(csv.DictReader((OUT/'s_restructure_20261018/script_classification.csv').open(encoding='utf-8-sig')))
for r in rows:
 if r['move_decision']!='move_candidate': continue
 p=OUT/r['source']; lines=p.read_text(encoding='utf-8',errors='replace').splitlines()
 anchors=[]
 for i,line in enumerate(lines,1):
  if any(x in line for x in ('__file__','Path.cwd()','os.getcwd()','Path(__file__)','parents[')):
   anchors.append(f'{i}:{line.strip()[:180]}')
 if anchors: print(r['source'],'|','; '.join(anchors[:5]))

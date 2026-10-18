import csv
from pathlib import Path
r=list(csv.DictReader(Path('outputs/s_restructure_20261018/script_classification.csv').open(encoding='utf-8-sig')))
for x in r:
 if x['move_decision']=='move_candidate' and x['own_hardcoded_matches']:
  print(x['source'],'|',x['own_hardcoded_matches'])

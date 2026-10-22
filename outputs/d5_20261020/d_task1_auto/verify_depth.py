"""Recompute aggregate TNAP H5 association; never export private compound rows."""
import collections
import hashlib
import json
import math
from pathlib import Path

source = Path('/driveA/xinrong/agentic-screening/outputs/d3_tnap_20261019/revision_v2_20261019/d3_1_v2_private_20261019/h5_compound_depth_labels.json')
rows = json.loads(source.read_text(encoding='utf-8'))
labels = collections.Counter(str(r['label']) for r in rows)
print('label_counts', dict(labels))
def is_hit(v):
    return str(v).lower() in ('1', 'true', 'hit', 'hit_support', 'active')
pos = [float(r['auxiliary_tid_count_mean']) for r in rows if is_hit(r['label'])]
neg = [float(r['auxiliary_tid_count_mean']) for r in rows if not is_hit(r['label'])]
assert len(pos) == 53 and len(neg) == 409
auc = sum((a > b) + .5*(a == b) for a in pos for b in neg)/(len(pos)*len(neg))
xs = [float(r['auxiliary_tid_count_mean']) for r in rows]
ys = [int(is_hit(r['label'])) for r in rows]
mx, my = sum(xs)/len(xs), sum(ys)/len(ys)
cov = sum((x-mx)*(y-my) for x,y in zip(xs,ys))/len(xs)
sx = math.sqrt(sum((x-mx)**2 for x in xs)/len(xs))
sy = math.sqrt(sum((y-my)**2 for y in ys)/len(ys))
out = {'schema':'d5_tnap_depth_recheck_v1','source_file_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
       'compound_count':len(rows),'hits':len(pos),'measured_nonhits':len(neg),
       'proxy':'auxiliary_tid_count_mean','auc':auc,'point_biserial_r':cov/(sx*sy),
       'private_rows_exported':False,'purpose':'source-quality check; not a campaign feature'}
here = Path(__file__).resolve().parent
(here/'tnap_depth_recheck.json').write_text(json.dumps(out, indent=2)+'\n', encoding='utf-8')
print(json.dumps(out))

"""Print only shape/keys of the existing private H5 depth file, never labels."""
import json
from pathlib import Path

p = Path('/driveA/xinrong/agentic-screening/outputs/d3_tnap_20261019/revision_v2_20261019/d3_1_v2_private_20261019/h5_compound_depth_labels.json')
d = json.loads(p.read_text())
print('top', type(d).__name__, list(d)[:20] if isinstance(d, dict) else 'len=' + str(len(d)))
if isinstance(d, list) and d:
    print('first_type', type(d[0]).__name__, 'first_keys', list(d[0]) if isinstance(d[0], dict) else None)
if isinstance(d, dict):
    for key, value in d.items():
        if isinstance(value, list) and value:
            print('list', key, 'len', len(value), 'first_type', type(value[0]).__name__,
                  'first_keys', list(value[0]) if isinstance(value[0], dict) else None)
        elif isinstance(value, dict):
            print('dict', key, 'keys', list(value)[:20])

"""Known-good regression for the D4 analysis reader's mechanical key fix."""
import json
import statistics
from pathlib import Path

root = Path('/driveA/xinrong/agentic-screening')
d3 = root / 'outputs/d3_tnap_20261019'
aggregate = json.loads((d3 / 'd3_6_report/aggregate.json').read_text())
for arm, expected in [('fixed', 20.35), ('forced_random_coldstart', 25.8)]:
    values = [json.loads((d3 / f'd3_6_runs_private_20261019/{arm}_bit_seed{s}.json').read_text())['summary']['H50']
              for s in range(20)]
    assert statistics.mean(values) == expected
    assert aggregate['arm_stats']['bit'][arm]['mean_H50'] == expected
glm = json.loads((root / 'outputs/d4_tnap_glm_20261019/d4_glm_private_20261019/runs/llm_bit_seed0/run.json').read_text())
run = glm['result']
selected = [key for row in run['trajectory'] for key in row['selection']]
assert len(selected) == len(set(selected)) == 50
assert sum(x['outcome'] for row in run['trajectory'] for x in row['observations']) == run['hits_at_budget'] == 23
print('Tier A known-good regression PASS: D3 20.35/25.80 and GLM bit seed0 H50=23')

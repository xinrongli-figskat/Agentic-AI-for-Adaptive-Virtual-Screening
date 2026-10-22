"""Rerun statistics in memory, compare existing JSON, never overwrite results."""
import contextlib
import hashlib
import importlib.util
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('s2s3_reanalysis', BASE / 'reanalyze_v2.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
names = ['s2_gate_reanalysis.json', 'adaptive_gap_descriptive.json', 'variance_estimate_audit.json']
before = {name: module.sha(BASE / name) for name in names}
captured = {}
def compare(name, result):
    old = json.loads((BASE / name).read_text(encoding='utf-8'))
    assert old.pop('utc') > json.loads((BASE / 'execution_lock_v2.json').read_text())['utc']
    result.pop('utc')
    assert old == result, name
    captured[name] = True
module.save = compare
sys.argv = [str(BASE / 'reanalyze_v2.py')]
with contextlib.redirect_stdout(io.StringIO()):
    module.main()
assert set(captured) == set(names)
assert before == {name: module.sha(BASE / name) for name in names}
result = {'utc': datetime.now(timezone.utc).isoformat(), 'full_reanalysis_exact_except_utc': captured,
          'saved_outputs_unchanged': before, 'all_result_times_after_lock': True,
          'glm_calls': 0, 'new_campaigns': 0}
target = BASE / 'reproduction_verification.json'
assert not target.exists()
target.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
print(json.dumps(result))

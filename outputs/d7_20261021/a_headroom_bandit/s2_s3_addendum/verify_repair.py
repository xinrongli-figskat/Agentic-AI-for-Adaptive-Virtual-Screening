"""Mechanical parser regression and frozen D5 known-good data verification."""
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
sys.path.insert(0, str(ROOT))
from outputs.d7_20261021.a_headroom_bandit.revision_11field.run_cpu import source_checks, sha, utc

original = (BASE / 'reanalyze.py').read_text(encoding='utf-8')
repaired = (BASE / 'reanalyze_v2.py').read_text(encoding='utf-8')
expected = original.replace("'execution_lock.json'", "'execution_lock_v2.json'")
expected = expected.replace(",line)]", ",line.replace('\\u2212','-'))]")
assert repaired == expected, 'Unexpected scientific-code changes'
source = (ROOT / 'outputs/d_discrimination_20261018/d1_summary.md').read_text(encoding='utf-8')
line = next(s for s in source.splitlines() if s.startswith('| **`fixed − label_shuffle`'))
bad = [float(v) for v in re.findall(r'[-+]?\d+(?:\.\d+)?', line)]
good = [float(v) for v in re.findall(r'[-+]?\d+(?:\.\d+)?', line.replace('\u2212', '-'))]
assert bad == [2.15, .95, 4.9, 2.95, .7, 5.3]
assert good == [2.15, -.95, 4.9, 2.95, .7, 5.3]
result = {'utc': utc(), 'mechanical_patch_only': True,
          'original_script_sha256': sha(BASE / 'reanalyze.py'),
          'repaired_script_sha256': sha(BASE / 'reanalyze_v2.py'),
          'original_parser_output': bad, 'repaired_parser_output': good,
          'frozen_D5_known_good': source_checks(), 'glm_calls': 0, 'new_campaigns': 0}
path = BASE / 'mechanical_repair_regression.json'
assert not path.exists()
path.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
print(json.dumps(result))

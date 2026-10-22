"""D7-B repeat runner; imports the frozen D5 experiment without modifying it."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

ROOT = Path('/driveA/xinrong/agentic-screening')
sys.path.insert(0, str(ROOT))
BASE = ROOT / 'outputs/d7_20261021/b_model_variance'
PRIVATE = ROOT / 'outputs/d7_20261021/b_model_variance_private'
D6 = ROOT / 'outputs/d6_20261020/b_menu_description_private/runs_v0_replay/runs/tnap/bit'
D5 = ROOT / 'outputs/d5_20261020/e_menu_private/runs/tnap/bit'
EXPECTED_D5 = [26,32,31,23,28,24,25,16,25,31,11,29,25,25,24,24,28,25,25,19]
EXPECTED_FIXED = {
    'knn_greedy': 20.35, 'knn_diverse': 18.45,
    'uniform_random': 6.00, 'persistent_random_until_first_hit': 25.80,
    'diverse_random_coldstart': 24.05, 'logreg_greedy': 25.80,
    'ens_one_step_proxy': 25.80,
}


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    tmp.replace(path)
    if 'private' in str(path):
        os.chmod(path, 0o600)


def run_path(root, seed):
    return root / 'runs' / 'tnap' / 'bit' / f'glm_extended_seed{seed}' / 'run.json'


def inspect_run(path, seed):
    row = json.loads(Path(path).read_text())
    assert row['complete'] and row['seed'] == seed and row['representation'] == 'bit'
    assert row['arm'] == 'glm_extended' and row['pool'] == 'tnap'
    assert len(row['trajectory']) == 5 and row['queried_count'] == 50
    assert row['glm_calls'] == 4
    observations = [r for step in row['trajectory'] for r in step['observations']]
    assert len(observations) == len({r['compound_key'] for r in observations}) == 50
    assert row['H50'] == sum(r['outcome'] for r in observations)
    calls = [step['glm_call'] for step in row['trajectory'][1:]]
    assert all(c and c['request_id'] and c['usage'] and c['raw_response'] for c in calls)
    return row


def baseline():
    from outputs.d5_20261020.e_menu import run_extended as frozen
    frozen.validate_sources()
    d5 = [inspect_run(D5 / f'glm_extended_seed{s}' / 'run.json', s)
          for s in range(20)]
    assert [r['H50'] for r in d5] == EXPECTED_D5
    fixed = {}
    for arm, expected in EXPECTED_FIXED.items():
        vals = [inspect_cpu(D5 / f'fixed_{arm}_seed{s}' / 'run.json', s)
                for s in range(20)]
        fixed[arm] = sum(vals)/20
        assert round(fixed[arm], 2) == expected, (arm, fixed[arm], expected)
    d6 = [inspect_run(D6 / f'glm_extended_seed{s}' / 'run.json', s)
          for s in range(10)]
    return d5, d6, fixed


def inspect_cpu(path, seed):
    row = json.loads(Path(path).read_text())
    assert row['complete'] and row['seed'] == seed and row['glm_calls'] == 0
    return row['H50']


def lock():
    d5, d6, fixed = baseline()
    files = {
        str((BASE / 'B_SPEC.md').relative_to(ROOT)): sha(BASE / 'B_SPEC.md'),
        str((BASE / 'b_repeat.py').relative_to(ROOT)): sha(BASE / 'b_repeat.py'),
        'outputs/d5_20261020/e_menu_code_lock.json': sha(ROOT / 'outputs/d5_20261020/e_menu_code_lock.json'),
        'outputs/d3_tnap_20261019/freeze_tnap_v1/freeze_receipt.json': sha(ROOT / 'outputs/d3_tnap_20261019/freeze_tnap_v1/freeze_receipt.json'),
    }
    for seed in range(20):
        p = D5 / f'glm_extended_seed{seed}' / 'run.json'
        files[str(p.relative_to(ROOT))] = sha(p)
    for seed in range(10):
        p = D6 / f'glm_extended_seed{seed}' / 'run.json'
        files[str(p.relative_to(ROOT))] = sha(p)
    save(BASE / 'B_LOCK.json', {
        'utc': utc(), 'post_exposure': True, 'files': files,
        'd5_glm_h50': [r['H50'] for r in d5],
        'd6_replay_h50': [r['H50'] for r in d6],
        'd5_fixed_means': fixed,
        'max_new_model_decisions': 360,
    })
    return {'status': 'locked_no_network', 'file_count': len(files),
            'lock_sha256': sha(BASE / 'B_LOCK.json'), 'utc': utc()}


def verify_lock():
    lock_data = json.loads((BASE / 'B_LOCK.json').read_text())
    for relative, expected in lock_data['files'].items():
        assert sha(ROOT / relative) == expected, relative
    baseline()
    return lock_data


class TrackedClient:
    """Use the unchanged official client with an instrumented urllib opener."""
    def __init__(self, receipt_dir):
        from campaign_v0.glm_api import OfficialGLMDecisionClient
        self.receipt_dir = Path(receipt_dir)
        self.receipt_dir.mkdir(parents=True, exist_ok=True)
        self.http_idx = len(list(self.receipt_dir.glob('http_*.json')))
        self.decision_idx = len(list(self.receipt_dir.glob('decision_*.json')))
        self.inner = OfficialGLMDecisionClient(model_name='glm-5.3-flash',
                                               opener=self._opener)
        self.last_usage = None
        self.last_request_id = None
        self.last_attempt_log = []

    def _opener(self, request, timeout):
        started = time.perf_counter()
        self.http_idx += 1
        target = self.receipt_dir / f'http_{self.http_idx:03d}.json'
        try:
            with urlopen(request, timeout=timeout) as response:
                data = response.read()
                status = response.status
            raw = data.decode('utf-8')
            assert self.inner._api_key not in raw
            save(target, {'utc': utc(), 'http_status': status, 'raw_provider_response': raw,
                          'elapsed_seconds': time.perf_counter()-started})
            return io.BytesIO(data)
        except HTTPError as exc:
            data = exc.read()
            raw = data.decode('utf-8', errors='replace')
            assert self.inner._api_key not in raw
            save(target, {'utc': utc(), 'http_status': exc.code, 'raw_provider_response': raw,
                          'elapsed_seconds': time.perf_counter()-started})
            raise HTTPError(exc.url, exc.code, exc.msg, exc.hdrs, io.BytesIO(data)) from exc
        except Exception as exc:
            save(target, {'utc': utc(), 'http_status': None,
                          'error_type': type(exc).__name__, 'error': str(exc),
                          'elapsed_seconds': time.perf_counter()-started})
            raise

    def __call__(self, summary):
        all_decisions = list(PRIVATE.glob('rep*/seed*/decision_*.json'))
        if len(all_decisions) >= 360:
            raise RuntimeError('D7-B hard budget 360 model decisions reached')
        self.decision_idx += 1
        target = self.receipt_dir / f'decision_{self.decision_idx:03d}.json'
        started = time.perf_counter()
        first_http = self.http_idx + 1
        try:
            content = self.inner(summary)
            self.last_usage = self.inner.last_usage
            self.last_request_id = self.inner.last_request_id
            self.last_attempt_log = self.inner.last_attempt_log
            save(target, {'utc': utc(), 'status': 'success',
                          'request_id': self.last_request_id, 'usage': self.last_usage,
                          'raw_content': content, 'http_attempts': list(range(first_http, self.http_idx+1)),
                          'api_attempt_log': self.last_attempt_log,
                          'elapsed_seconds': time.perf_counter()-started})
            return content
        except Exception as exc:
            self.last_usage = self.inner.last_usage
            self.last_request_id = self.inner.last_request_id
            self.last_attempt_log = self.inner.last_attempt_log
            save(target, {'utc': utc(), 'status': 'failure',
                          'request_id': self.last_request_id, 'usage': self.last_usage,
                          'error_type': type(exc).__name__, 'error': str(exc),
                          'http_attempts': list(range(first_http, self.http_idx+1)),
                          'api_attempt_log': self.last_attempt_log,
                          'elapsed_seconds': time.perf_counter()-started})
            raise


def run(seed, rep):
    verify_lock()
    assert 0 <= seed < 20 and 1 <= rep <= 5
    if rep == 1 and seed < 10:
        path = D6 / f'glm_extended_seed{seed}' / 'run.json'
        row = inspect_run(path, seed)
        return {'seed': seed, 'rep': rep, 'existing_d6': True, 'H50': row['H50'],
                'new_model_decisions': 0}
    from outputs.d5_20261020.e_menu import run_extended as frozen
    frozen.PRIVATE_OUT = PRIVATE / f'rep{rep}'
    client = TrackedClient(PRIVATE / f'rep{rep}' / f'seed{seed}')
    result = frozen.run_one('tnap', 'bit', seed, 'glm_extended', client=client)
    row = inspect_run(run_path(frozen.PRIVATE_OUT, seed), seed)
    assert result['H50'] == row['H50']
    return {'seed': seed, 'rep': rep, 'existing_d6': False,
            'H50': row['H50'], 'new_model_decisions': len(list(client.receipt_dir.glob('decision_*.json'))),
            'new_http_attempts': len(list(client.receipt_dir.glob('http_*.json')))}


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('lock')
    q = sub.add_parser('run')
    q.add_argument('--seed', type=int, required=True)
    q.add_argument('--rep', type=int, required=True)
    sub.add_parser('status')
    a = p.parse_args()
    if a.command == 'lock':
        result = lock()
    elif a.command == 'run':
        result = run(a.seed, a.rep)
    else:
        lock_data = verify_lock()
        complete = []
        for seed in range(20):
            for rep in range(1, 6):
                path = (D6 / f'glm_extended_seed{seed}' / 'run.json' if seed < 10 and rep == 1
                        else run_path(PRIVATE / f'rep{rep}', seed))
                if path.exists() and json.loads(path.read_text()).get('complete'):
                    complete.append([seed, rep])
        result = {'complete_repeats': len(complete), 'new_decision_receipts':
                  len(list(PRIVATE.glob('rep*/seed*/decision_*.json'))),
                  'new_http_receipts': len(list(PRIVATE.glob('rep*/seed*/http_*.json'))),
                  'lock_sha256': sha(BASE / 'B_LOCK.json')}
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()

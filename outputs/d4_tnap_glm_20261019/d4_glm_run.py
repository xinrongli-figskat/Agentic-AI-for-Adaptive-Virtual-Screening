"""D4 TNAP GLM arm with byte-identical v1 policy tools and crash-safe checkpoints.

Only public state is passed to the frozen LLM controller. Oracle labels and
revealed observations remain in a private result directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

ROOT = Path('/driveA/xinrong/agentic-screening')
sys.path.insert(0, str(ROOT))
from campaign_v0.campaign_core import run_campaign
from campaign_v0.glm_api import GLMAPIError, OfficialGLMDecisionClient
from campaign_v0.llm_controller import ToolChoiceLLMController
from oracle_boundary_v0.oracle_boundary import BatchOracle, read_jsonl

BASE = ROOT / 'outputs/d4_tnap_glm_20261019'
FREEZE = ROOT / 'outputs/d3_tnap_20261019/freeze_tnap_v1'
PRIVATE_LABELS = ROOT / 'outputs/d3_tnap_20261019/freeze_tnap_v1_private_labels/oracle_labels.jsonl'
OUT = BASE / 'd4_glm_private_20261019'
RECEIPT_SHA = 'f8801efbe28f73ddbcf9c5a2d493d862cbf124f311b6659e9224f2161b5bf662'
PROTOCOL_SHA = '8384797c0348b51e0b0bb2547b77520b36981d81af4b1320be4e6adb49b17943'
V1_MANIFEST_SHA = '3866c7bfc99e92b8e0d6f92b98955d5e68a7ae202f609eac90d0e7a201f98235'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    with temp.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, sort_keys=True)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    temp.replace(path)
    os.chmod(path, 0o600)


def protected_check():
    lock = json.loads((BASE / 'pre_real_declarations_lock.json').read_text(encoding='utf-8-sig'))
    assert lock['before_first_real_glm_call']
    for row in lock['files']:
        assert sha(BASE / row['path']) == row['sha256']
    parity = json.loads((BASE / 'prompt_config_parity.json').read_text())
    assert parity['prompt_config_identical']
    assert sha(ROOT / 'data/curation_private/frozen_dyrk3_v1/manifest.json') == V1_MANIFEST_SHA
    manifest = json.loads((ROOT / 'data/curation_private/frozen_dyrk3_v1/manifest.json').read_text())
    for name in ('campaign_core.py', 'glm_api.py', 'llm_controller.py', 'numerical_tools.py'):
        path = ROOT / 'campaign_v0' / name
        assert sha(path) == manifest['source_sha256'][str(path)]
    assert sha(FREEZE / 'freeze_receipt.json') == RECEIPT_SHA
    assert sha(ROOT / 'outputs/d3_tnap_20261019/tnap_v1_campaign_protocol.md') == PROTOCOL_SHA
    frozen = json.loads((BASE / 'frozen_integrity_preflight.json').read_text())
    for path, expected in frozen['protected_file_hashes'].items():
        assert sha(path) == expected, path
    probe = json.loads((BASE / 'synthetic_probe.json').read_text())
    assert probe['request_succeeded'] and probe['uses_real_labels'] is False
    assert probe['model'] == 'glm-5.3-flash' and probe['request_id']
    return {name: sha(BASE / name) for name in ('pre_real_declarations_lock.json',
                                                'prompt_config_parity.json',
                                                'frozen_integrity_preflight.json',
                                                'synthetic_probe.json')}


class JournalledController:
    name = 'llm_policy_choice'

    def __init__(self, pending_path):
        self.pending_path = pending_path
        self.attempt_timings = []
        self.retry_wait_seconds = []

        def timed_opener(request, timeout):
            started = time.perf_counter()
            try:
                response = urlopen(request, timeout=timeout)
            except Exception as exc:
                self.attempt_timings.append({'seconds': time.perf_counter() - started,
                                             'http_status': exc.code if isinstance(exc, HTTPError) else None,
                                             'error_type': type(exc).__name__})
                raise
            timing_log = self.attempt_timings

            class TimedResponse:
                def __enter__(self):
                    response.__enter__()
                    return self

                def read(self):
                    try:
                        return response.read()
                    finally:
                        timing_log.append({'seconds': time.perf_counter() - started,
                                           'http_status': getattr(response, 'status', 200),
                                           'error_type': None})

                def __exit__(self, *args):
                    return response.__exit__(*args)

            return TimedResponse()

        def timed_sleep(seconds):
            started = time.perf_counter()
            time.sleep(seconds)
            self.retry_wait_seconds.append(time.perf_counter() - started)

        self.client = OfficialGLMDecisionClient(model_name='glm-5.3-flash',
                                                 opener=timed_opener, sleeper=timed_sleep)
        self.base = ToolChoiceLLMController(self.client, model_name='glm-5.3-flash')
        self.decision_log = []

    def choose(self, state, allowed):
        marker = {'round': state['next_round'],
                  'revealed_compounds': [r['compound_key'] for r in state['revealed']],
                  'revealed_outcomes': [r['outcome'] for r in state['revealed']]}
        state_sha = hashlib.sha256(json.dumps(marker, sort_keys=True).encode()).hexdigest()
        if self.pending_path.exists():
            pending = json.loads(self.pending_path.read_text())
            assert pending['state_sha256'] == state_sha
            assert pending['decision']['policy'] in allowed
            self.decision_log.append(pending['llm_call'])
            return pending['decision']
        self.attempt_timings = []
        self.retry_wait_seconds = []
        try:
            decision = self.base.choose(state, allowed)
        except Exception as exc:
            events_path = self.pending_path.parent / 'failed_decision_events.json'
            events = json.loads(events_path.read_text()) if events_path.exists() else []
            events.append({'utc': utc(), 'state_sha256': state_sha,
                           'error_type': type(exc).__name__,
                           'public_api_diagnostic': exc.public_diagnostic() if isinstance(exc, GLMAPIError) else None,
                           'api_attempt_log': self.client.last_attempt_log,
                           'api_attempt_timings': self.attempt_timings,
                           'retry_wait_seconds': self.retry_wait_seconds,
                           'request_id': self.client.last_request_id,
                           'returned_usage': self.client.last_usage,
                           'decision_seconds': getattr(exc, 'decision_seconds', None)})
            atomic_json(events_path, events)
            raise
        call = dict(self.base.decision_log[-1])
        call['api_attempt_timings'] = list(self.attempt_timings)
        call['retry_wait_seconds'] = list(self.retry_wait_seconds)
        atomic_json(self.pending_path, {'utc': utc(), 'state_sha256': state_sha,
                                        'decision': decision, 'llm_call': call})
        self.decision_log.append(call)
        return decision


def initialize_out(preflight_hashes):
    if OUT.exists():
        return
    OUT.mkdir(parents=True, mode=0o700)
    os.chmod(OUT, 0o700)
    (OUT / 'runs').mkdir(mode=0o700)
    (OUT / 'STATUS').write_text('in_progress\n')
    (OUT / 'RUN_LOG.md').write_text(
        f'# D4 TNAP GLM arm\n\nFirst real-call run started UTC: {utc()}\n'
        f'Preflight hashes: {json.dumps(preflight_hashes, sort_keys=True)}\n'
        '40 runs, 160 policy decisions, same v1 model and policy modules. '
        'No forced fallback. Checkpoint before each oracle query.\n')


def manifest():
    entries = []
    for path in sorted(OUT.rglob('*')):
        if path.is_file() and path.name != 'MANIFEST.json':
            entries.append({'path': path.relative_to(OUT).as_posix(),
                            'bytes': path.stat().st_size, 'sha256': sha(path)})
    atomic_json(OUT / 'MANIFEST.json', {'files': entries, 'self_excluded': True})


def run_one(seed, rep, preflight_hashes):
    assert seed in range(20) and rep in ('bit', 'count')
    run_dir = OUT / 'runs' / f'llm_{rep}_seed{seed}'
    run_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(run_dir, 0o700)
    run_path, pending_path = run_dir / 'run.json', run_dir / 'pending_decision.json'
    identity = {'freeze_receipt_sha256': RECEIPT_SHA, 'preflight_hashes': preflight_hashes,
                'seed': seed, 'representation': rep, 'controller': 'llm_policy_choice'}
    if run_path.exists():
        saved = json.loads(run_path.read_text())
        assert all(saved[k] == value for k, value in identity.items())
        if saved['status'] == 'complete':
            assert not pending_path.exists()
            return saved['result']
        trajectory = saved['trajectory']
        prior_feature_seconds = saved['feature_build_seconds']
    else:
        trajectory, prior_feature_seconds = [], 0.0
    assert len(trajectory) <= 4
    if pending_path.exists():
        pending = json.loads(pending_path.read_text())
        assert pending['llm_call']['api_request_id'] and pending['decision']['policy'] in (
            'knn_greedy', 'knn_diverse', 'uniform_random')
    candidates = read_jsonl(FREEZE / 'public/candidates.jsonl')
    private = read_jsonl(PRIVATE_LABELS)
    labels = {row['compound_key']: row['outcome'] for row in private}
    assert len(candidates) == len(labels) == 462 and sum(labels.values()) == 53
    oracle = BatchOracle(candidates, labels, seed=seed, total_budget=50,
                         initialization_queries=10, batch_size=10)
    controller = JournalledController(pending_path)

    def checkpoint(rows, feature_seconds):
        atomic_json(run_path, {**identity, 'status': 'in_progress', 'trajectory': rows,
                               'feature_build_seconds': feature_seconds, 'updated_utc': utc()})
        if pending_path.exists():
            pending_path.unlink()

    try:
        result = run_campaign(candidates, oracle, controller, seed=seed,
                              representation=rep, existing_trajectory=trajectory,
                              on_checkpoint=checkpoint, prior_feature_seconds=prior_feature_seconds)
    except Exception as exc:
        events_path = run_dir / 'failure_events.json'
        events = json.loads(events_path.read_text()) if events_path.exists() else []
        events.append({'utc': utc(), 'error_type': type(exc).__name__,
                       'completed_batches': len(json.loads(run_path.read_text())['trajectory']) if run_path.exists() else 0,
                       'pending_successful_decision': pending_path.exists(),
                       'public_api_diagnostic': exc.public_diagnostic() if isinstance(exc, GLMAPIError) else None})
        atomic_json(events_path, events)
        raise
    assert result['queried_count'] == 50 and len(result['trajectory']) == 5
    selections = [key for row in result['trajectory'] for key in row['selection']]
    assert len(selections) == len(set(selections)) == 50
    assert sum(labels[key] for key in selections) == result['hits_at_budget']
    assert all(row['llm_call']['decision']['policy'] == row['decision']['policy']
               for row in result['trajectory'][1:])
    atomic_json(run_path, {**identity, 'status': 'complete', 'result': result, 'updated_utc': utc()})
    assert not pending_path.exists()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--representation', choices=('bit', 'count'), required=True)
    parser.add_argument('--seed-start', type=int, required=True)
    parser.add_argument('--seed-stop', type=int, required=True)
    args = parser.parse_args()
    assert 0 <= args.seed_start < args.seed_stop <= 20
    preflight_hashes = protected_check()
    if not os.environ.get('ZAI_API_KEY'):
        raise ValueError('ZAI_API_KEY is not set')
    initialize_out(preflight_hashes)
    for seed in range(args.seed_start, args.seed_stop):
        result = run_one(seed, args.representation, preflight_hashes)
        print(json.dumps({'representation': args.representation, 'seed': seed,
                          'hits_at_budget': result['hits_at_budget'], 'status': 'complete'}), flush=True)
    manifest()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        if OUT.exists():
            (OUT / 'STATUS').write_text('paused_failure\n')
            manifest()
        raise

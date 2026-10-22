"""Verify all TNAP GLM runs and lock the post-hoc policy proportions."""
from __future__ import annotations

import hashlib
import json
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/driveA/xinrong/agentic-screening')
BASE = ROOT / 'outputs/d4_tnap_glm_20261019'
PRIVATE = BASE / 'd4_glm_private_20261019'
D3_RUNS = ROOT / 'outputs/d3_tnap_20261019/d3_6_runs_private_20261019'
POLICIES = ('knn_greedy', 'knn_diverse', 'uniform_random')
ZERO = (5, 6, 15, 17, 18, 19)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, value):
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + '\n', encoding='utf-8')


def main():
    assert (BASE / 'd4_floor_lock.json').exists()
    assert (BASE / 'pre_real_declarations_lock.json').exists()
    assert not (BASE / 'matched_proportion_spec.json').exists()
    assert (PRIVATE / 'STATUS').read_text().strip() == 'in_progress'
    from d4_glm_run import protected_check
    protected_check()
    counts = {}
    first = {}
    costs = {'successful_decisions': 0, 'http_attempts': 0, 'failed_http_attempts': 0,
             'prompt_tokens_returned': 0, 'completion_tokens_returned': 0,
             'reasoning_tokens_returned': 0, 'missing_usage_decisions': 0,
             'decision_seconds': 0.0, 'retry_wait_seconds': 0.0,
             'feature_build_seconds': 0.0, 'analysis_seconds': 0.0,
             'selection_seconds': 0.0, 'failure_events': 0}
    run_hashes = {}
    for rep in ('bit', 'count'):
        counts[rep] = Counter()
        first[rep] = {}
        for seed in range(20):
            path = PRIVATE / f'runs/llm_{rep}_seed{seed}/run.json'
            saved = json.loads(path.read_text())
            run_hashes[f'{rep}_seed{seed}'] = sha(path)
            assert saved['status'] == 'complete' and saved['seed'] == seed and saved['representation'] == rep
            run = saved['result']
            assert run['queried_count'] == 50 and len(run['trajectory']) == 5
            selections = [key for step in run['trajectory'] for key in step['selection']]
            assert len(set(selections)) == len(selections) == 50
            assert sum(obs['outcome'] for step in run['trajectory'] for obs in step['observations']) == run['hits_at_budget']
            old = json.loads((D3_RUNS / f'fixed_{rep}_seed{seed}.json').read_text())
            assert old['result']['trajectory'][0]['selection'] == run['trajectory'][0]['selection']
            assert old['result']['trajectory'][0]['observations'] == run['trajectory'][0]['observations']
            for step in run['trajectory'][1:]:
                decision, call = step['decision'], step['llm_call']
                assert decision['policy'] == call['decision']['policy'] and call['model'] == 'glm-5.3-flash'
                assert call['api_request_id'] and call['api_attempt_log']
                counts[rep][decision['policy']] += 1
                costs['successful_decisions'] += 1
                costs['http_attempts'] += len(call['api_attempt_log'])
                costs['failed_http_attempts'] += sum(x.get('http_status') != 200 for x in call['api_attempt_log'])
                assert len(call['api_attempt_timings']) == len(call['api_attempt_log'])
                costs['retry_wait_seconds'] += sum(call.get('retry_wait_seconds') or [])
                usage = call.get('api_usage')
                if usage:
                    costs['prompt_tokens_returned'] += usage.get('prompt_tokens', 0)
                    costs['completion_tokens_returned'] += usage.get('completion_tokens', 0)
                    costs['reasoning_tokens_returned'] += (usage.get('completion_tokens_details') or {}).get('reasoning_tokens', 0)
                else:
                    costs['missing_usage_decisions'] += 1
                costs['decision_seconds'] += call['decision_seconds']
            costs['feature_build_seconds'] += run['feature_build_seconds']
            costs['analysis_seconds'] += run['analysis_seconds_total']
            costs['selection_seconds'] += run['selection_seconds_total']
            events_path = path.parent / 'failure_events.json'
            if events_path.exists():
                costs['failure_events'] += len(json.loads(events_path.read_text()))
            if seed in ZERO:
                assert run['trajectory'][0]['cumulative_hits'] == 0
                first[rep][str(seed)] = {'policy': run['trajectory'][1]['decision']['policy'],
                                         'H50': run['hits_at_budget']}
        assert sum(counts[rep].values()) == 80
    assert costs['successful_decisions'] == 160
    lock = json.loads((BASE / 'pre_real_declarations_lock.json').read_text(encoding='utf-8-sig'))
    first_real = (PRIVATE / 'RUN_LOG.md').read_text().split('First real-call run started UTC: ')[1].splitlines()[0]
    assert lock['locked_utc'] < first_real
    spec = {'schema': 'tnap_d4_posthoc_matched_proportion_v1',
            'locked_utc': datetime.now(timezone.utc).isoformat(),
            'posthoc': True, 'source_glm_run_hashes': run_hashes,
            'representations': {
                rep: {'policy_counts': dict(counts[rep]),
                      'policy_fractions': {policy: counts[rep][policy] / 80 for policy in POLICIES}}
                for rep in ('bit', 'count')},
            'sampling': 'For each representation, seed 0..20 and feedback round 1..4, '
                        'interpret SHA256(f"mp|{seed}|{round}") as a 256-bit integer divided by 2**256. '
                        'Walk policies in this fixed order: knn_greedy, knn_diverse, uniform_random; '
                        'select the first cumulative GLM fraction exceeding that number. '
                        'No LLM, no label-conditioned proportion and no forced fallback.',
            'pairing_note': 'Seed 20 is descriptive only; comparisons to GLM pair seeds 0..19.',
            'pre_registered_arm': False}
    write_new(BASE / 'matched_proportion_spec.json', spec)
    write_new(BASE / 'post_glm_verification.json', {
        'status': 'pass', 'checked_utc': datetime.now(timezone.utc).isoformat(),
        'run_count': 40, 'cost': costs, 'zero_hit_first_decisions': first,
        'policy_counts': {rep: dict(counts[rep]) for rep in ('bit', 'count')},
        'run_hashes': run_hashes, 'first_real_call_utc': first_real,
        'declarations_lock_utc': lock['locked_utc']})
    print(json.dumps({'status': 'pass', 'cost': costs, 'policy_counts': {rep: dict(counts[rep]) for rep in counts},
                      'zero_hit_first_decisions': first, 'matched_spec_sha256': sha(BASE / 'matched_proportion_spec.json')},
                     ensure_ascii=False))


if __name__ == '__main__':
    main()

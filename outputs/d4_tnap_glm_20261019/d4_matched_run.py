"""Post-hoc TNAP policy-proportion comparator; no GLM calls."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path('/driveA/xinrong/agentic-screening')
sys.path.insert(0, str(ROOT))
from campaign_v0.campaign_core import run_campaign
from oracle_boundary_v0.oracle_boundary import BatchOracle, read_jsonl

BASE = ROOT / 'outputs/d4_tnap_glm_20261019'
SPEC = BASE / 'matched_proportion_spec.json'
OUT = BASE / 'd4_matched_private_20261019'
EXPECTED_SPEC_SHA = 'ded39cbe4b93bcdb0805909bb2a9a3d13951afcf976276dbd5f21557530c0858'
POLICIES = ('knn_greedy', 'knn_diverse', 'uniform_random')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, value):
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + '\n', encoding='utf-8')
    os.chmod(path, 0o600)


class MatchedController:
    name = 'matched_proportion_tnap_posthoc'

    def __init__(self, fractions, seed):
        self.fractions = fractions
        self.seed = seed
        self.decisions = []

    def choose(self, state, allowed):
        assert tuple(allowed) == POLICIES
        round_number = state['next_round']
        digest = hashlib.sha256(f'mp|{self.seed}|{round_number}'.encode()).digest()
        draw = int.from_bytes(digest, 'big') / 2**256
        running = 0.0
        policy = POLICIES[-1]
        for name in POLICIES:
            running += self.fractions[name]
            if draw < running:
                policy = name
                break
        self.decisions.append({'round': round_number, 'draw': draw, 'policy': policy})
        return {'policy': policy, 'reason': 'Post-hoc hash draw from locked GLM policy proportions'}


def main():
    assert sha(SPEC) == EXPECTED_SPEC_SHA
    spec = json.loads(SPEC.read_text())
    assert spec['posthoc'] and not spec['pre_registered_arm']
    for key, expected in spec['source_glm_run_hashes'].items():
        assert sha(BASE / f'd4_glm_private_20261019/runs/llm_{key.replace("_seed", "_seed")}/run.json') == expected
    assert not OUT.exists(), 'Matched output already exists; do not overwrite'
    OUT.mkdir(parents=True, mode=0o700)
    os.chmod(OUT, 0o700)
    candidates = read_jsonl(ROOT / 'outputs/d3_tnap_20261019/freeze_tnap_v1/public/candidates.jsonl')
    private = read_jsonl(ROOT / 'outputs/d3_tnap_20261019/freeze_tnap_v1_private_labels/oracle_labels.jsonl')
    labels = {r['compound_key']: r['outcome'] for r in private}
    assert len(candidates) == len(labels) == 462 and sum(labels.values()) == 53
    rows = []
    for rep in ('bit', 'count'):
        fractions = spec['representations'][rep]['policy_fractions']
        assert abs(sum(fractions.values()) - 1) < 1e-12
        for seed in range(21):
            oracle = BatchOracle(candidates, labels, seed=seed, total_budget=50,
                                 initialization_queries=10, batch_size=10)
            controller = MatchedController(fractions, seed)
            result = run_campaign(candidates, oracle, controller, seed=seed, representation=rep)
            selections = [key for step in result['trajectory'] for key in step['selection']]
            assert len(selections) == len(set(selections)) == 50
            assert result['hits_at_budget'] == sum(labels[key] for key in selections)
            assert len(controller.decisions) == 4
            if seed < 20:
                glm = json.loads((BASE / f'd4_glm_private_20261019/runs/llm_{rep}_seed{seed}/run.json').read_text())
                assert glm['result']['trajectory'][0]['selection'] == result['trajectory'][0]['selection']
            write_new(OUT / f'matched_{rep}_seed{seed}.json', {
                'posthoc': True, 'spec_sha256': EXPECTED_SPEC_SHA, 'seed': seed,
                'representation': rep, 'paired_main_analysis': seed < 20,
                'decisions': controller.decisions, 'result': result})
            rows.append({'representation': rep, 'seed': seed, 'H50': result['hits_at_budget']})
        print(json.dumps({'representation': rep, 'runs': 21}), flush=True)
    write_new(OUT / 'summary.json', {'posthoc': True, 'runs': len(rows), 'rows': rows,
                                     'spec_sha256': EXPECTED_SPEC_SHA})
    (OUT / 'STATUS').write_text('done\n')
    print(json.dumps({'status': 'done', 'runs': len(rows), 'spec_sha256': EXPECTED_SPEC_SHA}))


if __name__ == '__main__':
    main()

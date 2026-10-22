"""D4 paired, stratified TNAP analysis; reads frozen results without new queries."""
from __future__ import annotations

import hashlib
import json
import random
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from scipy.stats import fisher_exact

ROOT = Path('/driveA/xinrong/agentic-screening')
BASE = ROOT / 'outputs/d4_tnap_glm_20261019'
GLM = BASE / 'd4_glm_private_20261019'
MATCHED = BASE / 'd4_matched_private_20261019'
D3 = ROOT / 'outputs/d3_tnap_20261019'
OUT = BASE / 'attempt2_20261019/d4_analysis_private_20261019'
ZERO = (5, 6, 15, 17, 18, 19)
ARMS = ('forced_random_coldstart', 'structure_prior', 'label_shuffle',
        'fixed', 'matched_proportion_tnap', 'random')
EXPECTED_SPEC = 'ded39cbe4b93bcdb0805909bb2a9a3d13951afcf976276dbd5f21557530c0858'
EXPECTED_CURATION = 'db688a4a9814d9fb2dd7238a39075ee41f72d1da7c3ba4934ec8835bd2285c73'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + '\n', encoding='utf-8')


def paired(values):
    assert len(values) >= 2
    rng = random.Random(20261018)
    draws = sorted(statistics.mean(rng.choice(values) for _ in values) for _ in range(10000))
    return {'n': len(values), 'mean': statistics.mean(values),
            'ci_low': draws[249], 'ci_high': draws[9750],
            'sd': statistics.stdev(values), 'individual_differences': values}


def first_hit(selected, labels):
    return next((i for i, key in enumerate(selected, 1) if labels[key] == 1), None)


def curve_auc(curve):
    assert len(curve) == 5
    return sum((curve[i] + curve[i + 1]) / 2 for i in range(4)) / 4


def load():
    verification = json.loads((BASE / 'post_glm_verification.json').read_text())
    assert verification['status'] == 'pass' and verification['cost']['successful_decisions'] == 160
    assert sha(BASE / 'matched_proportion_spec.json') == EXPECTED_SPEC
    assert (MATCHED / 'STATUS').read_text().strip() == 'done'
    private_path = D3 / 'freeze_tnap_v1_private_labels/oracle_labels.jsonl'
    labels = {r['compound_key']: r['outcome'] for r in (json.loads(line) for line in private_path.read_text().splitlines())}
    assert len(labels) == 462 and sum(labels.values()) == 53
    runs, provenance = {}, {}
    for rep in ('bit', 'count'):
        for seed in range(20):
            glm_path = GLM / f'runs/llm_{rep}_seed{seed}/run.json'
            assert sha(glm_path) == verification['run_hashes'][f'{rep}_seed{seed}']
            saved = json.loads(glm_path.read_text())
            run = saved['result']
            selected = [key for step in run['trajectory'] for key in step['selection']]
            runs[rep, 'GLM', seed] = {'H50': run['hits_at_budget'],
                                      'curve': run['hit_recovery_checkpoints'],
                                      'first_hit': first_hit(selected, labels),
                                      'selected': selected, 'trajectory': run['trajectory']}
            provenance[f'GLM_{rep}_seed{seed}'] = sha(glm_path)
            for arm in ARMS:
                if arm == 'matched_proportion_tnap':
                    path = MATCHED / f'matched_{rep}_seed{seed}.json'
                    other = json.loads(path.read_text())
                    assert other['posthoc'] and other['spec_sha256'] == EXPECTED_SPEC
                    result = other['result']
                    selections = [key for step in result['trajectory'] for key in step['selection']]
                    row = {'H50': result['hits_at_budget'],
                           'curve': result['hit_recovery_checkpoints'],
                           'first_hit': first_hit(selections, labels), 'selected': selections}
                else:
                    path = D3 / f'd3_6_runs_private_20261019/{arm}_{rep}_seed{seed}.json'
                    other = json.loads(path.read_text())
                    summary = other['summary']
                    selections = [key for step in other['result']['trajectory'] for key in step['selection']]
                    assert summary['H50'] == sum(labels[key] for key in selections)
                    row = {'H50': summary['H50'], 'curve': summary['cumulative_true'],
                           'first_hit': summary['queries_to_first_hit'], 'selected': selections}
                assert len(selections) == len(set(selections)) == 50
                assert selections[:10] == selected[:10]
                runs[rep, arm, seed] = row
                provenance[f'{arm}_{rep}_seed{seed}'] = sha(path)
    d3 = json.loads((D3 / 'd3_6_report/aggregate.json').read_text())
    assert d3['zero_hit_initialization_seeds'] == list(ZERO)
    assert d3['arm_stats']['bit']['fixed']['mean_H50'] == 20.35
    assert d3['arm_stats']['bit']['forced_random_coldstart']['mean_H50'] == 25.8
    return verification, labels, runs, provenance, d3


def stratified(runs):
    results = {}
    groups = {'overall': list(range(20)), 'zero_hit_initialization': list(ZERO),
              'other_initialization': [s for s in range(20) if s not in ZERO]}
    for rep in ('bit', 'count'):
        results[rep] = {}
        for group, seeds in groups.items():
            results[rep][group] = {}
            for arm in ARMS:
                values = [runs[rep, 'GLM', s]['H50'] - runs[rep, arm, s]['H50'] for s in seeds]
                results[rep][group][arm] = paired(values)
    return results


def policies(runs):
    result = {}
    for rep in ('bit', 'count'):
        matrix = defaultdict(Counter)
        first_decisions = {}
        for seed in range(20):
            trajectory = runs[rep, 'GLM', seed]['trajectory']
            if seed in ZERO:
                first_decisions[str(seed)] = trajectory[1]['decision']['policy']
            for i in range(1, 5):
                previous_hits = sum(x['outcome'] for x in trajectory[i-1]['observations'])
                bucket = '0' if previous_hits == 0 else '1-2' if previous_hits <= 2 else '3-5' if previous_hits <= 5 else '6+'
                matrix[bucket][trajectory[i]['decision']['policy']] += 1
        def fisher(a, b):
            x, y = matrix[a], matrix[b]
            table = [[x['knn_diverse'], sum(x.values()) - x['knn_diverse']],
                     [y['knn_diverse'], sum(y.values()) - y['knn_diverse']]]
            return {'groups': [a, b], 'table_diverse_vs_other': table,
                    'two_sided_p': float(fisher_exact(table).pvalue) if all(sum(row) for row in table) else None}
        result[rep] = {'first_decisions_zero_hit_seeds': first_decisions,
                       'by_previous_batch_hits': {b: dict(matrix[b]) for b in ('0','1-2','3-5','6+')},
                       'fisher_3_5_vs_6_plus': fisher('3-5', '6+'),
                       'fisher_zero_vs_nonzero': {
                           'table_diverse_vs_other': [
                               [matrix['0']['knn_diverse'], sum(matrix['0'].values()) - matrix['0']['knn_diverse']],
                               [sum(matrix[b]['knn_diverse'] for b in ('1-2','3-5','6+')),
                                sum(sum(matrix[b].values()) - matrix[b]['knn_diverse'] for b in ('1-2','3-5','6+'))]],
                           'two_sided_p': None}}
        table = result[rep]['fisher_zero_vs_nonzero']['table_diverse_vs_other']
        if all(sum(row) for row in table):
            result[rep]['fisher_zero_vs_nonzero']['two_sided_p'] = float(fisher_exact(table).pvalue)
    return result


def descriptive(runs, labels):
    output = {}
    for rep in ('bit', 'count'):
        output[rep] = {}
        for arm in ('GLM',) + ARMS:
            cohort = [runs[rep, arm, seed] for seed in range(20)]
            firsts = [row['first_hit'] for row in cohort]
            curve = [statistics.mean(row['curve'][i] for row in cohort) for i in range(5)]
            output[rep][arm] = {'mean_H50': curve[-1], 'mean_curve_10_20_30_40_50': curve,
                                'mean_auc_10_50': statistics.mean(curve_auc(row['curve']) for row in cohort),
                                'enrichment_vs_random_expectation': curve[-1] / (50 * 53 / 462),
                                'first_hit_observed_count': sum(x is not None for x in firsts),
                                'first_hit_right_censored_at_50': sum(x is None for x in firsts),
                                'mean_first_hit_among_observed': statistics.mean(x for x in firsts if x is not None),
                                'restricted_mean_first_hit_51_encoding': statistics.mean(x if x is not None else 51 for x in firsts)}
    return output


def near_threshold(runs, labels):
    path = ROOT / 'data/curation_private/chembl37_batch_curations/chembl37_batch_curation_d1d3b87ef2b3ea4e/CHEMBL1738510/compounds_private.json'
    assert sha(path) == EXPECTED_CURATION
    usable = {r['compound_key']: r for r in json.loads(path.read_text()) if r['usable_for_prototype_review']}
    assert set(usable) == set(labels)
    output = {}
    for rep in ('bit', 'count'):
        output[rep] = {}
        for arm in ('GLM', 'matched_proportion_tnap'):
            rows = []
            for seed in range(20):
                groups = Counter()
                for key in runs[rep, arm, seed]['selected']:
                    record = usable[key]
                    low, high = record['exact_min_nM'], record['exact_max_nM']
                    if low is None or high is None or float(low) != float(high):
                        kind = 'censored_or_not_unique_exact'
                    elif 800 <= float(low) <= 1250:
                        kind = 'near_exact'
                    else:
                        kind = 'far_exact'
                    groups[kind + '_count'] += 1
                    groups[kind + '_hits'] += labels[key]
                assert sum(groups[x + '_count'] for x in ('near_exact','far_exact','censored_or_not_unique_exact')) == 50
                assert sum(groups[x + '_hits'] for x in ('near_exact','far_exact','censored_or_not_unique_exact')) == runs[rep, arm, seed]['H50']
                rows.append(groups)
            output[rep][arm] = {key: statistics.mean(r.get(key, 0) for r in rows)
                                for key in ('near_exact_count','near_exact_hits','far_exact_count','far_exact_hits',
                                            'censored_or_not_unique_exact_count','censored_or_not_unique_exact_hits')}
    return output


def main():
    assert not OUT.exists(), 'Analysis already saved; do not overwrite'
    verification, labels, runs, provenance, d3 = load()
    comparisons = stratified(runs)
    strategy = policies(runs)
    metrics = descriptive(runs, labels)
    diagnostic = near_threshold(runs, labels)
    OUT.mkdir(parents=True)
    analysis = {'schema': 'tnap_d4_analysis_v1', 'created_utc': datetime.now(timezone.utc).isoformat(),
                'post_exposure': True, 'seed_count': 20, 'representations': ['bit','count'],
                'main_floor': 'forced_random_coldstart', 'primary_contrasts': ['forced_random_coldstart','structure_prior'],
                'paired_bootstrap_resamples': 10000, 'paired_bootstrap_seed': 20261018,
                'zero_hit_initialization_seeds': list(ZERO), 'comparisons': comparisons,
                'strategy': strategy, 'descriptive': metrics, 'near_threshold_descriptive': diagnostic,
                'cost': verification['cost'], 'random_expected_H50': 50 * 53 / 462,
                'multiple_comparisons_adjusted': False,
                'measurement_limitation': 'TNAP characterization depth differs by compound and strongly correlates with measured labels; no uniform-effort or other-target generalization.',
                'matched_proportion_posthoc': True,
                'matched_seed_20_excluded_from_pairs': True,
                'source_run_sha256': provenance,
                'source_aggregate_sha256': sha(D3 / 'd3_6_report/aggregate.json'),
                'matched_spec_sha256': EXPECTED_SPEC}
    dump(OUT / 'analysis.json', analysis)
    (OUT / 'STATUS').write_text('done\n')
    summary = {'status': 'done', 'bit': {arm: {k: v for k, v in comparisons['bit']['overall'][arm].items() if k != 'individual_differences'} for arm in ARMS},
               'count': {arm: {k: v for k, v in comparisons['count']['overall'][arm].items() if k != 'individual_differences'} for arm in ARMS},
               'glm_H50': {rep: metrics[rep]['GLM']['mean_H50'] for rep in ('bit','count')},
               'zero_first': {rep: strategy[rep]['first_decisions_zero_hit_seeds'] for rep in ('bit','count')},
               'analysis_sha256': sha(OUT / 'analysis.json')}
    dump(BASE / 'attempt2_20261019/d4_analysis_summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()

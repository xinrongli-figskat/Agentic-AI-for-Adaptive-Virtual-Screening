"""D7-A post-exposure, read-only reanalysis of locked D5 runs; zero campaigns/API calls."""
import argparse
import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
sys.path.insert(0, str(ROOT))
ARCHIVE = ROOT / 'data/curation_private/d5_backups/d5_e_menu_private_20261020.zip'
EXPECTED = '2b812fc95cac56d225d5b3034940598ce05df12180bb403d7e17aeb81ce9440a'
MENU = ('knn_greedy', 'knn_diverse', 'uniform_random', 'persistent_random_until_first_hit', 'diverse_random_coldstart', 'logreg_greedy', 'ens_one_step_proxy')

def utc():
    return datetime.now(timezone.utc).isoformat()

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def save(name, obj):
    path = BASE / name
    assert not path.exists(), str(path)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--lock', action='store_true')
    args = parser.parse_args()
    if args.lock:
        save('a1_spec_lock.json', {'utc': utc(), 'post_exposure': True, 'spec_sha256': sha(BASE / 'A1_SPEC.md'), 'script_sha256': sha(__file__), 'new_campaigns': 0, 'glm_calls': 0})
        return
    lock = json.loads((BASE / 'a1_spec_lock.json').read_text())
    assert lock['spec_sha256'] == sha(BASE / 'A1_SPEC.md')
    assert lock['script_sha256'] == sha(__file__)
    assert sha(ARCHIVE) == EXPECTED
    assert sha(ROOT / 'outputs/d5_20261020/e_menu_results.json') == '7abdc8ca49fd9944f312be0beeab046ba7a9c4aa1ff8d23686e21696401de319'
    results = []
    with zipfile.ZipFile(ARCHIVE) as archive:
        names = archive.namelist()
        assert len(names) == 760
        def read(pool, rep, arm, seed):
            suffix = f'e_menu_private/runs/{pool}/{rep}/{arm}_seed{seed}/run.json'
            matches = [n for n in names if n.endswith(suffix)]
            assert len(matches) == 1, (suffix, matches)
            obj = json.loads(archive.read(matches[0]))
            assert obj['complete'] and obj['queried_count'] == 50
            return obj
        expected = dict(zip(MENU, (20.35, 18.45, 6.00, 25.80, 24.05, 25.80, 25.80)))
        actual = {arm: sum(read('tnap','bit','fixed_'+arm,s)['H50'] for s in range(20)) / 20 for arm in MENU}
        assert actual == expected, actual
        glm = [read('tnap','bit','glm_extended',s)['H50'] for s in range(20)]
        assert glm == [26,32,31,23,28,24,25,16,25,31,11,29,25,25,24,24,28,25,25,19], glm
        save('known_good_regression.json', {'post_exposure': True, 'utc': utc(), 'archive_sha256': EXPECTED, 'member_count': len(names), 'fixed_means': actual, 'glm_extended_H50': glm, 'fixed_means_exact': True, 'glm_array_exact': True})
        for pool, n, k in [('tnap',462,53),('dyrk3',231,116)]:
            for rep in ('bit','count'):
                matrix = []
                ceiling = []
                for s in range(20):
                    runs = [read(pool,rep,'fixed_'+arm,s) for arm in MENU]
                    initial = [r['trajectory'][0]['selection'] for r in runs]
                    assert all(ids == initial[0] for ids in initial)
                    init_hits = runs[0]['trajectory'][0]['cumulative_hits']
                    ceiling.append(init_hits + min(40, k-init_hits))
                    matrix.append([r['H50'] for r in runs])
                matrix = np.asarray(matrix)
                means = matrix.mean(axis=0)
                nontrivial = matrix[:,[i for i,arm in enumerate(MENU) if arm != 'uniform_random']]
                ranges = np.ptp(nontrivial, axis=1)
                rng = np.random.default_rng(20261018)
                boot = ranges[rng.integers(0,20,size=(10000,20))].mean(axis=1)
                best = float(means.max())
                results.append({'pool':pool, 'representation':rep, 'fixed_means': dict(zip(MENU,means.tolist())), 'spread_all':float(np.ptp(means)), 'spread_nontrivial':float(np.ptp(nontrivial.mean(axis=0))), 'spread_paired_mean':float(ranges.mean()), 'spread_paired_mean_ci95':np.quantile(boot,[.025,.975]).tolist(), 'paired_spread_by_seed':ranges.tolist(), 'oracle_ceiling_mean':float(np.mean(ceiling)), 'best_fixed_mean':best, 'ceiling_gap':float(np.mean(ceiling))-best, 'random_floor':float(means[2]), 'random_expectation':50*k/n, 'random_observed_minus_expected':float(means[2])-50*k/n})
        save('headroom_d5_reanalysis.json', {'post_exposure':True, 'utc':utc(), 'source_archive_sha256':EXPECTED, 'spec_lock_sha256':sha(BASE/'a1_spec_lock.json'), 'new_campaigns':0, 'glm_calls':0, 'bootstrap_seed':20261018, 'bootstrap_resamples':10000, 'cells':results})
    # Capture the real production summary builders with a synthetic client. No API.
    from campaign_v0.llm_controller import ToolChoiceLLMController
    from outputs.d5_20261020.e_menu.run_extended import Controller
    class Capture:
        last_usage = last_request_id = None
        last_attempt_log = []
        def __call__(self, summary):
            self.summary = summary
            return json.dumps({'policy':'knn_greedy','reason':'Synthetic information-field inspection.'})
    state = {'candidate_pool':[{'compound_key':f'synthetic_{i}', 'standardized_smiles':'C'} for i in range(20)], 'revealed':[{'compound_key':f'synthetic_{i}', 'outcome':int(i==0)} for i in range(10)], 'queried_count':10,'remaining_budget':40,'next_round':1,'next_batch_size':10,'numerical_summary':{}}
    old, seven = Capture(), Capture()
    ToolChoiceLLMController(old,model_name='synthetic-no-api').choose(state,MENU)
    Controller('glm_extended',0,client=seven).choose(state)
    old_fields, seven_fields = set(old.summary), set(seven.summary)
    assert len(old_fields)==14 and len(seven_fields)==11 and old_fields != seven_fields
    save('information_set_conflict.json', {'post_exposure':True, 'utc':utc(), 'capture_method':'actual production choose methods, synthetic state and no-network stub clients', 'legacy_source_sha256':sha(ROOT/'campaign_v0/llm_controller.py'), 'd5_source_sha256':sha(ROOT/'outputs/d5_20261020/e_menu/run_extended.py'), 'legacy_fields':sorted(old_fields), 'd5_fields':sorted(seven_fields), 'only_legacy':sorted(old_fields-seven_fields), 'only_d5':sorted(seven_fields-old_fields), 'exact_field_equality':False, 'glm_calls':0, 'tier':'B'})
    print(json.dumps({'status':'A1_COMPLETE_A2_A3_TIER_B', 'cells':results, 'glm_calls':0}, ensure_ascii=False))

if __name__ == '__main__':
    main()

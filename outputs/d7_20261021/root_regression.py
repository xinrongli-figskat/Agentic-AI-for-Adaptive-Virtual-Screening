"""Root-owned independent D7 regression. Read-only frozen inputs; no GLM."""
import hashlib
import json
import zipfile
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    checks = []
    def check(p, expected):
        actual = sha(p)
        checks.append(dict(path=str(p.relative_to(ROOT)), expected=expected, actual=actual, match=actual == expected))
        assert actual == expected, str(p)

    archive_path = ROOT / 'data/curation_private/d5_backups/d5_e_menu_private_20261020.zip'
    check(archive_path, '2b812fc95cac56d225d5b3034940598ce05df12180bb403d7e17aeb81ce9440a')
    expected = {'knn_greedy':20.35, 'knn_diverse':18.45, 'uniform_random':6., 'persistent_random_until_first_hit':25.8, 'diverse_random_coldstart':24.05, 'logreg_greedy':25.8, 'ens_one_step_proxy':25.8}
    with zipfile.ZipFile(archive_path) as z:
        assert len(z.namelist()) == 760
        def h50(arm, seed):
            suffix = f'e_menu_private/runs/tnap/bit/{arm}_seed{seed}/run.json'
            names = [n for n in z.namelist() if n.endswith(suffix)]
            assert len(names) == 1
            r = json.loads(z.read(names[0]))
            assert r['complete'] and r['queried_count'] == 50
            return r['H50']
        means = {arm:sum(h50('fixed_'+arm,s) for s in range(20))/20 for arm in expected}
        vector = [h50('glm_extended',s) for s in range(20)]
    assert means == expected
    assert vector == [26,32,31,23,28,24,25,16,25,31,11,29,25,25,24,24,28,25,25,19]
    tnap = json.loads((ROOT/'outputs/d3_tnap_20261019/freeze_tnap_v1/pool_manifest.json').read_text())
    for key in ('public','private'):
        check(Path(tnap[key]['path']),tnap[key]['sha256'])
    frozen = ROOT/'data/curation_private/frozen_dyrk3_v1'
    dyrk3 = json.loads((frozen/'manifest.json').read_text())
    check(Path(dyrk3['public_dir'])/'candidates.jsonl', dyrk3['data_sha256']['public_candidates'])
    check(Path(dyrk3['private_dir'])/'oracle_labels.jsonl', dyrk3['data_sha256']['private_labels'])
    for source, expected_sha in dyrk3['source_sha256'].items():
        p = Path(source)
        check(p, expected_sha)
        check(frozen/'source_snapshot'/p.relative_to(ROOT),expected_sha)
    result = dict(utc=datetime.now(timezone.utc).isoformat(), post_exposure=True,
        fixed_means=means, glm_extended_H50=vector, fixed_means_exact=True,
        glm_array_exact=True, frozen_data_and_code_checks=checks,
        all_hashes_match=True, new_glm_calls=0, new_campaigns=0)
    out = BASE/'root_regression_and_frozen_checks.json'
    assert not out.exists(), 'Preserve earlier verification; use a new version.'
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':True,'hash_checks':len(checks),'fixed_means':means,'new_glm_calls':0}))

if __name__ == '__main__':
    main()

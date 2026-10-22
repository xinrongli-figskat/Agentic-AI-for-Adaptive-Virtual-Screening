"""D7-E: offline checks; never executes a campaign or calls a model."""
import argparse
import csv
import hashlib
import json
import statistics
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def utc():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def run_remote(root, out):
    started = utc()
    archive = root / 'data/curation_private/d5_backups/d5_e_menu_private_20261020.zip'
    blob = archive.read_bytes()
    assert digest(blob) == '2b812fc95cac56d225d5b3034940598ce05df12180bb403d7e17aeb81ce9440a'
    assert len(blob) == 2455539
    z = zipfile.ZipFile(archive)
    assert len(z.namelist()) == 760
    def saved(arm, seed):
        suffix = f'/tnap/bit/{arm}_seed{seed}/run.json'
        names = [n for n in z.namelist() if n.endswith(suffix)]
        assert len(names) == 1, names
        content = z.read(names[0])
        return names[0], content, json.loads(content)
    expected_fixed = {'knn_greedy': 20.35, 'knn_diverse': 18.45, 'uniform_random': 6.0,
                      'persistent_random_until_first_hit': 25.8, 'diverse_random_coldstart': 24.05,
                      'logreg_greedy': 25.8, 'ens_one_step_proxy': 25.8}
    means = {}
    for arm, expected in expected_fixed.items():
        vals = [saved('fixed_'+arm, s)[2]['H50'] for s in range(20)]
        means[arm] = sum(vals)/20
        assert means[arm] == expected, (arm, means[arm])
    extended = [saved('glm_extended', s)[2]['H50'] for s in range(20)]
    assert extended == [26,32,31,23,28,24,25,16,25,31,11,29,25,25,24,24,28,25,25,19]
    old_csv = root / 'outputs/d5_20261020/a_mechanism/all_glm_policy_sequences.csv'
    rows = list(csv.DictReader(old_csv.open(encoding='utf-8', newline='')))
    old_counts = Counter(r[f'r{i}_policy'] for r in rows for i in range(1, 5))
    assert dict(old_counts) == {'knn_diverse':84,'knn_greedy':59,'uniform_random':17}
    results = json.loads((root/'outputs/d5_20261020/e_menu_results.json').read_text())
    basic_checks = {}
    for rep in ('bit','count'):
        reconstructed_basic = results['comparisons'][rep]['glm_basic']['values_by_seed']
        old = [int(r['glm_H50']) for r in sorted((r for r in rows if r['representation']==rep),key=lambda r:int(r['seed']))]
        assert old == reconstructed_basic
        basic_checks[rep] = {'matching_seeds':20, 'derived_from':'locked e_menu_results.json comparisons[representation].glm_basic.values_by_seed'}
    corrected_counts, replay_counts = Counter(), Counter()
    comparisons = []
    input_hashes = []
    calls = 0
    for seed in range(10):
        name, content, baseline = saved('glm_extended', seed)
        replay_path = root/f'outputs/d6_20261020/b_menu_description_private/runs_v0_replay/runs/tnap/bit/glm_extended_seed{seed}/run.json'
        replay_bytes = replay_path.read_bytes()
        replay = json.loads(replay_bytes)
        assert all(r['complete'] and r['queried_count']==50 and r['pool']=='tnap' and r['representation']=='bit' and r['seed']==seed for r in (baseline,replay))
        bt, rt = baseline['trajectory'], replay['trajectory']
        bp = [s['decision']['policy'] for s in bt[1:]]
        rp = [s['decision']['policy'] for s in rt[1:]]
        assert len(bp)==len(rp)==4
        corrected_counts.update(bp); replay_counts.update(rp)
        bs, rs = bt[1]['glm_call']['public_summary'],rt[1]['glm_call']['public_summary']
        assert len(bs)==len(rs)==11
        equal_fields = {k:bs[k]==rs.get(k) for k in bs}
        state_equal = bs == rs
        canonical = lambda x:json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
        assert (canonical(bs)==canonical(rs)) == state_equal
        info_equal = bt[1]['information_available']==rt[1]['information_available']
        init_equal = bt[0]['selection']==rt[0]['selection']
        comparisons.append({'seed':seed, 'initialization_equal':init_equal,
                            'first_public_summary_equal':state_equal,'first_information_available_equal':info_equal,
                            'first_summary_field_count':len(bs),'field_equality':equal_fields,
                            'first_summary_canonical_sha256':digest(canonical(bs)),
                            'replay_first_summary_canonical_sha256':digest(canonical(rs)),
                            'first_policy_equal':bp[0]==rp[0], 'complete_sequence_equal':bp==rp,
                            'd5_authoritative_policies':bp,'d6_replay_policies':rp,
                            'd5_H50':baseline['H50'],'d6_H50':replay['H50']})
        input_hashes.append({'seed':seed,'archive_member':name,'archive_member_sha256':digest(content),
                             'replay_path':str(replay_path.relative_to(root)),'replay_sha256':digest(replay_bytes)})
        for s in rt[1:]:
            call = s['glm_call']
            assert call['request_id'] and call['raw_response'] and call['usage'] and call['decision_seconds']>=0
            calls += len(call['api_attempt_log'])
    assert dict(corrected_counts)=={'diverse_random_coldstart':2,'knn_greedy':10,'knn_diverse':17,'logreg_greedy':1,'ens_one_step_proxy':9,'uniform_random':1},corrected_counts
    assert replay_counts['ens_one_step_proxy']==16
    totals = {k:sum(r[k] for r in comparisons) for k in ('initialization_equal','first_public_summary_equal','first_information_available_equal','first_policy_equal','complete_sequence_equal')}
    assert totals == {'initialization_equal':10,'first_public_summary_equal':10,'first_information_available_equal':10,'first_policy_equal':4,'complete_sequence_equal':1},totals
    assert [r['seed'] for r in comparisons if r['complete_sequence_equal']]==[5]
    assert calls == 40
    dump(out/'corrected_baseline_checks.json',{'task':'D7-E','post_exposure':True,'started_utc':started,'finished_utc':utc(),
         'new_glm_calls':0,'new_campaigns':0,'archive_sha256':digest(blob),'archive_bytes':len(blob),'archive_members':len(z.namelist()),
         'known_good_fixed_means':means,'known_good_glm_extended_H50':extended,'wrong_reference_policy_counts':dict(old_counts),
         'wrong_reference_matches_glm_basic':basic_checks,'d5_authoritative_policy_counts_seeds_0_9':dict(corrected_counts),
         'd6_replay_policy_counts':dict(replay_counts),'comparison_totals':totals,'per_seed':comparisons,'input_receipts':input_hashes,
         'd6_http_attempts_with_returned_receipts':calls,'d6_budget_limit':450,'corrected_tier_b_condition':9>=2,
         'note':'Input equality uses all saved public_summary fields and information_available, with canonical JSON hashes; this does not independently attest wire-level HTTP bytes.'})


def run_local(root,out):
    base=root/'outputs/d6_20261020'
    checks={}
    for directory in ('a_identity_gate','b_menu_description','c_d5_addendum'):
        manifest=base/directory/'MANIFEST.json'
        data=json.loads(manifest.read_text(encoding='utf-8'))
        members=data['files']
        members=[{'path':k,'sha256':v} for k,v in members.items()] if isinstance(members,dict) else members
        checked=[]
        for item in members:
            p=(manifest.parent/item['path']).resolve()
            assert p.is_relative_to(manifest.parent.resolve())
            actual=digest(p.read_bytes())
            assert actual==item['sha256'],p
            checked.append({'path':item['path'],'sha256':actual})
        checks[directory]={'verified_members':len(checked),'members':checked,'manifest_sha256':digest(manifest.read_bytes())}
    mtimes={}
    for name in ('DEVIATION_TIER_A_B0_PATH_REPAIR.md','BLOCKED_b0_incomplete_replay.md','b0_replay_summary.json'):
        p=base/'b_menu_description'/name
        mtimes[name]={'sha256':digest(p.read_bytes()),'observed_local_mtime_utc':datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat()}
    dump(out/'historical_record_checks.json',{'task':'D7-E','post_exposure':True,'checked_utc':utc(),
         'd6_report_sha256':digest((base/'d6_report.md').read_bytes()),'d6_manifest_checks':checks,'historical_file_metadata':mtimes,
         'd6_wave1_second_wave_authorized':json.loads((base/'d6_wave1_verification.json').read_text())['second_wave_authorized'],
         'new_glm_calls':0,'new_campaigns':0,
         'timestamp_caveat':'File mtime records saved-file timing, not independently measured repair-event time. Original mtime corroborates the supplied D7 card; actual repair time is not known.'})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--local',action='store_true')
    a=p.parse_args();out=a.root/'outputs/d7_20261021/e_record_fixes';out.mkdir(parents=True,exist_ok=True)
    (run_local if a.local else run_remote)(a.root,out)
    print('D7-E offline verification passed')

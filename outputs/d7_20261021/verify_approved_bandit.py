"""Independent root review of D7 A2/A3 private transcripts; no new campaigns."""
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
REV = BASE/'a_headroom_bandit/revision_11field'
FIELDS = {'task','candidate_count','queried_count','remaining_budget','next_round','revealed_hits','recent_revealed_hits','numerical_summary','allowed_policies','policy_descriptions','commitment_note'}

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    lock = json.loads((REV/'execution_lock.json').read_text())
    assert digest(REV/'run_cpu.py') == lock['code_sha256']
    assert digest(REV/'A2_A3_SPEC.md') == lock['spec_sha256']
    assert digest(BASE/'bandit_approval_20261021.md') == lock['approval_sha256']
    locked_at = datetime.fromisoformat(lock['utc']).timestamp()
    paths = sorted((REV/'runs_private').rglob('*.json'))
    assert len(paths) == 1480
    primaries = [p for p in paths if not p.stem.endswith('_repeat')]
    assert len(primaries) == 1160
    summary = json.loads((REV/'cpu_summary.json').read_text())['rows']
    lookup = {(r['pool'],r['representation'],r['seed'],r['arm'],r['batch_size']):r for r in summary}
    assert len(lookup)==1160
    repeated = regressions = summaries = reward_updates = 0
    archive = ROOT/'data/curation_private/d5_backups/d5_e_menu_private_20261020.zip'
    assert digest(archive)=='2b812fc95cac56d225d5b3034940598ce05df12180bb403d7e17aeb81ce9440a'
    with zipfile.ZipFile(archive) as z:
        names=z.namelist()
        def reference(pool,rep,arm,seed):
            matches=[n for n in names if n.endswith(f'e_menu_private/runs/{pool}/{rep}/{arm}_seed{seed}/run.json')]
            assert len(matches)==1
            return json.loads(z.read(matches[0]))
        for p in primaries:
            assert p.stat().st_mtime >= locked_at
            r=json.loads(p.read_text()); steps=r['trajectory']; batch=r['batch_size']
            assert r['complete'] and r['queried_count']==50 and len(steps)==1+40//batch
            seen=set(); cumulative=0; counts={}; rewards={}; aa={}; bb={}
            for i,s in enumerate(steps):
                ids=s['selection']; obs=s['observations']
                assert len(ids)==(10 if i==0 else batch) and len(set(ids))==len(ids)
                assert not seen.intersection(ids)
                assert [o['compound_key'] for o in obs]==ids
                if i:
                    pub=s['public_summary']; assert set(pub)==FIELDS
                    assert pub['queried_count']==len(seen) and pub['remaining_budget']==50-len(seen)
                    assert pub['revealed_hits']==cumulative
                    summaries+=1
                h=sum(o['outcome'] for o in obs)
                assert all(o['outcome'] in (0,1) for o in obs)
                cumulative+=h; seen.update(ids)
                assert s['cumulative_hits']==cumulative
                if i and r['arm'].startswith('bandit_'):
                    arm=s['decision']['policy']; reward=h/batch
                    counts[arm]=counts.get(arm,0)+1
                    rewards[arm]=rewards.get(arm,0.)+reward
                    aa[arm]=aa.get(arm,1.)+reward; bb[arm]=bb.get(arm,1.)+(1-reward)
                    following=(steps[i+1]['decision']['previous_batch_update'] if i<len(steps)-1 else r['terminal_controller']['last_batch_update'])
                    assert following==dict(policy=arm,batch_queries=batch,new_hits=h,reward=reward)
                    reward_updates+=1
            assert len(seen)==50 and r['H50']==cumulative
            key=(r['pool'],r['representation'],r['seed'],r['arm'],batch)
            assert lookup[key]['H50']==cumulative
            ref=reference(r['pool'],r['representation'],'fixed_knn_greedy',r['seed'])
            assert steps[0]['selection']==ref['trajectory'][0]['selection']
            if r['arm'].startswith('bandit_'):
                q=p.with_name(p.stem+'_repeat.json'); assert q.exists() and json.loads(q.read_text())==r
                terminal=r['terminal_controller']['posterior']
                for arm in terminal['pulls']:
                    assert terminal['pulls'][arm]==counts.get(arm,0)
                    assert terminal['reward_sums'][arm]==rewards.get(arm,0.)
                    assert terminal['alpha'][arm]==aa.get(arm,1.) and terminal['beta'][arm]==bb.get(arm,1.)
                assert sum(terminal['pulls'].values())==40//batch
                assert terminal['actual_choices']+terminal['automatic_steps']==40//batch
                repeated+=1
            elif batch==10:
                ref=reference(r['pool'],r['representation'],r['arm'].replace(':','_'),r['seed'])
                assert len(ref['trajectory'])==len(steps)
                for a,b in zip(steps,ref['trajectory']):
                    assert all(a[f]==b[f] for f in ('selection','observations','cumulative_hits'))
                regressions+=1
    assert repeated==320 and regressions==280
    result=dict(recorded_utc=datetime.now(timezone.utc).isoformat(),post_exposure=True,
        unique_configurations=1160,physical_transcripts=1480,deterministic_repeated_configurations=repeated,
        g4_bit_fixed_D5_regressions=regressions,summary_count_and_budget_checks=summaries,
        independently_recomputed_batch_reward_updates=reward_updates,posterior_accounting_exact=True,
        initialization_matches_D5_all=True,lock_predates_all_runs=True,new_glm_calls=0,
        second_wave_authorized=False,note='A passed after explicit interface amendment; D definition blockers remain unapproved.')
    out=BASE/'approved_bandit_root_verification.json'; assert not out.exists()
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))

if __name__=='__main__':main()

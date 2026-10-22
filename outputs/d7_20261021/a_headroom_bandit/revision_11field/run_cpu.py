"""Post-exposure D7 CPU-only bandit and granularity experiments."""
import os
for _name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[_name] = '1'

import argparse
import hashlib
import json
import math
import random
import sys
import time
import zipfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
sys.path.insert(0,str(ROOT))
from outputs.d5_20261020.e_menu.expanded_tools import ExpandedTools, MENU
from outputs.d5_20261020.e_menu.run_extended import Controller as D5Controller, load_pool, validate_sources
from oracle_boundary_v0.oracle_boundary import BatchOracle

ARCHIVE = ROOT/'data/curation_private/d5_backups/d5_e_menu_private_20261020.zip'
ARCHIVE_SHA = '2b812fc95cac56d225d5b3034940598ce05df12180bb403d7e17aeb81ce9440a'
APPROVAL = ROOT/'outputs/d7_20261021/bandit_approval_20261021.md'
APPROVAL_SHA = 'ae6dfd39b6f1e2f8e38b3bea56216890ec7315137b7965a384aafcee2043fc9a'
BANDITS = ('bandit_thompson','bandit_ucb1')
SUMMARY_FIELDS = {'task','candidate_count','queried_count','remaining_budget','next_round','revealed_hits','recent_revealed_hits','numerical_summary','allowed_policies','policy_descriptions','commitment_note'}
CACHE = {}

def utc(): return datetime.now(timezone.utc).isoformat()
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
    temp.replace(path)

class Capture:
    last_usage=last_request_id=None
    last_attempt_log=[]
    def __call__(self,summary):
        self.summary=summary
        return json.dumps({'policy':'knn_greedy','reason':'No-network public-summary adapter.'})

def summary_of(state, batch, seed):
    client=Capture()
    D5Controller('glm_extended',seed,client=client).choose(state)
    original=client.summary
    assert set(original)==SUMMARY_FIELDS
    summary=dict(original)
    if batch != 10:
        summary['task']=original['task'].replace('batch of 10',f'batch of {batch}')
        summary['commitment_note']=original['commitment_note'].replace('spend 10 oracle',f'spend {batch} oracle')
    else:
        assert summary==original
    assert set(summary)==set(original)
    return summary

class Bandit:
    """Only the production summary enters this controller, never an oracle or pool."""
    def __init__(self,kind,seed):
        assert kind in BANDITS
        self.kind=kind;self.seed=seed
        self.alpha={p:1.0 for p in MENU};self.beta={p:1.0 for p in MENU}
        self.count={p:0 for p in MENU};self.reward_sum={p:0.0 for p in MENU}
        self.previous=None;self.last_queries=10;self.last_hits=None
        self.commit=False;self.actual_choices=0;self.automatic_steps=0

    def feedback(self,summary):
        assert set(summary)==SUMMARY_FIELDS
        h=int(summary['revealed_hits']);q=int(summary['queried_count'])
        update=None
        if self.last_hits is not None and self.previous is not None:
            b=q-self.last_queries;new=h-self.last_hits
            assert b>0 and 0<=new<=b
            r=new/b;p=self.previous
            self.alpha[p]+=r;self.beta[p]+=1-r
            self.count[p]+=1;self.reward_sum[p]+=r
            update={'policy':p,'batch_queries':b,'new_hits':new,'reward':r}
        self.last_queries=q;self.last_hits=h;self.previous=None
        if h>0:self.commit=False
        return update

    def choose(self,summary):
        update=self.feedback(summary)
        h=summary['revealed_hits'];r=summary['next_round']
        automatic=self.commit and h==0
        if automatic:
            policy='persistent_random_until_first_hit';scores=None
            self.automatic_steps+=1
        else:
            self.actual_choices+=1
            if self.kind=='bandit_thompson':
                scores={}
                for p in MENU:
                    seed_bytes=hashlib.sha256(f'd7_thompson|{self.seed}|{r}|{p}'.encode()).digest()
                    scores[p]=random.Random(int.from_bytes(seed_bytes,'big')).betavariate(self.alpha[p],self.beta[p])
            else:
                t=1+sum(self.count.values())
                scores={p:(math.inf if self.count[p]==0 else self.reward_sum[p]/self.count[p]+math.sqrt(2*math.log(t)/self.count[p])) for p in MENU}
            policy=max(MENU,key=lambda p:scores[p])
        if policy=='persistent_random_until_first_hit' and h==0:self.commit=True
        self.previous=policy
        return {'policy':policy,'automatic_commitment':automatic,'previous_batch_update':update,'selection_scores':None if scores is None else {p:('infinity' if math.isinf(v) else v) for p,v in scores.items()},'posterior_before_batch':self.snapshot()}

    def snapshot(self):
        return {'alpha':dict(self.alpha),'beta':dict(self.beta),'pulls':dict(self.count),'reward_sums':dict(self.reward_sum),'actual_choices':self.actual_choices,'automatic_steps':self.automatic_steps}

def archive_read(z,pool,rep,arm,seed):
    suffix=f'e_menu_private/runs/{pool}/{rep}/{arm}_seed{seed}/run.json'
    matches=[n for n in z.namelist() if n.endswith(suffix)]
    assert len(matches)==1,(suffix,matches)
    return json.loads(z.read(matches[0]))

def source_checks():
    validate_sources()
    assert sha(APPROVAL)==APPROVAL_SHA
    assert sha(ARCHIVE)==ARCHIVE_SHA
    expected=dict(zip(MENU,(20.35,18.45,6.00,25.80,24.05,25.80,25.80)))
    with zipfile.ZipFile(ARCHIVE) as z:
        assert len(z.namelist())==760
        actual={p:sum(archive_read(z,'tnap','bit','fixed_'+p,s)['H50'] for s in range(20))/20 for p in MENU}
        assert actual==expected
        glm=[archive_read(z,'tnap','bit','glm_extended',s)['H50'] for s in range(20)]
        assert glm==[26,32,31,23,28,24,25,16,25,31,11,29,25,25,24,24,28,25,25,19]
    return {'utc':utc(),'archive_sha256':ARCHIVE_SHA,'members':760,'fixed_means':actual,'glm_extended_H50':glm,'exact_pass':True}

def pool_cache(pool,rep):
    key=(pool,rep)
    if key not in CACHE:
        candidates,private=load_pool(pool)
        CACHE[key]=(candidates,private,ExpandedTools(candidates,rep))
    return CACHE[key]

def one(job):
    pool,rep,seed,arm,batch=job
    candidates,private,tools=pool_cache(pool,rep)
    oracle=BatchOracle(candidates,private,seed=seed,total_budget=50,initialization_queries=10,batch_size=batch)
    ctrl=Bandit(arm,seed) if arm in BANDITS else D5Controller(arm,seed)
    first=oracle.proposed_initial_ids();response=oracle.query_batch_tool({'compound_keys':first})
    trajectory=[{'stage':'initialization','selection':first,'observations':response['observations'],'cumulative_hits':sum(x['outcome'] for x in response['observations'])}]
    while oracle.public_state()['remaining_budget']:
        state=oracle.public_state();state['numerical_summary']=tools.legacy.describe_state(state)
        summary=summary_of(state,batch,seed)
        if arm in BANDITS:decision=ctrl.choose(summary)
        else:decision,_=ctrl.choose(state)
        selected=tools.select(state,decision['policy'],seed,state['next_round'])
        response=oracle.query_batch_tool({'compound_keys':selected})
        trajectory.append({'stage':f"feedback_round_{response['round']}",'public_summary':summary,'decision':decision,'selection':selected,'observations':response['observations'],'cumulative_hits':sum(x['outcome'] for x in oracle.public_state()['revealed'])})
    terminal=None
    if arm in BANDITS:
        final_state=oracle.public_state();final_state['numerical_summary']=None
        update=ctrl.feedback(summary_of(final_state,batch,seed))
        terminal={'last_batch_update':update,'posterior':ctrl.snapshot()}
        assert sum(ctrl.count.values())==40//batch
    queried=[key for step in trajectory for key in step['selection']]
    assert len(queried)==len(set(queried))==50
    return {'post_exposure':True,'pool':pool,'representation':rep,'seed':seed,'arm':arm,'batch_size':batch,'granularity':'g'+str(40//batch),'complete':True,'queried_count':50,'H50':trajectory[-1]['cumulative_hits'],'trajectory':trajectory,'terminal_controller':terminal}

def execute_job(job):
    pool,rep,seed,arm,batch=job
    path=BASE/'runs_private'/pool/rep/f'g{40//batch}'/f"{arm.replace(':','_')}_seed{seed}.json"
    repeated=path.with_name(path.stem+'_repeat.json')
    if path.exists():
        saved=json.loads(path.read_text())
        assert saved['complete']
        if arm in BANDITS:
            assert repeated.exists()
            assert json.loads(repeated.read_text())==saved
        return compact(saved,True)
    start=time.perf_counter();result=one(job)
    save(path,result)
    if arm in BANDITS:
        again=one(job)
        save(repeated,again)
        assert result==again,'Deterministic replay mismatch'
    with zipfile.ZipFile(ARCHIVE) as z:
        ref=archive_read(z,pool,rep,'fixed_knn_greedy',seed)
        assert result['trajectory'][0]['selection']==ref['trajectory'][0]['selection']
        if batch==10:
            if arm.startswith('fixed:'):
                ref=archive_read(z,pool,rep,arm.replace(':','_'),seed)
                for a,b in zip(result['trajectory'],ref['trajectory']):
                    for field in ('selection','observations','cumulative_hits'):
                        assert a[field]==b[field],(job,field)
                assert result['H50']==ref['H50']
    return {**compact(result,False),'elapsed_seconds':time.perf_counter()-start}

def compact(result,resumed):
    terminal=result['terminal_controller']
    return {k:result[k] for k in ('pool','representation','seed','arm','batch_size','granularity','H50')}|{'resumed':resumed,'determinism_repeated':result['arm'] in BANDITS,'actual_choices':None if terminal is None else terminal['posterior']['actual_choices'],'automatic_steps':None if terminal is None else terminal['posterior']['automatic_steps']}

def synthetic_checks():
    c=[{'compound_key':f'synthetic_{i}','standardized_smiles':'C'} for i in range(60)]
    # Change only unrevealed outcomes; keep initialized observations identical.
    key_order=BatchOracle(c,{x['compound_key']:0 for x in c},seed=8,total_budget=50,initialization_queries=10,batch_size=10).proposed_initial_ids()
    states=[]
    for unseen in (0,1):
        priv={x['compound_key']:(0 if x['compound_key'] in key_order else unseen) for x in c}
        oracle=BatchOracle(c,priv,seed=8,total_budget=50,initialization_queries=10,batch_size=10)
        oracle.query_batch_tool({'compound_keys':key_order})
        state=oracle.public_state();state['numerical_summary']={'synthetic':True};states.append(state)
    summaries=[summary_of(s,10,8) for s in states]
    assert summaries[0]==summaries[1]
    for arm in BANDITS:assert Bandit(arm,8).choose(summaries[0])==Bandit(arm,8).choose(summaries[1])
    # UCB must try menu order; changed batch lengths use cumulative deltas.
    u=Bandit('bandit_ucb1',0);s=dict(summaries[0]);s['revealed_hits']=1
    for j,p in enumerate(MENU[:4]):
        s['next_round']=j+1;s['queried_count']=10+j*10;s['revealed_hits']=1+j
        assert u.choose(s)['policy']==p
    # Force a commitment and verify that repeated batches credit only that arm.
    b=Bandit('bandit_thompson',0);s=dict(summaries[0]);s['next_round']=1
    b.last_hits=0;b.last_queries=10;b.previous='persistent_random_until_first_hit';b.commit=True
    s['queried_count']=30;s['revealed_hits']=0;s['next_round']=2
    dec=b.choose(s);assert dec['automatic_commitment'] and b.count['persistent_random_until_first_hit']==1
    assert b.beta['persistent_random_until_first_hit']==2.0
    s['queried_count']=50;s['revealed_hits']=2;s['next_round']=3
    update=b.feedback(s);assert update['reward']==.1 and not b.commit
    assert b.alpha['persistent_random_until_first_hit']==1.1
    return {'post_exposure':True,'utc':utc(),'d5_exact_field_set':sorted(SUMMARY_FIELDS),'field_count':11,'production_capture_exact':True,'g4_full_values_match_production':True,'unrevealed_perturbation_invariant':True,'ucb_first_four_menu_order':True,'commitment_reward_accounting':True,'glm_calls':0}

def jobs():
    answer=[]
    for pool in ('tnap','dyrk3'):
        for batch in (20,10,5):
            for arm in tuple('fixed:'+p for p in MENU)+BANDITS:
                for seed in range(20):answer.append((pool,'bit',seed,arm,batch))
        for arm in BANDITS:
            for seed in range(20):answer.append((pool,'count',seed,arm,10))
    assert len(answer)==len(set(answer))==1160
    assert sum(j[3] in BANDITS for j in answer)==320
    return answer

def ci(values):
    x=np.asarray(values,dtype=float);rng=np.random.default_rng(20261018)
    boot=x[rng.integers(0,len(x),size=(10000,len(x)))].mean(axis=1)
    return [float(v) for v in np.quantile(boot,[.025,.975])]

def analyze(rows):
    table={(r['pool'],r['representation'],r['batch_size'],r['arm'],r['seed']):r['H50'] for r in rows}
    fixed={};glms={}
    with zipfile.ZipFile(ARCHIVE) as z:
        for pool in ('tnap','dyrk3'):
            for rep in ('bit','count'):
                fixed[pool,rep]={p:[archive_read(z,pool,rep,'fixed_'+p,s)['H50'] for s in range(20)] for p in MENU}
                if pool=='tnap':glms[rep]=[archive_read(z,pool,rep,'glm_extended',s)['H50'] for s in range(20)]
    comparisons=[];gran=[]
    for pool in ('tnap','dyrk3'):
        for rep in ('bit','count'):
            fm=fixed[pool,rep];best=max(np.mean(v) for v in fm.values())
            tied=[p for p in MENU if np.mean(fm[p])==best]
            for arm in BANDITS:
                x=np.asarray([table[pool,rep,10,arm,s] for s in range(20)])
                comp={'pool':pool,'representation':rep,'arm':arm,'H50_mean':float(x.mean()),'H50_by_seed':x.tolist(),'best_fixed_tied':tied,'versus_best_fixed':[]}
                for p in tied:
                    d=x-np.asarray(fm[p]);comp['versus_best_fixed'].append({'policy':p,'paired_difference':float(d.mean()),'ci95':ci(d)})
                if pool=='tnap':
                    d=x-np.asarray(glms[rep]);comp['versus_D5_GLM']={'paired_difference':float(d.mean()),'ci95':ci(d),'interpretation':'provisional descriptive comparison; D7-B model variance not included'}
                comparisons.append(comp)
        for batch in (20,10,5):
            vectors={arm:np.asarray([table[pool,'bit',batch,arm,s] for s in range(20)]) for arm in tuple('fixed:'+p for p in MENU)+BANDITS}
            means={arm:float(v.mean()) for arm,v in vectors.items()}
            fm={p:means['fixed:'+p] for p in MENU}
            nt=np.asarray([vectors['fixed:'+p] for p in MENU if p!='uniform_random'])
            ranges=np.ptp(nt,axis=0)
            top=max(fm.values());tied=[p for p in MENU if fm[p]==top]
            record={'pool':pool,'representation':'bit','granularity':'g'+str(40//batch),'batch_size':batch,'means':means,'spread_all':max(fm.values())-min(fm.values()),'spread_nontrivial':float(np.ptp(nt.mean(axis=1))),'spread_paired_mean':float(ranges.mean()),'spread_paired_mean_ci95':ci(ranges),'paired_ranges':ranges.tolist(),'best_fixed_tied':tied,'bandit_vs_cell_best':[]}
            for arm in BANDITS:
                for p in tied:
                    d=vectors[arm]-vectors['fixed:'+p]
                    record['bandit_vs_cell_best'].append({'bandit':arm,'fixed':p,'paired_difference':float(d.mean()),'ci95':ci(d)})
            gran.append(record)
    differences=[]
    for pool in ('tnap','dyrk3'):
        base=next(r for r in gran if r['pool']==pool and r['granularity']=='g4')
        for g in ('g2','g8'):
            r=next(r for r in gran if r['pool']==pool and r['granularity']==g)
            d=np.asarray(r['paired_ranges'])-np.asarray(base['paired_ranges'])
            differences.append({'pool':pool,'contrast':g+'-g4','paired_range_difference':float(d.mean()),'ci95':ci(d)})
    return {'post_exposure':True,'utc':utc(),'glm_calls':0,'bootstrap_seed':20261018,'bootstrap_resamples':10000,'bandit_g4':comparisons,'granularity':gran,'granularity_paired_contrasts':differences}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--lock',action='store_true');parser.add_argument('--workers',type=int,default=8)
    args=parser.parse_args()
    if args.lock:
        assert not (BASE/'execution_lock.json').exists()
        assert sha(APPROVAL)==APPROVAL_SHA
        validate_sources()
        save(BASE/'execution_lock.json',{'post_exposure':True,'utc':utc(),'approval_sha256':APPROVAL_SHA,'spec_sha256':sha(BASE/'A2_A3_SPEC.md'),'code_sha256':sha(__file__),'python_version':sys.version,'numpy_version':np.__version__,'glm_calls':0,'unique_jobs':1160,'physical_runs':1480})
        return
    lock=json.loads((BASE/'execution_lock.json').read_text())
    assert lock['code_sha256']==sha(__file__) and lock['spec_sha256']==sha(BASE/'A2_A3_SPEC.md')
    save(BASE/'known_good_regression.json',source_checks())
    save(BASE/'information_boundary_synthetic.json',synthetic_checks())
    rows=[];start=time.perf_counter()
    with ProcessPoolExecutor(max_workers=min(8,args.workers)) as executor:
        pending={executor.submit(execute_job,j):j for j in jobs()}
        for future in as_completed(pending):
            try:rows.append(future.result())
            except Exception as exc:
                save(BASE/'failure.json',{'utc':utc(),'job':pending[future],'error_type':type(exc).__name__,'error':str(exc),'completed':len(rows)})
                for f in pending:f.cancel()
                raise
            if len(rows)%20==0 or len(rows)==1160:
                progress={'utc':utc(),'completed_unique':len(rows),'expected_unique':1160,'elapsed_seconds':time.perf_counter()-start,'glm_calls':0}
                save(BASE/'progress.json',progress);print(json.dumps(progress),flush=True)
    rows.sort(key=lambda r:(r['pool'],r['representation'],r['batch_size'],r['arm'],r['seed']))
    save(BASE/'cpu_summary.json',{'post_exposure':True,'rows':rows,'unique_jobs':len(rows),'physical_runs':1480,'glm_calls':0})
    save(BASE/'analysis.json',analyze(rows))
    save(BASE/'validation.json',{'post_exposure':True,'utc':utc(),'completed_unique':1160,'physical_runs':1480,'bandit_repeated_configurations':320,'bandit_complete_trajectory_equality':True,'g4_fixed_D5_trajectory_equalities':280,'all_g4_initializations_match_D5':True,'query_count_each':50,'information_field_assertion_on_every_decision':True,'g4_summary_value_equality_on_every_decision':True,'glm_calls':0,'source_checks_post':source_checks()})
    print('COMPLETE_CPU_ONLY',flush=True)

if __name__=='__main__':main()

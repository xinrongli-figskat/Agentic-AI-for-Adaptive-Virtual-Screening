"""Post-exposure CPU-only control rehearsal on the frozen DYRK3 pool.

Original campaign_v0 and frozen data are read only. This is not a new campaign.
"""
import csv
import hashlib
import json
import math
import platform
import random
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path('/driveA/xinrong/agentic-screening')
PRIVATE=ROOT/'data/curation_private'
OUT=PRIVATE/'r5_cpu_controls_private_20261018'
FROZEN=PRIVATE/'frozen_dyrk3_v1'
sys.path.insert(0,str(ROOT))
from campaign_v0.campaign_core import FixedController, RandomController, run_campaign
from oracle_boundary_v0.oracle_boundary import BatchOracle, read_jsonl

POLICIES=('knn_greedy','knn_diverse','uniform_random')

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def seeded_int(message): return int.from_bytes(hashlib.sha256(message.encode()).digest(),'big')

class Controller:
    def __init__(self,kind,seed,rep,matched_slots):
        self.name=kind
        self.kind,self.seed,self.rep,self.matched_slots=kind,seed,rep,matched_slots
    def choose(self,state,allowed):
        rnd=state['next_round']
        if self.kind=='fixed_schedule': policy=('knn_greedy','knn_greedy','knn_diverse','knn_greedy')[rnd-1]
        elif self.kind=='rule_adaptive':
            prev=state['revealed'][-10:]
            policy='knn_diverse' if sum(x['outcome'] for x in prev)==0 else 'knn_greedy'
        elif self.kind=='random_mixture': policy=POLICIES[seeded_int(f'mix|{self.seed}|{rnd}')%3]
        elif self.kind=='matched_proportion': policy='knn_diverse' if (self.seed,rnd) in self.matched_slots else 'knn_greedy'
        elif self.kind=='label_shuffle': policy='knn_greedy'
        else: raise ValueError(self.kind)
        if sum(x['outcome'] for x in state['revealed'])==0:
            policy='uniform_random'
            reason='Predeclared zero-positive fallback; spends ordinary query budget'
        else: reason=f'Prescribed {self.kind} selection'
        assert policy in allowed
        return {'policy':policy,'reason':reason}

def shuffled_labels(labels,seed):
    keys=sorted(labels)
    values=[labels[k] for k in keys]
    perm=sorted(keys,key=lambda k:(hashlib.sha256(f'labelshuffle|{seed}|{k}'.encode()).digest(),k))
    return {key:val for key,val in zip(perm,values)}

def run_one(candidates,labels,controller,seed,rep,matched_slots):
    model_labels=shuffled_labels(labels,seed) if controller=='label_shuffle' else labels
    oracle=BatchOracle(candidates,model_labels,seed=seed,total_budget=50,initialization_queries=10,batch_size=10)
    if controller=='fixed': ctrl=FixedController()
    elif controller=='random': ctrl=RandomController()
    else: ctrl=Controller(controller,seed,rep,matched_slots)
    result=run_campaign(candidates,oracle,ctrl,seed=seed,representation=rep)
    selections=[key for step in result['trajectory'] for key in step['selection']]
    assert len(selections)==len(set(selections))==50
    true_cumulative=[]
    total=0
    for step in result['trajectory']:
        total+=sum(labels[k] for k in step['selection'])
        true_cumulative.append(total)
    first=next((i for i,key in enumerate(selections,1) if labels[key]==1),None)
    assert first is not None
    return result,{'controller':controller,'representation':rep,'seed':seed,
                   'H50_true':true_cumulative[-1],'queries_to_first_hit':first,
                   'initialization_true_hits':sum(labels[k] for k in selections[:10]),
                   'fallback_batches':sum((s.get('decision') or {}).get('reason','').startswith('Predeclared zero-positive fallback') for s in result['trajectory']),
                   'cumulative_true':true_cumulative}

def write_csv(path,rows,cols):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');w.writeheader();w.writerows(rows)

def main():
    start=datetime.now(timezone.utc).isoformat()
    manifest=json.loads((FROZEN/'manifest.json').read_text())
    candidates=read_jsonl(Path(manifest['public_dir'])/'candidates.jsonl')
    labelrows=read_jsonl(Path(manifest['private_dir'])/'oracle_labels.jsonl')
    labels={r['compound_key']:r['outcome'] for r in labelrows}
    assert len(candidates)==len(labels)==231 and sum(labels.values())==116
    assert sha(FROZEN/'manifest.json')=='3866c7bfc99e92b8e0d6f92b98955d5e68a7ae202f609eac90d0e7a201f98235'
    modes=('fixed','random','fixed_schedule','rule_adaptive','random_mixture','matched_proportion','label_shuffle')
    # Across 20 seeds x four rounds, exactly 50 diverse and 30 greedy decisions.
    slots=[(seed,rnd) for seed in range(20) for rnd in range(1,5)]
    matched=set(sorted(slots,key=lambda x:hashlib.sha256(f'matched|{x[0]}|{x[1]}'.encode()).digest())[:50])
    OUT.mkdir(parents=True,exist_ok=False)
    (OUT/'runs').mkdir()
    rows=[]
    regressions=[]
    for rep in ('bit','count'):
        for seed in range(20):
            for mode in modes:
                result,summary=run_one(candidates,labels,mode,seed,rep,matched)
                if mode in ('fixed','random') and seed<5:
                    oldpath=PRIVATE/'runs_dyrk3_v1'/f'{mode}_{rep}_seed{seed}'/'run.json'
                    old=json.loads(oldpath.read_text())['result']
                    same=[s['selection'] for s in result['trajectory']]==[s['selection'] for s in old['trajectory']]
                    same_h=result['hits_at_budget']==old['hits_at_budget']
                    assert same and same_h,(mode,rep,seed)
                    regressions.append({'controller':mode,'representation':rep,'seed':seed,'same_selection':same,'same_H50':same_h})
                if mode!='label_shuffle': assert result['hits_at_budget']==summary['H50_true']
                path=OUT/'runs'/f'{mode}_{rep}_seed{seed}.json'
                path.write_text(json.dumps({'identity':{'controller':mode,'representation':rep,'seed':seed},
                                            'result':result,'true_evaluation':summary},ensure_ascii=False,sort_keys=True)+'\n')
                rows.append({k:(json.dumps(v) if isinstance(v,list) else v) for k,v in summary.items()})
    write_csv(OUT/'control_summary.csv',rows,list(rows[0]))
    by=defaultdict(list)
    for row in rows:by[(row['controller'],row['representation'])].append(int(row['H50_true']))
    group=[{'controller':k[0],'representation':k[1],'seeds':len(v),'mean_H50':statistics.mean(v),
            'sd_H50':statistics.stdev(v)} for k,v in sorted(by.items())]
    write_csv(OUT/'group_summary.csv',group,list(group[0]))
    (OUT/'regression_0_4.json').write_text(json.dumps(regressions,indent=2)+'\n')
    assert len(regressions)==20
    # Paired seed bootstrap, descriptive. Two prespecified comparisons on bit representation.
    indexed={(r['controller'],r['representation'],int(r['seed'])):int(r['H50_true']) for r in rows}
    comparisons=[]
    rng=random.Random(20261018)
    # For this CPU rehearsal compare new controls with the prescribed fixed control.
    for mode in ('fixed_schedule','rule_adaptive','random_mixture','matched_proportion','label_shuffle'):
        d=[indexed[(mode,'bit',s)]-indexed[('fixed','bit',s)] for s in range(20)]
        draws=sorted(statistics.mean(rng.choice(d) for _ in range(20)) for _ in range(10000))
        comparisons.append({'mode':mode,'reference':'fixed','representation':'bit','n_pairs':20,
                            'mean_paired_difference':statistics.mean(d),'bootstrap_95_low':draws[249],
                            'bootstrap_95_high':draws[9750],'post_exposure_descriptive':True})
    write_csv(OUT/'paired_bootstrap_descriptive.csv',comparisons,list(comparisons[0]))
    (OUT/'STATUS').write_text('done\n')
    (OUT/'RUN_LOG.md').write_text(
        'post-exposure 的证据整理，不是新 benchmark、盲验证或新 campaign。\n\n'
        f'Start UTC: {start}\nEnd UTC: {datetime.now(timezone.utc).isoformat()}\n'
        'Command: .venv/bin/python -B run_controls.py\n'
        f'Python: {platform.python_version()}\nSeeds: 0–19\nBootstrap: 10000 seed 20261018\n'
        f'Code SHA-256: {sha(__file__)}\nFrozen manifest SHA-256: {sha(FROZEN/"manifest.json")}\n'
        f'Original numerical tools SHA-256: {sha(ROOT/"campaign_v0/numerical_tools.py")}\n'
        f'Original campaign core SHA-256: {sha(ROOT/"campaign_v0/campaign_core.py")}\n'
        'No GLM or network calls. Labels only in private run directory.\n',encoding='utf-8')
    import numpy,scipy,rdkit
    with (OUT/'RUN_LOG.md').open('a') as f:f.write(f'NumPy {numpy.__version__}; SciPy {scipy.__version__}; RDKit {rdkit.__version__}\n')
    entries=[]
    for path in sorted(OUT.rglob('*')):
        if path.is_file() and path.name!='MANIFEST.json':entries.append({'path':path.relative_to(OUT).as_posix(),'bytes':path.stat().st_size,'sha256':sha(path)})
    (OUT/'MANIFEST.json').write_text(json.dumps({'files':entries,'self_excluded':True},indent=2)+'\n')
    print(json.dumps({'status':'done','runs':len(rows),'regressions':len(regressions),'group_summary':group,
                      'manifest_sha256':sha(OUT/'MANIFEST.json')},ensure_ascii=False))

if __name__=='__main__':main()

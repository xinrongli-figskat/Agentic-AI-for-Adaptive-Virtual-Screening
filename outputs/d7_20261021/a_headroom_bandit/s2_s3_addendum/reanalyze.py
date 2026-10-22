"""S2/S3 retrospective CPU arithmetic only; no campaigns or API clients."""
import argparse
import hashlib
import json
import math
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[3]
sys.path.insert(0,str(ROOT))
from outputs.d7_20261021.a_headroom_bandit.revision_11field.run_cpu import archive_read, MENU, BANDITS, ARCHIVE, ARCHIVE_SHA
ADDENDUM=ROOT/'outputs/d7_20261021/task_card_D7_addendum_20261021.md'
ADDENDUM_SHA='fb5b81850f20aa7353ca564a6615f78f85f8694a05dad71af1189e5e7f36ced8'
PRIOR=BASE.parent/'revision_11field'
D3=ROOT/'outputs/d3_tnap_20261019/d3_6_report'
D1=ROOT/'outputs/d_discrimination_20261018'
E=ROOT/'outputs/d7_20261021/e_record_fixes'

def utc():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,obj):
    p=BASE/name;assert not p.exists(),name
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
def verify_member(directory,rel):
    m=json.loads((directory/'MANIFEST.json').read_text())
    rows=m.get('members',m.get('files'))
    row=next(r for r in rows if r['path']==rel)
    assert sha(directory/rel)==row['sha256'],str(directory/rel)
    return row['sha256']
def pct(x):return np.quantile(x,[.025,.975]).tolist()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--lock',action='store_true');args=parser.parse_args()
    inputs={'addendum':(ADDENDUM,ADDENDUM_SHA),'D5_archive':(ARCHIVE,ARCHIVE_SHA),'D7_CPU_summary':(PRIOR/'cpu_summary.json',verify_member(PRIOR,'cpu_summary.json')),'D7_analysis':(PRIOR/'analysis.json',verify_member(PRIOR,'analysis.json')),'D3_aggregate':(D3/'aggregate.json',verify_member(D3,'aggregate.json')),'D1_summary':(D1/'d1_summary.md',verify_member(D1,'d1_summary.md')),'D7_E_corrected':(E/'corrected_baseline_checks.json',verify_member(E,'corrected_baseline_checks.json'))}
    for p,s in inputs.values():assert sha(p)==s
    if args.lock:
        save('execution_lock.json',{'post_exposure':True,'utc':utc(),'script_sha256':sha(__file__),'spec_sha256':sha(BASE/'SPEC.md'),'inputs':{k:{'path':str(p),'sha256':s} for k,(p,s) in inputs.items()},'glm_calls':0,'new_campaigns':0});return
    lock=json.loads((BASE/'execution_lock.json').read_text());assert sha(__file__)==lock['script_sha256'];assert sha(BASE/'SPEC.md')==lock['spec_sha256']
    source_text=(D1/'d1_summary.md').read_text()
    line=next(s for s in source_text.splitlines() if s.startswith('| **`fixed − label_shuffle`'))
    numbers=[float(v) for v in re.findall(r'[-+]?\d+(?:\.\d+)?',line)]
    assert numbers==[2.15,-.95,4.90,2.95,.70,5.30],numbers
    d3=json.loads((D3/'aggregate.json').read_text())['paired_contrasts']
    tn=d3['bit']['fixed-label_shuffle']
    pool_gate={'tnap':{'mean':tn['mean'],'ci95':[tn['ci_low'],tn['ci_high']],'source':'D3 bit primary','passes':tn['ci_low']>0 or tn['ci_high']<0},'dyrk3':{'mean':numbers[0],'ci95':numbers[1:3],'source':'D1 bit primary (cited by D4)','passes':numbers[1]>0 or numbers[2]<0,'count_sensitivity_mean':numbers[3],'count_sensitivity_ci95':numbers[4:6]}}
    rng=np.random.default_rng(20261018);indices=rng.integers(0,20,size=(10000,20))
    six=[p for p in MENU if p!='uniform_random'];fixed={};glm={};gates=[]
    with zipfile.ZipFile(ARCHIVE) as z:
        for pool in ('tnap','dyrk3'):
            for rep in ('bit','count'):
                x=np.asarray([[archive_read(z,pool,rep,'fixed_'+p,s)['H50'] for p in six] for s in range(20)],dtype=float)
                fixed[pool,rep]=x
                if pool=='tnap':glm[rep]=np.asarray([archive_read(z,pool,rep,'glm_extended',s)['H50'] for s in range(20)],dtype=float)
                new=np.ptp(x[indices].mean(axis=1),axis=1)
                old=np.ptp(x,axis=1)[indices].mean(axis=1)
                assert np.all(new<=old+1e-12)
                new_ci=pct(new);old_ci=pct(old)
                old_pass=old_ci[0]>=2
                new_pass=pool_gate[pool]['passes'] and new_ci[0]>=2
                assert not new_pass or old_pass
                gates.append({'pool':pool,'representation':rep,'six_fixed_policies':six,'spread_nontrivial':float(np.ptp(x.mean(axis=0))),'spread_nontrivial_ci95':new_ci,'old_paired_spread_ci95':old_ci,'pool_primary_discriminability':pool_gate[pool],'old_gate_pass':old_pass,'new_gate_pass':new_pass,'empirical_bootstrap_nesting_all_10000':True,'interpretation':'existing D5 cell only; does not authorize new surrogate GLM execution'})
    save('s2_gate_reanalysis.json',{'post_exposure':True,'utc':utc(),'seed':20261018,'resamples':10000,'threshold':2.0,'pool_gate_representation':'bit primary for both representation cells','nested_tightening_proof':'range(mean across sampled seeds)<=mean(range within each sampled seed), every resample; new gate adds conjunctive pool test','rows':gates,'glm_calls':0,'new_campaigns':0})
    # All adaptive-gap values use existing archived CPU/GLM outcomes only.
    rows=json.loads((PRIOR/'cpu_summary.json').read_text())['rows']
    lookup={(r['pool'],r['representation'],r['granularity'],r['arm'],r['seed']):r['H50'] for r in rows}
    gaps=[]
    for pool in ('tnap','dyrk3'):
        for rep,gs in [('bit',('g2','g4','g8')),('count',('g4',))]:
            for g in gs:
                x=fixed[pool,rep] if g=='g4' else np.asarray([[lookup[pool,rep,g,'fixed:'+p,s] for p in six] for s in range(20)],dtype=float)
                y=np.asarray([[lookup[pool,rep,g,p,s] for p in BANDITS] for s in range(20)],dtype=float)
                row={'pool':pool,'representation':rep,'granularity':g,'model_scope':'D5 expanded numerical menu (not a new surrogate-factor cell)','fixed_best_ties':[p for p,v in zip(six,x.mean(axis=0)) if v==x.mean(axis=0).max()],'bandit_best_ties':[p for p,v in zip(BANDITS,y.mean(axis=0)) if v==y.mean(axis=0).max()],'bandit_adaptive_gap':float(x.mean(axis=0).max()-y.mean(axis=0).max()),'bandit_gap_ci95_reselected':pct(x[indices].mean(axis=1).max(axis=1)-y[indices].mean(axis=1).max(axis=1)),'glm_adaptive_gap_status':'not_observed','all_fixed_vs_bandit':[]}
                for i,p in enumerate(six):
                    for j,a in enumerate(BANDITS):
                        diff=x[:,i]-y[:,j]
                        row['all_fixed_vs_bandit'].append({'fixed_policy':p,'adaptive_policy':a,'mean_gap':float(diff.mean()),'ci95':pct(diff[indices].mean(axis=1))})
                if pool=='tnap' and g=='g4':
                    vals=glm[rep];row['glm_adaptive_gap_status']='observed_single_saved_run_per_seed'
                    row['glm_adaptive_gap']=float(x.mean(axis=0).max()-vals.mean())
                    row['glm_gap_ci95_reselected']=pct(x[indices].mean(axis=1).max(axis=1)-vals[indices].mean(axis=1))
                    row['all_fixed_vs_glm']=[{'fixed_policy':p,'mean_gap':float((x[:,i]-vals).mean()),'ci95':pct((x[:,i]-vals)[indices].mean(axis=1))} for i,p in enumerate(six)]
                gaps.append(row)
    save('adaptive_gap_descriptive.json',{'post_exposure':True,'utc':utc(),'selection_warning':'Both maxima are selected after observing all seeds. Re-selecting in bootstrap describes this max statistic but does not remove selection bias or create independent validation. All arm contrasts are included; no optimal adaptive policy or confirmatory gain is claimed.','seed':20261018,'resamples':10000,'rows':gaps,'glm_calls':0,'new_campaigns':0})
    e=json.loads((E/'corrected_baseline_checks.json').read_text())
    differences=np.asarray([r['d6_H50']-r['d5_H50'] for r in e['per_seed']],dtype=float)
    sd=float(differences.std(ddof=1))
    supplied={('bit','bandit_thompson'):[.52,7.98],('bit','bandit_ucb1'):[3.24,12.36],('count','bandit_thompson'):[-.26,6.16],('count','bandit_ucb1'):[2.03,9.97]}
    estimates=[]
    for rep in ('bit','count'):
        for arm in BANDITS:
            b=np.asarray([lookup['tnap',rep,'g4',arm,s] for s in range(20)])
            diff=glm[rep]-b;mean=float(diff.mean());var=float(diff.var(ddof=1))
            half=1.96*math.sqrt(var/20+4.20**2/20)
            interval=[mean-half,mean+half]
            estimates.append({'representation':rep,'bandit':arm,'mean_glm_minus_bandit':mean,'paired_sample_variance':var,'noise_proxy_used':4.2,'formula':'mean +/- 1.96*sqrt(sample_var(paired_diff)/20 + 4.20^2/20)','computed_sensitivity_ci95':interval,'task_card_given_provisional_ci95':supplied[rep,arm],'matches_task_card_at_two_decimals':np.round(interval,2).tolist()==supplied[rep,arm],'count_extrapolation_assumed':rep=='count','benefit_claim_status':'BLOCKED_variance_definition_not_established'})
    save('variance_estimate_audit.json',{'post_exposure':True,'utc':utc(),'d6_bit_paired_differences':differences.tolist(),'paired_difference_sample_sd':sd,'sd_div_sqrt2_assuming_independent_equal_variance':sd/math.sqrt(2),'pooled_two_repeat_within_seed_sd_assuming_equal_variance':float(np.sqrt(np.mean(differences**2)/2)),'task_card_proxy':4.20,'definition_warning':'4.20 is a rounded SD of differences between two runs, not an independently measured per-run SD_model; across-seed paired variance already includes one realized model sample. Sensitivity arithmetic is not validated variance decomposition.','rows':estimates,'tier':'B_benefit_claim_only','glm_calls':0,'new_campaigns':0})
    print(json.dumps({'gates':gates,'paired_difference_sd':sd,'sensitivity_matches':[r['matches_task_card_at_two_decimals'] for r in estimates]},ensure_ascii=False))

if __name__=='__main__':main()

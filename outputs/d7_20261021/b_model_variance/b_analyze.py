"""D7-B read-only variance analysis of the completed, locked TNAP-bit repeats."""
from __future__ import annotations

import hashlib
import json
import math
import random
import statistics as st
import sys
from collections import Counter
from pathlib import Path

ROOT=Path('/driveA/xinrong/agentic-screening')
sys.path.insert(0,str(ROOT))
from outputs.d7_20261021.b_model_variance import b_repeat as old
from outputs.d7_20261021.b_model_variance import b_resume_v2 as resume
from outputs.d5_20261020.e_menu import analyze_results as d5_analysis

BASE=old.BASE
PRIVATE=old.PRIVATE
SEEDS=tuple(range(20))
REPS=tuple(range(1,6))


def avg(x): return sum(x)/len(x)


def pct(samples):
    samples=sorted(samples)
    return [samples[250],samples[9750]]


def one_draw_bootstrap(matrix, comparator,seed=20261018,n=10000):
    rng=random.Random(seed)
    out=[]
    for _ in range(n):
        chosen=[rng.randrange(20) for _ in SEEDS]
        out.append(avg([matrix[s][rng.randrange(5)]-comparator[s] for s in chosen]))
    return pct(out)


def loaded():
    resume.verify_lock()
    d5,d6,fixed=old.baseline()
    matrix={}
    runs={}
    for seed in SEEDS:
        sequence=[]
        for rep in REPS:
            p=(old.D6/f'glm_extended_seed{seed}'/'run.json' if rep==1 and seed<10
               else old.run_path(PRIVATE/f'rep{rep}',seed))
            assert p.exists(),(seed,rep)
            row=old.inspect_run(p,seed)
            sequence.append(row)
        runs[seed]=sequence
        matrix[seed]=[r['H50'] for r in sequence]
        first=[r['trajectory'][1]['glm_call']['public_summary'] for r in sequence]
        assert all(item==first[0] for item in first),f'first prompt mismatch seed {seed}'
    return d5,d6,fixed,runs,matrix


def comparators():
    best=[d5_analysis.read_run('tnap','bit','fixed:persistent_random_until_first_hit',s)['H50']
          for s in SEEDS]
    return {
        'fixed_best_single_posthoc':best,
        'random_mixture_extended':[d5_analysis.read_run('tnap','bit','random_mixture_extended',s)['H50'] for s in SEEDS],
        'matched_proportion_extended':[d5_analysis.read_run('tnap','bit','matched_proportion_extended',s)['H50'] for s in SEEDS],
        'glm_basic':[d5_analysis.prior_run('bit',s,'glm_basic')['hits_at_budget'] for s in SEEDS],
        'forced_random_coldstart':[d5_analysis.prior_run('bit',s,'forced_random_coldstart')['hits_at_budget'] for s in SEEDS],
    }


def main():
    analysis_lock=json.loads((BASE/'B_ANALYSIS_LOCK.json').read_text())
    assert old.sha(BASE/'b_analyze.py')==analysis_lock['analysis_code_sha256']
    assert old.sha(BASE/'B_SPEC.md')==analysis_lock['original_spec_sha256']
    assert old.sha(BASE/'B_ADDENDUM_AFTER_TIER_B.md')==analysis_lock['addendum_spec_sha256']
    assert analysis_lock['bootstrap_seed']==20261018 and analysis_lock['resamples']==10000
    d5,d6,fixed,runs,matrix=loaded()
    assert len(matrix)==20 and all(len(x)==5 for x in matrix.values())
    physical=resume.physical_count()
    assert physical<=380
    receipts=sorted(PRIVATE.glob('rep*/seed*/decision_*.json'))
    http=sorted(PRIVATE.glob('rep*/seed*/http_*.json'))
    assert len(http)==physical and len(receipts)<=physical+1
    valid=0;format_invalid=0;other_failed=0
    usage=Counter();latencies=[]
    for p in receipts:
        d=json.loads(p.read_text())
        if d['status']=='failure':
            other_failed+=1
            continue
        try:
            parsed=json.loads(d['raw_content'])
            is_valid=set(parsed)=={'policy','reason'} and isinstance(parsed['reason'],str)
        except (ValueError,TypeError,KeyError): is_valid=False
        if is_valid: valid+=1
        else: format_invalid+=1
        assert d['request_id'] and d['usage'] and d['elapsed_seconds']>=0
        latencies.append(d['elapsed_seconds'])
        for name in ('prompt_tokens','completion_tokens','total_tokens'):
            usage[name]+=d['usage'].get(name,0)
    assert format_invalid>=1 and valid+format_invalid+other_failed==len(receipts)
    for p in http:
        d=json.loads(p.read_text())
        assert 'raw_provider_response' in d or 'error_type' in d
        assert d['elapsed_seconds']>=0
    first_agree=Counter(); later_agree=Counter()
    for seed in SEEDS:
        paths=runs[seed]
        for a in range(5):
            for b in range(a+1,5):
                for rnd in range(1,5):
                    x=paths[a]['trajectory'][rnd]['decision']['policy']
                    y=paths[b]['trajectory'][rnd]['decision']['policy']
                    bucket=first_agree if rnd==1 else later_agree
                    bucket['pairs']+=1
                    bucket['same']+=x==y
    pooled_var=sum(st.variance(matrix[s])*4 for s in SEEDS)/(20*4)
    pooled_sd=math.sqrt(pooled_var)
    per_seed_sd={str(s):st.stdev(matrix[s]) for s in SEEDS}
    k_required=math.ceil(pooled_var/(20*0.5**2))
    means=[avg(matrix[s]) for s in SEEDS]
    historical=[r['H50'] for r in d5]
    results={}
    for name,c in comparators().items():
        historical_diff=[historical[s]-c[s] for s in SEEDS]
        repeat_diff=[means[s]-c[s] for s in SEEDS]
        between_observed=st.variance(repeat_diff)
        true_seed_var=max(0,between_observed-pooled_var/5)
        se_one=math.sqrt((true_seed_var+pooled_var)/20)
        se_five=math.sqrt((true_seed_var+pooled_var/5)/20)
        old_effect=avg(historical_diff)
        new_effect=avg(repeat_diff)
        historic_normal=[old_effect-1.96*se_one,old_effect+1.96*se_one]
        repeated_normal=[new_effect-1.96*se_five,new_effect+1.96*se_five]
        results[name]={
            'd5_historical_mean_difference':old_effect,
            'd5_original_seed_bootstrap_ci':d5_analysis.paired_bootstrap(historical_diff),
            'd5_reexpressed_one_run_variance_component_ci':historic_normal,
            'd5_reexpressed_ci_excludes_zero':historic_normal[0]>0 or historic_normal[1]<0,
            'five_repeat_mean_difference':new_effect,
            'one_run_stratified_bootstrap_ci':one_draw_bootstrap(matrix,c),
            'five_repeat_variance_component_ci':repeated_normal,
            'five_repeat_ci_excludes_zero':repeated_normal[0]>0 or repeated_normal[1]<0,
            'estimated_true_seed_variance':true_seed_var,
            'model_variance':pooled_var,
            'one_run_se':se_one,'five_repeat_se':se_five,
        }
    summary={
        'generated_utc':old.utc(),'post_exposure':True,
        'status':'complete' if k_required<=5 else 'blocked_tier_b_variance_unaffordable',
        'target':'TNAP','representation':'bit','menu':'D5 V0 unchanged',
        'campaigns_total':100,'d6_existing_campaigns':10,'new_campaigns':90,
        'new_physical_http_requests':physical,'new_decision_receipts':len(receipts),
        'valid_new_decisions':valid,'format_invalid_decisions':format_invalid,
        'other_failed_decisions':other_failed,
        'returned_usage_new_requests':dict(usage),'decision_latency_mean_seconds':avg(latencies),
        'first_round_public_summary_equal_within_each_seed':True,
        'first_round_pairwise_policy_agreement':first_agree['same']/first_agree['pairs'],
        'first_round_pair_count':first_agree['pairs'],
        'later_round_pairwise_policy_agreement':later_agree['same']/later_agree['pairs'],
        'later_round_pairs_state_divergence_caveat':True,
        'pooled_within_seed_sd_model':pooled_sd,
        'per_seed_sd_summary':{'min':min(per_seed_sd.values()),'median':st.median(per_seed_sd.values()),
                               'max':max(per_seed_sd.values())},
        'model_noise_se_at_five_repeats':pooled_sd/math.sqrt(20*5),
        'minimum_repeats_for_model_noise_se_le_0_5':k_required,
        'b3_gate_pass':k_required<=5,
        'd6_sd_4_20_note':'D6 4.20 was SD of two-run differences, not a directly measured single-run model SD.',
        'seed_variance_note':'True seed variance estimated by subtracting within-seed model variance/k from between-seed repeat-mean variance, truncated at zero; normal CIs descriptive and do not correct multiplicity.',
        'comparisons':results,
        'public_note':'No molecule-level outcome, selection, or trajectory is included.'
    }
    old.save(BASE/'B_ANALYSIS.json',summary)
    old.save(PRIVATE/'replicate_matrix.json',{'matrix':matrix,'per_seed_sd':per_seed_sd})
    if k_required>5:
        (BASE/'BLOCKED_variance_unaffordable.md').write_text(
            '# D7-B3 Tier B stop\n\n'
            f'Pooled within-seed SD_model={pooled_sd:.3f}; k_required={k_required}>5 '
            'for model-noise SE <=0.5 across 20 seeds. The preregistered five repeats '
            'are insufficient. Do not run D7-C LLM arms. Independent CPU work continues.\n',
            encoding='utf-8')
    print(json.dumps({'status':summary['status'],'physical':physical,'sd_model':pooled_sd,
                      'k_required':k_required,'b3_gate_pass':summary['b3_gate_pass']},ensure_ascii=False))

if __name__=='__main__': main()

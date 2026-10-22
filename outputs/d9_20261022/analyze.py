"""Checkpoint and paired analysis for D9, without modifying historical outputs."""
from __future__ import annotations

import hashlib
import json
import math
import random
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PRIVATE = HERE / "d9_private"
C4 = ROOT / "outputs/d7_20261021/c4_five_private/runs"
C3 = ROOT / "outputs/d7_20261021/c_surrogate_factor_v2_orthogonal_five_private/runs/TNAP/S_strong"
C3_FIXED = ROOT / "outputs/d7_20261021/c_surrogate_factor_v2_orthogonal_private/runs/TNAP/S_strong"
REQUIRED = ("full_library_462", "no_unqueried_outcome_field",
            "no_hidden_pool_aggregates", "revealed_results_selected_only")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)+"\n", encoding="utf-8")


def percentile(values, p):
    values=sorted(values)
    pos=(len(values)-1)*p
    i=int(pos)
    return values[i]+(values[min(i+1,len(values)-1)]-values[i])*(pos-i)


def paired(diffs, noise_sd=0.0):
    rng=random.Random(20261018)
    means=[]
    for _ in range(10000):
        mean=sum(diffs[rng.randrange(len(diffs))] for _ in diffs)/len(diffs)
        if noise_sd:
            mean+=rng.gauss(0,noise_sd)
        means.append(mean)
    return [percentile(means,.025),percentile(means,.975)]


def inspect(start,end):
    runs=[]
    policies=Counter()
    realized=Counter()
    per_call=[]
    for seed in range(start,end):
        path=PRIVATE/"runs"/f"seed{seed}"/"run.json"
        run=read(path)
        if (not run["complete"] or run["arm"]!="llm_library_visible" or
            run["seed"]!=seed or run["queried_count"]!=50 or len(run["trajectory"])!=5):
            raise RuntimeError(f"D9 campaign invalid: {seed}")
        c4=read(C4/"rep1"/f"seed{seed}"/"run.json")
        if run["trajectory"][0]["selection"]!=c4["trajectory"][0]["selection"]:
            raise RuntimeError(f"D9 initialization mismatch: {seed}")
        keys=[k for step in run["trajectory"] for k in step["selection"]]
        if len(set(keys))!=50:
            raise RuntimeError(f"D9 repeat query: {seed}")
        if run["H50"]!=sum(int(o["outcome"]) for step in run["trajectory"] for o in step["observations"]):
            raise RuntimeError(f"D9 H50 mismatch: {seed}")
        for step in run["trajectory"][1:]:
            policies[step["policy"]]+=1
            realized[step["realized_behavior"]]+=1
            if step["glm_call"] is not None:
                call=step["glm_call"]
                if not all(call["information_boundary_assertions"].get(x) is True for x in REQUIRED):
                    raise RuntimeError(f"D9 boundary failed in run: {seed}")
                per_call.append(call)
        runs.append({"seed":seed,"H50":run["H50"],
                     "policy_counts":dict(Counter(s["policy"] for s in run["trajectory"][1:])),
                     "realized_behavior_counts":dict(Counter(s["realized_behavior"] for s in run["trajectory"][1:]))})
    http_paths=sorted((PRIVATE/"http").glob("http_*.json"))
    http=[read(p) for p in http_paths]
    if len(http)>88 or any(not all(x.get("information_boundary_assertions",{}).get(k) is True for k in REQUIRED) for x in http):
        raise RuntimeError("D9 physical cap or HTTP information-boundary receipt invalid")
    attempt_paths=list((PRIVATE/"runs").glob("seed*/decision_round*_try*.json"))
    attempts=[read(p) for p in attempt_paths]
    invalid=sum(a["status"]=="invalid_format" for a in attempts)
    if invalid and any(a["format_attempt"]>2 for a in attempts):
        raise RuntimeError("D9 format retry limit violated")
    result={"status":"pass", "seed_range":[start,end], "complete_campaigns":len(runs),
            "runs":runs,"policy_name_counts":dict(policies),
            "realized_behavior_counts":dict(realized),
            "model_decisions":len(per_call),"physical_calls_total_so_far":len(http),
            "invalid_format_responses_total_so_far":invalid,
            "invalid_format_fraction_per_physical_call":invalid/len(http) if http else 0,
            "four_runtime_assertions_per_model_call":{name:True for name in REQUIRED},
            "four_runtime_assertions_per_HTTP_attempt":{name:True for name in REQUIRED},
            "initializations_equal_C4":True,"unique_queries_50_each":True}
    return result


def checkpoint():
    result=inspect(0,10)
    if result["complete_campaigns"]!=10:
        raise RuntimeError("D9 checkpoint incomplete")
    write(HERE/"CHECKPOINT_0_9.json",result)
    return result


def final():
    checkpoint_result=read(HERE/"CHECKPOINT_0_9.json")
    if checkpoint_result["status"]!="pass" or checkpoint_result["complete_campaigns"]!=10:
        raise RuntimeError("D9 checkpoint not passed")
    all_runs=inspect(0,20)
    if all_runs["complete_campaigns"]!=20:
        raise RuntimeError("D9 full run incomplete")
    c4_by_seed=[]
    for seed in range(20):
        values=[read(C4/f"rep{rep}"/f"seed{seed}"/"run.json")["H50"] for rep in (1,2)]
        c4_by_seed.append(sum(values)/2)
    if sum(c4_by_seed)/20 != 11.325:
        raise RuntimeError("C4 mean regression failed")
    fixed={}
    for arm,expected in (("greedy",16.65),("diverse",9.65),("bandit_thompson",13.15)):
        parent = C3 if arm == "bandit_thompson" else C3_FIXED
        values=[read(parent/arm/f"seed{seed}.json")["H50"] for seed in range(20)]
        if sum(values)/20 != expected:
            raise RuntimeError(f"C3 {arm} mean regression failed")
        fixed[arm]=values
    d9=[row["H50"] for row in all_runs["runs"]]
    cpu=read(PRIVATE/"FREQUENCY_MATCHED_CPU_RESULTS.json")["cells"]["S_strong"]["mixture_H50_by_seed"]
    refs={"C4_policy_only_two_repeats_mean":c4_by_seed,
          "fixed_greedy":fixed["greedy"],"fixed_diverse":fixed["diverse"],
          "bandit_thompson":fixed["bandit_thompson"],"frequency_matched_CPU_mix":cpu}
    sigma=2.1943108257491692
    comparisons={}
    for name,ref in refs.items():
        diff=[d9[i]-ref[i] for i in range(20)]
        comparison={"reference_mean":sum(ref)/20,"D9_mean":sum(d9)/20,
                    "mean_difference":sum(diff)/20,"paired_seed_bootstrap_95_interval":paired(diff),
                    "paired_differences_by_seed":diff}
        if name=="C4_policy_only_two_repeats_mean":
            se=sigma*math.sqrt(1/20+1/40)
            comparison["B_model_SD"]=sigma
            comparison["model_noise_SE_added_to_bootstrap"]=se
            comparison["paired_bootstrap_plus_model_noise_95_interval"]=paired(diff,se)
        comparisons[name]=comparison
    receipts=[read(p) for p in sorted((PRIVATE/"runs").glob("seed*/decision_round*_try*.json"))]
    usage=[r.get("usage") for r in receipts if r.get("usage")]
    valid=sum(r["status"]=="valid_decision" for r in receipts)
    prompt=sum(int(u.get("prompt_tokens") or 0) for u in usage)
    completion=sum(int(u.get("completion_tokens") or 0) for u in usage)
    total=sum(int(u.get("total_tokens") or 0) for u in usage)
    result={"status":"complete", "post_exposure":True,
            "experiment":"TNAP/S_strong/bit/llm_library_visible/one_repeat",
            "runs":all_runs["runs"], "mean_D9_H50":sum(d9)/20,
            "D9_H50_by_seed":d9,"policy_name_counts":all_runs["policy_name_counts"],
            "realized_behavior_counts":all_runs["realized_behavior_counts"],
            "physical_calls":all_runs["physical_calls_total_so_far"],
            "project_cumulative_physical_estimate":683+all_runs["physical_calls_total_so_far"],
            "valid_decisions":valid,"invalid_format_responses":all_runs["invalid_format_responses_total_so_far"],
            "format_failure_fraction_per_physical_call":all_runs["invalid_format_fraction_per_physical_call"],
            "returned_usage":{"prompt_tokens":prompt,"completion_tokens":completion,
                              "total_tokens":total,"receipts_with_usage":len(usage),
                              "average_prompt_tokens_per_valid_decision":prompt/valid if valid else None},
            "information_boundary_assertions":all_runs["four_runtime_assertions_per_HTTP_attempt"],
            "comparisons":comparisons}
    write(HERE/"D9_ANALYSIS.json",result)
    return {k:result[k] for k in ("status","mean_D9_H50","policy_name_counts","realized_behavior_counts","physical_calls","valid_decisions","invalid_format_responses","returned_usage","comparisons")}


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=("checkpoint","final"))
    args=p.parse_args()
    print(json.dumps(checkpoint() if args.command=="checkpoint" else final(),ensure_ascii=False,indent=2))

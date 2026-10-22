"""Read-only D5 analysis of locked TNAP/DYRK3 runs."""

from __future__ import annotations

import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from outputs.d5_20261020.e_menu.expanded_tools import MENU
from outputs.d5_20261020.e_menu.run_extended import BASE, PRIVATE_OUT, ROOT, sha, utc, validate_sources

SEEDS = tuple(range(20))
REPS = ("bit", "count")
POOLS = ("tnap", "dyrk3")
FIXED = tuple(f"fixed:{policy}" for policy in MENU)
CPU_ARMS = FIXED + ("random_mixture_extended", "matched_proportion_extended")


def run_path(pool, rep, arm, seed):
    return PRIVATE_OUT / "runs" / pool / rep / f"{arm.replace(':', '_')}_seed{seed}" / "run.json"


def read_run(pool, rep, arm, seed):
    path = run_path(pool, rep, arm, seed)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["complete"] and data["queried_count"] == 50
    assert (data["pool"], data["representation"], data["arm"], data["seed"]) == (pool, rep, arm, seed)
    trajectory = data["trajectory"]
    assert len(trajectory) == 5 and len(trajectory[0]["selection"]) == 10
    selections = [key for step in trajectory for key in step["selection"]]
    assert len(selections) == len(set(selections)) == 50
    assert data["H50"] == sum(row["outcome"] for step in trajectory for row in step["observations"])
    return data


def prior_run(rep, seed, kind):
    if kind == "glm_basic":
        path = ROOT / f"outputs/d4_tnap_glm_20261019/d4_glm_private_20261019/runs/llm_{rep}_seed{seed}/run.json"
    else:
        assert kind == "forced_random_coldstart"
        path = ROOT / f"outputs/d3_tnap_20261019/d3_6_runs_private_20261019/forced_random_coldstart_{rep}_seed{seed}.json"
    d = json.loads(path.read_text(encoding="utf-8"))["result"]
    assert d["queried_count"] == 50
    return d


def mean(values):
    return sum(values) / len(values)


def paired_bootstrap(differences, seed=20261020, n=10000):
    rng = random.Random(seed)
    N = len(differences)
    samples = sorted(mean([differences[rng.randrange(N)] for _ in range(N)]) for _ in range(n))
    return [samples[int(n * 0.025)], samples[int(n * 0.975)]]


def summarize(values):
    return {"mean": mean(values), "min": min(values), "max": max(values), "values_by_seed": list(values)}


def checkpoint_means(group):
    return {str(budget): mean([d["trajectory"][budget // 10 - 1]["cumulative_hits"] for d in group])
            for budget in (10, 20, 30, 40, 50)}


def compare(lhs, rhs):
    differences = [a - b for a, b in zip(lhs, rhs)]
    return {"mean_paired_difference": mean(differences),
            "bootstrap_95_percent_descriptive": paired_bootstrap(differences),
            "differences_by_seed": differences}


def main():
    validate_sources()
    weights_path = BASE / "e_menu_matched_weights.json"
    weights_lock = json.loads((BASE / "e_menu_matched_weights_lock.json").read_text())
    assert sha(weights_path) == weights_lock["weights_sha256"]
    assert weights_lock["decision_slots"] == 160
    checkpoint = json.loads((BASE / "e_menu_bit_checkpoint.json").read_text())
    assert checkpoint["first_checkpoint_decision_slots"] == checkpoint["glm_calls"] == 40

    runs = {}
    for pool in POOLS:
        for rep in REPS:
            for arm in CPU_ARMS + (("glm_extended",) if pool == "tnap" else ()):
                runs[pool, rep, arm] = [read_run(pool, rep, arm, seed) for seed in SEEDS]

    initial_mismatches = []
    for pool in POOLS:
        for rep in REPS:
            for seed in SEEDS:
                reference = runs[pool, rep, CPU_ARMS[0]][seed]["trajectory"][0]["selection"]
                for arm in CPU_ARMS + (("glm_extended",) if pool == "tnap" else ()):
                    if runs[pool, rep, arm][seed]["trajectory"][0]["selection"] != reference:
                        initial_mismatches.append([pool, rep, seed, arm])
                if pool == "tnap":
                    for kind in ("glm_basic", "forced_random_coldstart"):
                        if prior_run(rep, seed, kind)["trajectory"][0]["selection"] != reference:
                            initial_mismatches.append([pool, rep, seed, kind])
    assert not initial_mismatches

    metrics = {}
    for pool in POOLS:
        metrics[pool] = {}
        for rep in REPS:
            per_arm = {}
            for arm in CPU_ARMS + (("glm_extended",) if pool == "tnap" else ()):
                group = runs[pool, rep, arm]
                per_arm[arm] = summarize([d["H50"] for d in group])
                per_arm[arm]["mean_cumulative_hits_at_queries"] = checkpoint_means(group)
                per_arm[arm]["mean_queries_to_first_hit"] = mean([
                    d["queries_to_first_hit"] if d["queries_to_first_hit"] is not None else 51 for d in group])
                per_arm[arm]["censored_first_hits"] = sum(d["first_hit_right_censored"] for d in group)
                per_arm[arm]["mean_selection_seconds_recorded"] = mean([
                    d["selection_seconds_total"] for d in group])
            metrics[pool][rep] = per_arm

    comparisons = {}
    policy_counts = Counter()
    glm_calls = 0
    http_attempts = 0
    glm_usage = Counter()
    glm_latency = []
    policy_counts_by_revealed_state = {"zero_hits": Counter(), "one_or_more_hits": Counter()}
    for rep in REPS:
        E = [d["H50"] for d in runs["tnap", rep, "glm_extended"]]
        fixed_means = {arm: metrics["tnap"][rep][arm]["mean"] for arm in FIXED}
        # The locked spec resolves tied means by MENU order, not name order.
        best = min(FIXED, key=lambda arm: (-fixed_means[arm], FIXED.index(arm)))
        comparators = {"fixed_best_single_posthoc": [d["H50"] for d in runs["tnap", rep, best]],
                       "random_mixture_extended": [d["H50"] for d in runs["tnap", rep, "random_mixture_extended"]],
                       "matched_proportion_extended": [d["H50"] for d in runs["tnap", rep, "matched_proportion_extended"]],
                       "glm_basic": [prior_run(rep, seed, "glm_basic")["hits_at_budget"] for seed in SEEDS],
                       "forced_random_coldstart": [prior_run(rep, seed, "forced_random_coldstart")["hits_at_budget"] for seed in SEEDS]}
        comparisons[rep] = {"posthoc_best_single_arm": best,
                            "comparisons": {name: compare(E, values) for name, values in comparators.items()},
                            "glm_basic": summarize(comparators["glm_basic"]),
                            "forced_random_coldstart": summarize(comparators["forced_random_coldstart"])}
        for d in runs["tnap", rep, "glm_extended"]:
            for step in d["trajectory"][1:]:
                policy_counts[step["decision"]["policy"]] += 1
                state_bucket = "zero_hits" if step["information_available"]["revealed_hits"] == 0 else "one_or_more_hits"
                policy_counts_by_revealed_state[state_bucket][step["decision"]["policy"]] += 1
                call = step.get("glm_call")
                if call is not None:
                    glm_calls += 1
                    http_attempts += len(call.get("api_attempt_log") or [])
                    usage = call.get("usage") or {}
                    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                        if usage.get(key) is not None:
                            glm_usage[key] += usage[key]
                    glm_latency.append(call["decision_seconds"])
    assert glm_calls <= 160 and sum(policy_counts.values()) == 160

    init_zero_seeds = {
        rep: [seed for seed in SEEDS
              if runs["tnap", rep, "glm_extended"][seed]["trajectory"][0]["cumulative_hits"] == 0]
        for rep in REPS
    }
    coldstart_strata = {}
    for rep in REPS:
        coldstart_strata[rep] = {}
        for stratum, seeds in (("zero_hit_initialization", init_zero_seeds[rep]),
                               ("at_least_one_hit_initialization", [s for s in SEEDS if s not in init_zero_seeds[rep]])):
            coldstart_strata[rep][stratum] = {
                "seeds": seeds,
                "glm_mean_H50": mean([runs["tnap", rep, "glm_extended"][s]["H50"] for s in seeds]) if seeds else None,
                "random_mixture_mean_H50": mean([runs["tnap", rep, "random_mixture_extended"][s]["H50"] for s in seeds]) if seeds else None,
                "forced_random_coldstart_mean_H50": mean([prior_run(rep, s, "forced_random_coldstart")["hits_at_budget"] for s in seeds]) if seeds else None,
            }

    # The DYRK3 negative control has no cold-start seed. Its cold-start repair
    # must therefore be exactly behaviorally identical to the inherited tools.
    negative_control = {}
    for rep in REPS:
        greedy = runs["dyrk3", rep, "fixed:knn_greedy"]
        persistent = runs["dyrk3", rep, "fixed:persistent_random_until_first_hit"]
        diverse = runs["dyrk3", rep, "fixed:knn_diverse"]
        diverse_repair = runs["dyrk3", rep, "fixed:diverse_random_coldstart"]
        zero_hit_initializations = sum(d["trajectory"][0]["cumulative_hits"] == 0 for d in greedy)
        negative_control[rep] = {
            "zero_hit_initializations": zero_hit_initializations,
            "greedy_vs_persistent_identical_trajectories": sum(
                [x["selection"] for x in a["trajectory"]] == [x["selection"] for x in b["trajectory"]]
                for a, b in zip(greedy, persistent)),
            "diverse_vs_coldstart_repair_identical_trajectories": sum(
                [x["selection"] for x in a["trajectory"]] == [x["selection"] for x in b["trajectory"]]
                for a, b in zip(diverse, diverse_repair)),
        }

    result = {"generated_utc": utc(), "post_exposure": True,
              "spec_sha256": sha(BASE / "d5_menu_spec.md"),
              "code_lock_sha256": sha(BASE / "e_menu_code_lock.json"),
              "weights_sha256": sha(weights_path),
              "runs_verified": len(POOLS) * len(REPS) * len(SEEDS) * len(CPU_ARMS) + len(REPS) * len(SEEDS),
              "initialization_mismatches": initial_mismatches,
              "glm_calls": glm_calls, "http_attempts": http_attempts,
              "glm_usage_returned": dict(glm_usage),
              "glm_mean_decision_seconds": mean(glm_latency) if glm_latency else None,
              "glm_policy_counts_all_slots": dict(policy_counts),
              "glm_policy_counts_by_revealed_state": {key: dict(value) for key, value in policy_counts_by_revealed_state.items()},
              "tnap_initial_zero_hit_seeds": init_zero_seeds,
              "tnap_coldstart_strata": coldstart_strata,
              "metrics": metrics, "comparisons": comparisons,
              "dyrk3_negative_control": negative_control,
              "statistical_note": "Seed-paired percentile bootstrap, 10000 resamples; descriptive, no multiplicity correction. Fixed-best single arm selected posthoc on same data."}
    path = BASE / "e_menu_results.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"runs_verified": result["runs_verified"], "glm_calls": glm_calls,
                      "result_sha256": sha(path), "comparisons_bit": comparisons["bit"],
                      "negative_control": negative_control}, ensure_ascii=False))


if __name__ == "__main__":
    main()

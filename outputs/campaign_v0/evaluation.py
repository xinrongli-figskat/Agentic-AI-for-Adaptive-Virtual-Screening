"""Evaluate complete campaign trajectories using revealed outcomes only."""

from collections import defaultdict
from math import sqrt


CHECKPOINTS = (10, 20, 30, 40, 50)


def check_run(run):
    trajectory = run["trajectory"]
    if run.get("queried_count") != 50 or len(trajectory) != 5:
        raise ValueError("Expected a complete 10+4x10 campaign")
    ids = []
    hits = []
    for step in trajectory:
        chosen = step["selection"]
        observed = step["observations"]
        if len(chosen) != 10 or [row["compound_key"] for row in observed] != chosen:
            raise ValueError("Query/observation order or batch size is inconsistent")
        if any(row["outcome"] not in (0, 1) for row in observed):
            raise ValueError("Non-binary observed outcome")
        ids.extend(chosen)
        hits.extend(row["outcome"] for row in observed)
        if step["cumulative_hits"] != sum(hits):
            raise ValueError("Incorrect cumulative hit count")
    if len(set(ids)) != 50 or run["hits_at_budget"] != sum(hits):
        raise ValueError("Repeated ID or incorrect H@50")
    if run["hit_recovery_checkpoints"] != [step["cumulative_hits"] for step in trajectory]:
        raise ValueError("Checkpoint count mismatch")
    return ids


def summarize_run(run):
    check_run(run)
    h = run["hit_recovery_checkpoints"]
    auc = sum((h[i] + h[i + 1]) / 2 for i in range(4)) / 4
    usage = [step.get("llm_call", {}).get("api_usage")
             for step in run["trajectory"][1:] if step.get("llm_call")]
    usage = [row for row in usage if isinstance(row, dict)]
    attempt_logs = [step.get("llm_call", {}).get("api_attempt_log")
                    for step in run["trajectory"][1:] if step.get("llm_call")]
    attempts = [item for log in attempt_logs if isinstance(log, list) for item in log]
    return {"controller": run["controller"], "seed": run["seed"],
            "representation": run.get("representation", "bit"),
            "h_at_50": h[-1], "h_checkpoints": h,
            "round_hits": [h[0]] + [h[i] - h[i - 1] for i in range(1, 5)],
            "auc_10_50_average_cumulative_hits": auc,
            "feature_build_seconds": run["feature_build_seconds"],
            "analysis_seconds_total": run.get("analysis_seconds_total", 0.0),
            "selection_seconds_total": run["selection_seconds_total"],
            "decision_seconds_total": run.get("decision_seconds_total", 0.0),
            "prompt_tokens": sum(row.get("prompt_tokens", 0) for row in usage),
            "completion_tokens": sum(row.get("completion_tokens", 0) for row in usage),
            "reasoning_tokens": sum(row.get("completion_tokens_details", {}).get("reasoning_tokens", 0)
                                    for row in usage),
            "api_calls_with_usage": len(usage),
            "api_attempts_total": len(attempts),
            "api_overload_rejections": sum(item.get("business_code") == "1305"
                                           for item in attempts)}


def compare_paired(runs, agent_name="llm_policy_choice",
                   fixed_name="prescribed_knn_greedy",
                   random_name="uniform_random_reference"):
    """Require identical seeds and initialization before computing paired results."""
    grouped = defaultdict(dict)
    for run in runs:
        check_run(run)
        key = (run.get("representation", "bit"), run["seed"])
        if run["controller"] in grouped[key]:
            raise ValueError("Duplicate controller/representation/seed run")
        grouped[key][run["controller"]] = run
    result = []
    for (representation, seed), by_controller in sorted(grouped.items()):
        if set(by_controller) != {agent_name, fixed_name, random_name}:
            raise ValueError("Missing matched controller for a seed")
        initial = [tuple(run["trajectory"][0]["selection"]) for run in by_controller.values()]
        if len(set(initial)) != 1:
            raise ValueError("Controllers did not share initialization")
        a, f, r = (by_controller[name]["hits_at_budget"] for name in
                   (agent_name, fixed_name, random_name))
        result.append({"representation": representation, "seed": seed,
                       "llm_h_at_50": a, "fixed_h_at_50": f, "random_h_at_50": r,
                       "llm_minus_fixed": a - f, "llm_minus_random": a - r})
    def mean(values):
        return sum(values) / len(values)
    def sample_sd(values):
        return sqrt(sum((value - mean(values)) ** 2 for value in values) / (len(values) - 1)) \
               if len(values) > 1 else None
    by_representation = {}
    for representation in sorted({row["representation"] for row in result}):
        subset = [row for row in result if row["representation"] == representation]
        differences = [row["llm_minus_fixed"] for row in subset]
        random_hits = [row["random_h_at_50"] for row in subset]
        by_representation[representation] = {
            "seed_count": len(subset),
            "mean_llm_minus_fixed": mean(differences),
            "sample_sd_llm_minus_fixed": sample_sd(differences),
            "random_mean_h_at_50": mean(random_hits),
            "random_sample_sd_h_at_50": sample_sd(random_hits),
        }
    return {"paired_runs": result, "by_representation": by_representation}

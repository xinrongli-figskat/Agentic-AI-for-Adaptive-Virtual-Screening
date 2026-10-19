"""Analyze the locked D2-2 extension without making GLM or oracle calls."""
import csv
import hashlib
import json
import random
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/driveA/xinrong/agentic-screening")
ATTEMPT = ROOT / "outputs/d2_controls_20261019/attempt2_20261019"
PRIVATE = ROOT / "outputs/d2_controls_20261019/d2_glm_private_20261019"
OLD = ROOT / "data/curation_private/runs_dyrk3_v1"
R5 = ROOT / "data/curation_private/r5_cpu_controls_private_20261018/control_summary.csv"
D1 = ROOT / "outputs/d_discrimination_20261018/d1_descriptor_association_private_/structure_prior_runs.csv"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def paired(values):
    rng = random.Random(20261018)
    draws = sorted(statistics.mean(rng.choice(values) for _ in values) for _ in range(10000))
    return {"n_pairs": len(values), "mean_H50_difference": statistics.mean(values),
            "bootstrap_95_low": draws[249], "bootstrap_95_high": draws[9750],
            "paired_sd": statistics.stdev(values)}


def first_hit_index(run):
    outcomes = [obs["outcome"] for step in run["trajectory"] for obs in step["observations"]]
    return next((i for i, value in enumerate(outcomes, start=1) if value == 1), None)


def auc(run):
    curve = run["hit_recovery_checkpoints"]
    assert len(curve) == 5
    return sum((curve[i] + curve[i + 1]) / 2 for i in range(4)) / 4


def load_runs():
    old_hashes = json.loads((ATTEMPT / "d2_preflight/old_glm_run_hashes.json").read_text())
    runs = {}
    new_hashes = {}
    for rep in ("bit", "count"):
        for seed in range(20):
            if seed < 5:
                path = OLD / f"llm_{rep}_seed{seed}/run.json"
                assert sha(path) == old_hashes[f"{rep}_seed{seed}"], (rep, seed)
            else:
                path = PRIVATE / f"runs/llm_{rep}_seed{seed}/run.json"
                new_hashes[f"{rep}_seed{seed}"] = sha(path)
            saved = json.loads(path.read_text())
            assert saved["status"] == "complete"
            assert saved["seed"] == seed and saved["representation"] == rep
            run = saved["result"]
            assert run["queried_count"] == 50 and len(run["trajectory"]) == 5
            selections = [key for step in run["trajectory"] for key in step["selection"]]
            assert len(selections) == len(set(selections)) == 50
            assert len(run["hit_recovery_checkpoints"]) == 5
            assert run["hits_at_budget"] == run["hit_recovery_checkpoints"][-1]
            assert sum(obs["outcome"] for step in run["trajectory"] for obs in step["observations"]) == run["hits_at_budget"]
            assert all(step.get("llm_call") and step["llm_call"]["model"] == "glm-5.3-flash"
                       for step in run["trajectory"][1:])
            runs[rep, seed] = run
    return runs, old_hashes, new_hashes


def manifest(directory):
    files = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name != "MANIFEST.json":
            files.append({"path": path.relative_to(directory).as_posix(),
                          "bytes": path.stat().st_size, "sha256": sha(path)})
    atomic_json(directory / "MANIFEST.json", {"files": files, "self_excluded": True})


def main():
    assert (ATTEMPT / "d2_preflight/STATUS").read_text().strip() == "done"
    lock = json.loads((ATTEMPT / "pre_real_declarations_lock.json").read_text())
    first_start = (PRIVATE / "RUN_LOG.md").read_text().split("First real-call run started UTC: ")[1].splitlines()[0]
    assert lock["locked_utc"] < first_start, "Power and budget not locked before real call"
    runs, old_hashes, new_hashes = load_runs()
    r5 = {(row["controller"], row["representation"], int(row["seed"])): row
          for row in csv.DictReader(R5.open(newline="", encoding="utf-8"))}
    struct = {(row["representation"], int(row["seed"])): int(row["H50_true"])
              for row in csv.DictReader(D1.open(newline="", encoding="utf-8"))}
    assert len(r5) == 280 and len(struct) == 40
    comparisons = {}
    for rep in ("bit", "count"):
        comparisons[rep] = {}
        for floor in ("structure_prior", "fixed", "label_shuffle", "matched_proportion", "random"):
            values = []
            for seed in range(20):
                base = struct[rep, seed] if floor == "structure_prior" else int(r5[floor, rep, seed]["H50_true"])
                values.append(runs[rep, seed]["hits_at_budget"] - base)
            comparisons[rep][floor] = paired(values)
    strategy = {}
    cost = {"new_successful_decisions": 0, "new_http_attempts": 0,
            "new_failed_http_attempts": 0, "new_request_ids": 0,
            "prompt_tokens_returned": 0, "completion_tokens_returned": 0,
            "reasoning_tokens_returned": 0, "returned_usage_missing_decisions": 0,
            "decision_seconds_including_retries": 0.0,
            "feature_build_seconds": 0.0, "numerical_analysis_seconds": 0.0,
            "selection_seconds": 0.0,
            "data_acquisition_seconds": None,
            "data_acquisition_note": "unknown; frozen source acquisition was outside these campaign runs"}
    old_cost = {"old_completed_decisions": 0, "old_recorded_http_attempts_in_completed_decisions": 0,
                "old_prompt_tokens_returned_in_completed_decisions": 0,
                "old_completion_tokens_returned_in_completed_decisions": 0,
                "old_reasoning_tokens_returned_in_completed_decisions": 0,
                "old_failure_events": 0,
                "old_failed_call_usage_note": "unknown where provider usage was not returned; old failures are not imputed"}
    curves = {}
    for rep in ("bit", "count"):
        policies = Counter()
        by_previous_hits = defaultdict(Counter)
        old_sequences, new_sequences = [], []
        no_hit_initializations = 0
        mean_curve = [0.0] * 5
        first_hit_queries = []
        for seed in range(20):
            run = runs[rep, seed]
            curve = run["hit_recovery_checkpoints"]
            no_hit_initializations += curve[0] == 0
            mean_curve = [x + y / 20 for x, y in zip(mean_curve, curve)]
            first_hit_queries.append(first_hit_index(run))
            seq = []
            for step_index in range(1, 5):
                step = run["trajectory"][step_index]
                policy = step["decision"]["policy"]
                assert policy in ("knn_greedy", "knn_diverse", "uniform_random")
                seq.append(policy)
                policies[policy] += 1
                previous = curve[step_index - 1] - (curve[step_index - 2] if step_index >= 2 else 0)
                bucket = "0" if previous == 0 else ("1-2" if previous <= 2 else ("3-5" if previous <= 5 else "6+"))
                by_previous_hits[bucket][policy] += 1
                if seed >= 5:
                    call = step["llm_call"]
                    cost["new_successful_decisions"] += 1
                    cost["new_http_attempts"] += len(call["api_attempt_log"])
                    cost["new_failed_http_attempts"] += sum(a.get("http_status") != 200 for a in call["api_attempt_log"])
                    cost["new_request_ids"] += bool(call.get("api_request_id"))
                    usage = call.get("api_usage")
                    if usage:
                        cost["prompt_tokens_returned"] += usage.get("prompt_tokens", 0)
                        cost["completion_tokens_returned"] += usage.get("completion_tokens", 0)
                        cost["reasoning_tokens_returned"] += (usage.get("completion_tokens_details") or {}).get("reasoning_tokens", 0)
                    else:
                        cost["returned_usage_missing_decisions"] += 1
                    cost["decision_seconds_including_retries"] += call["decision_seconds"]
                else:
                    call = step["llm_call"]
                    old_cost["old_completed_decisions"] += 1
                    old_cost["old_recorded_http_attempts_in_completed_decisions"] += len(call.get("api_attempt_log") or [])
                    usage = call.get("api_usage") or {}
                    old_cost["old_prompt_tokens_returned_in_completed_decisions"] += usage.get("prompt_tokens", 0)
                    old_cost["old_completion_tokens_returned_in_completed_decisions"] += usage.get("completion_tokens", 0)
                    old_cost["old_reasoning_tokens_returned_in_completed_decisions"] += (usage.get("completion_tokens_details") or {}).get("reasoning_tokens", 0)
            (old_sequences if seed < 5 else new_sequences).append(seq)
            if seed >= 5:
                cost["feature_build_seconds"] += run["feature_build_seconds"]
                cost["numerical_analysis_seconds"] += run["analysis_seconds_total"]
                cost["selection_seconds"] += run["selection_seconds_total"]
        assert sum(policies.values()) == 80
        strategy[rep] = {"policy_counts": dict(policies),
                         "policy_fractions": {k: policies[k] / 80 for k in ("knn_diverse", "knn_greedy", "uniform_random")},
                         "by_previous_batch_hits": {k: dict(v) for k, v in sorted(by_previous_hits.items())},
                         "zero_previous_hit_decision_count": sum(by_previous_hits["0"].values()),
                         "zero_hit_initialization_seeds": no_hit_initializations,
                         "old_seed_sequences": old_sequences, "new_seed_sequences": new_sequences,
                         "new_seed_diverse_dominant": sum(seq.count("knn_diverse") >= 3 for seq in new_sequences)}
        curves[rep] = {"mean_cumulative_hits_10_20_30_40_50": mean_curve,
                       "mean_auc_10_to_50": statistics.mean(auc(runs[rep, seed]) for seed in range(20)),
                       "mean_H50": mean_curve[-1],
                       "enrichment_vs_random_pool_expectation": mean_curve[-1] / (50 * 116 / 231),
                       "mean_queries_to_first_hit": statistics.mean(first_hit_queries),
                       "queries_to_first_hit": first_hit_queries}
    assert cost["new_successful_decisions"] == 120
    assert cost["new_request_ids"] == 120
    failures = []
    for run_dir in sorted((PRIVATE / "runs").iterdir()):
        path = run_dir / "failure_events.json"
        if path.exists():
            failures += json.loads(path.read_text())
    cost["failure_events"] = len(failures)
    cost["failure_event_types"] = dict(Counter(x["error_type"] for x in failures))
    for rep in ("bit", "count"):
        for seed in range(5):
            path = OLD / f"llm_{rep}_seed{seed}/failure_events.json"
            if path.exists():
                old_cost["old_failure_events"] += len(json.loads(path.read_text()))
    assert old_cost["old_completed_decisions"] == 40
    from d2_protected_hashes import snapshot as protected_snapshot
    baseline = json.loads((ATTEMPT / "d2_2_protected_baseline.json").read_text())
    assert protected_snapshot() == baseline["files"], "Protected file hashes changed"
    analysis = {"analysis_utc": utc(), "post_exposure": True,
                "candidate_count": 231, "measured_hits_in_pool": 116,
                "old_glm_run_hashes": old_hashes, "new_glm_run_hashes": new_hashes,
                "comparisons": comparisons, "strategy": strategy, "curves": curves,
                "cost": cost, "old_cost": old_cost,
                "protected_files_unchanged": len(baseline["files"]),
                "power_lock_utc": lock["locked_utc"], "first_real_call_run_start_utc": first_start}
    atomic_json(PRIVATE / "analysis.json", analysis)
    (PRIVATE / "STATUS").write_text("done\n")
    with (PRIVATE / "RUN_LOG.md").open("a", encoding="utf-8") as log:
        log.write(f"Analysis completed UTC: {utc()}\n"
                  f"120/120 new decisions, {cost['new_http_attempts']} HTTP attempts, "
                  f"{cost['failure_events']} saved failure events.\n"
                  f"Protected files unchanged: {len(baseline['files'])}.\n")
    manifest(PRIVATE)
    print(json.dumps({"status": "done", "new_decisions": 120,
                      "http_attempts": cost["new_http_attempts"],
                      "failure_events": cost["failure_events"],
                      "protected_files_unchanged": len(baseline["files"]),
                      "bit_primary": {k: comparisons["bit"][k] for k in ("structure_prior", "fixed")},
                      "manifest_sha256": sha(PRIVATE / "MANIFEST.json")}, ensure_ascii=False))


if __name__ == "__main__":
    main()

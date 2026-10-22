"""D3-5/6 TNAP CPU controls. All per-compound results remain private."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import statistics
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from rdkit import DataStructs

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from campaign_v0.campaign_core import FixedController, RandomController, run_campaign
from campaign_v0.numerical_tools import NumericalTools
from oracle_boundary_v0.oracle_boundary import BatchOracle, read_jsonl

BASE = ROOT / "outputs/d3_tnap_20261019"
FREEZE = BASE / "freeze_tnap_v1"
PRIVATE = BASE / "freeze_tnap_v1_private_labels"
PREFLIGHT = BASE / "d3_5_preflight"
RUN_PRIVATE = BASE / "d3_6_runs_private_20261019"
REPORT = BASE / "d3_6_report"
RECEIPT_SHA = "f8801efbe28f73ddbcf9c5a2d493d862cbf124f311b6659e9224f2161b5bf662"
PROTOCOL_SHA = "8384797c0348b51e0b0bb2547b77520b36981d81af4b1320be4e6adb49b17943"
D1_SHA = "2b59e83b01f35ed5cd43505518517ad25920beee8bc06f83f4afab08706708c3"
D2_SHA = "6d7d54a8ae84a53916f151c74249451d486993ccd6e7814818c1d18df126951a"
ARMS = ("random", "structure_prior", "label_shuffle", "fixed", "fixed_schedule", "rule_adaptive_v2", "forced_random_coldstart")
REPS = ("bit", "count")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def now():
    return datetime.now(timezone.utc).isoformat()


def verify_frozen():
    assert sha(FREEZE / "freeze_receipt.json") == RECEIPT_SHA
    assert sha(BASE / "tnap_v1_campaign_protocol.md") == PROTOCOL_SHA
    lock = json.loads((BASE / "tnap_v1_campaign_protocol_lock.json").read_text())
    assert lock["protocol_sha256"] == PROTOCOL_SHA
    assert sha(ROOT / "outputs/d_discrimination_20261018/d1_descriptor_spec.md") == D1_SHA
    assert sha(ROOT / "outputs/d2_controls_20261019/d2_rule_adaptive_spec.md") == D2_SHA
    receipt = json.loads((FREEZE / "freeze_receipt.json").read_text())
    for f in receipt["files"]:
        assert sha(f["snapshot"]) == f["sha256"], f["snapshot"]
    public = FREEZE / "public/candidates.jsonl"
    rows = read_jsonl(public)
    assert len(rows) == 462 and len({r["compound_key"] for r in rows}) == 462
    assert all(set(r) == {"compound_key", "standardized_smiles"} for r in rows)
    return rows


def structure_scores(candidates, rep):
    """Only the public candidate list enters this descriptor function."""
    tools = NumericalTools(candidates, representation=rep)
    keys = sorted(tools.fingerprints)
    scores = {}
    for key in keys:
        fp = tools.fingerprints[key]
        values = DataStructs.BulkTanimotoSimilarity(fp, [tools.fingerprints[k] for k in keys if k != key])
        scores[key] = sum(sorted(values, reverse=True)[:5]) / 5
    return scores


def structure_select(scores, queried, seed, rnd):
    available = set(scores) - set(queried)
    return sorted(available, key=lambda k: (-scores[k], hashlib.sha256(f"structprior|{seed}|{rnd}|{k}".encode()).digest(), k))[:10]


def structure_run(candidates, oracle_labels, scores, seed):
    oracle = BatchOracle(candidates, oracle_labels, seed=seed, total_budget=50, initialization_queries=10, batch_size=10)
    selected = []
    steps = []
    first = oracle.proposed_initial_ids()
    t = time.perf_counter()
    response = oracle.query_batch_tool({"compound_keys": first})
    steps.append({"selection": first, "observations": response["observations"], "stage": "initialization"})
    selected.extend(first)
    for rnd in range(1, 5):
        chosen = structure_select(scores, selected, seed, rnd)
        response = oracle.query_batch_tool({"compound_keys": chosen})
        steps.append({"selection": chosen, "observations": response["observations"], "stage": f"feedback_round_{rnd}"})
        selected.extend(chosen)
    return {"trajectory": steps, "feature_build_seconds": 0.0, "analysis_seconds_total": 0.0,
            "selection_seconds_total": time.perf_counter() - t, "decision_seconds_total": 0.0}


def shuffled_labels(labels, seed):
    keys = sorted(labels)
    values = [labels[k] for k in keys]
    permuted_keys = sorted(keys, key=lambda k: (hashlib.sha256(f"labelshuffle|{seed}|{k}".encode()).digest(), k))
    return {key: value for key, value in zip(permuted_keys, values)}


class PolicyController:
    def __init__(self, name):
        self.name = name
        self.decisions = []

    def choose(self, state, allowed):
        rnd = state["next_round"]
        revealed = state["revealed"]
        if self.name == "fixed_schedule":
            policy = ("knn_greedy", "knn_greedy", "knn_diverse", "knn_greedy")[rnd - 1]
        elif self.name == "rule_adaptive_v2":
            counts = [sum(int(r["outcome"]) for r in revealed[i:i + 10]) for i in range(0, len(revealed), 10)]
            assert len(counts) == rnd
            policy = "knn_greedy" if rnd == 1 else ("knn_diverse" if counts[-1] < sum(counts[:-1]) / len(counts[:-1]) else "knn_greedy")
        elif self.name == "forced_random_coldstart":
            policy = "uniform_random" if sum(r["outcome"] for r in revealed) == 0 else "knn_greedy"
        elif self.name == "label_shuffle":
            policy = "knn_greedy"
        else:
            raise ValueError(self.name)
        assert policy in allowed
        self.decisions.append({"round": rnd, "policy": policy, "observed_hits": sum(r["outcome"] for r in revealed)})
        return {"policy": policy, "reason": f"Predeclared {self.name} round {rnd}"}


def preflight():
    assert not PREFLIGHT.exists(), "Preflight already saved; do not rewrite"
    candidates = verify_frozen()
    PREFLIGHT.mkdir()
    started = now()
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in [
        FREEZE / "freeze_receipt.json", BASE / "tnap_v1_campaign_protocol.md",
        ROOT / "campaign_v0/campaign_core.py", ROOT / "campaign_v0/numerical_tools.py",
        ROOT / "oracle_boundary_v0/oracle_boundary.py",
        ROOT / "outputs/d_discrimination_20261018/d1_descriptor_spec.md",
        ROOT / "outputs/d2_controls_20261019/d2_rule_adaptive_spec.md", Path(__file__)]}
    scores = {}
    for rep in REPS:
        scores[rep] = structure_scores(candidates, rep)
        dump(PREFLIGHT / f"structure_scores_{rep}.json", scores[rep])
    public_only_receipt = {"utc": now(), "labels_loaded": False, "candidate_count": len(candidates),
                           "scores_sha256": {rep: sha(PREFLIGHT / f"structure_scores_{rep}.json") for rep in REPS}}
    dump(PREFLIGHT / "structure_only_receipt.json", public_only_receipt)
    # Synthetic oracle, unrelated to the real labels. The score-only arm must
    # select the exact same sequence under a random outcome permutation.
    keys = sorted(r["compound_key"] for r in candidates)
    synthetic = {k: int(hashlib.sha256(f"synthetic|{k}".encode()).digest()[0] < 30) for k in keys}
    perm = keys[:]
    random.Random(20261018).shuffle(perm)
    permuted = {k: synthetic[p] for k, p in zip(keys, perm)}
    assert synthetic != permuted
    invariance = 0
    for rep in REPS:
        for seed in range(20):
            left = structure_run(candidates, synthetic, scores[rep], seed)
            right = structure_run(candidates, permuted, scores[rep], seed)
            assert [s["selection"] for s in left["trajectory"]] == [s["selection"] for s in right["trajectory"]]
            invariance += 1
    model = shuffled_labels(synthetic, 0)
    assert Counter(model.values()) == Counter(synthetic.values()) and model != synthetic
    assert sum(model[k] != synthetic[k] for k in keys) > 0
    oracle = BatchOracle(candidates, model, seed=0, total_budget=50, initialization_queries=10, batch_size=10)
    first = oracle.proposed_initial_ids()
    observed = oracle.query_batch_tool({"compound_keys": first})["observations"]
    assert [x["outcome"] for x in observed] == [model[k] for k in first]
    assert all(set(x) == {"compound_key", "outcome"} for x in observed)
    for seed in range(20):
        expected = BatchOracle(candidates, synthetic, seed=seed, total_budget=50, initialization_queries=10, batch_size=10).proposed_initial_ids()
        assert len(expected) == 10
        for _ in ARMS:
            assert BatchOracle(candidates, permuted, seed=seed, total_budget=50, initialization_queries=10, batch_size=10).proposed_initial_ids() == expected
    root_test = subprocess.run([sys.executable, "-B", "-m", "unittest", "test_oracle_boundary"],
        cwd=ROOT / "oracle_boundary_v0", capture_output=True, text=True)
    assert root_test.returncode == 0, root_test.stdout + root_test.stderr
    cold_test = subprocess.run([sys.executable, "-B", "-m", "unittest", "outputs.d3_tnap_20261019.test_coldstart"],
        cwd=ROOT, capture_output=True, text=True)
    assert cold_test.returncode == 0, cold_test.stdout + cold_test.stderr
    report = {"status": "pass", "started_utc": started, "finished_utc": now(),
        "synthetic_oracle_boundary": "pass", "label_shuffle_separation": "pass",
        "structure_prior_permutation_invariance_cases": invariance, "d3_0_monotonicity": "pass",
        "shared_initialization_seeds": 20, "frozen_hashes": hashes, "glm_calls": 0,
        "scores_sha256": public_only_receipt["scores_sha256"]}
    dump(PREFLIGHT / "preflight_manifest.json", report)
    (PREFLIGHT / "preflight_report.md").write_text(
        f"# D3-5 preflight\n\nUTC {report['finished_utc']}. All checks passed: synthetic oracle boundary, label-shuffle separation, {invariance} score-only permutation invariance cases (2 reps × 20 seeds), D3-0 monotonicity, shared initialization, and frozen hashes. GLM calls 0.\n", encoding="utf-8", newline="\n")
    (PREFLIGHT / "STATUS").write_text("done\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "preflight_sha256": sha(PREFLIGHT / "preflight_manifest.json"), "invariance_cases": invariance}))


def paired(differences):
    rng = random.Random(20261018)
    draws = sorted(statistics.mean(rng.choice(differences) for _ in differences) for _ in range(10000))
    return {"mean": statistics.mean(differences), "ci_low": draws[249], "ci_high": draws[9750],
            "paired_sd": statistics.stdev(differences)}


def run():
    assert (PREFLIGHT / "STATUS").read_text().strip() == "done"
    pre = json.loads((PREFLIGHT / "preflight_manifest.json").read_text())
    assert pre["status"] == "pass"
    candidates = verify_frozen()
    assert sha(Path(__file__)) == pre["frozen_hashes"][str(Path(__file__).relative_to(ROOT))]
    for relative, expected in pre["frozen_hashes"].items():
        assert sha(ROOT / relative) == expected, relative
    assert not RUN_PRIVATE.exists() and not REPORT.exists(), "D3-6 result already exists"
    scores = {rep: json.loads((PREFLIGHT / f"structure_scores_{rep}.json").read_text()) for rep in REPS}
    for rep in REPS:
        assert sha(PREFLIGHT / f"structure_scores_{rep}.json") == pre["scores_sha256"][rep]
    labels = {r["compound_key"]: r["outcome"] for r in read_jsonl(PRIVATE / "oracle_labels.jsonl")}
    assert len(labels) == 462 and sum(labels.values()) == 53
    RUN_PRIVATE.mkdir()
    REPORT.mkdir()
    rows = []
    total_start = time.perf_counter()
    for rep in REPS:
        for seed in range(20):
            initial = BatchOracle(candidates, labels, seed=seed, total_budget=50, initialization_queries=10, batch_size=10).proposed_initial_ids()
            init_true_hits = sum(labels[k] for k in initial)
            for arm in ARMS:
                started = time.perf_counter()
                if arm == "structure_prior":
                    result = structure_run(candidates, labels, scores[rep], seed)
                    decisions = []
                else:
                    model_labels = shuffled_labels(labels, seed) if arm == "label_shuffle" else labels
                    oracle = BatchOracle(candidates, model_labels, seed=seed, total_budget=50, initialization_queries=10, batch_size=10)
                    controller = FixedController() if arm == "fixed" else RandomController() if arm == "random" else PolicyController(arm)
                    result = run_campaign(candidates, oracle, controller, seed=seed, representation=rep)
                    decisions = getattr(controller, "decisions", [])
                selections = [key for step in result["trajectory"] for key in step["selection"]]
                assert len(selections) == len(set(selections)) == 50
                assert selections[:10] == initial
                true_cumulative = []
                total = 0
                for step in result["trajectory"]:
                    total += sum(labels[k] for k in step["selection"])
                    true_cumulative.append(total)
                first_hit = next((i for i, key in enumerate(selections, 1) if labels[key] == 1), None)
                assert len(true_cumulative) == 5
                row = {"representation": rep, "seed": seed, "arm": arm, "H50": total,
                    "initialization_hits": init_true_hits, "zero_hit_initialization": init_true_hits == 0,
                    "queries_to_first_hit": first_hit,
                    "cumulative_true": true_cumulative,
                    "average_cumulative_hits_10_50": sum((true_cumulative[i]+true_cumulative[i+1])/2 for i in range(4))/4,
                    "trigger_rounds": [d["round"] for d in decisions if arm == "rule_adaptive_v2" and d["policy"] == "knn_diverse"],
                    "fallback_rounds": [d["round"] for d in decisions if arm == "forced_random_coldstart" and d["policy"] == "uniform_random"],
                    "feature_build_seconds": result["feature_build_seconds"],
                    "analysis_seconds": result["analysis_seconds_total"],
                    "selection_seconds": result["selection_seconds_total"],
                    "wall_seconds": time.perf_counter() - started}
                rows.append(row)
                dump(RUN_PRIVATE / f"{arm}_{rep}_seed{seed}.json", {"summary": row, "result": result, "decisions": decisions})
            print(json.dumps({"representation": rep, "seed": seed, "completed_arms": len(ARMS)}), flush=True)
    assert len(rows) == 280
    summary = {}
    contrasts = {}
    zero_seed = [s for s in range(20) if next(r for r in rows if r["representation"] == "bit" and r["seed"] == s and r["arm"] == "fixed")["zero_hit_initialization"]]
    for rep in REPS:
        by = {(r["arm"], r["seed"]): r for r in rows if r["representation"] == rep}
        summary[rep] = {arm: {"mean_H50": statistics.mean(by[arm, s]["H50"] for s in range(20)),
                              "sd_H50": statistics.stdev(by[arm, s]["H50"] for s in range(20)),
                              "mean_curve": [statistics.mean(by[arm,s]["cumulative_true"][i] for s in range(20)) for i in range(5)],
                              "mean_queries_to_first_hit": statistics.mean(by[arm,s]["queries_to_first_hit"] for s in range(20)),
                              "mean_wall_seconds": statistics.mean(by[arm,s]["wall_seconds"] for s in range(20))} for arm in ARMS}
        pairs = [("fixed","structure_prior"),("fixed","label_shuffle"),("rule_adaptive_v2","fixed"),
                 ("fixed_schedule","fixed"),("forced_random_coldstart","fixed")]
        pairs.extend((arm,"random") for arm in ARMS if arm != "random")
        contrasts[rep] = {f"{a}-{b}": paired([by[a,s]["H50"]-by[b,s]["H50"] for s in range(20)]) for a,b in pairs}
    triggers = {rep: {"seeds_with_trigger": sum(bool(r["trigger_rounds"]) for r in rows if r["representation"]==rep and r["arm"]=="rule_adaptive_v2"),
                      "round_counts": dict(Counter(x for r in rows if r["representation"]==rep and r["arm"]=="rule_adaptive_v2" for x in r["trigger_rounds"]))} for rep in REPS}
    zero = {rep: {arm: {"mean_H50": statistics.mean(r["H50"] for r in rows if r["representation"]==rep and r["arm"]==arm and r["seed"] in zero_seed),
                        "mean_queries_to_first_hit": statistics.mean(r["queries_to_first_hit"] for r in rows if r["representation"]==rep and r["arm"]==arm and r["seed"] in zero_seed)} for arm in ARMS} for rep in REPS} if zero_seed else {}
    aggregate = {"schema": "tnap_d3_cpu_aggregate_v1", "finished_utc": now(), "protocol_sha256": PROTOCOL_SHA,
        "freeze_receipt_sha256": RECEIPT_SHA, "runs": len(rows), "glm_calls": 0,
        "zero_hit_initialization_seeds": zero_seed, "zero_hit_seed_count": len(zero_seed),
        "arm_summaries": summary, "paired_contrasts": contrasts, "adaptive_triggers": triggers,
        "zero_hit_subgroup": zero, "total_wall_seconds": time.perf_counter()-total_start,
        "random_expected_H50": 50*53/462,
        "measurement_limitation": "Depth-of-characterization differs by compound and correlates strongly with the label; results do not extrapolate to uniform-effort screens or other targets."}
    dump(REPORT / "aggregate.json", aggregate)
    with (RUN_PRIVATE / "run_index.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v) if isinstance(v,list) else v for k,v in row.items()})
    (REPORT / "STATUS").write_text("done\n", encoding="utf-8")
    print(json.dumps({"status": "done", "aggregate_sha256": sha(REPORT / "aggregate.json"), "zero_hit_seeds": zero_seed, "runs": len(rows)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("preflight", "run"))
    arguments = parser.parse_args()
    preflight() if arguments.mode == "preflight" else run()

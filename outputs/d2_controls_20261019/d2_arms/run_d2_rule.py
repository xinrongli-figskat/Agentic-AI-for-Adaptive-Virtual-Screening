"""D2-1 post-exposure adaptive-rule control and regression protection.

Writes compound-level outcomes only under d2_rule_adaptive_private_20261019.
No GLM or network call is made.
"""
import csv
import hashlib
import json
import os
import platform
import random
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/driveA/xinrong/agentic-screening")
sys.path.insert(0, str(ROOT))
import run_controls as r5_code
from campaign_v0.campaign_core import run_campaign
from oracle_boundary_v0.oracle_boundary import BatchOracle, read_jsonl

BASE = ROOT / "outputs/d2_controls_20261019"
OUT = BASE / "d2_rule_adaptive_private_20261019"
R5 = ROOT / "data/curation_private/r5_cpu_controls_private_20261018"
D1 = ROOT / "outputs/d_discrimination_20261018"
FROZEN = ROOT / "data/curation_private/frozen_dyrk3_v1"
SPEC_HASH = "6d7d54a8ae84a53916f151c74249451d486993ccd6e7814818c1d18df126951a"
FROZEN_HASH = "3866c7bfc99e92b8e0d6f92b98955d5e68a7ae202f609eac90d0e7a201f98235"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def policy_v2(observed_batch_hits, upcoming_batch):
    """Pure mapping: one initialization and up to three prior feedback batches."""
    if upcoming_batch not in (1, 2, 3, 4) or len(observed_batch_hits) != upcoming_batch:
        raise ValueError("Incorrect decision-point mapping")
    if any(not isinstance(h, int) or h < 0 or h > 10 for h in observed_batch_hits):
        raise ValueError("Invalid observed batch hit count")
    if upcoming_batch == 1:
        return "knn_greedy"
    previous_mean = sum(observed_batch_hits[:-1]) / len(observed_batch_hits[:-1])
    return "knn_diverse" if observed_batch_hits[-1] < previous_mean else "knn_greedy"


class AdaptiveV2Controller:
    name = "rule_adaptive_v2"

    def __init__(self):
        self.decisions = []

    def choose(self, state, allowed):
        rnd = state["next_round"]
        revealed = state["revealed"]
        if len(revealed) != 10 * rnd:
            raise ValueError("Wrong number of revealed outcomes at decision point")
        hits = [sum(int(item["outcome"]) for item in revealed[i:i + 10])
                for i in range(0, len(revealed), 10)]
        planned = policy_v2(hits, rnd)
        cold_start = sum(hits) == 0
        actual = "uniform_random" if cold_start else planned
        if actual not in allowed:
            raise ValueError("Missing allowed policy")
        self.decisions.append({"upcoming_batch": rnd, "observed_hits": hits,
                               "planned_policy": planned, "actual_policy": actual,
                               "triggered": planned == "knn_diverse" and not cold_start,
                               "cold_start_fallback": cold_start})
        reason = ("Predeclared zero-positive fallback; spends ordinary query budget" if cold_start
                  else f"Predeclared v2 declining-yield rule after batches {hits}")
        return {"policy": actual, "reason": reason}


def first_trigger_from_fixed(cumulative):
    if len(cumulative) != 5:
        raise ValueError("Expected initialization plus four feedback batches")
    hits = [int(cumulative[0])] + [int(cumulative[i]) - int(cumulative[i - 1]) for i in range(1, 5)]
    for upcoming in range(1, 5):
        if policy_v2(hits[:upcoming], upcoming) == "knn_diverse":
            return upcoming
    return None


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def paired(diffs):
    rng = random.Random(20261018)
    draws = sorted(statistics.mean(rng.choice(diffs) for _ in diffs) for _ in range(10000))
    return statistics.mean(diffs), draws[249], draws[9750]


def manifest(directory):
    entries = []
    for p in sorted(directory.rglob("*")):
        if p.is_file() and p.name != "MANIFEST.json":
            entries.append({"path": p.relative_to(directory).as_posix(), "bytes": p.stat().st_size,
                            "sha256": sha(p)})
    (directory / "MANIFEST.json").write_text(json.dumps({"files": entries, "self_excluded": True}, indent=2) + "\n")


def run_v2(candidates, labels, seed, rep):
    oracle = BatchOracle(candidates, labels, seed=seed, total_budget=50,
                         initialization_queries=10, batch_size=10)
    controller = AdaptiveV2Controller()
    result = run_campaign(candidates, oracle, controller, seed=seed, representation=rep)
    selections = [key for step in result["trajectory"] for key in step["selection"]]
    assert len(selections) == len(set(selections)) == 50
    assert len(controller.decisions) == 4
    assert [d["upcoming_batch"] for d in controller.decisions] == [1, 2, 3, 4]
    assert result["hits_at_budget"] == sum(labels[key] for key in selections)
    return result, controller.decisions


def main():
    start = utc()
    assert sha(BASE / "d2_rule_adaptive_spec.md") == SPEC_HASH
    assert sha(FROZEN / "manifest.json") == FROZEN_HASH
    assert sha(BASE / "d2_arms/run_controls.py") == "efc8a414949caf669047119d3b10ea65b0772c0a03c281503b4b740d34122bd0"
    frozen = json.loads((FROZEN / "manifest.json").read_text())
    candidates = read_jsonl(Path(frozen["public_dir"]) / "candidates.jsonl")
    labels = {r["compound_key"]: r["outcome"] for r in read_jsonl(Path(frozen["private_dir"]) / "oracle_labels.jsonl")}
    assert len(candidates) == len(labels) == 231 and sum(labels.values()) == 116
    original_paths = [FROZEN / "manifest.json", R5 / "control_summary.csv",
                      ROOT / "campaign_v0/campaign_core.py", ROOT / "campaign_v0/numerical_tools.py",
                      ROOT / "oracle_boundary_v0/oracle_boundary.py"]
    originals = {str(path): sha(path) for path in original_paths}
    original_summary = list(csv.DictReader((R5 / "control_summary.csv").open(newline="", encoding="utf-8")))
    by = {(row["controller"], row["representation"], int(row["seed"])): row for row in original_summary}
    assert len(by) == 280
    expected_modes = {"fixed", "random", "fixed_schedule", "rule_adaptive",
                      "random_mixture", "matched_proportion", "label_shuffle"}
    assert {k[0] for k in by} == expected_modes
    # Predict first trigger from the already saved fixed trajectory, before any new v2 result.
    predicted = {}
    expected = {"bit": {3: 6, 4: 4}, "count": {2: 2, 3: 7, 4: 5}}
    for rep in ("bit", "count"):
        predicted[rep] = {seed: first_trigger_from_fixed(json.loads(by[("fixed", rep, seed)]["cumulative_true"]))
                          for seed in range(20)}
        counts = Counter(value for value in predicted[rep].values() if value is not None)
        if dict(counts) != expected[rep]:
            raise AssertionError(f"Locked first-trigger prediction mismatch before run: {rep} {dict(counts)}")
    OUT.mkdir(parents=True, exist_ok=False)
    (OUT / "runs").mkdir()
    (OUT / "first_trigger_prediction.json").write_text(json.dumps({
        "created_utc": utc(), "from": "existing R5 fixed cumulative_true",
        "predicted_counts": expected,
        "predicted_seed_to_first_batch": predicted,
        "spec_sha256": SPEC_HASH,
    }, indent=2, sort_keys=True) + "\n")
    # D2-4 regression: rerun all existing arms from unchanged copied R5 code.
    slots = [(seed, rnd) for seed in range(20) for rnd in range(1, 5)]
    matched = set(sorted(slots, key=lambda x: hashlib.sha256(f"matched|{x[0]}|{x[1]}".encode()).digest())[:50])
    checked = 0
    fixed_random_v1 = 0
    for rep in ("bit", "count"):
        for seed in range(20):
            for mode in sorted(expected_modes):
                result, row = r5_code.run_one(candidates, labels, mode, seed, rep, matched)
                previous = by[(mode, rep, seed)]
                for field in ("H50_true", "queries_to_first_hit", "initialization_true_hits", "fallback_batches"):
                    assert str(row[field]) == previous[field], (mode, rep, seed, field)
                assert row["cumulative_true"] == json.loads(previous["cumulative_true"]), (mode, rep, seed, "curve")
                checked += 1
                if mode in ("fixed", "random") and seed < 5:
                    oldpath = ROOT / "data/curation_private/runs_dyrk3_v1" / f"{mode}_{rep}_seed{seed}" / "run.json"
                    old = json.loads(oldpath.read_text())["result"]
                    assert [s["selection"] for s in result["trajectory"]] == [s["selection"] for s in old["trajectory"]]
                    assert result["hits_at_budget"] == old["hits_at_budget"]
                    fixed_random_v1 += 1
    assert checked == 280 and fixed_random_v1 == 20
    # Distinct synthetic-label boundary test and explicit label-shuffle separation.
    unittest_result = subprocess.run([sys.executable, "-B", "-m", "unittest", "oracle_boundary_v0.test_oracle_boundary"],
                                     cwd=ROOT, capture_output=True, text=True)
    if unittest_result.returncode:
        raise AssertionError("Synthetic oracle boundary tests failed: " + unittest_result.stderr[-1000:])
    permuted = r5_code.shuffled_labels(labels, 0)
    assert sorted(permuted.values()) == sorted(labels.values()) and permuted != labels
    shuffled_result, shuffled_summary = r5_code.run_one(candidates, labels, "label_shuffle", 0, "bit", matched)
    model_observed = [obs for step in shuffled_result["trajectory"] for obs in step["observations"]]
    assert all(obs["outcome"] == permuted[obs["compound_key"]] for obs in model_observed)
    true_selected = [key for step in shuffled_result["trajectory"] for key in step["selection"]]
    assert shuffled_summary["H50_true"] == sum(labels[key] for key in true_selected)
    assert any(permuted[key] != labels[key] for key in true_selected)
    regression = {"existing_rows_recomputed_identical": checked,
                  "v1_fixed_random_0_4_exact_replays": fixed_random_v1,
                  "synthetic_boundary_tests": "passed",
                  "label_shuffle_model_sees_permuted": True,
                  "label_shuffle_true_evaluation_separate": True,
                  "source_hashes_unchanged": originals == {path: sha(path) for path in originals}}
    assert regression["source_hashes_unchanged"]
    (OUT / "regression_protection.json").write_text(json.dumps(regression, indent=2) + "\n")
    rows, first_actual = [], {"bit": {}, "count": {}}
    for rep in ("bit", "count"):
        for seed in range(20):
            result, decisions = run_v2(candidates, labels, seed, rep)
            diverse = [d["upcoming_batch"] for d in decisions if d["triggered"]]
            first_actual[rep][seed] = diverse[0] if diverse else None
            if first_actual[rep][seed] != predicted[rep][seed]:
                raise AssertionError(f"Hard stop: first trigger differs from locked target {rep} seed={seed}")
            (OUT / "runs" / f"rule_adaptive_v2_{rep}_seed{seed}.json").write_text(json.dumps({
                "controller": "rule_adaptive_v2", "representation": rep, "seed": seed,
                "result": result, "decisions": decisions,
            }, sort_keys=True) + "\n")
            rows.append({"controller": "rule_adaptive_v2", "representation": rep,
                         "seed": seed, "H50_true": result["hits_at_budget"],
                         "first_trigger_batch": first_actual[rep][seed] if diverse else "",
                         "trigger_count": len(diverse), "trigger_batches": json.dumps(diverse),
                         "fallback_batches": sum(d["cold_start_fallback"] for d in decisions),
                         "cumulative_true": json.dumps(result["hit_recovery_checkpoints"])})
    write_csv(OUT / "control_summary.csv", rows, list(rows[0]))
    trigger_report = {}
    for rep in ("bit", "count"):
        first = Counter(value for value in first_actual[rep].values() if value is not None)
        total = Counter(batch for row in rows if row["representation"] == rep
                        for batch in json.loads(row["trigger_batches"]))
        assert dict(first) == expected[rep]
        trigger_report[rep] = {"first_trigger_seeds": sum(first.values()),
                               "first_trigger_round_distribution": dict(first),
                               "all_trigger_round_distribution": dict(total),
                               "all_trigger_count": sum(total.values()),
                               "same_H50_as_fixed_seed_count": sum(int(row["H50_true"]) == int(by[("fixed", rep, int(row["seed"]))]["H50_true"])
                                       for row in rows if row["representation"] == rep)}
    (OUT / "trigger_report.json").write_text(json.dumps(trigger_report, indent=2, sort_keys=True) + "\n")
    structure = list(csv.DictReader((D1 / "d1_descriptor_association_private_" / "structure_prior_runs.csv").open(newline="", encoding="utf-8")))
    struct_by = {(r["representation"], int(r["seed"])): int(r["H50_true"]) for r in structure}
    paired_rows = []
    for rep in ("bit", "count"):
        v2 = {int(row["seed"]): int(row["H50_true"]) for row in rows if row["representation"] == rep}
        for floor in ("random", "structure_prior", "label_shuffle", "fixed", "rule_adaptive_v1"):
            if floor == "structure_prior":
                f = {seed: struct_by[(rep, seed)] for seed in range(20)}
            else:
                old_name = "rule_adaptive" if floor == "rule_adaptive_v1" else floor
                f = {seed: int(by[(old_name, rep, seed)]["H50_true"]) for seed in range(20)}
            mean, low, high = paired([v2[seed] - f[seed] for seed in range(20)])
            paired_rows.append({"representation": rep, "numerator": "rule_adaptive_v2",
                                "denominator": floor, "n_pairs": 20,
                                "mean_H50_difference": mean, "bootstrap_95_low": low,
                                "bootstrap_95_high": high})
    write_csv(OUT / "paired_comparisons.csv", paired_rows, list(paired_rows[0]))
    assert originals == {path: sha(path) for path in originals}
    import numpy, scipy, rdkit
    (OUT / "STATUS").write_text("done\n")
    (OUT / "RUN_LOG.md").write_text(
        f"Start UTC: {start}\nEnd UTC: {utc()}\n"
        f"Specification SHA-256: {SPEC_HASH}\n"
        "Decision mapping: batch 1 forced greedy; batch 2 compares h1 to mean(h0); "
        "batch 3 compares h2 to mean(h0,h1); batch 4 compares h3 to mean(h0,h1,h2).\n"
        f"Command: .venv/bin/python -B outputs/d2_controls_20261019/d2_arms/run_d2_rule.py\n"
        f"Python {platform.python_version()}; NumPy {numpy.__version__}; SciPy {scipy.__version__}; RDKit {rdkit.__version__}\n"
        f"Code SHA-256: {sha(__file__)}\nCopied R5 SHA-256: {sha(BASE/'d2_arms/run_controls.py')}\n"
        "Seeds: 0-19; bootstrap 10000 seed 20261018; GLM calls: 0\n"
        f"Existing source hashes unchanged: {regression['source_hashes_unchanged']}\n"
        "Post-exposure descriptive control; not a new campaign or benchmark.\n")
    manifest(OUT)
    print(json.dumps({"status": "done", "regression": regression,
                      "first_trigger": trigger_report,
                      "manifest_sha256": sha(OUT / "MANIFEST.json")}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "BLOCKER.md").write_text(
            f"# D2-1 hard stop\n\nUTC: {utc()}\nType: {type(exc).__name__}\n"
            f"Reason: {exc}\nNo D2-2 GLM run is authorized after this failure.\n")
        (OUT / "STATUS").write_text("blocked\n")
        raise

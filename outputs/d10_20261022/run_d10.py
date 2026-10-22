"""D10 deterministic CPU comparator; does not modify any earlier experiment."""
from __future__ import annotations

import hashlib
import json
import os
import random
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[name] = "1"

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "outputs"))
sys.path.insert(0, str(ROOT / "outputs/d7_20261021/c_surrogate_factor/runtime_packages"))

from oracle_boundary_v0.oracle_boundary import BatchOracle
from outputs.d7_20261021.c4_five.run_c4 import candidates_and_labels
from outputs.d7_20261021.c_surrogate_factor_v2_orthogonal.c3_core import OrthogonalSelector
from outputs.d9_20261022.reconcile import behavior

WEIGHTS = {"greedy_like": 54, "diverse_like": 17, "random": 9}
ORDER = ("greedy_like", "diverse_like", "random")
POLICY = {"greedy_like": "greedy", "diverse_like": "diverse", "random": "random"}
D9_ANALYSIS = ROOT / "outputs/d9_20261022/D9_ANALYSIS.json"
PROTOCOL = HERE / "D10_PROTOCOL.md"
LOCK = HERE / "D10_LOCK.json"
PRIVATE = HERE / "d10_private"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def draw(seed: int, round_number: int) -> str:
    digest = hashlib.sha256(f"d10_d9_matched_mix_v1|S_strong|{seed}|{round_number}".encode()).digest()
    index = int.from_bytes(digest[:16], "big") % 80
    for category in ORDER:
        if index < WEIGHTS[category]:
            return category
        index -= WEIGHTS[category]
    raise AssertionError("SHA-256 draw outside weights")


def percentile(values: list[float], p: float) -> float:
    sorted_values = sorted(values)
    position = (len(sorted_values) - 1) * p
    low = int(position)
    high = min(low + 1, len(sorted_values) - 1)
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * (position - low)


def paired_interval(differences: list[int]) -> list[float]:
    rng = random.Random(20261018)
    means = [sum(differences[rng.randrange(20)] for _ in range(20)) / 20 for _ in range(10000)]
    return [percentile(means, 0.025), percentile(means, 0.975)]


def validate_reference() -> dict:
    d9 = json.loads(D9_ANALYSIS.read_text(encoding="utf-8"))
    if d9["D9_H50_by_seed"] != [23, 23, 16, 4, 15, 5, 21, 17, 15, 27, 8, 17, 16, 4, 5, 20, 22, 16, 5, 6]:
        raise RuntimeError("D9 seed vector differs from D10 specification")
    if d9["mean_D9_H50"] != 14.25:
        raise RuntimeError("D9 mean differs from D10 specification")
    if d9["realized_behavior_counts"] != WEIGHTS:
        raise RuntimeError("D9 realized behavior counts differ from D10 specification")
    return d9


def load_lock() -> dict:
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    for key, path in (("protocol", PROTOCOL), ("runner", Path(__file__)), ("D9_analysis", D9_ANALYSIS)):
        if sha(path) != lock["sha256"][key]:
            raise RuntimeError(f"Locked input changed: {key}")
    return lock


def lock_before_run() -> None:
    if LOCK.exists():
        raise FileExistsError(LOCK)
    validate_reference()
    candidates, labels = candidates_and_labels()
    if len(candidates) != 462 or len(labels) != 462 or sum(labels.values()) != 53:
        raise RuntimeError("TNAP frozen input cardinality changed")
    write_json(LOCK, {
        "utc": datetime.now(timezone.utc).isoformat(),
        "status": "locked_before_D10_control_results",
        "post_exposure": True,
        "weights": WEIGHTS,
        "seeds": list(range(20)),
        "sha256": {"protocol": sha(PROTOCOL), "runner": sha(Path(__file__)), "D9_analysis": sha(D9_ANALYSIS)},
    })


def one(seed: int, candidates: list[dict], labels: dict, selector: OrthogonalSelector) -> dict:
    oracle = BatchOracle(candidates, labels, seed=seed, total_budget=50,
                         initialization_queries=10, batch_size=10)
    initial = oracle.proposed_initial_ids()
    d9_path = ROOT / f"outputs/d9_20261022/d9_private/runs/seed{seed}/run.json"
    d9_run = json.loads(d9_path.read_text(encoding="utf-8"))
    if initial != d9_run["trajectory"][0]["selection"]:
        raise RuntimeError(f"Seed {seed} initial ten differ from D9")
    answer = oracle.query_batch_tool({"compound_keys": initial})
    trajectory = [{"stage": 0, "drawn_behavior": "initialization", "realized_behavior": "label_blind",
                   "selection": initial, "observations": answer["observations"]}]
    while oracle.public_state()["remaining_budget"]:
        state = oracle.public_state()
        category = draw(seed, state["next_round"])
        selection, mode = selector.select(state, "S_strong", POLICY[category], seed)
        answer = oracle.query_batch_tool({"compound_keys": selection})
        trajectory.append({"stage": state["next_round"], "drawn_behavior": category,
                           "policy": POLICY[category], "mode": mode, "realized_behavior": behavior(mode),
                           "selection": selection, "observations": answer["observations"]})
    keys = [key for stage in trajectory for key in stage["selection"]]
    if len(keys) != 50 or len(set(keys)) != 50 or len(trajectory) != 5:
        raise RuntimeError("50-query budget, uniqueness, or stage count failed")
    hits = sum(int(obs["outcome"]) for stage in trajectory for obs in stage["observations"])
    return {"seed": seed, "H50": hits, "trajectory": trajectory}


def run() -> dict:
    lock = load_lock()
    d9 = validate_reference()
    candidates, labels = candidates_and_labels()
    selector = OrthogonalSelector(candidates)
    start = time.perf_counter()
    first = [one(seed, candidates, labels, selector) for seed in range(20)]
    second = [one(seed, candidates, labels, selector) for seed in range(20)]
    if first != second:
        raise RuntimeError("Full-trajectory deterministic replay failed")
    drawn = Counter(step["drawn_behavior"] for run in first for step in run["trajectory"][1:])
    realized = Counter(step["realized_behavior"] for run in first for step in run["trajectory"][1:])
    if sum(drawn.values()) != 80 or sum(realized.values()) != 80:
        raise RuntimeError("Expected 80 feedback decisions")
    h50 = [r["H50"] for r in first]
    differences = [d9["D9_H50_by_seed"][seed] - h50[seed] for seed in range(20)]
    interval = paired_interval(differences)
    interpretation = ("no_detectable_timing_contribution_beyond_rule_frequency"
                      if interval[0] <= 0 <= interval[1] else
                      "positive_timing_contribution" if interval[0] > 0 else "negative_timing_contribution")
    for r in first:
        write_json(PRIVATE / "runs" / f"seed{r['seed']}.json", r)
    summary = {
        "post_exposure": True, "pool": "TNAP", "surrogate": "S_strong", "representation": "bit",
        "seed_count": 20, "seed_range": [0, 19], "query_budget_including_initialization": 50,
        "initialization_queries": 10, "feedback_decisions": 80,
        "hash_draw": "SHA256(d10_d9_matched_mix_v1|S_strong|seed|round); first 128 bits modulo 80",
        "source_behavior_weights": WEIGHTS,
        "drawn_behavior_counts": {k: drawn[k] for k in ORDER},
        "realized_behavior_counts": {k: realized[k] for k in ORDER},
        "mixture_H50_by_seed": h50, "mean_mixture_H50": sum(h50) / 20,
        "D9_H50_by_seed": d9["D9_H50_by_seed"], "mean_D9_H50": 14.25,
        "paired_D9_minus_mixture_by_seed": differences,
        "mean_D9_minus_mixture": sum(differences) / 20,
        "paired_bootstrap_95_interval": interval,
        "bootstrap_resamples": 10000, "bootstrap_seed": 20261018,
        "deterministic_full_trajectory_replay": first == second,
        "same_seed_initialization_verified_against_D9": True,
        "prespecified_interpretation_branch": interpretation,
        "locked_protocol_utc": lock["utc"], "lock_sha256": sha(LOCK),
        "D9_analysis_sha256": sha(D9_ANALYSIS),
        "elapsed_cpu_seconds_including_replay": time.perf_counter() - start,
        "GLM_calls": 0,
    }
    write_json(HERE / "D10_D9_MATCHED_MIX.json", summary)
    return summary


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in {"lock", "run"}:
        raise SystemExit("Usage: python run_d10.py {lock|run}")
    if sys.argv[1] == "lock":
        lock_before_run()
        print(json.dumps({"status": "locked_before_results", "lock_sha256": sha(LOCK)}))
    else:
        result = run()
        print(json.dumps({k: result[k] for k in ("mean_mixture_H50", "mean_D9_minus_mixture",
                                                "paired_bootstrap_95_interval", "prespecified_interpretation_branch")}, indent=2))

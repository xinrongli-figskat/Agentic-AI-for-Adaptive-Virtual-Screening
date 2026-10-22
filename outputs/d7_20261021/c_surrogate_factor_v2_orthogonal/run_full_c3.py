"""Resumable, CPU-only orthogonal factor campaigns and aggregate analysis."""
from __future__ import annotations

import os
for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"
import argparse
import hashlib
import json
import math
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PRIVATE = ROOT / "outputs/d7_20261021/c_surrogate_factor_v2_orthogonal_private"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "outputs"))
sys.path.insert(0, str(ROOT / "outputs/d7_20261021/c_surrogate_factor/runtime_packages"))
import numpy as np
from scipy.stats import spearmanr
from oracle_boundary_v0.oracle_boundary import BatchOracle
from outputs.campaign_v0.numerical_tools import NumericalTools
from outputs.d7_20261021.c_surrogate_factor_v2.run_c2v2 import load_inputs, read_jsonl
from outputs.d7_20261021.c_surrogate_factor_v2_orthogonal.c3_core import OrthogonalSelector, POLICIES

SURROGATES = ("S_weak", "S_maccs", "S_incumbent", "S_strong", "S_morgan_logreg", "S_morgan_gbdt")
GBDT = ("S_strong", "S_morgan_gbdt")
COMMON_FIXED = ("greedy", "diverse", "persistent_random_until_first_hit", "diverse_random_coldstart")
META = ("bandit_thompson", "bandit_ucb1", "random_mixture")
CACHE = {}


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2,
                               sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    temp.replace(path)


class MetaController:
    def __init__(self, name, seed):
        if name not in META:
            raise ValueError(name)
        self.name, self.seed = name, seed
        self.alpha = {p: 1.0 for p in POLICIES}
        self.beta = {p: 1.0 for p in POLICIES}
        self.count = {p: 0 for p in POLICIES}
        self.reward_sum = {p: 0.0 for p in POLICIES}
        self.previous = None
        self.last_queries = 10
        self.last_hits = None
        self.commit = False

    def feedback(self, state):
        queried = int(state["queried_count"])
        hits = sum(int(row["outcome"]) for row in state["revealed"])
        if self.last_hits is not None and self.previous is not None:
            delta_q = queried - self.last_queries
            delta_h = hits - self.last_hits
            if delta_q != 10 or not 0 <= delta_h <= 10:
                raise ValueError("Invalid feedback interval")
            p = self.previous
            reward = delta_h / delta_q
            self.alpha[p] += reward
            self.beta[p] += 1-reward
            self.count[p] += 1
            self.reward_sum[p] += reward
        self.last_queries, self.last_hits, self.previous = queried, hits, None
        if hits:
            self.commit = False

    def choose(self, state):
        self.feedback(state)
        hits = self.last_hits
        round_number = state["next_round"]
        if self.commit and hits == 0:
            policy = "persistent_random_until_first_hit"
        elif self.name == "random_mixture":
            digest = hashlib.sha256(f"c3mix|{self.seed}|{round_number}".encode()).digest()
            policy = POLICIES[int.from_bytes(digest[:8], "big") % len(POLICIES)]
        elif self.name == "bandit_thompson":
            scores = {}
            for policy in POLICIES:
                digest = hashlib.sha256(f"c3_thompson|{self.seed}|{round_number}|{policy}".encode()).digest()
                scores[policy] = random.Random(int.from_bytes(digest, "big")).betavariate(
                    self.alpha[policy], self.beta[policy])
            policy = max(POLICIES, key=lambda p: scores[p])
        else:
            t = 1 + sum(self.count.values())
            scores = {p: (math.inf if self.count[p] == 0 else
                          self.reward_sum[p]/self.count[p] + math.sqrt(2*math.log(t)/self.count[p]))
                      for p in POLICIES}
            policy = max(POLICIES, key=lambda p: scores[p])
        if policy == "persistent_random_until_first_hit" and hits == 0:
            self.commit = True
        self.previous = policy
        return policy


def pool_cache(pool):
    if pool not in CACHE:
        pub, private = load_inputs()[pool]
        candidates = read_jsonl(pub)
        labels = {row["compound_key"]: int(row["outcome"]) for row in read_jsonl(private)}
        if len(candidates) != len(labels) or set(labels) != {row["compound_key"] for row in candidates}:
            raise ValueError("Frozen pool identities differ")
        CACHE[pool] = (candidates, labels, OrthogonalSelector(candidates), NumericalTools(candidates))
    return CACHE[pool]


def path_for(job):
    pool, surrogate, arm, seed = job
    if arm == "random":
        return PRIVATE / "runs" / pool / "surrogate_invariant" / "random" / f"seed{seed}.json"
    return PRIVATE / "runs" / pool / surrogate / arm / f"seed{seed}.json"


def one(job):
    pool, surrogate, arm, seed = job
    candidates, labels, selector, numerical = pool_cache(pool)
    oracle = BatchOracle(candidates, labels, seed=seed, total_budget=50,
                         initialization_queries=10, batch_size=10)
    controller = MetaController(arm, seed) if arm in META else None
    initial = oracle.proposed_initial_ids()
    first = oracle.query_batch_tool({"compound_keys": initial})
    trajectory = [{"stage": 0, "policy": "initialization", "mode": "label_blind",
                   "selection": initial, "observations": first["observations"]}]
    while oracle.public_state()["remaining_budget"]:
        state = oracle.public_state()
        policy = controller.choose(state) if controller else arm
        if arm == "random":
            selected = numerical.select_batch(state, policy="uniform_random", seed=seed,
                                              round_number=state["next_round"])
            mode = "policy_random"
        else:
            selected, mode = selector.select(state, surrogate, policy, seed)
        answer = oracle.query_batch_tool({"compound_keys": selected})
        trajectory.append({"stage": state["next_round"], "policy": policy, "mode": mode,
                           "revealed_hits_before": sum(x["outcome"] for x in state["revealed"]),
                           "selection": selected, "observations": answer["observations"]})
    if controller:
        controller.feedback(oracle.public_state())
        if sum(controller.count.values()) != 4:
            raise RuntimeError("Meta-controller reward accounting incomplete")
    all_keys = [key for row in trajectory for key in row["selection"]]
    if len(all_keys) != len(set(all_keys)) or len(all_keys) != 50:
        raise RuntimeError("Invalid query count or duplicate")
    return {"status": "complete", "post_exposure": True, "pool": pool,
            "surrogate": surrogate if arm != "random" else None,
            "arm": arm, "seed": seed, "surrogate_invariant": arm == "random",
            "H50": sum(x["outcome"] for row in trajectory for x in row["observations"]),
            "queried_count": 50, "trajectory": trajectory, "glm_calls": 0}


def execute(job):
    path = path_for(job)
    if path.exists():
        saved = json.loads(path.read_text())
        if (saved.get("status") != "complete" or saved.get("pool") != job[0]
            or saved.get("seed") != job[3] or saved.get("arm") != job[2]):
            raise RuntimeError("Saved run identity mismatch")
        return {"pool": job[0], "surrogate": job[1], "arm": job[2], "seed": job[3],
                "H50": saved["H50"], "resumed": True}
    started = time.perf_counter()
    result = one(job)
    save(path, result)
    return {"pool": job[0], "surrogate": job[1], "arm": job[2], "seed": job[3],
            "H50": result["H50"], "elapsed_seconds": time.perf_counter()-started,
            "resumed": False}


def jobs():
    output = []
    for pool in ("TNAP", "DYRK3"):
        for seed in range(20):
            output.append((pool, None, "random", seed))
        for surrogate in SURROGATES:
            arms = COMMON_FIXED + META + (() if surrogate in GBDT else ("ens_one_step_proxy",))
            for arm in arms:
                for seed in range(20):
                    output.append((pool, surrogate, arm, seed))
    if len(output) != len(set(output)) or len(output) != 1880:
        raise RuntimeError("C3 job design changed")
    return output


def bootstrap_spread(matrix):
    values = np.asarray(matrix, dtype=float)
    if values.shape[1] != 20:
        raise ValueError("Twenty paired seeds required")
    rng = np.random.default_rng(20261018)
    sample = rng.integers(0, 20, size=(10000, 20))
    means = values[:, sample].mean(axis=2)
    spreads = np.ptp(means, axis=0)
    return [float(v) for v in np.quantile(spreads, [.025, .975])]


def analyze(rows):
    table = {(x["pool"], x["surrogate"], x["arm"], x["seed"]): x["H50"] for x in rows}
    c2 = json.loads((HERE / "C2_SIX_PUBLIC.json").read_text())
    cells, trends = {}, {}
    for pool in ("TNAP", "DYRK3"):
        random_values = [table[pool, None, "random", s] for s in range(20)]
        n, k = (462, 53) if pool == "TNAP" else (231, 116)
        cells[pool] = {"random_floor": {"observed_mean": float(np.mean(random_values)),
                                         "analytical_expectation": 50*k/n,
                                         "surrogate_invariant": True}, "surrogates": {}}
        for surrogate in SURROGATES:
            arms = COMMON_FIXED + META + (() if surrogate in GBDT else ("ens_one_step_proxy",))
            vectors = {arm: [table[pool, surrogate, arm, s] for s in range(20)] for arm in arms}
            means = {arm: float(np.mean(values)) for arm, values in vectors.items()}
            fixed = {arm: means[arm] for arm in COMMON_FIXED}
            best_fixed = max(fixed.values())
            best_meta = max(means[arm] for arm in META)
            spread = max(fixed.values()) - min(fixed.values())
            cells[pool]["surrogates"][surrogate] = {
                "auc": c2["pools"][pool]["metrics"][surrogate]["roc_auc"],
                "ef1_percent": c2["pools"][pool]["metrics"][surrogate]["ef1_percent"],
                "H50_mean_by_arm": means,
                "spread_nontrivial_common": spread,
                "spread_nontrivial_common_bootstrap_ci95": bootstrap_spread(
                    [vectors[arm] for arm in COMMON_FIXED]),
                "adaptive_gap": best_fixed-best_meta,
                "ens_inclusive_spread": (max(means[a] for a in COMMON_FIXED+("ens_one_step_proxy",))-
                                          min(means[a] for a in COMMON_FIXED+("ens_one_step_proxy",)))
                                         if surrogate not in GBDT else None,
                "ens_status": "skipped_equal_compute_wall_time" if surrogate in GBDT else "complete",
            }
        if pool == "TNAP":
            names = c2["pools"][pool]["observed_auc_rank_ascending"]
            points = [{"surrogate": name,
                       "auc": cells[pool]["surrogates"][name]["auc"],
                       "spread_nontrivial": cells[pool]["surrogates"][name]["spread_nontrivial_common"],
                       "adaptive_gap": cells[pool]["surrogates"][name]["adaptive_gap"]}
                      for name in names]
            rho_spread = spearmanr([p["auc"] for p in points],
                                   [p["spread_nontrivial"] for p in points]).statistic
            rho_gap = spearmanr([p["auc"] for p in points],
                                [p["adaptive_gap"] for p in points]).statistic
            trends = {"points_in_locked_auc_order": points,
                      "spearman_auc_vs_spread": float(rho_spread) if np.isfinite(rho_spread) else None,
                      "spearman_auc_vs_adaptive_gap": float(rho_gap) if np.isfinite(rho_gap) else None,
                      "interpretation": "six post-exposure descriptive points; not causal"}
    tnap_eligible = [name for name in SURROGATES if
                     cells["TNAP"]["surrogates"][name]["spread_nontrivial_common_bootstrap_ci95"][0] >= 2.0]
    tnap_eligible.sort(key=lambda name: -cells["TNAP"]["surrogates"][name]["spread_nontrivial_common_bootstrap_ci95"][0])
    return {"status": "C3_CPU_COMPLETE", "utc": utc(), "post_exposure": True,
            "completed_unique_campaigns": len(rows), "glm_calls": 0,
            "bootstrap_seed": 20261018, "bootstrap_resamples": 10000,
            "cells": cells, "TNAP_six_point_trend": trends,
            "C4_TNAP_cell_gate_eligible_order": tnap_eligible,
            "C4_DYRK3_LLM_role": "excluded by pre-existing S-2 pool-level signal gate",
            "C4_status": "not_authorized_CP2_not_requested"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    lock = json.loads((HERE / "C3_FULL_LOCK_v3.json").read_text())
    for key, name in (("full_spec", "C3_FULL_SPEC_v3.md"), ("full_runner", "run_full_c3.py"),
                      ("core", "c3_core.py"), ("regressions", "C3_REVISED_REGRESSIONS.json"),
                      ("C2", "C2_SIX_PUBLIC.json"), ("ENS_timing", "ENS_PUBLIC_TIMING.json")):
        if sha(HERE / name) != lock["file_sha256"][key]:
            raise RuntimeError("Locked input changed: " + name)
    completed = []
    start = time.perf_counter()
    with ProcessPoolExecutor(max_workers=max(1, min(args.workers, 8))) as executor:
        pending = {executor.submit(execute, job): job for job in jobs()}
        for future in as_completed(pending):
            try:
                completed.append(future.result())
            except Exception as exc:
                save(HERE / "C3_FAILURE.json", {"status": "failed", "utc": utc(),
                    "job": pending[future], "completed_this_invocation": len(completed),
                    "error_type": type(exc).__name__, "message": str(exc)})
                for task in pending:
                    task.cancel()
                raise
            if len(completed) % 20 == 0 or len(completed) == 1880:
                progress = {"status": "running" if len(completed) < 1880 else "complete",
                    "utc": utc(), "completed_this_invocation": len(completed), "total_jobs": 1880,
                    "elapsed_seconds": time.perf_counter()-start, "glm_calls": 0}
                save(HERE / "C3_PROGRESS.json", progress)
                print(json.dumps(progress), flush=True)
    completed.sort(key=lambda row: (row["pool"], str(row["surrogate"]), row["arm"], row["seed"]))
    if len(completed) != 1880:
        raise RuntimeError("Incomplete CPU matrix")
    summary = analyze(completed)
    save(HERE / "C3_PUBLIC_SUMMARY.json", summary)
    save(HERE / "C3_RUN_RECEIPT.json", {"status": "complete", "utc": utc(),
        "unique_campaigns": 1880, "private_run_root": str(PRIVATE / "runs"),
        "private_details_not_published": True, "glm_calls": 0,
        "execution_lock_sha256": sha(HERE / "C3_FULL_LOCK_v3.json")})
    print("C3_COMPLETE_CPU_ONLY", flush=True)


if __name__ == "__main__":
    main()

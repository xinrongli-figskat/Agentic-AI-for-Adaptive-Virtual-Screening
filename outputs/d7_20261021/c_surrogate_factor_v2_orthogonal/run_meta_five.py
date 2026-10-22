"""Versioned, five-action, CPU-only C3 meta-controller correction."""
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
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PRIVATE = ROOT / "outputs/d7_20261021/c_surrogate_factor_v2_orthogonal_five_private"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "outputs"))
sys.path.insert(0, str(ROOT / "outputs/d7_20261021/c_surrogate_factor/runtime_packages"))
import numpy as np
from scipy.stats import spearmanr
from oracle_boundary_v0.oracle_boundary import BatchOracle
from outputs.d7_20261021.c_surrogate_factor_v2.run_c2v2 import load_inputs, read_jsonl
from outputs.d7_20261021.c_surrogate_factor_v2_orthogonal.c3_core import OrthogonalSelector
from outputs.d7_20261021.c_surrogate_factor_v2_orthogonal.run_full_c3 import (
    SURROGATES, COMMON_FIXED, META, save, sha, utc,
)

MENU = ("greedy", "diverse", "random", "persistent_random_until_first_hit",
        "diverse_random_coldstart")
POOLS = ("TNAP", "DYRK3")
LOCK_FILES = ("C3_FIVE_MENU_SPEC_v1.md", "run_meta_five.py", "c3_core.py",
              "C3_FULL_LOCK_v3.json", "C3_PUBLIC_SUMMARY.json", "C3_AUDIT.json",
              "C2_SIX_PUBLIC.json", "DEVIATION_C3_GBDT_META_ENS.md")
CACHE = {}


class FiveMenuController:
    def __init__(self, name, seed):
        if name not in META:
            raise ValueError(name)
        self.name, self.seed = name, seed
        self.alpha = {p: 1.0 for p in MENU}
        self.beta = {p: 1.0 for p in MENU}
        self.count = {p: 0 for p in MENU}
        self.reward_sum = {p: 0.0 for p in MENU}
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
            policy = self.previous
            reward = delta_h / delta_q
            self.alpha[policy] += reward
            self.beta[policy] += 1 - reward
            self.count[policy] += 1
            self.reward_sum[policy] += reward
        self.last_queries, self.last_hits, self.previous = queried, hits, None
        if hits:
            self.commit = False

    def choose(self, state):
        self.feedback(state)
        round_number = state["next_round"]
        if self.commit and self.last_hits == 0:
            policy = "persistent_random_until_first_hit"
        elif self.name == "random_mixture":
            digest = hashlib.sha256(f"c3v5mix|{self.seed}|{round_number}".encode()).digest()
            policy = MENU[int.from_bytes(digest[:8], "big") % len(MENU)]
        elif self.name == "bandit_thompson":
            scores = {}
            for item in MENU:
                digest = hashlib.sha256(
                    f"c3v5_thompson|{self.seed}|{round_number}|{item}".encode()).digest()
                scores[item] = random.Random(int.from_bytes(digest, "big")).betavariate(
                    self.alpha[item], self.beta[item])
            policy = max(MENU, key=lambda item: scores[item])
        else:
            t = 1 + sum(self.count.values())
            scores = {item: (math.inf if self.count[item] == 0 else
                      self.reward_sum[item] / self.count[item] +
                      math.sqrt(2 * math.log(t) / self.count[item])) for item in MENU}
            policy = max(MENU, key=lambda item: scores[item])
        if policy == "persistent_random_until_first_hit" and self.last_hits == 0:
            self.commit = True
        self.previous = policy
        return policy


def jobs():
    result = [(pool, surrogate, arm, seed) for pool in POOLS
              for surrogate in SURROGATES for arm in META for seed in range(20)]
    if len(result) != 720 or len(set(result)) != 720:
        raise RuntimeError("Five-menu factorial design changed")
    return result


def path_for(job):
    pool, surrogate, arm, seed = job
    return PRIVATE / "runs" / pool / surrogate / arm / f"seed{seed}.json"


def pool_cache(pool):
    if pool not in CACHE:
        pub, private = load_inputs()[pool]
        candidates = read_jsonl(pub)
        labels = {row["compound_key"]: int(row["outcome"]) for row in read_jsonl(private)}
        if len(candidates) != len(labels) or {row["compound_key"] for row in candidates} != set(labels):
            raise ValueError("Frozen pool identities differ")
        CACHE[pool] = (candidates, labels, OrthogonalSelector(candidates))
    return CACHE[pool]


def one(job):
    pool, surrogate, arm, seed = job
    candidates, labels, selector = pool_cache(pool)
    oracle = BatchOracle(candidates, labels, seed=seed, total_budget=50,
                         initialization_queries=10, batch_size=10)
    controller = FiveMenuController(arm, seed)
    initial = oracle.proposed_initial_ids()
    first = oracle.query_batch_tool({"compound_keys": initial})
    trajectory = [{"stage": 0, "policy": "initialization", "mode": "label_blind",
                   "selection": initial, "observations": first["observations"]}]
    while oracle.public_state()["remaining_budget"]:
        state = oracle.public_state()
        policy = controller.choose(state)
        if policy not in MENU:
            raise RuntimeError("Out-of-menu action")
        selected, mode = selector.select(state, surrogate, policy, seed)
        answer = oracle.query_batch_tool({"compound_keys": selected})
        trajectory.append({"stage": state["next_round"], "policy": policy, "mode": mode,
                           "revealed_hits_before": sum(row["outcome"] for row in state["revealed"]),
                           "selection": selected, "observations": answer["observations"]})
    controller.feedback(oracle.public_state())
    if sum(controller.count.values()) != 4:
        raise RuntimeError("Reward accounting incomplete")
    keys = [key for stage in trajectory for key in stage["selection"]]
    if len(keys) != len(set(keys)) or len(keys) != 50 or len(trajectory) != 5:
        raise RuntimeError("Invalid trajectory")
    return {"status": "complete", "post_exposure": True, "menu_version": "C3_five_v1",
            "pool": pool, "surrogate": surrogate, "arm": arm, "seed": seed,
            "H50": sum(row["outcome"] for stage in trajectory for row in stage["observations"]),
            "queried_count": 50, "trajectory": trajectory, "glm_calls": 0}


def execute(job):
    path = path_for(job)
    if path.exists():
        saved = json.loads(path.read_text(encoding="utf-8"))
        if any(saved.get(k) != v for k, v in zip(
            ("pool", "surrogate", "arm", "seed"), job)) or saved.get("status") != "complete":
            raise RuntimeError("Saved run identity mismatch")
        return {"job": job, "H50": saved["H50"], "resumed": True}
    started = time.perf_counter()
    result = one(job)
    save(path, result)
    return {"job": job, "H50": result["H50"], "resumed": False,
            "elapsed_seconds": time.perf_counter() - started}


def lock_path():
    return HERE / "C3_FIVE_MENU_LOCK_v1.json"


def make_lock():
    if lock_path().exists():
        raise FileExistsError("Five-menu lock already exists")
    original = json.loads((HERE / "C3_PUBLIC_SUMMARY.json").read_text(encoding="utf-8"))
    if original["completed_unique_campaigns"] != 1880:
        raise RuntimeError("Original C3 matrix incomplete")
    pools = load_inputs()
    value = {"status": "locked_before_five_menu_results", "utc": utc(),
             "post_exposure": True, "jobs": len(jobs()), "menu": MENU,
             "file_sha256": {name: sha(HERE / name) for name in LOCK_FILES},
             "frozen_pool_sha256": {pool: {"public": hashlib.sha256(blobs[0]).hexdigest(),
                                              "private": hashlib.sha256(blobs[1]).hexdigest()}
                                    for pool, blobs in pools.items()}}
    save(lock_path(), value)
    return value


def verify_lock():
    lock = json.loads(lock_path().read_text(encoding="utf-8"))
    if lock["jobs"] != 720 or tuple(lock["menu"]) != MENU:
        raise RuntimeError("Locked menu or job count changed")
    for name in LOCK_FILES:
        if sha(HERE / name) != lock["file_sha256"][name]:
            raise RuntimeError("Locked input changed: " + name)
    pools = load_inputs()
    for pool in POOLS:
        if hashlib.sha256(pools[pool][0]).hexdigest() != lock["frozen_pool_sha256"][pool]["public"] or \
           hashlib.sha256(pools[pool][1]).hexdigest() != lock["frozen_pool_sha256"][pool]["private"]:
            raise RuntimeError("Frozen pool changed: " + pool)
    return lock


def synthetic_preflight():
    if len(MENU) != 5 or "ens_one_step_proxy" in MENU or len(jobs()) != 720:
        raise RuntimeError("Five-menu design failed")
    # Only public structures and synthetic outcomes are used below.
    pub = read_jsonl(load_inputs()["TNAP"][0])
    selector = OrthogonalSelector(pub)
    keys = [row["compound_key"] for row in pub]
    initial = BatchOracle(pub, {key: 0 for key in keys}, seed=0,
                          total_budget=50, initialization_queries=10,
                          batch_size=10).proposed_initial_ids()
    initial_set = set(initial)
    a = {key: int(i % 2 == 0) if key in initial_set else 0 for i, key in enumerate(keys)}
    b = {key: a[key] if key in initial_set else 1 for key in keys}
    results = []
    for name in META:
        selected = []
        for labels in (a, b):
            oracle = BatchOracle(pub, labels, seed=0, total_budget=50,
                                 initialization_queries=10, batch_size=10)
            oracle.query_batch_tool({"compound_keys": initial})
            state = oracle.public_state()
            policy = FiveMenuController(name, 0).choose(state)
            ids, _ = selector.select(state, "S_incumbent", policy, 0)
            selected.append((policy, ids))
        if selected[0] != selected[1]:
            raise RuntimeError("Unrevealed synthetic outcomes changed first action")
        results.append({"controller": name, "first_policy": selected[0][0]})
    return {"status": "pass", "public_only_structures": True,
            "unrevealed_synthetic_outcomes_invariant": True,
            "menu_size": 5, "job_count": 720, "controllers": results}


def run(workers):
    verify_lock()
    save(HERE / "C3_FIVE_SYNTHETIC_PREFLIGHT.json", synthetic_preflight())
    started = time.perf_counter()
    completed = 0
    with ProcessPoolExecutor(max_workers=max(1, min(workers, 8))) as executor:
        pending = {executor.submit(execute, job): job for job in jobs()}
        for future in as_completed(pending):
            try:
                future.result()
            except Exception as exc:
                save(HERE / "C3_FIVE_FAILURE.json", {"utc": utc(), "job": pending[future],
                    "completed_this_invocation": completed,
                    "error_type": type(exc).__name__, "message": str(exc)})
                for task in pending:
                    task.cancel()
                raise
            completed += 1
            if completed % 20 == 0 or completed == 720:
                progress = {"status": "complete" if completed == 720 else "running",
                    "utc": utc(), "completed_this_invocation": completed,
                    "total_jobs": 720, "elapsed_seconds": time.perf_counter() - started,
                    "glm_calls": 0}
                save(HERE / "C3_FIVE_PROGRESS.json", progress)
                print(json.dumps(progress), flush=True)


def audit_and_analyze():
    verify_lock()
    original = json.loads((HERE / "C3_PUBLIC_SUMMARY.json").read_text(encoding="utf-8"))
    c2 = json.loads((HERE / "C2_SIX_PUBLIC.json").read_text(encoding="utf-8"))
    pools = load_inputs()
    candidates = {p: read_jsonl(pools[p][0]) for p in POOLS}
    all_labels = {p: {r["compound_key"]: int(r["outcome"]) for r in read_jsonl(pools[p][1])}
                  for p in POOLS}
    table = {}
    policy_counts = Counter()
    hashes = []
    for job in jobs():
        path = path_for(job)
        result = json.loads(path.read_text(encoding="utf-8"))
        pool, surrogate, arm, seed = job
        if any(result.get(k) != v for k, v in zip(("pool", "surrogate", "arm", "seed"), job)):
            raise RuntimeError("Run identity mismatch")
        steps = result["trajectory"]
        keys = [k for step in steps for k in step["selection"]]
        expected_init = BatchOracle(candidates[pool], all_labels[pool], seed=seed,
                                    total_budget=50, initialization_queries=10,
                                    batch_size=10).proposed_initial_ids()
        if len(steps) != 5 or len(keys) != 50 or len(set(keys)) != 50 or steps[0]["selection"] != expected_init:
            raise RuntimeError("Query schedule or initialization mismatch")
        if result["glm_calls"] != 0 or result["queried_count"] != 50:
            raise RuntimeError("Cost or budget mismatch")
        if any(step["policy"] not in MENU for step in steps[1:]):
            raise RuntimeError("Out-of-menu action in saved trajectory")
        for step in steps:
            if step["observations"] != [{"compound_key": key, "outcome": all_labels[pool][key]}
                                        for key in step["selection"]]:
                raise RuntimeError("Observation or ordering mismatch")
        if result["H50"] != sum(row["outcome"] for step in steps for row in step["observations"]):
            raise RuntimeError("H50 mismatch")
        policy_counts.update(step["policy"] for step in steps[1:])
        table[job] = result["H50"]
        hashes.append(f"{path.relative_to(PRIVATE).as_posix()} {sha(path)}")
    combined = hashlib.sha256(("\n".join(sorted(hashes)) + "\n").encode()).hexdigest()
    cells = {}
    for pool in POOLS:
        cells[pool] = {}
        for surrogate in SURROGATES:
            old = original["cells"][pool]["surrogates"][surrogate]
            fixed = {arm: old["H50_mean_by_arm"][arm] for arm in COMMON_FIXED}
            meta = {arm: float(np.mean([table[pool, surrogate, arm, seed] for seed in range(20)]))
                    for arm in META}
            cells[pool][surrogate] = {"auc": old["auc"], "fixed_mean_H50": fixed,
                "five_menu_meta_mean_H50": meta,
                "best_fixed_minus_best_meta_H50": max(fixed.values()) - max(meta.values()),
                "fixed_spread_unmodified": old["spread_nontrivial_common"],
                "fixed_spread_CI95_unmodified": old["spread_nontrivial_common_bootstrap_ci95"]}
    order = c2["pools"]["TNAP"]["observed_auc_rank_ascending"]
    auc = [cells["TNAP"][name]["auc"] for name in order]
    gaps = [cells["TNAP"][name]["best_fixed_minus_best_meta_H50"] for name in order]
    rho = spearmanr(auc, gaps).statistic
    public = {"status": "C3_FIVE_MENU_CPU_COMPLETE", "utc": utc(),
        "post_exposure": True, "completed_campaigns": len(table), "glm_calls": 0,
        "menu": MENU, "menu_size": len(MENU), "meta_controllers": META,
        "original_fixed_and_random_unchanged": True,
        "cells": cells, "TNAP_six_point_auc_vs_adaptive_gap": {
            "order": order, "adaptive_gap_H50": gaps,
            "spearman_rho": float(rho) if np.isfinite(rho) else None,
            "descriptive_noncausal": True},
        "C4_TNAP_cell_gate_eligible_order": original["C4_TNAP_cell_gate_eligible_order"],
        "C4_status": "CP2_approval_required_no_GLM_calls"}
    save(HERE / "C3_FIVE_PUBLIC_SUMMARY.json", public)
    audit = {"status": "pass", "utc": utc(), "campaigns": len(table),
             "queried_per_campaign": 50, "distinct_per_campaign": 50,
             "seed_paired_label_blind_initialization": True,
             "policy_decision_counts": dict(sorted(policy_counts.items())),
             "ENS_decisions": 0, "glm_calls": 0,
             "private_tree_sha256": combined,
             "lock_sha256": sha(lock_path())}
    save(HERE / "C3_FIVE_AUDIT.json", audit)
    return public, audit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("lock", "preflight", "run", "audit"))
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.command == "lock":
        print(json.dumps(make_lock(), ensure_ascii=False, indent=2))
    elif args.command == "preflight":
        verify_lock()
        value = synthetic_preflight()
        save(HERE / "C3_FIVE_SYNTHETIC_PREFLIGHT.json", value)
        print(json.dumps(value, ensure_ascii=False, indent=2))
    elif args.command == "run":
        run(args.workers)
    else:
        public, audit = audit_and_analyze()
        print(json.dumps({"status": public["status"], "audit": audit["status"],
                          "campaigns": audit["campaigns"], "ENS_decisions": 0,
                          "glm_calls": 0}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

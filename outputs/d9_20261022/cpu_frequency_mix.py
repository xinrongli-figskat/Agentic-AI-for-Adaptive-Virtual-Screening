"""D9 post-exposure CPU controls, with fixed hash draws and paired seeds."""
from __future__ import annotations

import hashlib
import json
import os
import random
import sys
import zipfile
from collections import Counter
from pathlib import Path

for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[key] = "1"
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "outputs"))
sys.path.insert(0, str(ROOT / "outputs/d7_20261021/c_surrogate_factor/runtime_packages"))

from oracle_boundary_v0.oracle_boundary import BatchOracle
from outputs.d7_20261021.c_surrogate_factor_v2.run_c2v2 import load_inputs, read_jsonl
from outputs.d7_20261021.c_surrogate_factor_v2_orthogonal.c3_core import OrthogonalSelector
from outputs.d9_20261022.reconcile import behavior, reconcile

ARCHIVE = ROOT / ".sync_audit/d5_20261020/d5_e_menu_private_20261020.zip"
MAPPING = {
    "knn_greedy": "greedy_like", "logreg_greedy": "greedy_like",
    "ens_one_step_proxy": "greedy_like", "knn_diverse": "diverse_like",
    "uniform_random": "random",
}


def incumbent_weights() -> tuple[dict, list]:
    counts = Counter()
    per_seed = []
    with zipfile.ZipFile(ARCHIVE) as archive:
        for seed in range(20):
            name = f"outputs/d5_20261020/e_menu_private/runs/tnap/bit/glm_extended_seed{seed}/run.json"
            run = json.loads(archive.read(name))
            if not run["complete"] or len(run["trajectory"]) != 5:
                raise RuntimeError(f"D5 bit reference incomplete: {seed}")
            per_seed.append({"seed": seed, "H50": run["H50"]})
            hits_before = sum(int(r["outcome"]) for r in run["trajectory"][0]["observations"])
            for step in run["trajectory"][1:]:
                p = step["decision"]["policy"]
                if p == "diverse_random_coldstart":
                    category = "random" if hits_before == 0 else "diverse_like"
                else:
                    category = MAPPING[p]
                counts[category] += 1
                hits_before += sum(int(r["outcome"]) for r in step["observations"])
    if sum(counts.values()) != 80:
        raise RuntimeError("D5 bit decision count changed")
    return dict(counts), per_seed


def draw(weights, surrogate, seed, round_number):
    order = ("greedy_like", "diverse_like", "random")
    total = sum(weights.values())
    digest = hashlib.sha256(f"d9_frequency_mix_v1|{surrogate}|{seed}|{round_number}".encode()).digest()
    index = int.from_bytes(digest[:16], "big") % total
    for category in order:
        if index < weights.get(category, 0):
            return category
        index -= weights.get(category, 0)
    raise AssertionError("Hash draw fell outside categories")


def one(candidates, labels, selector, surrogate, weights, seed):
    oracle = BatchOracle(candidates, labels, seed=seed, total_budget=50,
                         initialization_queries=10, batch_size=10)
    initial = oracle.proposed_initial_ids()
    answer = oracle.query_batch_tool({"compound_keys": initial})
    trajectory = [{"stage": 0, "policy": "initialization", "mode": "label_blind",
                   "selection": initial, "observations": answer["observations"]}]
    while oracle.public_state()["remaining_budget"]:
        state = oracle.public_state()
        category = draw(weights, surrogate, seed, state["next_round"])
        policy = {"greedy_like": "greedy", "diverse_like": "diverse", "random": "random"}[category]
        selection, mode = selector.select(state, surrogate, policy, seed)
        answer = oracle.query_batch_tool({"compound_keys": selection})
        trajectory.append({"stage": state["next_round"], "drawn_behavior": category,
                           "policy": policy, "mode": mode, "realized_behavior": behavior(mode),
                           "selection": selection, "observations": answer["observations"]})
    keys = [key for stage in trajectory for key in stage["selection"]]
    if len(keys) != 50 or len(set(keys)) != 50:
        raise RuntimeError("CPU mixture violated 50-query budget or uniqueness")
    return {"seed": seed, "surrogate": surrogate, "H50": sum(int(o["outcome"]) for s in trajectory for o in s["observations"]),
            "trajectory": trajectory}


def percentile(values, p):
    v = sorted(values)
    x = (len(v)-1)*p
    lo = int(x)
    return v[lo] + (v[min(lo+1,len(v)-1)]-v[lo])*(x-lo)


def paired_interval(diffs):
    rng = random.Random(20261018)
    means = [sum(diffs[rng.randrange(len(diffs))] for _ in diffs)/len(diffs)
             for _ in range(10000)]
    return [percentile(means,.025), percentile(means,.975)]


def main():
    HERE.mkdir(parents=True, exist_ok=True)
    rec = reconcile()
    strong = rec["correct_realized_behavior_counts"]
    incumbent, incumbent_reference = incumbent_weights()
    public_blob, private_blob = load_inputs()["TNAP"]
    candidates = read_jsonl(public_blob)
    labels = {r["compound_key"]: int(r["outcome"]) for r in read_jsonl(private_blob)}
    selector = OrthogonalSelector(candidates)
    c4 = {seed: [] for seed in range(20)}
    for row in rec["per_run_H50"]:
        c4[row["seed"]].append(row["H50"])
    reference = {"S_strong": [sum(c4[i])/2 for i in range(20)],
                 "S_incumbent": [row["H50"] for row in incumbent_reference]}
    if sum(reference["S_strong"])/20 != 11.325:
        raise RuntimeError("C4 H50 regression failed")
    outputs = {}
    for surrogate, weights in (("S_strong", strong), ("S_incumbent", incumbent)):
        first = [one(candidates, labels, selector, surrogate, weights, i) for i in range(20)]
        second = [one(candidates, labels, selector, surrogate, weights, i) for i in range(20)]
        if first != second:
            raise RuntimeError(f"CPU trajectories are not deterministic: {surrogate}")
        realized = Counter(behavior(s["mode"]) for r in first for s in r["trajectory"][1:])
        drawn = Counter(s["drawn_behavior"] for r in first for s in r["trajectory"][1:])
        mix = [r["H50"] for r in first]
        diffs = [reference[surrogate][i]-mix[i] for i in range(20)]
        outputs[surrogate] = {
            "source_weights": weights, "drawn_behavior_counts": dict(drawn),
            "realized_behavior_counts": dict(realized), "mean_mix_H50": sum(mix)/20,
            "mean_reference_LLM_H50": sum(reference[surrogate])/20,
            "paired_differences_by_seed": diffs,
            "mean_LLM_minus_mix": sum(diffs)/20,
            "paired_bootstrap_95_interval": paired_interval(diffs),
            "mixture_H50_by_seed": mix, "reference_H50_by_seed": reference[surrogate],
            "deterministic_full_trajectory_replay": True,
            "runs": first,
        }
    result = {"post_exposure": True, "pool": "TNAP", "representation": "bit",
              "seed_count": 20, "bootstrap_resamples": 10000, "bootstrap_seed": 20261018,
              "hash_draw": "SHA256(d9_frequency_mix_v1|surrogate|seed|round), first 128 bits modulo total observed behavior count",
              "D5_archive_sha256": hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
              "D5_mapping_note": "Seven-menu D5 bit GLM actions are coarsened to five-menu behavior classes. ENS and logistic greedy are assigned to greedy-like/model-ranked, although their selections are not identical to S_incumbent greedy. This is a descriptive frequency comparator, not an otherwise identical randomized control; only the S_strong comparison isolates timing under the same selector.",
              "D5_mapping": {**MAPPING, "diverse_random_coldstart": "random if no revealed hit, otherwise diverse_like"},
              "cells": outputs}
    private_out = HERE / "d9_private"
    private_out.mkdir(parents=True, exist_ok=True)
    (private_out / "FREQUENCY_MATCHED_CPU_RESULTS.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps({s: {k: v[k] for k in ("source_weights", "realized_behavior_counts", "mean_mix_H50", "mean_reference_LLM_H50", "mean_LLM_minus_mix", "paired_bootstrap_95_interval")} for s,v in outputs.items()}, indent=2))


if __name__ == "__main__":
    main()

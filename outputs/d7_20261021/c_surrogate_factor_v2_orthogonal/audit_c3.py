"""Post-run integrity audit and descriptive paired-range supplement."""
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PRIVATE = ROOT / "outputs/d7_20261021/c_surrogate_factor_v2_orthogonal_private/runs"
POOLS = ("TNAP", "DYRK3")
SURROGATES = ("S_weak", "S_maccs", "S_incumbent", "S_strong", "S_morgan_logreg", "S_morgan_gbdt")
COMMON = ("greedy", "diverse", "persistent_random_until_first_hit", "diverse_random_coldstart")


def main():
    files = sorted(PRIVATE.rglob("*.json"))
    if len(files) != 1880:
        raise RuntimeError(f"Expected 1880 private runs, got {len(files)}")
    root_hash = hashlib.sha256()
    initial = {}
    fallback_counts = {}
    vectors = {}
    duplicate_pairs = {}
    for path in files:
        blob = path.read_bytes()
        root_hash.update(str(path.relative_to(PRIVATE)).replace("\\", "/").encode()+b"\0")
        root_hash.update(hashlib.sha256(blob).digest())
        run = json.loads(blob)
        if run["status"] != "complete" or run["queried_count"] != 50 or run["glm_calls"] != 0:
            raise RuntimeError(f"Incomplete run {path}")
        stages = run["trajectory"]
        if len(stages) != 5 or any(len(stage["selection"]) != 10 or len(stage["observations"]) != 10
                                   for stage in stages):
            raise RuntimeError(f"Invalid stage count {path}")
        ids = [key for stage in stages for key in stage["selection"]]
        if len(ids) != len(set(ids)) or any([row["compound_key"] for row in stage["observations"]] != stage["selection"]
                                           for stage in stages):
            raise RuntimeError(f"Duplicate query or observation order mismatch {path}")
        if run["H50"] != sum(row["outcome"] for stage in stages for row in stage["observations"]):
            raise RuntimeError(f"H50 mismatch {path}")
        key = (run["pool"], run["seed"])
        this_init = stages[0]["selection"]
        if key in initial and initial[key] != this_init:
            raise RuntimeError("Seed-paired initialization differs")
        initial[key] = this_init
        cell = (run["pool"], run["surrogate"], run["arm"], run["seed"])
        if cell in vectors:
            raise RuntimeError("Repeated configuration")
        vectors[cell] = run["H50"]
        fallback_counts[run["pool"]] = fallback_counts.get(run["pool"], 0) + sum(
            stage["mode"] == "one_class_random_fallback" for stage in stages[1:])
        if run["arm"] == "random" and not run["surrogate_invariant"]:
            raise RuntimeError("Random missing invariant flag")
    if len(initial) != 40:
        raise RuntimeError("Missing pool/seed initializations")
    paired = {}
    for pool in POOLS:
        paired[pool] = {}
        for name in SURROGATES:
            seed_ranges = [max(vectors[pool, name, arm, seed] for arm in COMMON) -
                           min(vectors[pool, name, arm, seed] for arm in COMMON)
                           for seed in range(20)]
            paired[pool][name] = {"spread_paired_mean_descriptive": sum(seed_ranges)/20,
                                  "paired_ranges_by_seed": seed_ranges}
            greedy = [vectors[pool,name,"greedy",seed] for seed in range(20)]
            persistent = [vectors[pool,name,"persistent_random_until_first_hit",seed] for seed in range(20)]
            diverse = [vectors[pool,name,"diverse",seed] for seed in range(20)]
            cold = [vectors[pool,name,"diverse_random_coldstart",seed] for seed in range(20)]
            duplicate_pairs[pool,name] = {"greedy_equals_persistent_all_seeds": greedy == persistent,
                                          "diverse_equals_coldstart_all_seeds": diverse == cold}
    result = {"status": "C3_INTEGRITY_PASS", "utc": datetime.now(timezone.utc).isoformat(),
              "private_run_count": len(files), "private_merkle_style_sha256": root_hash.hexdigest(),
              "paired_initialization_groups": len(initial), "queries_per_run": 50,
              "all_queries_distinct_and_observations_aligned": True, "glm_calls": 0,
              "one_class_fallback_batches_by_pool": fallback_counts,
              "strategy_collapse_checks": {f"{p}/{s}": x for (p,s),x in duplicate_pairs.items()},
              "spread_paired_mean_is_descriptive_not_a_gate": paired}
    (HERE / "C3_AUDIT.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "private_run_count": len(files),
                      "private_merkle_style_sha256": root_hash.hexdigest(),
                      "fallback_batches": fallback_counts,
                      "all_collapsed": all(all(y.values()) for y in duplicate_pairs.values())},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()

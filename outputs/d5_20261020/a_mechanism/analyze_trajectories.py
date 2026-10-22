"""Read-only D3/D4 trajectory audit for D5 mechanism analysis.

Run from the repository root. This script writes only to its own D5 A folder.
It deliberately keeps compound-level labels out of Git-visible outputs.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
D3 = ROOT / "outputs/d3_tnap_20261019"
D4 = ROOT / "outputs/d4_tnap_glm_20261019"
MIRROR = D4 / "remote_backup_private_20261019/d4_tnap_glm_20261019"
ZERO = (5, 6, 15, 17, 18, 19)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def trajectory(rep: str, seed: int):
    path = MIRROR / f"d4_glm_private_20261019/runs/llm_{rep}_seed{seed}/run.json"
    verification = json.loads((D4 / "post_glm_verification.json").read_text())
    assert sha(path) == verification["run_hashes"][f"{rep}_seed{seed}"]
    run = json.loads(path.read_text())["result"]
    rows = run["trajectory"]
    assert len(rows) == 5 and run["queried_count"] == 50
    keys = [k for row in rows for k in row["selection"]]
    assert len(keys) == len(set(keys)) == 50
    cumulative = 0
    for row in rows:
        assert len(row["selection"]) == len(row["observations"]) == 10
        assert row["selection"] == [o["compound_key"] for o in row["observations"]]
        cumulative += sum(o["outcome"] for o in row["observations"])
        assert cumulative == row["cumulative_hits"]
    assert cumulative == run["hits_at_budget"]
    return run


def control(rep: str, arm: str, seed: int):
    path = D3 / f"d3_6_runs_private_20261019/{arm}_{rep}_seed{seed}.json"
    saved = json.loads(path.read_text())
    assert saved["summary"]["H50"] == saved["result"]["hits_at_budget"]
    return saved


def main():
    all_rows = []
    zero_rows = []
    for rep in ("bit", "count"):
        for seed in range(20):
            run = trajectory(rep, seed)
            ts = run["trajectory"]
            init_hits = ts[0]["cumulative_hits"]
            row = {"representation": rep, "seed": seed, "initial_hits": init_hits,
                   "glm_H50": run["hits_at_budget"]}
            for number in range(1, 5):
                before = ts[number - 1]["cumulative_hits"]
                after = ts[number]["cumulative_hits"]
                info = ts[number]["information_available"]
                assert info["revealed_count"] == number * 10
                assert info["revealed_hits"] == before
                row[f"r{number}_policy"] = ts[number]["decision"]["policy"]
                row[f"r{number}_before_hits"] = before
                row[f"r{number}_new_hits"] = after - before
                row[f"r{number}_cumulative_hits"] = after
            all_rows.append(row)
            if seed not in ZERO:
                continue
            assert init_hits == 0
            forced = control(rep, "forced_random_coldstart", seed)
            fixed = control(rep, "fixed", seed)
            forced_ts = forced["result"]["trajectory"]
            assert ts[0]["selection"] == forced_ts[0]["selection"]
            assert ts[0]["selection"] == fixed["result"]["trajectory"][0]["selection"]
            zero_opportunities = [number for number in range(1, 5)
                                  if ts[number - 1]["cumulative_hits"] == 0]
            random_at_zero = [number for number in zero_opportunities
                              if row[f"r{number}_policy"] == "uniform_random"]
            diverse_at_zero = [number for number in zero_opportunities
                               if row[f"r{number}_policy"] == "knn_diverse"]
            greedy_at_zero = [number for number in zero_opportunities
                              if row[f"r{number}_policy"] == "knn_greedy"]
            initial_random_streak = 0
            for number in zero_opportunities:
                if row[f"r{number}_policy"] == "uniform_random" and number == initial_random_streak + 1:
                    initial_random_streak += 1
                else:
                    break
            forced_zero_opportunities = [number for number in range(1, 5)
                                         if forced_ts[number - 1]["cumulative_hits"] == 0]
            for number in forced_zero_opportunities:
                assert forced_ts[number]["decision"]["policy"] == "uniform_random"
            zero_rows.append({**row,
                              "forced_H50": forced["summary"]["H50"],
                              "fixed_H50": fixed["summary"]["H50"],
                              "glm_minus_forced": run["hits_at_budget"] - forced["summary"]["H50"],
                              "glm_zero_hit_opportunities": len(zero_opportunities),
                              "glm_random_when_zero": len(random_at_zero),
                              "glm_diverse_when_zero": len(diverse_at_zero),
                              "glm_greedy_when_zero": len(greedy_at_zero),
                              "glm_random_initial_streak": initial_random_streak,
                              "forced_zero_hit_opportunities": len(forced_zero_opportunities),
                              "forced_random_when_zero": len(forced_zero_opportunities),
                              "glm_first_hit_round": next((n for n in range(1, 5)
                                                            if ts[n]["cumulative_hits"] > 0), None),
                              "forced_first_hit_round": next((n for n in range(1, 5)
                                                               if forced_ts[n]["cumulative_hits"] > 0), None)})

    def write_csv(name, rows):
        with (OUT / name).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    write_csv("all_glm_policy_sequences.csv", all_rows)
    write_csv("zero_hit_seed_comparison.csv", zero_rows)
    summary = {}
    for rep in ("bit", "count"):
        group = [r for r in zero_rows if r["representation"] == rep]
        summary[rep] = {
            "zero_seed_count": len(group),
            "glm_zero_hit_decision_opportunities": sum(r["glm_zero_hit_opportunities"] for r in group),
            "glm_random_while_zero": sum(r["glm_random_when_zero"] for r in group),
            "glm_diverse_while_zero": sum(r["glm_diverse_when_zero"] for r in group),
            "glm_greedy_while_zero": sum(r["glm_greedy_when_zero"] for r in group),
            "glm_initial_random_streak_distribution": dict(Counter(r["glm_random_initial_streak"] for r in group)),
            "forced_random_while_zero": sum(r["forced_random_when_zero"] for r in group),
            "glm_minus_forced_mean_zero_seeds": sum(r["glm_minus_forced"] for r in group) / len(group),
            "glm_H50_zero_seed_mean": sum(r["glm_H50"] for r in group) / len(group),
            "forced_H50_zero_seed_mean": sum(r["forced_H50"] for r in group) / len(group),
            "fixed_H50_zero_seed_mean": sum(r["fixed_H50"] for r in group) / len(group),
        }
    (OUT / "trajectory_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

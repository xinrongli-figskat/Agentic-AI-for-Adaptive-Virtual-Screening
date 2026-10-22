"""Run all predeclared D5 fixed-item and uniform-mixture CPU controls."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path("/driveA/xinrong/agentic-screening")
sys.path.insert(0, str(ROOT))
from outputs.d5_20261020.e_menu.expanded_tools import MENU
from outputs.d5_20261020.e_menu.run_extended import BASE, PRIVATE_OUT, run_one, save_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", choices=("tnap", "dyrk3", "both"), default="both")
    args = parser.parse_args()
    pools = ("tnap", "dyrk3") if args.pool == "both" else (args.pool,)
    arms = tuple(f"fixed:{policy}" for policy in MENU) + ("random_mixture_extended",)
    jobs = [(pool, rep, seed, arm) for pool in pools for rep in ("bit", "count")
            for arm in arms for seed in range(20)]
    assert len(jobs) == 320 * len(pools)
    progress_path = PRIVATE_OUT / "cpu_matrix_progress.json"
    completed = 0
    for pool, rep, seed, arm in jobs:
        result = run_one(pool, rep, seed, arm)
        assert result["complete"] and result["glm_calls"] == 0
        completed += 1
        if completed % 20 == 0 or completed == len(jobs):
            save_json(progress_path, {"completed": completed, "expected": len(jobs),
                                      "last_job": {"pool": pool, "representation": rep,
                                                   "seed": seed, "arm": arm},
                                      "all_complete_so_far": True})
            print(json.dumps({"completed": completed, "expected": len(jobs),
                              "last_pool": pool, "last_representation": rep,
                              "last_arm": arm}), flush=True)


if __name__ == "__main__":
    main()

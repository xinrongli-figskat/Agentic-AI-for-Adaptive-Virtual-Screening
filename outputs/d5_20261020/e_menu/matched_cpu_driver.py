"""Posthoc shared-menu mixture CPU execution after 160-slot GLM menu trial."""

from __future__ import annotations

import json
from pathlib import Path

from outputs.d5_20261020.e_menu.run_extended import BASE, PRIVATE_OUT, run_one, sha, validate_sources


def main():
    validate_sources()
    lock = json.loads((BASE / "e_menu_matched_weights_lock.json").read_text())
    weights_path = BASE / "e_menu_matched_weights.json"
    assert sha(weights_path) == lock["weights_sha256"]
    weights = json.loads(weights_path.read_text())
    count = 0
    for pool in ("tnap", "dyrk3"):
        for rep in ("bit", "count"):
            for seed in range(20):
                result = run_one(pool, rep, seed, "matched_proportion_extended", mix_weights=weights)
                assert result["complete"] and result["glm_calls"] == 0
                count += 1
                if count % 20 == 0:
                    print(json.dumps({"completed": count, "expected": 80, "pool": pool,
                                      "representation": rep}), flush=True)
    assert count == 80


if __name__ == "__main__":
    main()

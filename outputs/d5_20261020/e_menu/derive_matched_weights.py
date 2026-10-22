"""Posthoc GLM menu proportions for the shared-tool CPU mixture control."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path("/driveA/xinrong/agentic-screening")
sys.path.insert(0, str(ROOT))
from outputs.d5_20261020.e_menu.expanded_tools import MENU
from outputs.d5_20261020.e_menu.run_extended import BASE, PRIVATE_OUT, sha, utc, validate_sources


def main():
    validate_sources()
    weights = Counter()
    calls = 0
    slots = 0
    for rep in ("bit", "count"):
        for seed in range(20):
            run_path = PRIVATE_OUT / "runs" / "tnap" / rep / f"glm_extended_seed{seed}" / "run.json"
            run = json.loads(run_path.read_text())
            assert run["complete"] and len(run["trajectory"]) == 5
            for step in run["trajectory"][1:]:
                slots += 1
                if step.get("glm_call") is not None:
                    weights[step["decision"]["policy"]] += 1
                    calls += 1
    assert slots == 160 and calls <= 160 and sum(weights.values()) == calls
    assert set(weights) <= set(MENU)
    result = {policy: weights[policy] for policy in MENU}
    path = BASE / "e_menu_matched_weights.json"
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    lock = {"derived_at_utc": utc(), "posthoc": True,
            "derived_from": "TNAP GLM open decision calls only; automatic commitment slots excluded",
            "decision_slots": slots, "model_calls": calls,
            "weights_sha256": sha(path), "derivation_script_sha256": sha(Path(__file__))}
    lock_path = BASE / "e_menu_matched_weights_lock.json"
    lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision_slots": slots, "glm_calls": calls,
                      "weights_sha256": sha(path), "weights": result}))


if __name__ == "__main__":
    main()

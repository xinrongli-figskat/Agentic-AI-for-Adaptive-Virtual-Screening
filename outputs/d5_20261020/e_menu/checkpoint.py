"""Read-only D5 first-10-bit-seed checkpoint, before any later GLM runs."""

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
    results = []
    counts = Counter()
    calls = 0
    http = 0
    returned_tokens = Counter()
    for seed in range(10):
        folder = PRIVATE_OUT / "runs" / "tnap" / "bit" / f"glm_extended_seed{seed}"
        assert not (folder / "failure_events.json").exists(), folder
        assert not (folder / "pending.json").exists(), folder
        run = json.loads((folder / "run.json").read_text())
        assert run["complete"] and run["seed"] == seed and run["representation"] == "bit"
        assert run["pool"] == "tnap" and run["arm"] == "glm_extended"
        assert len(run["trajectory"]) == 5 and run["queried_count"] == 50
        keys = [key for step in run["trajectory"] for key in step["selection"]]
        assert len(keys) == len(set(keys)) == 50
        assert sum(row["outcome"] for step in run["trajectory"]
                   for row in step["observations"]) == run["H50"]
        for step in run["trajectory"][1:]:
            assert step["decision"]["policy"] in MENU
            counts[step["decision"]["policy"]] += 1
            call = step["glm_call"]
            if call is not None:
                assert call["request_id"] and call["usage"]
                assert call["public_summary"]["queried_count"] == step["information_available"]["revealed_count"]
                assert "private_labels" not in json.dumps(call["public_summary"])
                calls += 1
                http += len(call["api_attempt_log"])
                for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                    returned_tokens[key] += int(call["usage"].get(key, 0))
        assert run["glm_calls"] == sum(step["glm_call"] is not None
                                       for step in run["trajectory"][1:])
        results.append({"seed": seed, "H50": run["H50"], "glm_calls": run["glm_calls"]})
    assert sum(counts.values()) == 40 and calls <= 40
    assert http >= calls
    result = {"checked_at_utc": utc(), "status": "pass",
              "first_checkpoint_decision_slots": 40,
              "completed_runs": 10, "unique_queries_per_run": 50,
              "glm_calls": calls, "http_attempts": http,
              "policy_counts": dict(counts), "returned_tokens": dict(returned_tokens),
              "runs": results, "frozen_and_code_lock_verified": True,
              "new_program_file_sha256": sha(Path(__file__))}
    path = BASE / "e_menu_bit_checkpoint.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "completed_runs": 10,
                      "decision_slots": 40, "glm_calls": calls,
                      "checkpoint_sha256": sha(path)}))


if __name__ == "__main__":
    main()

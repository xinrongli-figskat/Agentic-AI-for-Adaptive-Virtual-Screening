"""Offline, additive audit of the C4 physical-call ceiling checkpoint."""

import hashlib
import json
from collections import Counter
from pathlib import Path

from analyze_c4 import frozen_labels
from run_c4 import (
    HERE, MENU, PRIVATE, file_sha, lock_path, physical_count, run_path, save, utc,
)


def main():
    candidates, labels = frozen_labels()
    public_keys = {item["compound_key"] for item in candidates}
    complete, partial, total_queried = 0, [], 0
    named, modes, decisions, automatic = Counter(), Counter(), 0, 0
    for rep in (1, 2):
        for seed in range(20):
            path = run_path(rep, seed)
            if not path.exists():
                raise RuntimeError(f"Missing run: {rep}/{seed}")
            run = json.loads(path.read_text(encoding="utf-8"))
            if run["lock_sha256"] != file_sha(lock_path()):
                raise RuntimeError("Lock mismatch")
            steps = run["trajectory"]
            keys = [key for step in steps for key in step["selection"]]
            if len(keys) != len(set(keys)) or len(keys) > 50 or not set(keys) <= public_keys:
                raise RuntimeError(f"Query or identity failure: {rep}/{seed}")
            if len(keys) != run["queried_count"]:
                raise RuntimeError("Recorded query count differs")
            for step in steps:
                expected = [
                    {"compound_key": key, "outcome": labels[key]}
                    for key in step["selection"]
                ]
                if step["observations"] != expected:
                    raise RuntimeError(f"Oracle mismatch: {rep}/{seed}")
                if step["stage"]:
                    if step["policy"] not in MENU or step["policy"] == "ens_one_step_proxy":
                        raise RuntimeError("ENS or out-of-menu decision")
                    named[step["policy"]] += 1
                    modes[step["mode"]] += 1
                    if step["automatic_commitment"]:
                        automatic += 1
                    else:
                        decisions += 1
            if run["complete"]:
                if len(keys) != 50 or len(steps) != 5:
                    raise RuntimeError("Incomplete run marked complete")
                complete += 1
            else:
                partial.append({"repeat": rep, "seed": seed,
                                "queries": len(keys), "completed_feedback_batches": len(steps)-1})
            total_queried += len(keys)

    http = [json.loads(path.read_text(encoding="utf-8"))
            for path in sorted((PRIVATE / "http").glob("http_*.json"))]
    if len(http) != physical_count() or [item["index"] for item in http] != list(range(1, len(http)+1)):
        raise RuntimeError("Physical-call receipt sequence invalid")
    transport = Counter(item["status"] for item in http)
    response_files = list((PRIVATE / "runs").rglob("decision_round*_try*.json"))
    responses = [json.loads(path.read_text(encoding="utf-8")) for path in response_files]
    response_status = Counter(item["status"] for item in responses)
    if response_status.get("valid_decision", 0) != decisions:
        raise RuntimeError("Valid decision receipts differ from trajectories")
    usage = Counter()
    for item in responses:
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            value = (item.get("usage") or {}).get(key)
            if isinstance(value, int):
                usage[key] += value
    private_hashes = sorted(
        f"{path.relative_to(PRIVATE).as_posix()} {file_sha(path)}"
        for path in PRIVATE.rglob("*.json")
    )
    result = {
        "status": "physical_budget_exhausted_before_full_matrix",
        "utc": utc(),
        "scope": "TNAP/S_strong/bit",
        "locked_protocol_sha256": file_sha(HERE / "C4_PROTOCOL_v1.md"),
        "lock_sha256": file_sha(lock_path()),
        "planned_campaigns": 40,
        "complete_campaigns": complete,
        "partial_campaigns": partial,
        "total_oracle_queries_saved": total_queried,
        "physical_provider_calls": len(http),
        "physical_call_statuses": dict(transport),
        "model_response_statuses": dict(response_status),
        "valid_model_decisions": decisions,
        "automatic_commitment_batches": automatic,
        "policy_name_counts": dict(named),
        "realized_mode_counts": dict(modes),
        "returned_usage": dict(usage),
        "ENS_decisions": 0,
        "private_tree_sha256": hashlib.sha256(("\n".join(private_hashes)+"\n").encode()).hexdigest(),
        "primary_comparison_complete": complete == 40,
        "maximum_additional_decisions_needed": 4 - partial[0]["completed_feedback_batches"] if partial else 0,
    }
    save(HERE / "C4_BUDGET_HALT_AUDIT.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

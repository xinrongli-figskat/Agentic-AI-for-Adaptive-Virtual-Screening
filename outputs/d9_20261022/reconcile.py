"""Read-only reconciliation of the locked C4 trajectories."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
C4 = ROOT / "outputs/d7_20261021/c4_five_private/runs"
PUBLIC = ROOT / "outputs/d7_20261021/c4_five/C4_PUBLIC_ANALYSIS.json"


def behavior(mode: str) -> str:
    if mode == "scored_greedy":
        return "greedy_like"
    if mode == "scored_diverse":
        return "diverse_like"
    if mode in {"policy_random", "policy_coldstart_random", "one_class_random_fallback"}:
        return "random"
    raise ValueError(f"Unrecognized C4 execution mode: {mode}")


def reconcile() -> dict:
    public = json.loads(PUBLIC.read_text(encoding="utf-8"))
    names, realized = Counter(), Counter()
    automatic, coldstart, one_class = [], [], []
    per_run, source_hashes = [], {}
    for rep in (1, 2):
        for seed in range(20):
            path = C4 / f"rep{rep}" / f"seed{seed}" / "run.json"
            raw = path.read_bytes()
            source_hashes[str(path.relative_to(ROOT)).replace("\\", "/")] = hashlib.sha256(raw).hexdigest()
            run = json.loads(raw)
            if not run["complete"] or len(run["trajectory"]) != 5:
                raise RuntimeError(f"Incomplete C4 run: {path}")
            per_run.append({"repeat": rep, "seed": seed, "H50": run["H50"]})
            for stage in run["trajectory"][1:]:
                policy, mode = stage["policy"], stage["mode"]
                names[policy] += 1
                realized[behavior(mode)] += 1
                marker = {"repeat": rep, "seed": seed, "stage": stage["stage"],
                          "policy": policy, "mode": mode,
                          "hits_before": stage["revealed_hits_before"]}
                if stage.get("automatic_commitment"):
                    automatic.append(marker)
                if mode == "policy_coldstart_random":
                    coldstart.append(marker)
                if mode == "one_class_random_fallback":
                    one_class.append(marker)
                if policy in {"persistent_random_until_first_hit", "diverse_random_coldstart"}:
                    if stage["revealed_hits_before"] == 0 and behavior(mode) != "random":
                        raise RuntimeError("Cold-start policy was not random")
                    if stage["revealed_hits_before"] > 0 and behavior(mode) == "random" and mode != "one_class_random_fallback":
                        raise RuntimeError("Post-hit policy unexpectedly random")
    mean_h50 = sum(row["H50"] for row in per_run) / 40
    if mean_h50 != 11.325 or sum(names.values()) != 160 or sum(realized.values()) != 160:
        raise RuntimeError("C4 regression failed")
    return {"source": "40 C4 locked private trajectories; no historical file modified",
            "source_sha256": source_hashes, "run_count": 40, "decision_batches": 160,
            "C4_mean_H50": mean_h50,
            "original_policy_name_counts": public["policy_name_counts"],
            "original_realized_behavior_counts": public["realized_behavior_counts"],
            "recounted_policy_name_counts": dict(names),
            "correct_realized_behavior_counts": dict(realized),
            "automatic_commitment_batches": automatic,
            "coldstart_random_batches": coldstart,
            "one_class_random_fallback_batches": one_class,
            "classification_rule": {"scored_greedy": "greedy_like", "scored_diverse": "diverse_like",
                                    "policy_random": "random", "policy_coldstart_random": "random",
                                    "one_class_random_fallback": "random"},
            "counting_rule": "Every post-initialization batch counts once; automatic commitment counts as its executed mode even when no GLM call was made.",
            "C4_public_table_to_correct": "neither" if (dict(names) == public["policy_name_counts"] and dict(realized) == public["realized_behavior_counts"]) else ("realized_behavior_counts" if dict(names) == public["policy_name_counts"] else "both"),
            "explanation": "The task-card arithmetic 107/52/1 assumes cold-start actions always act as scored policies. In fact, 13 such batches ran seeded random because no hit had yet been revealed; together with one explicit random batch this yields random=14. The original C4 realized count is trajectory-correct; only that proposed nominal mapping needs correction.",
            "per_run_H50": per_run}


if __name__ == "__main__":
    HERE.mkdir(parents=True, exist_ok=True)
    result = reconcile()
    output = HERE / "C4_BEHAVIOUR_COUNT_RECONCILIATION.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("C4_mean_H50", "recounted_policy_name_counts", "correct_realized_behavior_counts", "C4_public_table_to_correct")}, ensure_ascii=False))

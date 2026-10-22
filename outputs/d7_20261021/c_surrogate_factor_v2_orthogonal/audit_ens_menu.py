"""Aggregate strategy choices in GBDT meta runs; publish no private outcomes."""
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PRIVATE = ROOT / "outputs/d7_20261021/c_surrogate_factor_v2_orthogonal_private/runs"


def main():
    counts = {}
    for pool in ("TNAP", "DYRK3"):
        for surrogate in ("S_strong", "S_morgan_gbdt"):
            by_arm = {}
            for arm in ("bandit_thompson", "bandit_ucb1", "random_mixture"):
                paths = sorted((PRIVATE / pool / surrogate / arm).glob("seed*.json"))
                if len(paths) != 20:
                    raise RuntimeError("Expected 20 meta runs per cell")
                policies = Counter()
                ens_runs = 0
                for path in paths:
                    run = json.loads(path.read_text())
                    choices = [step["policy"] for step in run["trajectory"][1:]]
                    policies.update(choices)
                    ens_runs += "ens_one_step_proxy" in choices
                by_arm[arm] = {"policy_counts": dict(policies),
                               "runs_that_selected_ENS": ens_runs}
            counts[f"{pool}/{surrogate}"] = by_arm
    total = sum(entry["policy_counts"].get("ens_one_step_proxy", 0)
                for cell in counts.values() for entry in cell.values())
    result = {"status": "GBDT_META_ENS_SPEC_CONFLICT_CONFIRMED", "utc": datetime.now(timezone.utc).isoformat(),
              "post_exposure": True, "fixed_GBDT_ENS_runs": 0,
              "GBDT_meta_ENS_decisions": total,
              "GBDT_meta_runs_total": 2*2*3*20,
              "count_by_pool_surrogate_arm": counts,
              "affected_metrics": ["GBDT adaptive_gap", "six-point AUC-versus-adaptive-gap trend"],
              "unaffected_metrics": ["fixed common-policy spread and bootstrap intervals", "random floor"],
              "glm_calls": 0}
    (HERE / "C3_GBDT_META_ENS_AUDIT.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"status": result["status"],
                      "GBDT_meta_ENS_decisions": total,
                      "GBDT_meta_runs_total": result["GBDT_meta_runs_total"]}))


if __name__ == "__main__":
    main()

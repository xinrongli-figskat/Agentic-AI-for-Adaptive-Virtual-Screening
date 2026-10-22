"""No-real-label boundary and budget smoke checks before C3 full execution."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "outputs"))
sys.path.insert(0, str(ROOT / "outputs/d7_20261021/c_surrogate_factor/runtime_packages"))
from oracle_boundary_v0.oracle_boundary import BatchOracle
from outputs.d7_20261021.c_surrogate_factor_v2_orthogonal.c3_core import OrthogonalSelector
from outputs.d7_20261021.c_surrogate_factor_v2_orthogonal.run_full_c3 import MetaController, SURROGATES, jobs


def main():
    source = ROOT / "data/benchmarks/tnap_chembl1738510_v1/public/candidates.jsonl"
    candidates = [json.loads(line) for line in source.read_text().splitlines() if line][:80]
    keys = [row["compound_key"] for row in candidates]
    first = BatchOracle(candidates, {key: 0 for key in keys}, seed=8,
                        total_budget=50, initialization_queries=10, batch_size=10).proposed_initial_ids()
    outputs = []
    for unseen in (0, 1):
        labels = {key: (0 if key in first else unseen) for key in keys}
        oracle = BatchOracle(candidates, labels, seed=8, total_budget=50,
                             initialization_queries=10, batch_size=10)
        oracle.query_batch_tool({"compound_keys": first})
        state = oracle.public_state()
        selector = OrthogonalSelector(candidates)
        results = {}
        for name in SURROGATES:
            results[name] = {}
            for policy in ("greedy", "diverse", "random",
                           "persistent_random_until_first_hit", "diverse_random_coldstart"):
                selection, mode = selector.select(state, name, policy, 8)
                results[name][policy] = (selection, mode)
        for meta in ("bandit_thompson", "bandit_ucb1", "random_mixture"):
            results[meta] = MetaController(meta, 8).choose(state)
        outputs.append(results)
    if outputs[0] != outputs[1]:
        raise AssertionError("Unrevealed synthetic labels affected C3 selection")
    if len(jobs()) != 1880:
        raise AssertionError("Unexpected C3 job count")
    result = {"status": "C3_SYNTHETIC_PREFLIGHT_PASS", "utc": datetime.now(timezone.utc).isoformat(),
              "real_labels_read": False, "unrevealed_outcome_perturbation_invariant": True,
              "checked_surrogates": list(SURROGATES), "unique_jobs": 1880,
              "glm_calls": 0}
    (HERE / "C3_SYNTHETIC_PREFLIGHT.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()

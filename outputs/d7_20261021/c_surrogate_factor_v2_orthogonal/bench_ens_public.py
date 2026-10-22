"""Measure full-size 64+64 ENS refitting on public TNAP structures and fake labels."""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "outputs"))
sys.path.insert(0, str(ROOT / "outputs/d7_20261021/c_surrogate_factor/runtime_packages"))
from oracle_boundary_v0.oracle_boundary import deterministic_order
from outputs.d7_20261021.c_surrogate_factor_v2_orthogonal.c3_core import OrthogonalSelector


def main():
    path = ROOT / "data/benchmarks/tnap_chembl1738510_v1/public/candidates.jsonl"
    candidates = [json.loads(line) for line in path.read_text().splitlines() if line]
    selector = OrthogonalSelector(candidates)
    first = deterministic_order([row["compound_key"] for row in candidates], 0, "init")[:10]
    state = {"revealed": [{"compound_key": key, "outcome": i % 2} for i, key in enumerate(first)],
             "next_batch_size": 10, "next_round": 1, "remaining_budget": 40}
    measured = {}
    for name in ("S_morgan_gbdt", "S_strong"):
        started = time.perf_counter()
        selection, mode = selector.select(state, name, "ens_one_step_proxy", 0)
        measured[name] = {"elapsed_seconds": time.perf_counter()-started,
                          "selected_count": len(selection), "mode": mode}
        print(json.dumps({name: measured[name]}), flush=True)
    result = {"status": "PUBLIC_SYNTHETIC_ENS_WALL_TIME", "utc": datetime.now(timezone.utc).isoformat(),
              "no_real_labels": True, "glm_calls": 0, "criterion_seconds_per_decision": 5.0,
              "skip_both_GBDT_ENS": any(item["elapsed_seconds"] > 5.0 for item in measured.values()),
              "measured": measured}
    (HERE / "ENS_PUBLIC_TIMING.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()

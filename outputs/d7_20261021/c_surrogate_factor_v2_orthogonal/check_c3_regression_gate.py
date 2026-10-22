"""Check the first known one-class seed against immutable D5 trajectories.

This is a stop-gate diagnostic, not a new campaign. It executes no C3 matrix.
"""
import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "outputs"))
sys.path.insert(0, str(ROOT / "outputs/d7_20261021/c_surrogate_factor/runtime_packages"))
from oracle_boundary_v0.oracle_boundary import BatchOracle
from outputs.campaign_v0.numerical_tools import NumericalTools
from outputs.d7_20261021.c_surrogate_factor_v2.run_c2v2 import load_inputs, read_jsonl
from outputs.d7_20261021.c_surrogate_factor.c1_surrogates import SurrogateBank

ARCHIVE = ROOT / ".sync_audit/d5_20261020/d5_e_menu_private_20261020.zip"
ARCHIVE_SHA = "2b812fc95cac56d225d5b3034940598ce05df12180bb403d7e17aeb81ce9440a"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if sha(ARCHIVE) != ARCHIVE_SHA:
        raise RuntimeError("Historical D5 archive hash mismatch")
    inputs = load_inputs()
    candidates = read_jsonl(inputs["TNAP"][0])
    labels = {row["compound_key"]: int(row["outcome"])
              for row in read_jsonl(inputs["TNAP"][1])}
    seed = 5  # First frozen D5 seed with a zero-hit initialization.
    oracle = BatchOracle(candidates, labels, seed=seed, total_budget=50,
                         initialization_queries=10, batch_size=10)
    initial = oracle.proposed_initial_ids()
    oracle.query_batch_tool({"compound_keys": initial})
    state = oracle.public_state()
    if sum(row["outcome"] for row in state["revealed"]) != 0:
        raise RuntimeError("Expected zero-hit initialization changed")
    one_class = SurrogateBank(candidates).score("S_incumbent", state["revealed"])
    if one_class is not None:
        raise RuntimeError("Locked C1 one-class fallback changed")
    numerical = NumericalTools(candidates, representation="bit")
    frozen_greedy = numerical.select_batch(state, policy="knn_greedy", seed=seed,
                                           round_number=state["next_round"])
    required_c1_fallback = numerical.select_batch(state, policy="uniform_random", seed=seed,
                                                   round_number=state["next_round"])
    with zipfile.ZipFile(ARCHIVE) as z:
        matches = [name for name in z.namelist() if name.endswith(
            f"e_menu_private/runs/tnap/bit/fixed_knn_greedy_seed{seed}/run.json")]
        if len(matches) != 1:
            raise RuntimeError("Historical run not unique")
        historical = json.loads(z.read(matches[0]))
    saved = historical["trajectory"][1]["selection"]
    if saved != frozen_greedy:
        raise RuntimeError("D5 source and historical trajectory differ")
    divergence = next((i for i, (x, y) in enumerate(zip(required_c1_fallback, saved), 1)
                       if x != y), None)
    result = {
        "status": "TIER_B_STOP_PRE_C3", "utc": datetime.now(timezone.utc).isoformat(),
        "pool": "TNAP", "representation": "bit", "seed": seed,
        "checkpoint": "first feedback batch after 10-query zero-hit initialization",
        "revealed_hits_before_selection": 0,
        "locked_C1_score": None,
        "locked_C1_required_policy": "uniform_random",
        "D5_frozen_policy": "knn_greedy",
        "first_divergent_selection_position": divergence,
        "selection_sequences_equal": required_c1_fallback == saved,
        "C1_fallback_first_three_keys": required_c1_fallback[:3],
        "D5_first_three_keys": saved[:3],
        "D5_historical_H50": historical["H50"],
        "D5_archive_sha256": ARCHIVE_SHA,
        "C1_v1_code_sha256": sha(ROOT / "outputs/d7_20261021/c_surrogate_factor/c1_surrogates.py"),
        "D5_numerical_tools_sha256": sha(ROOT / "outputs/campaign_v0/numerical_tools.py"),
        "C1_v2_lock_sha256": sha(HERE / "C1_LOCK_v2.json"),
        "C2_six_summary_sha256": sha(HERE / "C2_SIX_PUBLIC.json"),
        "C3_campaigns_executed": 0,
        "C4_GLM_calls": 0,
    }
    out = HERE / "C3_REGRESSION_GATE.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

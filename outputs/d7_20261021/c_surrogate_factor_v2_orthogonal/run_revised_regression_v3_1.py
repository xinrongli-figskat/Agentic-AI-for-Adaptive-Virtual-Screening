"""Run only the seven versioned TNAP compatibility checks and stop on mismatch."""
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
from outputs.d7_20261021.c_surrogate_factor_v2.run_c2v2 import load_inputs, read_jsonl
from outputs.d7_20261021.c_surrogate_factor_v2_orthogonal.c3_core import OrthogonalSelector

ARCHIVE = ROOT / ".sync_audit/d5_20261020/d5_e_menu_private_20261020.zip"
ARCHIVE_SHA = "2b812fc95cac56d225d5b3034940598ce05df12180bb403d7e17aeb81ce9440a"
CASES = (
    ("greedy", "S_incumbent", "persistent_random_until_first_hit"),
    ("diverse", "S_incumbent", "diverse_random_coldstart"),
    ("random", "S_incumbent", "uniform_random"),
    ("persistent_random_until_first_hit", "S_incumbent", "persistent_random_until_first_hit"),
    ("diverse_random_coldstart", "S_incumbent", "diverse_random_coldstart"),
    ("greedy", "S_morgan_logreg", "logreg_greedy"),
    ("ens_one_step_proxy", "S_incumbent", "ens_one_step_proxy"),
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def historical(z, policy, seed):
    suffix = f"e_menu_private/runs/tnap/bit/fixed_{policy}_seed{seed}/run.json"
    matches = [name for name in z.namelist() if name.endswith(suffix)]
    if len(matches) != 1:
        raise RuntimeError((suffix, matches))
    return json.loads(z.read(matches[0]))


def run_one(candidates, labels, selector, policy, surrogate, seed):
    oracle = BatchOracle(candidates, labels, seed=seed, total_budget=50,
                         initialization_queries=10, batch_size=10)
    selections = [oracle.proposed_initial_ids()]
    responses = [oracle.query_batch_tool({"compound_keys": selections[0]})["observations"]]
    modes = ["initialization"]
    while oracle.public_state()["remaining_budget"]:
        state = oracle.public_state()
        selected, mode = selector.select(state, surrogate, policy, seed)
        selections.append(selected)
        responses.append(oracle.query_batch_tool({"compound_keys": selected})["observations"])
        modes.append(mode)
    if sum(map(len, selections)) != 50 or len({key for batch in selections for key in batch}) != 50:
        raise RuntimeError("Query budget or uniqueness violated")
    return selections, responses, modes


def main():
    lock = json.loads((HERE / "C3_V3_1_LOCK.json").read_text())
    for key, filename in (("addendum", "C3_REGRESSION_ADDENDUM_v3.md"),
                          ("core", "c3_core.py"), ("runner", "run_revised_regression_v3_1.py")):
        if sha(HERE / filename) != lock["file_sha256"][key]:
            raise RuntimeError("Locked C3 file changed: " + filename)
    if sha(ARCHIVE) != ARCHIVE_SHA:
        raise RuntimeError("D5 backup changed")
    public, private = load_inputs()["TNAP"]
    candidates = read_jsonl(public)
    labels = {row["compound_key"]: int(row["outcome"]) for row in read_jsonl(private)}
    selector = OrthogonalSelector(candidates)
    results = []
    with zipfile.ZipFile(ARCHIVE) as z:
        for policy, surrogate, historical_arm in CASES:
            values = []
            for seed in range(20):
                selections, responses, modes = run_one(candidates, labels, selector, policy, surrogate, seed)
                reference = historical(z, historical_arm, seed)["trajectory"]
                hits_initial = sum(row["outcome"] for row in responses[0])
                for stage in range(5):
                    # ENS is intentionally different on zero-hit initialization
                    # seeds; verify the fallback and budget, not false identity.
                    compare = not (policy == "ens_one_step_proxy" and hits_initial == 0)
                    if compare and (selections[stage] != reference[stage]["selection"] or
                                    responses[stage] != reference[stage]["observations"]):
                        failure = {"status": "TIER_B_STOP", "policy": policy, "surrogate": surrogate,
                                   "seed": seed, "stage": stage,
                                   "first_new_key": selections[stage][0],
                                   "first_historical_key": reference[stage]["selection"][0]}
                        (HERE / "C3_REVISED_REGRESSION_FAILURE.json").write_text(
                            json.dumps(failure, indent=2) + "\n", encoding="utf-8")
                        print(json.dumps(failure)); return 2
                if policy == "ens_one_step_proxy" and hits_initial == 0:
                    # All states with just one observed class must use C1 fallback.
                    seen = []
                    for batch, mode in zip(responses[1:], modes[1:]):
                        if len({row["outcome"] for row in responses[0]+seen}) == 1 and mode != "one_class_random_fallback":
                            raise RuntimeError("ENS cold-start fallback missing")
                        seen.extend(batch)
                values.append(sum(row["outcome"] for batch in responses for row in batch))
            results.append({"policy": policy, "surrogate": surrogate,
                            "historical_arm": historical_arm,
                            "mean_H50": sum(values)/20, "by_seed": values,
                            "historical_identity_checked_where_applicable": True})
            print(json.dumps({"completed_case": policy, "surrogate": surrogate,
                              "mean_H50": results[-1]["mean_H50"]}), flush=True)
    output = {"status": "C3_REVISED_REGRESSIONS_PASS", "utc": datetime.now(timezone.utc).isoformat(),
              "post_exposure": True, "glm_calls": 0, "case_count": len(results),
              "cases": results, "lock_sha256": sha(HERE / "C3_V3_1_LOCK.json")}
    (HERE / "C3_REVISED_REGRESSIONS.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

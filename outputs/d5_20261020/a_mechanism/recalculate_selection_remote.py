"""Read-only numerical replay on lab-4090; feed to remote Python stdin.

No file is written on the remote host. Compound-level output belongs in the
Git-ignored selection_private folder on the local machine.
"""

import hashlib
import json
import sys
from pathlib import Path

from rdkit import DataStructs

ROOT = Path("/driveA/xinrong/agentic-screening")
sys.path.insert(0, str(ROOT))
from campaign_v0.numerical_tools import NumericalTools

seed = 19
public = [json.loads(line) for line in (ROOT / "outputs/d3_tnap_20261019/freeze_tnap_v1/public/candidates.jsonl").read_text().splitlines()]
labels = {r["compound_key"]: r["outcome"] for r in
          (json.loads(line) for line in (ROOT / "outputs/d3_tnap_20261019/freeze_tnap_v1_private_labels/oracle_labels.jsonl").read_text().splitlines())}
assert len(public) == len(labels) == 462 and sum(labels.values()) == 53
run = json.loads((ROOT / f"outputs/d4_tnap_glm_20261019/d4_glm_private_20261019/runs/llm_bit_seed{seed}/run.json").read_text())
init = run["result"]["trajectory"][0]
assert sum(r["outcome"] for r in init["observations"]) == 0
assert all(labels[r["compound_key"]] == 0 for r in init["observations"])
state = {"revealed": init["observations"], "next_batch_size": 10, "remaining_budget": 40}

results = {"seed": seed, "public_candidates_sha256": hashlib.sha256(
    (ROOT / "outputs/d3_tnap_20261019/freeze_tnap_v1/public/candidates.jsonl").read_bytes()).hexdigest(),
    "initialization_compound_count": 10, "initialization_hits": 0, "representations": {}}
for rep in ("bit", "count"):
    tools = NumericalTools(public, representation=rep)
    scores = tools.score_knn(state)
    base = 1 / (2 + 10)
    rep_result = {}
    for policy in ("knn_greedy", "knn_diverse", "uniform_random"):
        chosen = tools.select_batch(state, policy=policy, seed=seed, round_number=1)
        rows = []
        for rank, key in enumerate(chosen, 1):
            sims = sorted((DataStructs.TanimotoSimilarity(tools.fingerprints[key],
                      tools.fingerprints[r["compound_key"]]) for r in state["revealed"]), reverse=True)
            sumw = sum(v*v for v in sims[:5])
            predicted = (2 * base) / (2 + sumw)
            assert abs(scores[key] - predicted) < 1e-12
            rows.append({"rank": rank, "compound_key": key, "outcome": labels[key],
                         "score": scores[key], "sum_five_tanimoto_squared": sumw,
                         "max_similarity_to_initialization": sims[0]})
        rep_result[policy] = {"selected": rows, "hits_in_batch": sum(row["outcome"] for row in rows),
                              "mean_sumw": sum(row["sum_five_tanimoto_squared"] for row in rows)/10,
                              "mean_maxsim": sum(row["max_similarity_to_initialization"] for row in rows)/10,
                              "selection_sha256": hashlib.sha256(",".join(chosen).encode()).hexdigest()}
    results["representations"][rep] = rep_result

print(json.dumps(results, ensure_ascii=False, sort_keys=True))

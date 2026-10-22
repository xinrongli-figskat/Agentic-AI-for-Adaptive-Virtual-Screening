"""Read-only six-seed TNAP numerical replay; send to remote Python stdin."""

import hashlib
import json
import sys
from pathlib import Path

from rdkit import DataStructs

ROOT = Path("/driveA/xinrong/agentic-screening")
sys.path.insert(0, str(ROOT))
from campaign_v0.numerical_tools import NumericalTools

SEEDS = (5, 6, 15, 17, 18, 19)
PUBLIC_PATH = ROOT / "outputs/d3_tnap_20261019/freeze_tnap_v1/public/candidates.jsonl"
LABEL_PATH = ROOT / "outputs/d3_tnap_20261019/freeze_tnap_v1_private_labels/oracle_labels.jsonl"
public = [json.loads(line) for line in PUBLIC_PATH.read_text().splitlines()]
labels = {r["compound_key"]: r["outcome"] for r in
          (json.loads(line) for line in LABEL_PATH.read_text().splitlines())}
assert len(public) == len(labels) == 462 and sum(labels.values()) == 53

result = {"public_sha256": hashlib.sha256(PUBLIC_PATH.read_bytes()).hexdigest(),
          "private_labels_sha256": hashlib.sha256(LABEL_PATH.read_bytes()).hexdigest(),
          "seeds": list(SEEDS), "representations": {}}
for rep in ("bit", "count"):
    tools = NumericalTools(public, representation=rep)
    result["representations"][rep] = {}
    for seed in SEEDS:
        run = json.loads((ROOT / f"outputs/d4_tnap_glm_20261019/d4_glm_private_20261019/runs/llm_{rep}_seed{seed}/run.json").read_text())
        init = run["result"]["trajectory"][0]
        assert sum(r["outcome"] for r in init["observations"]) == 0
        assert all(labels[r["compound_key"]] == 0 for r in init["observations"])
        state = {"revealed": init["observations"], "next_batch_size": 10,
                 "remaining_budget": 40}
        scores = tools.score_knn(state)
        observed = [r["compound_key"] for r in state["revealed"]]
        by_policy = {}
        for policy in ("knn_greedy", "knn_diverse", "uniform_random"):
            selected = tools.select_batch(state, policy=policy, seed=seed, round_number=1)
            compound_rows = []
            for rank, key in enumerate(selected, 1):
                similarities = sorted((DataStructs.TanimotoSimilarity(tools.fingerprints[key],
                                    tools.fingerprints[ref]) for ref in observed), reverse=True)
                sumw = sum(x*x for x in similarities[:5])
                expected_score = (2/12) / (2+sumw)
                assert abs(scores[key] - expected_score) < 1e-12
                compound_rows.append({"rank": rank, "compound_key": key,
                                      "outcome": labels[key], "score": scores[key],
                                      "sumw": sumw, "maxsim_to_observed": similarities[0]})
            pairs = [DataStructs.TanimotoSimilarity(tools.fingerprints[a], tools.fingerprints[b])
                     for i, a in enumerate(selected) for b in selected[i+1:]]
            by_policy[policy] = {
                "selected": compound_rows,
                "batch_hits": sum(row["outcome"] for row in compound_rows),
                "mean_sumw": sum(row["sumw"] for row in compound_rows)/10,
                "mean_maxsim_to_observed": sum(row["maxsim_to_observed"] for row in compound_rows)/10,
                "mean_intrabatch_similarity": sum(pairs)/len(pairs),
                "selection_sha256": hashlib.sha256(",".join(selected).encode()).hexdigest(),
            }
        result["representations"][rep][str(seed)] = by_policy

print(json.dumps(result, ensure_ascii=False, sort_keys=True))

"""Verify remote numerical replay against frozen first-round trajectories."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
D3 = ROOT / "outputs/d3_tnap_20261019"
D4_PRIVATE = (ROOT / "outputs/d4_tnap_glm_20261019/remote_backup_private_20261019"
              / "d4_tnap_glm_20261019/d4_glm_private_20261019")
raw = json.loads((OUT / "selection_private/selection_zero6.json").read_text(encoding="utf-8-sig"))

public_path = D3 / "freeze_tnap_v1/public/candidates.jsonl"
label_path = D3 / "freeze_tnap_v1_private_labels/oracle_labels.jsonl"
assert hashlib.sha256(public_path.read_bytes()).hexdigest() == raw["public_sha256"]
assert hashlib.sha256(label_path.read_bytes()).hexdigest() == raw["private_labels_sha256"]

rows = []
for rep in ("bit", "count"):
    for seed in raw["seeds"]:
        choices = raw["representations"][rep][str(seed)]
        glm_path = D4_PRIVATE / f"runs/llm_{rep}_seed{seed}/run.json"
        glm = json.loads(glm_path.read_text())["result"]
        policy = glm["trajectory"][1]["decision"]["policy"]
        assert glm["trajectory"][1]["selection"] == [r["compound_key"] for r in choices[policy]["selected"]]
        forced_path = D3 / f"d3_6_runs_private_20261019/forced_random_coldstart_{rep}_seed{seed}.json"
        forced = json.loads(forced_path.read_text())["result"]
        assert forced["trajectory"][1]["selection"] == [r["compound_key"] for r in choices["uniform_random"]["selected"]]
        for name, item in choices.items():
            rows.append({"representation": rep, "seed": seed, "policy": name,
                         "selected_count": len(item["selected"]),
                         "hit_count_evaluation_only": item["batch_hits"],
                         "mean_sum_five_similarity_squared": item["mean_sumw"],
                         "mean_max_similarity_to_initialization": item["mean_maxsim_to_observed"],
                         "mean_within_batch_similarity": item["mean_intrabatch_similarity"],
                         "selection_sha256": item["selection_sha256"]})

with (OUT / "selection_zero6_summary.csv").open("w", newline="", encoding="utf-8") as stream:
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
print(json.dumps({"replayed_policy_selections": 12, "forced_random_selections": 12,
                  "selection_summaries": len(rows)}, indent=2))

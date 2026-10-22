"""D5 synthetic-only campaign and source-boundary preflight."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/driveA/xinrong/agentic-screening")
sys.path.insert(0, str(ROOT))
from oracle_boundary_v0.oracle_boundary import BatchOracle, read_jsonl
from outputs.d5_20261020.e_menu.expanded_tools import MENU, ExpandedTools
from outputs.d5_20261020.e_menu.run_extended import (
    BASE, DYRK3_MANIFEST_SHA, TNAP_RECEIPT_SHA, Controller, sha, validate_sources,
)


def public_rows(pool):
    if pool == "tnap":
        path = ROOT / "outputs/d3_tnap_20261019/freeze_tnap_v1/public/candidates.jsonl"
        expected = 462
    else:
        manifest = json.loads((ROOT / "data/curation_private/frozen_dyrk3_v1/manifest.json").read_text())
        path = Path(manifest["public_dir"]) / "candidates.jsonl"
        expected = 231
    rows = read_jsonl(path)
    assert len(rows) == expected
    assert all(set(row) == {"compound_key", "standardized_smiles"} for row in rows)
    return rows


def synthetic_labels(rows):
    return {row["compound_key"]: int(hashlib.sha256(
        f"d5synthetic|{row['compound_key']}".encode()).digest()[0] < 45) for row in rows}


def run_synthetic(rows, labels, policy, representation):
    oracle = BatchOracle(rows, labels, seed=0, total_budget=50,
                         initialization_queries=10, batch_size=10)
    tools = ExpandedTools(rows, representation)
    controller = Controller(f"fixed:{policy}", 0)
    selected = []
    first = oracle.proposed_initial_ids()
    oracle.query_batch_tool({"compound_keys": first})
    selected.extend(first)
    for _ in range(4):
        state = oracle.public_state()
        choice, _ = controller.choose(state)
        batch = tools.select(state, choice["policy"], 0, state["next_round"])
        oracle.query_batch_tool({"compound_keys": batch})
        selected.extend(batch)
    assert len(selected) == len(set(selected)) == 50
    assert oracle.public_state()["remaining_budget"] == 0
    return first


def main():
    lock = validate_sources()
    test = subprocess.run([sys.executable, "-B", "-m", "unittest",
                           "outputs.d5_20261020.e_menu.test_expanded"],
                          cwd=ROOT, capture_output=True, text=True)
    assert test.returncode == 0, test.stdout + test.stderr
    frozen = {"dyrk3_manifest_sha256": sha(ROOT / "data/curation_private/frozen_dyrk3_v1/manifest.json"),
              "tnap_receipt_sha256": sha(ROOT / "outputs/d3_tnap_20261019/freeze_tnap_v1/freeze_receipt.json")}
    assert frozen["dyrk3_manifest_sha256"] == DYRK3_MANIFEST_SHA
    assert frozen["tnap_receipt_sha256"] == TNAP_RECEIPT_SHA
    campaigns = []
    for pool in ("tnap", "dyrk3"):
        rows = public_rows(pool)
        labels = synthetic_labels(rows)
        initializations = []
        for representation in ("bit", "count"):
            for policy in MENU:
                first = run_synthetic(rows, labels, policy, representation)
                initializations.append(first)
                campaigns.append({"pool": pool, "representation": representation,
                                  "policy": policy, "queried_count": 50,
                                  "distinct_compounds": 50})
        assert all(first == initializations[0] for first in initializations)
    result = {"status": "pass", "uses_real_labels": False,
              "public_only_candidate_fields": True,
              "synthetic_full_campaigns": campaigns,
              "synthetic_campaign_count": len(campaigns),
              "shared_initialization": True,
              "frozen_hashes": frozen,
              "code_lock_sha256": sha(BASE / "e_menu_code_lock.json"),
              "menu_spec_sha256": lock["spec_sha256"]}
    path = BASE / "e_menu_synthetic_preflight.json"
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "synthetic_campaign_count": len(campaigns),
                      "uses_real_labels": False, "preflight_sha256": sha(path)}))


if __name__ == "__main__":
    main()

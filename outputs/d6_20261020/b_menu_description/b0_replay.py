"""D6-B0 deterministic replay of the D5 TNAP-bit GLM arm.

This script deliberately imports the frozen D5 runner.  It changes only the
private output root, so the request summary, model settings, oracle schedule,
and numerical selection code are the same as D5.  It never edits D5 files.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/driveA/xinrong/agentic-screening")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BASE = ROOT / "outputs/d6_20261020/b_menu_description"
PRIVATE = ROOT / "outputs/d6_20261020/b_menu_description_private"
EXPECTED = {
    "campaign_v0/llm_controller.py": "30c1c75da16636518d947b1eecb7207c922034ce1863adc0417f9fa676dde2b7",
    "campaign_v0/campaign_core.py": "3044fb6b5f61bb435eb50a04dd8dcd23ed89abd314c420799c9dc4079d40f0a1",
    "outputs/d3_tnap_20261019/freeze_tnap_v1/freeze_receipt.json": "f8801efbe28f73ddbcf9c5a2d493d862cbf124f311b6659e9224f2161b5bf662",
    "outputs/d3_tnap_20261019/freeze_tnap_v1/pool_manifest.json": "c4206075c51db7c9fc14a9ab910b87c91adb82f5fd468dba74edba244d27feb1",
    "data/curation_private/frozen_dyrk3_v1/manifest.json": "3866c7bfc99e92b8e0d6f92b98955d5e68a7ae202f609eac90d0e7a201f98235",
    "outputs/d5_20261020/e_menu_code_lock.json": "5cd4edae70c83519a75eb9e90068ad3444128cb0375239479c66d4f860625859",
    "deliveries_20261018/outputs/r3_ranked_numeric_private_20261018_v2/ranked_numeric_qualified_62.csv": "dfb3569217454cd73a6c60b69128988aa1f57dc9866b7949728954933add47b9",
    "data/source_dbs/chembl_37/extracted/chembl_37.db": "4be13df3b68e25dcd0bff44bf094033b5aebe98f415acdc8c1cdf380e0c15142",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_json(path: Path, value: object, private: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                         encoding="utf-8")
    temporary.replace(path)
    if private:
        os.chmod(path, 0o600)


def preconditions() -> dict[str, str]:
    observed = {relative: sha(ROOT / relative) for relative in EXPECTED}
    mismatches = {p: {"expected": EXPECTED[p], "observed": observed[p]}
                  for p in EXPECTED if observed[p] != EXPECTED[p]}
    if mismatches:
        save_json(BASE / "BLOCKED_precondition_hash_mismatch.json",
                  {"utc": utc(), "mismatches": mismatches})
        raise SystemExit("Tier C: prerequisite hash mismatch")
    return observed


def d5_sequences() -> dict[int, list[str]]:
    path = ROOT / "outputs/d5_20261020/a_mechanism/all_glm_policy_sequences.csv"
    result: dict[int, list[str]] = {}
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["representation"] == "bit" and int(row["seed"]) < 10:
                result[int(row["seed"])] = [row[f"r{i}_policy"] for i in range(1, 5)]
    assert sorted(result) == list(range(10))
    return result


def policy_sequence(run_path: Path) -> list[str]:
    saved = json.loads(run_path.read_text(encoding="utf-8"))
    return [step["decision"]["policy"] for step in saved["trajectory"]
            if step["stage"].startswith("feedback_round_")]


def copy_receipts(run_path: Path, seed: int) -> int:
    saved = json.loads(run_path.read_text(encoding="utf-8"))
    count = 0
    for step in saved["trajectory"]:
        call = step.get("glm_call")
        if call is None:
            continue
        round_label = step["stage"].rsplit("_", 1)[-1]
        save_json(PRIVATE / "llm_receipts" / f"seed{seed}_round{round_label}.json", call,
                  private=True)
        count += 1
    return count


def main() -> None:
    BASE.mkdir(parents=True, exist_ok=True)
    PRIVATE.mkdir(parents=True, exist_ok=True)
    observed = preconditions()
    # Import only after the legacy hashes have been checked.
    from campaign_v0.glm_api import OfficialGLMDecisionClient
    from outputs.d5_20261020.e_menu import run_extended as frozen_runner

    frozen_runner.validate_sources()
    frozen_runner.PRIVATE_OUT = PRIVATE / "runs_v0_replay"
    d5 = d5_sequences()
    replay: dict[int, list[str]] = {}
    receipt_count = 0
    for seed in range(10):
        # ``run_extended`` owns a ``runs/`` level below its configured root.
        # Reuse a completed seed after a path-only post-run failure so the
        # prescribed B-0 budget remains exactly 40 calls.
        path = (frozen_runner.PRIVATE_OUT / "runs" / "tnap" / "bit"
                / f"glm_extended_seed{seed}" / "run.json")
        if not path.exists():
            client = OfficialGLMDecisionClient(model_name="glm-5.3-flash")
            frozen_runner.run_one("tnap", "bit", seed, "glm_extended", client=client)
        replay[seed] = policy_sequence(path)
        assert len(replay[seed]) == 4, (seed, replay[seed])
        receipt_count += copy_receipts(path, seed)

    differences = [{"seed": seed, "d5": d5[seed], "replay": replay[seed]}
                   for seed in range(10) if d5[seed] != replay[seed]]
    result = {
        "task": "D6-B0", "post_exposure": True, "started_and_finished_utc": utc(),
        "precondition_hashes": observed, "model": "glm-5.3-flash",
        "request_settings": {"thinking": "enabled", "reasoning_effort": "low",
                             "do_sample": False, "max_tokens": 1024, "timeout_seconds": 120},
        "decision_points_expected": 40, "decision_receipts_saved_private": receipt_count,
        "sequences_compared": 10, "different_sequences": differences,
        "status": "pass" if not differences else ("rerun_required" if len(differences) == 1 else "blocked"),
    }
    save_json(BASE / "b0_replay_summary.json", result)
    if len(differences) >= 2:
        (BASE / "BLOCKED_nondeterminism.md").write_text(
            "# Tier B stop: B-0 nondeterminism\n\n"
            "The D5 and replay policy sequences differ for two or more seeds. "
            "See `b0_replay_summary.json`; B-1 and later B work must not start.\n", encoding="utf-8")
        raise SystemExit("Tier B: two or more policy sequences differ")
    if len(differences) == 1:
        raise SystemExit("B-0 requires an independently rerun seed before B-1")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()

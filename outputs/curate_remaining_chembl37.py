"""Resumable, CPU-only structural audit of remaining numeric-prescreen assays.

It reuses the existing assay auditor and qualification protocol. Private
provisional labels stay under the supplied output root; no campaign is run.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
from urllib.parse import quote

from assay_audit_v0 import audit_assay as audit
from curate_chembl37_batch import audit_one, sha, write_json


def selected_queue(prescreen: dict, already_done: set[str]) -> list[dict]:
    remaining = [row for row in prescreen["assays"]
                 if row["numeric_prescreen_pass"] and row["assay_id"] not in already_done]
    remaining.sort(key=lambda row: (-min(row["hit_support_ids"], row["nonhit_support_ids"]),
                                    -row["supported_ids"], row["assay_id"]))
    return remaining


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--database", type=Path, required=True)
    p.add_argument("--prescreen", type=Path, required=True)
    p.add_argument("--prior-run", action="append", type=Path, required=True)
    p.add_argument("--output-root", type=Path, required=True)
    p.add_argument("--max-assays", type=int, default=15)
    p.add_argument("--max-pairwise", type=int, default=1500)
    args = p.parse_args()
    if args.max_assays < 1 or args.max_pairwise < 250:
        raise ValueError("Invalid audit limit")
    prescreen_manifest = json.loads((args.prescreen / "manifest.json").read_text())
    db_hash = sha(args.database)
    if db_hash != prescreen_manifest["database_sha256"]:
        raise ValueError("Database differs from prescreen")
    prescreen_path = args.prescreen / "result.json"
    prescreen_hash = sha(prescreen_path)
    prescreen = json.loads(prescreen_path.read_text())
    already_done = set()
    prior_hashes = {}
    for prior in args.prior_run:
        prior_manifest = json.loads((prior / "manifest.json").read_text())
        prior_db = prior_manifest.get("database_sha256")
        prior_prescreen = prior_manifest.get("prescreen_result_sha256",
                                            prior_manifest.get("prescreen_sha256"))
        if prior_db != db_hash or prior_prescreen != prescreen_hash:
            raise ValueError(f"Prior run differs from this database/prescreen: {prior}")
        result_path = prior / "results.json"
        for row in json.loads(result_path.read_text()):
            already_done.add(row["assay_id"])
        prior_hashes[str(prior.resolve())] = sha(result_path)
    queue = selected_queue(prescreen, already_done)
    root = Path(__file__).parent
    config_path = root / "candidate_discovery_v0" / "criteria_v0.json"
    policy_path = root / "assay_audit_v0" / "audit_policy_v0.json"
    protocol_path = root / "curation_agent_v3" / "protocol.json"
    rules_path = root / "task1_v5_source_adjudication_rules_20261016.md"
    script_hash = sha(Path(__file__))
    run_id = hashlib.sha256((prescreen_hash + script_hash +
                             "|".join(sorted(already_done)) + str(args.max_pairwise)).encode()).hexdigest()[:16]
    run = args.output_root / ("remaining_curation_" + run_id)
    expected_manifest = {
        "schema": "chembl37_remaining_curation_v1",
        "database_sha256": db_hash,
        "prescreen_sha256": prescreen_hash,
        "script_sha256": script_hash,
        "criteria_sha256": sha(config_path),
        "audit_policy_sha256": sha(policy_path),
        "qualification_protocol_sha256": sha(protocol_path),
        "source_rules_sha256": sha(rules_path),
        "prior_result_hashes": prior_hashes,
        "prior_assay_count": len(already_done),
        "assay_queue": [row["assay_id"] for row in queue],
        "selection": "remaining numeric-prescreen assays sorted by minority-class support, total support, ID",
        "max_pairwise": args.max_pairwise,
        "provisional_labels_private": True,
        "campaign_ready": False,
    }
    if run.exists():
        if json.loads((run / "manifest.json").read_text()) != expected_manifest:
            raise ValueError("Existing run manifest differs; refusing to resume")
        progress = json.loads((run / "progress.json").read_text())
    else:
        run.mkdir(parents=True)
        write_json(run / "manifest.json", expected_manifest)
        progress = []
        write_json(run / "progress.json", progress)
    completed = {row["assay_id"] for row in progress}
    if completed != set(expected_manifest["assay_queue"][:len(progress)]):
        raise ValueError("Progress is not a prefix of frozen queue")
    uri = "file:" + quote(str(args.database.resolve()), safe="/") + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    newly_done = 0
    try:
        helper = audit.load_helper()
        for meta in queue[len(progress):]:
            if newly_done >= args.max_assays:
                break
            aid = meta["assay_id"]
            summary = audit_one(conn, meta, json.loads(config_path.read_text()),
                                json.loads(policy_path.read_text()),
                                json.loads(protocol_path.read_text()), helper,
                                run / aid, args.max_pairwise)
            progress.append({"assay_id": aid, "source_tier": meta["source_tier"],
                             "target_id": meta["target_id"],
                             "pool": summary["budget"]["provisional_pool_size"],
                             "hits": summary["budget"]["hit_support_count"],
                             "nonhits": summary["budget"]["nonhit_support_count"],
                             "qualification": summary["qualification"],
                             "campaign_ready": False})
            write_json(run / "progress.json", progress)
            newly_done += 1
            print(json.dumps({"assay_id": aid, "pool": progress[-1]["pool"],
                              "numerical_eligibility": summary["qualification"].get("numerical_eligibility"),
                              "completed": len(progress), "total": len(queue)}), flush=True)
    finally:
        conn.close()
    if len(progress) == len(queue):
        write_json(run / "results.json", progress)
    print(json.dumps({"status": "offline_curation_complete" if len(progress) == len(queue)
                      else "paused_at_assay_limit", "run_dir": str(run),
                      "newly_done": newly_done, "completed": len(progress),
                      "remaining": len(queue) - len(progress), "campaign_ready": False}))


if __name__ == "__main__":
    main()

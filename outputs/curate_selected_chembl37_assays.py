"""Run the existing private assay auditor on explicitly named prescreen assays.

This avoids repeating an entire source tier when one promising candidate needs
structural review. It does not publish labels or authorize a campaign.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
from urllib.parse import quote

from curate_chembl37_batch import audit_one, sha, write_json
from assay_audit_v0 import audit_assay as audit


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--database", type=Path, required=True)
    p.add_argument("--prescreen", type=Path, required=True)
    p.add_argument("--output-root", type=Path, required=True)
    p.add_argument("--assay-id", action="append", required=True)
    p.add_argument("--max-pairwise", type=int, default=1500)
    args = p.parse_args()
    if len(set(args.assay_id)) != len(args.assay_id):
        raise ValueError("Duplicate assay ID")
    manifest = json.loads((args.prescreen / "manifest.json").read_text())
    if manifest["database_sha256"] != sha(args.database):
        raise ValueError("Database differs from prescreen")
    prescreen = json.loads((args.prescreen / "result.json").read_text())
    choices = {row["assay_id"]: row for row in prescreen["assays"]}
    selected = []
    for aid in args.assay_id:
        if aid not in choices or not choices[aid]["numeric_prescreen_pass"]:
            raise ValueError(f"Not an eligible named prescreen candidate: {aid}")
        selected.append(choices[aid])
    root = Path(__file__).parent
    config_path = root / "candidate_discovery_v0" / "criteria_v0.json"
    policy_path = root / "assay_audit_v0" / "audit_policy_v0.json"
    protocol_path = root / "curation_agent_v3" / "protocol.json"
    rules_path = root / "task1_v5_source_adjudication_rules_20261016.md"
    digest = hashlib.sha256((sha(args.prescreen / "result.json") + sha(Path(__file__)) +
                             "|".join(args.assay_id)).encode()).hexdigest()[:16]
    run = args.output_root / ("selected_curation_" + digest)
    run.mkdir(parents=True, exist_ok=False)
    write_json(run / "manifest.json", {
        "schema": "chembl37_selected_curation_v1",
        "database_sha256": manifest["database_sha256"],
        "prescreen_sha256": sha(args.prescreen / "result.json"),
        "script_sha256": sha(Path(__file__)),
        "criteria_sha256": sha(config_path),
        "audit_policy_sha256": sha(policy_path),
        "qualification_protocol_sha256": sha(protocol_path),
        "source_rules_sha256": sha(rules_path),
        "selected_assays": args.assay_id,
        "provisional_labels_private": True,
        "campaign_ready": False,
    })
    uri = "file:" + quote(str(args.database.resolve()), safe="/") + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    results = []
    try:
        helper = audit.load_helper()
        for meta in selected:
            summary = audit_one(conn, meta, json.loads(config_path.read_text()),
                                json.loads(policy_path.read_text()),
                                json.loads(protocol_path.read_text()), helper,
                                run / meta["assay_id"], args.max_pairwise)
            results.append({"assay_id": meta["assay_id"], "source_tier": meta["source_tier"],
                            "pool": summary["budget"]["provisional_pool_size"],
                            "hits": summary["budget"]["hit_support_count"],
                            "nonhits": summary["budget"]["nonhit_support_count"],
                            "qualification": summary["qualification"],
                            "campaign_ready": False})
            write_json(run / "progress.json", results)
            print(json.dumps(results[-1]), flush=True)
    finally:
        conn.close()
    write_json(run / "results.json", results)
    print(json.dumps({"status": "offline_curation_complete", "run_dir": str(run),
                      "assays_audited": len(results), "campaign_ready": False}))


if __name__ == "__main__":
    main()

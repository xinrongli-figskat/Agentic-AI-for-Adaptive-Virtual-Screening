"""Offline structural audit of high-priority ChEMBL_37 prescreen candidates.

Everything written by this script is private curation evidence, including
provisional outcomes. Nothing here is a campaign pool or benchmark freeze.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3
from urllib.parse import quote

from assay_audit_v0 import audit_assay as audit
from curation_agent_v3.engine import qualification


ROW_SQL = """
SELECT act.activity_id, act.molregno, mol.chembl_id AS molecule_chembl_id,
       structures.canonical_smiles, act.standard_type, act.standard_relation,
       act.standard_value, act.standard_units, act.potential_duplicate,
       act.data_validity_comment, act.activity_comment,
       docs.chembl_id AS document_chembl_id
FROM activities AS act
LEFT JOIN molecule_dictionary AS mol ON mol.molregno = act.molregno
LEFT JOIN compound_structures AS structures ON structures.molregno = act.molregno
LEFT JOIN docs ON docs.doc_id = act.doc_id
WHERE act.assay_id = ? AND act.standard_type = 'IC50'
ORDER BY act.activity_id
"""


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(16 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, value: object) -> str:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return sha(path)


def choose(result: dict, per_tier: int) -> list[dict]:
    priorities = ("research_article", "patent_via_bindingdb", "direct_patent", "other_or_unknown")
    picked = []
    for tier in priorities:
        rows = [r for r in result["assays"] if r["source_tier"] == tier and r["numeric_prescreen_pass"]]
        rows.sort(key=lambda r: (-min(r["hit_support_ids"], r["nonhit_support_ids"]),
                                 -r["supported_ids"], r["assay_id"]))
        picked.extend(rows[:per_tier])
    return picked


def audit_one(connection: sqlite3.Connection, meta: dict, config: dict, base_policy: dict,
              protocol: dict, helper: object, output: Path, max_pairwise: int) -> dict:
    assay_id = meta["assay_id"]
    assay_key = connection.execute("SELECT assay_id FROM assays WHERE chembl_id=?", (assay_id,)).fetchone()
    if assay_key is None:
        raise ValueError(f"Assay vanished from database: {assay_id}")
    rows = [dict(row) for row in connection.execute(ROW_SQL, (assay_key[0],))]
    if len(rows) != meta["raw_ic50_records"]:
        raise ValueError(f"Assay row count changed: {assay_id}")
    for row in rows:
        row["assay_chembl_id"] = assay_id
        row["target_chembl_id"] = meta["target_id"]
        row["assay_type"] = "B"
    policy = json.loads(json.dumps(base_policy))
    policy.update(target_chembl_id=meta["target_id"], assay_chembl_id=assay_id,
                  budget_proposals=[{"name": "prospective_draft", "query_budget": protocol["query_budget"],
                                     "initialization_queries": protocol["initialization_queries"],
                                     "feedback_batch_size": protocol["feedback_batch_size"]}])
    policy["diversity_policy"]["maximum_compounds_for_exact_pairwise_analysis"] = max_pairwise
    records, id_audit, compounds, sensitivity = audit.audit_records(rows, config, policy, helper)
    usable = sum(c["usable_for_prototype_review"] for c in compounds)
    diversity = audit.diversity(compounds, policy) if usable <= max_pairwise else None
    budget = audit.budget_analysis(compounds, policy["budget_proposals"])
    summary = {"assay_id": assay_id, "target_id": meta["target_id"], "source_tier": meta["source_tier"],
               "record_count": len(records), "standardized_identity_count": len(compounds),
               "source_ids_quarantined": sum(r["structure_status"] != "ok" for r in id_audit),
               "class_states_all_standardized_identities": dict(Counter(c["provisional_state"] for c in compounds)),
               "budget": budget, "threshold_sensitivity": sensitivity,
               "diversity": ({k: v for k, v in diversity.items() if k != "clusters"} if diversity else None),
               "exact_pairwise_limit_exceeded": usable > max_pairwise,
               "source_endpoint_resolved": False, "campaign_ready": False}
    if diversity is None:
        summary["qualification"] = {"status": "requires_declared_large_pool_diversity_method",
                                     "scientific_review_complete": False, "campaign_ready": False}
    else:
        q_input = {"complete": True, "target_type": "SINGLE PROTEIN", "assay_type": "B",
                   "confidence_score": int(meta["confidence_score"]), "budget": budget,
                   "diversity": summary["diversity"]}
        summary["qualification"] = qualification(q_input, protocol)
    output.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for filename, payload in (("source_records.json", rows), ("record_audit.json", records),
                              ("source_id_audit.json", id_audit), ("compounds_private.json", compounds),
                              ("summary.json", summary), ("policy_snapshot.json", policy)):
        hashes[filename] = write_json(output / filename, payload)
    if diversity is not None:
        hashes["diversity.json"] = write_json(output / "diversity.json", diversity)
    hashes["file_hashes.json"] = write_json(output / "file_hashes.json", hashes)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--prescreen", type=Path, required=True, help="Prescreen output directory")
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--per-tier", type=int, default=3)
    parser.add_argument("--max-pairwise", type=int, default=1500)
    args = parser.parse_args()
    if not 1 <= args.per_tier <= 20 or args.max_pairwise < 250:
        raise ValueError("Invalid audit selection limits")
    prescreen_manifest = json.loads((args.prescreen / "manifest.json").read_text())
    if prescreen_manifest.get("database_sha256") != sha(args.database):
        raise ValueError("Database differs from numeric prescreen")
    prescreen = json.loads((args.prescreen / "result.json").read_text())
    if prescreen.get("campaign_ready") is not False:
        raise ValueError("Unexpected prescreen state")
    selected = choose(prescreen, args.per_tier)
    root = Path(__file__).parent
    config_path = root / "candidate_discovery_v0" / "criteria_v0.json"
    policy_path = root / "assay_audit_v0" / "audit_policy_v0.json"
    protocol_path = root / "curation_agent_v3" / "protocol.json"
    source_rules_path = root / "task1_v5_source_adjudication_rules_20261016.md"
    config = json.loads(config_path.read_text())
    policy = json.loads(policy_path.read_text())
    protocol = json.loads(protocol_path.read_text())
    source_rules_hash = sha(source_rules_path)
    helper = audit.load_helper()
    run_id = hashlib.sha256((sha(args.prescreen / "result.json") + sha(Path(__file__)) +
                             str(args.per_tier) + str(args.max_pairwise)).encode()).hexdigest()[:16]
    run = args.output_root / ("chembl37_batch_curation_" + run_id)
    run.mkdir(parents=True, exist_ok=False)
    manifest = {"schema": "chembl37_batch_curation_v1", "prescreen_result_sha256": sha(args.prescreen / "result.json"),
                "database_sha256": prescreen_manifest["database_sha256"], "script_sha256": sha(Path(__file__)),
                "criteria_sha256": sha(config_path), "audit_policy_sha256": sha(policy_path),
                "qualification_protocol_sha256": sha(protocol_path), "selected_assays": [r["assay_id"] for r in selected],
                "source_adjudication_rules_sha256": source_rules_hash,
                "selection": "top minimum-class support within each source tier, then total support, then ID",
                "per_tier": args.per_tier, "max_pairwise": args.max_pairwise,
                "provisional_labels_private": True, "campaign_ready": False}
    write_json(run / "manifest.json", manifest)
    uri = "file:" + quote(str(args.database.resolve()), safe="/") + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    results = []
    try:
        for meta in selected:
            summary = audit_one(connection, meta, config, policy, protocol, helper,
                                run / meta["assay_id"], args.max_pairwise)
            results.append({"assay_id": meta["assay_id"], "source_tier": meta["source_tier"],
                            "pool": summary["budget"]["provisional_pool_size"],
                            "hits": summary["budget"]["hit_support_count"],
                            "nonhits": summary["budget"]["nonhit_support_count"],
                            "qualification": summary["qualification"], "campaign_ready": False})
            write_json(run / "progress.json", results)
            print(json.dumps(results[-1], ensure_ascii=False), flush=True)
    finally:
        connection.close()
    write_json(run / "results.json", results)
    print(json.dumps({"status": "offline_curation_complete", "run_dir": str(run),
                      "assays_audited": len(results), "campaign_ready": False}))


if __name__ == "__main__":
    main()

"""Offline numerical/structure curation of the archived S1PR1 assay window."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import zipfile

from assay_audit_v0 import audit_assay as audit


ASSAY_ID = "CHEMBL5734042"
TARGET_ID = "CHEMBL4333"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--expected-archive-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    archive_bytes = args.archive.read_bytes()
    if sha256(archive_bytes) != args.expected_archive_sha256.lower():
        raise ValueError("Archived run hash mismatch")
    with zipfile.ZipFile(args.archive) as source:
        window_bytes = source.read("run/evidence/E0174_thin_target_window.json")
        criteria_bytes = source.read("run/source_snapshot/vendor/discovery_criteria.json")
    window = json.loads(window_bytes)
    criteria = json.loads(criteria_bytes)
    if window["target_id"] != TARGET_ID or not window["complete"] or len(window["records"]) != window["total"]:
        raise ValueError("Archived target window is incomplete or wrong target")
    rows = [record for record in window["records"] if record["assay_chembl_id"] == ASSAY_ID]
    if len(rows) != 295 or any(record["target_chembl_id"] != TARGET_ID or record["standard_type"] != "IC50"
                               for record in rows):
        raise ValueError("Archived assay scope mismatch")
    policy = json.loads((Path(__file__).resolve().parent / "assay_audit_v0" / "audit_policy_v0.json").read_bytes())
    policy["target_chembl_id"] = TARGET_ID
    policy["assay_chembl_id"] = ASSAY_ID
    policy["hit_threshold_nM"] = "1000"
    policy["budget_proposals"] = [{"name": "review_only_50_query_draft", "query_budget": 50,
                                    "initialization_queries": 10, "feedback_batch_size": 10}]
    helper = audit.load_helper()
    record_audit, id_audit, compounds, sensitivity = audit.audit_records(rows, criteria, policy, helper)
    diversity = audit.diversity(compounds, policy)
    budget = audit.budget_analysis(compounds, policy["budget_proposals"])
    summary = {"archive_sha256": sha256(archive_bytes), "target_window_sha256": sha256(window_bytes),
               "discovery_criteria_sha256": sha256(criteria_bytes),
               "assay_id": ASSAY_ID, "target_id": TARGET_ID,
               "source_record_count": len(rows), "source_molecule_ids": len({r["molecule_chembl_id"] for r in rows}),
               "standardized_identity_count": len(compounds),
               "provisional_states": dict(Counter(c["provisional_state"] for c in compounds)),
               "quarantined_source_ids": sum(item["structure_status"] != "ok" for item in id_audit),
               "budget": budget, "diversity": {k: v for k, v in diversity.items() if k != "clusters"},
               "threshold_sensitivity": sensitivity,
               "source_endpoint_review_status": "unresolved_while_numeric_curation_runs",
               "campaign_ready": False,
               "limitations": ["Offline curation of the v4 archived target window; no fresh ChEMBL fetch.",
                               "Provisional support classes are not frozen campaign labels.",
                               "Patent AA assay method and receptor construct are not established by this curation."]}
    report = {"schema": "s1pr1_archived_assay_offline_curation_v1", "summary": summary,
              "record_audit": record_audit, "source_id_audit": id_audit,
              "compounds": compounds, "clusters": diversity["clusters"], "policy": policy}
    data = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        if args.output.read_bytes() != data:
            raise FileExistsError("Existing curation differs; do not overwrite")
    else:
        with args.output.open("xb") as handle:
            handle.write(data)
    print(json.dumps({"status": "offline_curated_not_campaign_ready",
                      "provisional_states": summary["provisional_states"],
                      "budget": budget, "largest_cluster_fraction": summary["diversity"]["largest_cluster_fraction"],
                      "report_sha256": sha256(data), "output": str(args.output)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

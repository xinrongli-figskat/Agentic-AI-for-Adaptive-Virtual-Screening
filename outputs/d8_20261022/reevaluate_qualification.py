from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RANKED = ROOT / "outputs/r3_ranked_numeric_private_20261018_v2/ranked_numeric_qualified_62.csv"
METRICS = ROOT / "outputs/b2_candidate_metrics_private_20261017/candidate_metrics.csv"
GATES = ROOT / "outputs/d7_20261021/d_identity_gate_v2/revision_v3/gate_decisions_62.csv"


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    ranked = read_csv(RANKED)
    metrics = {row["assay_id"]: row for row in read_csv(METRICS)}
    gates = {row["assay_id"]: row for row in read_csv(GATES)}
    if len(ranked) != 62 or len(gates) != 62 or set(r["assay_id"] for r in ranked) != set(gates) or not set(g["assay_id"] for g in ranked) <= set(metrics):
        raise SystemExit("Input mismatch: expected the same 62 assay IDs in both source tables")
    rows = []
    for m in ranked:
        m = {**metrics[m["assay_id"]], **m}
        g = gates[m["assay_id"]]
        assay = m["assay_id"]
        credential = g["identity_credential"]
        if assay == "CHEMBL1738510":
            relaxed = "existing_source_limited_evaluation_set"
            changed = "endpoint/source-detail certainty and measurement-effort association are reported as limitations"
        elif credential == "pass_t1":
            relaxed = "candidate_for_limited_source_review_not_yet_admitted"
            changed = "endpoint/source-detail certainty and measurement-effort association may be reported as limitations; identity credential retained"
        else:
            relaxed = "not_admitted_identity_evidence_unresolved"
            changed = "no relaxation applied; compound identity evidence remains unresolved"
        rows.append({
            "assay_id": assay,
            "target_id": m["target_id"],
            "target_name": m["target_name"],
            "strict_numerical_status": m.get("historical_numeric_status", "pass_numeric_by_R3_62_selection"),
            "strict_identity_credential": credential,
            "strict_source_review_complete": g["source_review_complete"],
            "strict_campaign_ready": g["campaign_ready"],
            "relaxed_status": relaxed,
            "relaxation_applied": changed,
            "measured_nonhit_support": int(m["measured_nonhit_support"]),
            "hit_support": int(m["K"]),
            "usable_compounds": int(m["N"]),
            "scaffold_buckets_including_acyclic": int(m["scaffold_bucket_count_including_acyclic"]),
            "largest_cluster_fraction": float(m["largest_cluster_fraction"]),
            "initialization_single_class_probability": float(m["P_single_class10"]),
            "query_fraction": float(m["query_fraction"]),
            "nonhits_times_scaffold_buckets": int(m["measured_nonhit_support"]) * int(m["scaffold_bucket_count_including_acyclic"]),
            "source_tier": g["source_tier"],
            "post_exposure": True,
            "campaign_run_authorized": False,
        })
    rows.sort(key=lambda r: (-r["nonhits_times_scaffold_buckets"], r["assay_id"]))
    columns = list(rows[0])
    csv_path = OUT / "relaxed_admission_62.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "status": "completed_re_evaluation_without_new_admission",
        "post_exposure": True,
        "input_rows": 62,
        "strict_numerical_pass": sum(r["strict_numerical_status"] == "pass_numeric" for r in rows),
        "strict_campaign_ready_in_saved_gate_table": sum(r["strict_campaign_ready"].lower() == "true" for r in rows),
        "existing_source_limited_evaluation_sets": sum(r["relaxed_status"] == "existing_source_limited_evaluation_set" for r in rows),
        "additional_limited_review_candidates_not_admitted": sum(r["relaxed_status"] == "candidate_for_limited_source_review_not_yet_admitted" for r in rows),
        "identity_evidence_unresolved": sum(r["relaxed_status"] == "not_admitted_identity_evidence_unresolved" for r in rows),
        "currently_usable_under_relaxed_prototype_interpretation": 1,
        "top_five_ranked_by_measured_nonhits_times_scaffold_buckets": [
            {k: r[k] for k in ("assay_id", "target_name", "measured_nonhit_support",
                               "scaffold_buckets_including_acyclic", "nonhits_times_scaffold_buckets",
                               "relaxed_status")}
            for r in rows[:5]
        ],
        "ranking_definition": "measured_nonhit_support × scaffold_buckets_including_acyclic; descending; assay_id ascending for ties",
        "limitations": [
            "The two additional source-tier-1 rows are candidates for limited review only; saved records do not establish them as usable evaluation sets.",
            "Relaxing documentation completeness does not resolve compound-identity mismatches or establish direct binding.",
            "No labels, pools, or campaign files were changed and no new evaluation run was started."
        ],
        "csv": str(csv_path.relative_to(ROOT)).replace("\\", "/"),
    }
    (OUT / "RELAXED_ADMISSION_62_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

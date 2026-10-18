"""Combine complete ChEMBL_37 assay-curation runs into an auditable funnel.

Aggregate data are private because they include provisional hit/nonhit counts.
No source or endpoint is automatically approved by this script.
"""

import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path

from curate_chembl37_batch import sha, write_json


def build(prescreen: dict, runs: list[list[dict]]) -> tuple[dict, list[dict]]:
    expected = {x["assay_id"] for x in prescreen["assays"] if x["numeric_prescreen_pass"]}
    rows = [row for run in runs for row in run]
    ids = [row["assay_id"] for row in rows]
    if len(ids) != len(set(ids)) or set(ids) != expected:
        raise ValueError("Curated assays are duplicated or do not cover the full numeric-prescreen set")
    meta = {row["assay_id"]: row for row in prescreen["assays"]}
    source = defaultdict(Counter)
    overall = Counter()
    failures = Counter()
    table = []
    for row in rows:
        if row.get("campaign_ready") is not False:
            raise ValueError("Unexpected campaign-ready flag")
        q = row["qualification"]
        value = q.get("numerical_eligibility")
        status = "pass_numeric" if value is True else "fail_numeric" if value is False else "pending_large_pool_diversity"
        overall[status] += 1
        source[row["source_tier"]][status] += 1
        failures.update(q.get("failed_checks", []))
        prior = meta[row["assay_id"]]
        table.append({
            "assay_id": row["assay_id"],
            "target_id": prior["target_id"],
            "target_name": prior["target_name"],
            "document_id": prior["document_id"],
            "doc_type": prior["doc_type"],
            "patent_id": prior.get("patent_id") or "",
            "source_tier_metadata_only": row["source_tier"],
            "curated_pool": row["pool"],
            "hit_support": row["hits"],
            "nonhit_support": row["nonhits"],
            "numerical_status": status,
            "qualification_tier": q.get("tier", q.get("status", "")),
            "failed_checks": ";".join(q.get("failed_checks", [])),
            "source_endpoint_resolved": False,
            "campaign_ready": False,
        })
    table.sort(key=lambda row: (row["numerical_status"] != "pass_numeric",
                                -row["curated_pool"], row["assay_id"]))
    summary = {
        "prescreen_numeric_candidate_assays": len(expected),
        "curated_assays": len(rows),
        "distinct_targets_in_numeric_candidates": len({row["target_id"] for row in table}),
        "numeric_outcomes": dict(overall),
        "by_source_tier_metadata_only": {key: dict(value) for key, value in sorted(source.items())},
        "failed_check_counts": dict(failures),
        "source_endpoint_approved_in_numeric_pipeline": 0,
        "campaign_ready_count": 0,
        "interpretation": "Numeric/structural curation only. Source approvals are outside this pipeline; source tiers are metadata, not primary-source approval.",
    }
    return summary, table


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prescreen", required=True, type=Path)
    p.add_argument("--curation-run", action="append", required=True, type=Path)
    p.add_argument("--output-dir", required=True, type=Path)
    args = p.parse_args()
    prescreen_path = args.prescreen / "result.json"
    prescreen = json.loads(prescreen_path.read_text())
    runs = []
    input_hashes = {str(prescreen_path): sha(prescreen_path)}
    for run in args.curation_run:
        path = run / "results.json"
        input_hashes[str(path)] = sha(path)
        runs.append(json.loads(path.read_text()))
    summary, table = build(prescreen, runs)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    summary["input_sha256"] = input_hashes
    summary["campaign_ready"] = False
    write_json(args.output_dir / "funnel.json", summary)
    with (args.output_dir / "candidate_table_private.csv").open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=list(table[0]))
        writer.writeheader()
        writer.writerows(table)
    write_json(args.output_dir / "receipt.json", {
        "funnel_sha256": sha(args.output_dir / "funnel.json"),
        "candidate_table_sha256": sha(args.output_dir / "candidate_table_private.csv"),
        "campaign_ready": False,
    })
    print(json.dumps({k: v for k, v in summary.items() if k != "input_sha256"}, indent=2))


if __name__ == "__main__":
    main()

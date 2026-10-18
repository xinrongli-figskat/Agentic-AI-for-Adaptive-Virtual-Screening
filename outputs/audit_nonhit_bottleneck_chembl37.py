"""Audit nonhit coverage in the archived ChEMBL 37 numeric prescreen.

This is a read-only reanalysis of the original SQLite-derived result.json. It
does not standardize structures, approve sources, create decoys, or make labels
available to a campaign.
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


TIERS = ("research_article", "patent_via_bindingdb", "direct_patent", "other_or_unknown")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit(prescreen_dir: Path) -> tuple[dict, list[dict]]:
    result_path = prescreen_dir / "result.json"
    manifest_path = prescreen_dir / "manifest.json"
    result_sha = sha256(result_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if result_sha != "f7ad0d2e45f0890f4833fafc99c1db2733bc70231875d51ac42f597052c218a5":
        raise ValueError("Prescreen result differs from the archived ChEMBL 37 run")
    if manifest.get("database_sha256") != "4be13df3b68e25dcd0bff44bf094033b5aebe98f415acdc8c1cdf380e0c15142":
        raise ValueError("Unexpected ChEMBL 37 database provenance")
    criteria = manifest["criteria"]
    if (criteria["minimum_source_molecules"], criteria["minimum_hits"],
            criteria["minimum_nonhits"], criteria["threshold_nM"]) != (250, 30, 100, "1000"):
        raise ValueError("Prescreen criteria changed")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assays = result["assays"]
    if len(assays) != 512 or len({a["assay_id"] for a in assays}) != len(assays):
        raise ValueError("Metadata-eligible assay inventory is incomplete or duplicated")
    if sum(bool(a["numeric_prescreen_pass"]) for a in assays) != 81:
        raise ValueError("Archived prescreen pass count changed")

    hit_floor, nonhit_floor, pool_floor = 30, 100, 250
    broad = [a for a in assays if a["hit_support_ids"] >= hit_floor
             and a["nonhit_support_ids"] < nonhit_floor]
    nonhit_only = [a for a in broad if a["supported_ids"] >= pool_floor]
    if any(a["numeric_prescreen_pass"] for a in nonhit_only):
        raise ValueError("A nonhit-deficient assay was marked as passing")
    rows = [{key: a[key] for key in (
        "assay_id", "target_id", "source_tier", "raw_ic50_records",
        "hit_support_ids", "nonhit_support_ids", "supported_ids",
        "conflict_ids", "unknown_only_ids")}
        for a in sorted(nonhit_only, key=lambda a: a["assay_id"])]
    by_tier = Counter(a["source_tier"] for a in nonhit_only)
    summary = {
        "schema": "chembl37_nonhit_bottleneck_r1_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "input": str(result_path.resolve()),
        "input_sha256": result_sha,
        "input_manifest_sha256": sha256(manifest_path),
        "database_sha256_from_manifest": manifest["database_sha256"],
        "original_sql_sha256_from_manifest": manifest["sql_sha256"],
        "original_enumerator_sha256_from_manifest": manifest["script_sha256"],
        "source_rules": "Reanalysis of the complete saved 512-assay result; support states were computed from the same SQLite by the archived enumerator, including censored relations, duplicate, validity and structure-string checks.",
        "criteria": {"raw_ic50_records_min": 250, "assay_type": "B",
                     "target_type": "SINGLE PROTEIN", "mapping_confidence_min": 9,
                     "source_hit_support_min": hit_floor,
                     "source_nonhit_support_min": nonhit_floor,
                     "source_supported_total_min": pool_floor},
        "metadata_eligible_assays": len(assays),
        "numeric_prescreen_pass_assays": 81,
        "hit_ge_30_nonhit_lt_100_assays": len(broad),
        "hit_ge_30_nonhit_lt_100_but_total_lt_250_assays": len(broad) - len(nonhit_only),
        "nonhit_only_numeric_gate_assays": len(nonhit_only),
        "nonhit_only_by_source_tier": {tier: by_tier[tier] for tier in TIERS},
        "conditional_if_nonhits_reached_100": "All listed assays already have >=250 supported source IDs and >=30 hit-support IDs, so >=100 nonhit-support IDs would pass these three source-ID count gates. This does not establish structure, diversity, endpoint, source or campaign eligibility.",
        "campaign_ready": False,
        "decoys_generated": False,
    }
    return summary, rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prescreen-dir", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    summary, rows = audit(args.prescreen_dir)
    code_sha = sha256(Path(__file__))
    run_id = hashlib.sha256((summary["input_sha256"] + code_sha).encode()).hexdigest()[:16]
    folder = args.output_root / ("nonhit_bottleneck_r1_" + run_id)
    folder.mkdir(parents=True, exist_ok=False)
    summary["analysis_code_sha256"] = code_sha
    (folder / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (folder / "assays_private.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (folder / "file_hashes.json").write_text(json.dumps({
        name: sha256(folder / name) for name in ("summary.json", "assays_private.csv")
    }, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output_dir": str(folder), "metadata_eligible": summary["metadata_eligible_assays"],
                      "nonhit_only_numeric_gate": len(rows),
                      "by_source_tier": summary["nonhit_only_by_source_tier"],
                      "campaign_ready": False}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

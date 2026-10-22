"""Read-only TNAP source/curation audit; never builds a campaign pool."""

import csv
import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path

ROOT = Path("/driveA/xinrong/agentic-screening")
OUT = ROOT / "outputs/d3_tnap_20261019"
PRIVATE = OUT / "d3_1_private_20261019"
DB = ROOT / "data/source_dbs/chembl_37/extracted/chembl_37.db"
CURATION = ROOT / "data/curation_private/chembl37_batch_curations/chembl37_batch_curation_d1d3b87ef2b3ea4e/CHEMBL1738510"
SOURCE = ROOT / "data/curation_private/source_audits/source_sample_CHEMBL1738510_cccc2760ddd56b29/pubchem_aid1056"
ALIGN = ROOT / "data/curation_private/source_audits/source_sample_CHEMBL1738510_cccc2760ddd56b29/full_alignment_v1"
EXPECTED_DB = "4be13df3b68e25dcd0bff44bf094033b5aebe98f415acdc8c1cdf380e0c15142"
LOCKED_SPEC = "9fd66ccb5606276349623c10fa60a5fe7bad3082293f04ccad349c2621a6f552"


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def main():
    if sha(OUT / "d3_coldstart_decision_spec.md") != LOCKED_SPEC:
        raise ValueError("D3-0 spec changed after lock")
    db_hash = sha(DB)
    if db_hash != EXPECTED_DB:
        raise ValueError("Official ChEMBL 37 SQLite hash differs: hard stop")
    receipt = json.loads((SOURCE / "full_receipt.json").read_text())
    if receipt["aid"] != 1056 or sha(SOURCE / "full.json") != receipt["sha256"]:
        raise ValueError("PubChem source receipt mismatch: hard stop")
    source = json.loads((SOURCE / "full.json").read_text())["PC_AssaySubmit"]
    names = {str(x["tid"]): x["name"] for x in source["assay"]["descr"]["results"]}
    source_rows = source["data"]
    tids = Counter(int(item["tid"]) for row in source_rows for item in row["data"])
    row_tids = [set(int(item["tid"]) for item in row["data"]) for row in source_rows]

    connection = sqlite3.connect("file:" + str(DB) + "?mode=ro", uri=True)
    connection.execute("pragma query_only=on")
    assay = connection.execute("""select a.assay_id,a.assay_type,a.confidence_score,a.tid,
                               t.chembl_id,t.target_type,t.organism
                               from assays a join target_dictionary t on t.tid=a.tid
                               where a.chembl_id='CHEMBL1738510'""").fetchone()
    if assay is None:
        raise ValueError("TNAP assay absent")
    accessions = [row[0] for row in connection.execute("""select c.accession from target_components tc
                    join component_sequences c on c.component_id=tc.component_id where tc.tid=?""", (assay[3],))]
    activities = connection.execute("""select activity_id,standard_type,standard_units,
                     standard_relation,standard_value,potential_duplicate,src_id
                     from activities where assay_id=? order by activity_id""", (assay[0],)).fetchall()
    connection.close()
    aligned = json.loads((ALIGN / "record_alignment.json").read_text())
    alignment_status = Counter(row["alignment_status"] for row in aligned)
    activity_ids = [int(row[0]) for row in activities]
    expected_ids = [int(row["activity_id"]) for row in aligned]
    if activity_ids != expected_ids or len(activities) != len(source_rows) or len(activities) != 485:
        raise ValueError("485-row source alignment or SQLite row count mismatch")
    homogeneity = {
        "assay_id": "CHEMBL1738510", "database_sha256": db_hash,
        "pubchem_full_sha256": receipt["sha256"],
        "source_row_count": len(source_rows), "sqlite_activity_count": len(activities),
        "readout_tid_1_name": names.get("1"), "readout_tid_2_name": names.get("2"),
        "readout_tid_counts": {str(k): tids[k] for k in sorted(tids)},
        "rows_with_both_tid_1_2": sum({1, 2}.issubset(s) for s in row_tids),
        "rows_with_only_tid_1_2": sum(s == {1, 2} for s in row_tids),
        "other_tids": sorted(set(tids) - {1, 2}),
        "alignment_status_counts": dict(alignment_status),
        "sqlite_standard_types": dict(Counter(str(row[1]) for row in activities)),
        "sqlite_standard_units": dict(Counter(str(row[2]) for row in activities)),
        "sqlite_potential_duplicate": dict(Counter(str(row[5]) for row in activities)),
        "sqlite_source_ids": dict(Counter(str(row[6]) for row in activities)),
        "assay_type": assay[1], "confidence_score": assay[2], "target_tid": assay[3],
        "target_chembl_id": assay[4], "target_type": assay[5],
        "target_organism": assay[6], "uniprot_accessions": accessions,
    }
    checks = {
        "485_source_to_sqlite_aligned": len(aligned) == 485 and alignment_status == {"matched": 485},
        "all_rows_use_tid_1_2": len(source_rows) == 485 and sum({1, 2}.issubset(s) for s in row_tids) == 485,
        "no_other_tid_present": all(s == {1, 2} for s in row_tids),
        "readout_names": names.get("1") == "IC50_Mean_Qualifier" and names.get("2") == "IC50_Mean",
        "all_ic50_nM": all(row[1:3] == ("IC50", "nM") for row in activities),
        "assay_B_confidence_9": assay[1:3] == ("B", 9),
        "single_human_protein": assay[5:7] == ("SINGLE PROTEIN", "Homo sapiens") and accessions == ["P05186"],
    }
    homogeneity["checks"] = checks
    homogeneity["passed"] = all(checks.values())
    OUT.mkdir(parents=True, exist_ok=True)
    PRIVATE.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "tnap_homogeneity_assertion.json", homogeneity)

    # Assign each raw activity exactly once. One representative per standardized identity;
    # extra records are duplicate/identity-collapse rows, then three ineligible identities.
    record_audit = json.loads((CURATION / "record_audit.json").read_text())
    compounds = json.loads((CURATION / "compounds_private.json").read_text())
    if sorted(int(r["activity_id"]) for r in record_audit) != activity_ids:
        raise ValueError("Curation record audit does not cover all SQLite activities")
    assignments = []
    for compound in compounds:
        ids = sorted(int(x) for x in compound["activity_ids"])
        if not ids:
            raise ValueError("Empty standardized identity")
        for activity_id in ids[1:]:
            assignments.append((activity_id, "duplicate_record_or_identity_collapse", compound["compound_key"], "additional raw activity for one standardized identity"))
        if not compound["usable_for_prototype_review"]:
            reason = compound["decision_reason"]
            if reason == "censored_bounds_or_exact_values_disagree_needs_review":
                category = "qualifier_censor_unknown"
            elif reason == "eligible_measurements_cross_hit_threshold":
                category = "conflict_cross_threshold"
            elif compound["structure_status"] != "ok":
                category = "structure_standardization_failure"
            else:
                category = "other_named_" + reason
            assignments.append((ids[0], category, compound["compound_key"], reason))
    assigned_ids = [row[0] for row in assignments]
    if len(assigned_ids) != len(set(assigned_ids)) or set(assigned_ids) - set(activity_ids):
        raise ValueError("Overlapping or unknown attrition assignment")
    retained = set(activity_ids) - set(assigned_ids)
    if len(compounds) != 465 or len(retained) != 462 or len(assignments) != 23:
        raise ValueError("485-to-462 reconciliation does not sum to 23: hard stop")
    with (PRIVATE / "tnap_485_to_462_reconciliation.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["activity_id", "category", "compound_key", "reason"])
        writer.writerows(sorted(assignments))
    counts = Counter(row[1] for row in assignments)
    for category in ("duplicate_record_or_identity_collapse", "qualifier_censor_unknown",
                     "structure_standardization_failure", "potential_duplicate",
                     "conflict_cross_threshold", "other_named"):
        counts.setdefault(category, 0)
    summary = {"raw_activity_rows": len(activities), "standardized_identities": len(compounds),
               "usable_compounds": len(retained), "attrition_total": len(assignments),
               "categories": dict(sorted(counts.items())),
               "private_csv_sha256": sha(PRIVATE / "tnap_485_to_462_reconciliation.csv"),
               "coverage_verified": len(retained) + len(assignments) == len(activity_ids)}
    write_json(OUT / "reconciliation_summary.json", summary)
    print(json.dumps({"homogeneity_passed": homogeneity["passed"], "checks": checks,
                      "reconciliation": summary}, ensure_ascii=False))
    if not homogeneity["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

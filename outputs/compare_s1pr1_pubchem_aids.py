"""Compare fixed S1PR1 source rows with two PubChem patent-family assays."""
from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path


PARENT_AID = "1799215"
DIVISION_AID = "1805650"
S1PR1_ACCESSION = "P21453"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crosswalk", required=True, type=Path)
    parser.add_argument("--assaysummary", required=True, type=Path)
    parser.add_argument("--parent-summary", required=True, type=Path)
    parser.add_argument("--division-summary", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    crosswalk = json.loads(args.crosswalk.read_bytes())
    payload = json.loads(args.assaysummary.read_bytes())["Table"]
    columns = payload["Columns"]["Column"]
    assay_rows = [dict(zip(columns, item["Cell"])) for item in payload["Row"]]
    descriptions = {}
    for aid, path in ((PARENT_AID, args.parent_summary), (DIVISION_AID, args.division_summary)):
        item = json.loads(path.read_bytes())["AssaySummaries"]["AssaySummary"][0]
        if str(item["AID"]) != aid:
            raise ValueError(f"Assay-summary AID mismatch for {aid}")
        descriptions[aid] = {"name": item["Name"], "description": item["Description"],
                             "source_name": item["SourceName"], "source_id": item["SourceID"],
                             "source_sha256": file_sha256(path)}
    result_rows = []
    for source in crosswalk["rows"]:
        found = []
        for aid in (PARENT_AID, DIVISION_AID):
            matches = [row for row in assay_rows if row["CID"] == str(source["pubchem_cid"])
                       and row["AID"] == aid and row["Target Accession"] == S1PR1_ACCESSION]
            if len(matches) != 1:
                raise ValueError(f"Expected exactly one {aid} S1PR1 record for CID {source['pubchem_cid']}")
            row = matches[0]
            if row["Activity Name"] != "IC50" or Decimal(row["Activity Value [uM]"]) != Decimal(source["patent_value"]):
                raise ValueError(f"PubChem numeric mismatch for CID {source['pubchem_cid']}")
            found.append({"aid": aid, "cid": row["CID"], "sid": row["SID"],
                          "target_accession": row["Target Accession"], "target_gene_id": row["Target GeneID"],
                          "activity_value_um": row["Activity Value [uM]"],
                          "activity_outcome": row["Activity Outcome"],
                          "relation_available_in_summary": False})
        result_rows.append({"activity_id": source["activity_id"], "patent_example": source["patent_example"],
                            "patent_relation": source["patent_relation"],
                            "patent_value_um": source["patent_value"], "records": found,
                            "status": "numeric_and_human_S1PR1_match_in_both_family_aids"})
    report = {"schema": "s1pr1_fixed_sample_pubchem_patent_family_aids_v1",
              "crosswalk_sha256": file_sha256(args.crosswalk),
              "assaysummary_sha256": file_sha256(args.assaysummary),
              "aid_descriptions": descriptions, "rows": result_rows,
              "status": "12_of_12_numeric_S1PR1_matches_in_original_and_division_pubchem_aids",
              "interpretation": "The later patent-family deposit describes ligand competition binding, but the original patent deposit has a TBD method; identical values do not independently prove identical experimental protocol.",
              "limitations": ["PubChem assay summary drops the original > censoring relation; patent and ChEMBL records retain it.",
                              "The later BindingDB deposit names competition binding but does not specify receptor construct or cell system.",
                              "This is a family cross-reference, not a new independent measurement."],
              "campaign_ready": False}
    data = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        if args.output.read_bytes() != data:
            raise FileExistsError("Existing AID comparison differs; do not overwrite")
    else:
        with args.output.open("xb") as handle:
            handle.write(data)
    print(json.dumps({"status": report["status"], "row_count": len(result_rows),
                      "report_sha256": hashlib.sha256(data).hexdigest(),
                      "output": str(args.output)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

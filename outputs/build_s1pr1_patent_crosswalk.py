"""Record preliminary table-2 matches for the fixed S1PR1 source sample.

Patent values below are a transcription of Table 2 in the published
US20170217963A1 application in the US10323029 patent family. This validates
numbers and example names but does not resolve the assay method or whether
all rows in CHEMBL5734042 belong to that table.
"""
from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path


PATENT_APPLICATION_URL = "https://patents.justia.com/patent/20170217963"
PUBCHEM_URL = "https://pubchem.ncbi.nlm.nih.gov/compound/"
TABLE2_S1P1_AA_IC50_UM = {
    "52572": ("=", "0.81"),
    "52604": ("=", "0.099"),
    "52770": ("=", "0.636"),
    "52776": ("=", "0.858"),
    "52530": ("=", "0.333"),
    "52634": ("=", "0.133"),
    "52686": ("=", "6.6"),
    "52687": ("=", "22.4"),
    "52628": ("=", "4"),
    "52708": (">", "28"),
    "52706": ("=", "4.5"),
    "52491": (">", "28"),
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_report(selection: dict, pubchem: dict, selection_hash: str) -> dict:
    if pubchem.get("selection_sha256") != selection_hash:
        raise ValueError("PubChem lookup belongs to a different fixed selection")
    by_molecule = {row["molecule_chembl_id"]: row for row in pubchem["results"]}
    if len(by_molecule) != 12:
        raise ValueError("Expected 12 distinct PubChem lookup rows")
    rows = []
    examples_seen = set()
    for item in selection["sample"]["selected"]:
        identifier = item["molecule_chembl_id"]
        source = by_molecule[identifier]
        if source["http_status"] != 200 or len(source["patent_examples"]) != 1:
            raise ValueError(f"Unresolved or ambiguous PubChem patent example: {identifier}")
        example_name = source["patent_examples"][0]
        example = example_name.split()[0]
        if example not in TABLE2_S1P1_AA_IC50_UM or example in examples_seen:
            raise ValueError(f"Example absent from transcription or repeated: {example}")
        examples_seen.add(example)
        relation, patent_value_um = TABLE2_S1P1_AA_IC50_UM[example]
        raw = item["raw_record"]
        if raw["standard_units"] != "nM" or raw["standard_relation"] != relation:
            raise ValueError(f"Relation or unit mismatch for {identifier}")
        if Decimal(raw["standard_value"]) != Decimal(patent_value_um) * 1000:
            raise ValueError(f"Numeric mismatch for {identifier}")
        rows.append({"activity_id": item["activity_id"], "molecule_chembl_id": identifier,
                     "preview_support": item["record_signal"],
                     "pubchem_cid": source["cid"], "pubchem_url": PUBCHEM_URL + str(source["cid"]),
                     "bindingdb_names": source["bindingdb_names"],
                     "patent_example": example_name, "patent_table": 2,
                     "patent_column": "S1P1 AA IC50", "patent_relation": relation,
                     "patent_value": patent_value_um, "patent_units": "uM",
                     "chembl_relation": raw["standard_relation"],
                     "chembl_value": raw["standard_value"], "chembl_units": raw["standard_units"],
                     "identity_evidence": "PubChem compound synonyms link ChEMBL ID to US10323029 example name",
                     "numeric_evidence": "US20170217963A1 Table 2 S1P1 AA IC50 value matches after uM-to-nM conversion",
                     "patent_application_url": PATENT_APPLICATION_URL,
                     "match_status": "provisional_identity_and_numeric_match_method_unresolved"})
    return {"schema": "s1pr1_patent_table2_provisional_crosswalk_v1",
            "status": "12_of_12_fixed_sample_provisional_identity_and_numeric_matches",
            "selection_sha256": selection_hash, "patent_application_url": PATENT_APPLICATION_URL,
            "table": 2, "column": "S1P1 AA IC50", "rows": rows,
            "unresolved": ["Grant-versus-application table equivalence not independently audited in full.",
                           "AA method and receptor construct/cell system remain undefined.",
                           "Not yet shown that no other patent table contributes to this ChEMBL assay.",
                           "BindingDB individual measurement records have not been checked."],
            "campaign_ready": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--expected-selection-sha256", required=True)
    parser.add_argument("--pubchem-summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    selection_bytes = args.selection.read_bytes()
    selection_hash = sha256(selection_bytes)
    if selection_hash != args.expected_selection_sha256.lower():
        raise ValueError("Fixed selection hash mismatch")
    report = make_report(json.loads(selection_bytes), json.loads(args.pubchem_summary.read_bytes()), selection_hash)
    data = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        if args.output.read_bytes() != data:
            raise FileExistsError("Existing crosswalk differs; do not overwrite")
    else:
        with args.output.open("xb") as handle:
            handle.write(data)
    print(json.dumps({"status": report["status"], "row_count": len(report["rows"]),
                      "crosswalk_sha256": sha256(data), "unresolved": report["unresolved"],
                      "output": str(args.output)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

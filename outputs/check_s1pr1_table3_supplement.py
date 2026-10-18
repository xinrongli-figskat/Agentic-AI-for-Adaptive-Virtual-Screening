"""Cross-check the locked Table 3 supplement against two patent texts and PubChem."""
from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

from lxml import html


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table3(path: Path) -> dict[str, list[str]]:
    root = html.fromstring(path.read_bytes())
    article = max(root.xpath("//article"), key=lambda node: len(node.text_content()))
    tables = article.xpath(".//table")
    if len(tables) != 3:
        raise ValueError("Expected three patent tables")
    rows = {}
    for node in tables[2].xpath(".//row"):
        fields = [" ".join(entry.text_content().split()) for entry in node.xpath("./entry")]
        if fields and re.match(r"^\d{5}\b", fields[0]):
            example = re.match(r"^(\d{5})\b", fields[0]).group(1)
            if example in rows:
                raise ValueError(f"Duplicate Table 3 example {example}")
            rows[example] = fields
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--application", required=True, type=Path)
    parser.add_argument("--grant", required=True, type=Path)
    parser.add_argument("--pubchem", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    selection = json.loads(args.selection.read_bytes())
    if len(selection["selected"]) != 4:
        raise ValueError("Expected four selected Table 3 sources")
    application, grant = table3(args.application), table3(args.grant)
    payload = json.loads(args.pubchem.read_bytes())["Table"]
    columns = payload["Columns"]["Column"]
    summary = [dict(zip(columns, row["Cell"])) for row in payload["Row"]]
    checked = []
    for selected in selection["selected"]:
        example = selected["patent_examples"][0].split()[0]
        if example not in application or example not in grant:
            raise ValueError(f"Example {example} not found in both patent texts")
        source = selected["chembl_measurements"][0]
        expected = Decimal(source["value"]) / Decimal(1000)
        observed = {}
        for name, table in (("application", application), ("grant", grant)):
            row = table[example]
            value = row[2].strip()
            relation = ">" if value.startswith(">") else "="
            numeric = Decimal(value.removeprefix(">"))
            if relation != source["relation"] or numeric != expected:
                raise ValueError(f"{name} Table 3 disagreement for {example}")
            observed[name] = {"example_label": row[0], "s1pr1_aa_ic50_um": value}
        pubchem = []
        for aid in ("1799215", "1805650"):
            matches = [row for row in summary if row["CID"] == str(selected["pubchem_cid"])
                       and row["AID"] == aid and row["Target Accession"] == "P21453"]
            if not matches and aid == "1805650":
                pubchem.append({"aid": aid, "status": "not_present_in_division_deposit"})
                continue
            if len(matches) != 1:
                raise ValueError(f"Expected one {aid} human S1PR1 record for {example}")
            row = matches[0]
            if row["Activity Name"] != "IC50" or Decimal(row["Activity Value [uM]"]) != expected:
                raise ValueError(f"PubChem numeric disagreement for {example}")
            pubchem.append({"aid": aid, "cid": row["CID"], "sid": row["SID"],
                            "target_accession": row["Target Accession"],
                            "activity_value_um": row["Activity Value [uM]"],
                            "relation_available_in_summary": False})
        checked.append({"activity_id": selected["activity_id"], "molecule_chembl_id": selected["molecule_chembl_id"],
                        "patent_example": example, "original_relation": source["relation"],
                        "original_value_nm": source["value"], "patent_rows": observed,
                        "pubchem_patent_family_rows": pubchem,
                        "status": "identity_numeric_receptor_crosscheck_pass_method_unresolved"})
    report = {"schema": "s1pr1_table3_locked_supplement_check_v1", "selection_sha256": digest(args.selection),
              "application_sha256": digest(args.application), "grant_sha256": digest(args.grant),
              "pubchem_sha256": digest(args.pubchem), "rows": checked,
              "limitations": ["PubChem assay summary omits original relation signs.",
                              "The later patent-family deposit does not contain every Table 3 compound; absence is not a conflict with the original patent deposit.",
                              "Neither patent table defines AA method, receptor construct, or cell system.",
                              "Patent family entries are not independent measurements."],
              "campaign_ready": False}
    data = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        if args.output.read_bytes() != data:
            raise FileExistsError("Do not overwrite a differing source check")
    else:
        args.output.write_bytes(data)
    print(json.dumps({"checked": len(checked), "report_sha256": digest(args.output)}, indent=2))


if __name__ == "__main__":
    main()

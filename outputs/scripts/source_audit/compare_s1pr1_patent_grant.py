"""Check archived application/grant tables against fixed S1PR1 sample."""
from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

from lxml import html


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table_rows(path: Path, table_index: int) -> list[list[str]]:
    root = html.fromstring(path.read_bytes())
    article = max(root.xpath("//article"), key=lambda node: len(node.text_content()))
    tables = article.xpath(".//table")
    if len(tables) != 3:
        raise ValueError(f"Expected three source tables in {path}")
    result = []
    for row in tables[table_index].xpath(".//row"):
        fields = [" ".join(entry.text_content().split()) for entry in row.xpath("./entry")]
        if fields and re.match(r"^\d{5}\b", fields[0]):
            result.append(fields)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--application", required=True, type=Path)
    parser.add_argument("--grant", required=True, type=Path)
    parser.add_argument("--crosswalk", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    matched = []
    counts = {}
    for table_index in (1, 2):
        application = table_rows(args.application, table_index)
        grant = table_rows(args.grant, table_index)
        counts[f"table_{table_index+1}"] = {"application_data_rows": len(application),
                                            "grant_data_rows": len(grant),
                                            "identical_extracted_rows": application == grant,
                                            "row_differences": [
                                                {"row_index": index, "application": source_row,
                                                 "grant": grant_row}
                                                for index, (source_row, grant_row)
                                                in enumerate(zip(application, grant))
                                                if source_row != grant_row],
                                            "row_count_difference": len(application) != len(grant)}
        if table_index == 1:
            source_by_example = {}
            for row in grant:
                example = re.match(r"^(\d{5})\b", row[0]).group(1)
                source_by_example.setdefault(example, []).append(row)
    crosswalk = json.loads(args.crosswalk.read_bytes())
    if len(crosswalk["rows"]) != 12:
        raise ValueError("Expected fixed 12-row crosswalk")
    for row in crosswalk["rows"]:
        example = row["patent_example"].split()[0]
        candidates = source_by_example.get(example, [])
        if len(candidates) != 1:
            raise ValueError(f"Expected one grant Table 2 row for {example}")
        value = candidates[0][2]
        relation = ">" if value.startswith(">") else "="
        numeric = value.removeprefix(">")
        if relation != row["patent_relation"] or Decimal(numeric) != Decimal(row["patent_value"]):
            raise ValueError(f"Grant value differs from crosswalk for {example}")
        matched.append({"activity_id": row["activity_id"], "example": example,
                        "grant_table": 2, "grant_column": "S1P1 AA IC50",
                        "grant_value_um": value,
                        "match_status": "grant_application_and_chembl_numeric_match"})
    report = {"schema": "s1pr1_patent_application_grant_comparison_v1",
              "application_url": "https://patents.justia.com/patent/20170217963",
              "grant_url": "https://trea.com/information/sphinogosine-1-phosphate-receptor-modulators-for-treatment-of-cardiopulmonary-di/patentgrant/42935ca1-4d4c-47d6-b4d9-4a3830d17641",
              "application_sha256": sha256(args.application), "grant_sha256": sha256(args.grant),
              "crosswalk_sha256": sha256(args.crosswalk), "table_comparison": counts,
              "fixed_sample_matches": matched, "campaign_ready": False,
              "unresolved": ["AA assay method and receptor construct/cell system remain undefined.",
                             "Not yet established that all CHEMBL5734042 rows belong to one patent table and endpoint."]}
    data = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        if args.output.read_bytes() != data:
            raise FileExistsError("Existing comparison differs; do not overwrite")
    else:
        with args.output.open("xb") as handle:
            handle.write(data)
    print(json.dumps({"tables": counts, "matched": len(matched),
                      "report_sha256": hashlib.sha256(data).hexdigest(),
                      "output": str(args.output)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

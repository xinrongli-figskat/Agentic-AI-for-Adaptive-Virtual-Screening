"""Extract S1P1 columns from archived US10323029 grant Tables 2 and 3."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from lxml import html


def normalized(text: str) -> str:
    return " ".join(text.split())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grant", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    grant_bytes = args.grant.read_bytes()
    root = html.fromstring(grant_bytes)
    article = max(root.xpath("//article"), key=lambda node: len(node.text_content()))
    tables = article.xpath(".//table")
    if len(tables) != 3:
        raise ValueError("Unexpected grant table count")
    result = []
    for index in (1, 2):
        rows = []
        for source_row in tables[index].xpath(".//row"):
            fields = [normalized(entry.text_content()) for entry in source_row.xpath("./entry")]
            if not fields:
                continue
            example = re.match(r"^(\d{5})\b", fields[0])
            if not example:
                continue
            if len(fields) < 3:
                raise ValueError(f"Incomplete patent row: {fields}")
            rows.append({"example": example.group(1), "example_label": fields[0],
                         "s1pr1_aa_ic50_um": fields[2],
                         "all_receptor_columns": fields[2:7]})
        result.append({"table": index + 1, "row_count": len(rows), "rows": rows})
    report = {"schema": "s1pr1_grant_patent_table_columns_v1", "grant_sha256": hashlib.sha256(grant_bytes).hexdigest(),
              "grant_url": "https://trea.com/information/sphinogosine-1-phosphate-receptor-modulators-for-treatment-of-cardiopulmonary-di/patentgrant/42935ca1-4d4c-47d6-b4d9-4a3830d17641",
              "tables": result, "limitation": "Text extraction preserves patent table numeric strings but does not define the AA assay method."}
    data = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        if args.output.read_bytes() != data:
            raise FileExistsError("Existing patent table extraction differs")
    else:
        with args.output.open("xb") as handle:
            handle.write(data)
    print(json.dumps({"table_row_counts": [t["row_count"] for t in result],
                      "report_sha256": hashlib.sha256(data).hexdigest(),
                      "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

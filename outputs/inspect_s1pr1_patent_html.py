"""Inspect a saved public patent page without requesting network resources."""
from __future__ import annotations

import argparse
from pathlib import Path

from lxml import html


def normalized(value: str) -> str:
    return " ".join(value.split())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    root = html.fromstring(args.path.read_bytes())
    article = root.xpath("//article")
    if not article:
        raise ValueError("Patent article missing")
    node = max(article, key=lambda entry: len(entry.text_content()))
    for element in node.xpath(".//heading"):
        print("HEADING", element.get("id"), normalized(element.text_content())[:140])
    for element in node.xpath(".//p"):
        text = normalized(element.text_content())
        if any(term in text.lower() for term in ("assay", "evaluation", "receptor", "table 2", "table 3")):
            if len(text) < 3000:
                print("PARAGRAPH", element.get("id"), text[:1000])
    for table in node.xpath(".//table"):
        label = normalized(table.xpath("string(./title)"))
        rows = table.xpath(".//row")
        print("TABLE", table.get("id"), label, "rows", len(rows))
        for row in rows:
            fields = [normalized(entry.text_content()) for entry in row.xpath("./entry")]
            if fields and (fields[0].startswith(("52572", "52604", "52770", "52776", "52686", "52687")) or "S1P1" in " ".join(fields)):
                print("ROW", fields[:9])


if __name__ == "__main__":
    main()

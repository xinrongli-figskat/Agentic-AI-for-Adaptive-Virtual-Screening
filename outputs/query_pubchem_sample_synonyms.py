"""Resolve fixed S1PR1 source-sample names against official PubChem PUG REST.

This is an auditable source-ID lookup, not a biological endpoint decision. No
ChEMBL, GLM, or campaign API is called. Existing receipts are never replaced.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


PATENT = re.compile(r"US[\s-]*10323029", re.I)
EXAMPLE = re.compile(r"US[\s-]*10323029\s*,?\s*Generic\s+formula\s+(\d+)(?:\s+([A-Z]{1,3}))?", re.I)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def write_once(path: Path, data: bytes) -> None:
    if path.exists():
        if path.read_bytes() != data:
            raise FileExistsError(f"Existing receipt differs: {path}")
        return
    with path.open("xb") as handle:
        handle.write(data)


def parse_synonyms(data: bytes, queried_id: str) -> dict:
    payload = json.loads(data)
    entries = payload.get("InformationList", {}).get("Information", [])
    if len(entries) != 1:
        raise ValueError(f"Expected one PubChem result for {queried_id}, got {len(entries)}")
    item = entries[0]
    synonyms = item.get("Synonym", [])
    if queried_id not in synonyms:
        raise ValueError(f"PubChem synonyms did not contain queried ChEMBL ID {queried_id}")
    patent_names = sorted(set(name for name in synonyms if PATENT.search(name)))
    bdbm_names = sorted(set(name for name in synonyms if re.fullmatch(r"BDBM\d+", name, re.I)))
    examples = sorted(set(match.group(1) + (" " + match.group(2).upper() if match.group(2) else "")
                          for name in patent_names for match in EXAMPLE.finditer(name)))
    return {"cid": item.get("CID"), "queried_chembl_id_present": True,
            "patent_synonyms": patent_names, "bindingdb_synonyms": bdbm_names,
            "patent_example_candidates": examples, "synonym_count": len(synonyms)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--expected-selection-sha256", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--timeout", type=int, default=25)
    args = parser.parse_args()
    raw_selection = args.selection.read_bytes()
    if digest(raw_selection) != args.expected_selection_sha256.lower():
        raise ValueError("Fixed selection hash differs; no network request made")
    selection = json.loads(raw_selection)
    if selection.get("schema") != "task1_v5_s1pr1_fixed_source_sample_v1":
        raise ValueError("Unexpected fixed-selection schema")
    chosen = selection["sample"]["selected"]
    if len(chosen) != 12 or len({x["molecule_chembl_id"] for x in chosen}) != 12:
        raise ValueError("Expected 12 distinct fixed source IDs")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summaries = []
    for item in chosen:
        molecule_id = item["molecule_chembl_id"]
        path = args.output_dir / (molecule_id + ".json")
        if path.exists():
            receipt = json.loads(path.read_bytes())
            if receipt.get("molecule_chembl_id") != molecule_id or receipt.get("selection_sha256") != digest(raw_selection):
                raise ValueError("Existing PubChem receipt does not belong to this sample")
        else:
            url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/" + quote(molecule_id) + "/synonyms/JSON"
            request = Request(url, headers={"User-Agent": "agentic-screening-source-review/1.0"})
            try:
                with urlopen(request, timeout=args.timeout) as response:
                    body = response.read()
                    status = response.status
            except HTTPError as exc:
                body = exc.read()
                status = exc.code
            except (URLError, TimeoutError) as exc:
                body = str(exc).encode("utf-8", errors="replace")
                status = None
            parsed = parse_synonyms(body, molecule_id) if status == 200 else None
            receipt = {"source": "PubChem PUG REST official API", "molecule_chembl_id": molecule_id,
                       "selection_sha256": digest(raw_selection), "url": url, "http_status": status,
                       "response_sha256": digest(body), "response_bytes": len(body),
                       "parsed": parsed, "error_body_preview": body[:500].decode("utf-8", errors="replace") if status != 200 else None,
                       "interpretation": "synonyms_only_not_measurement_or_endpoint_proof"}
            write_once(path, json_bytes(receipt))
            time.sleep(0.5)
        summaries.append({"molecule_chembl_id": molecule_id, "http_status": receipt["http_status"],
                          "cid": (receipt.get("parsed") or {}).get("cid"),
                          "patent_examples": (receipt.get("parsed") or {}).get("patent_example_candidates", []),
                          "bindingdb_names": (receipt.get("parsed") or {}).get("bindingdb_synonyms", [])})
    report = {"status": "pubchem_source_name_lookup_not_endpoint_decision",
              "selection_sha256": digest(raw_selection), "request_count_max": 12,
              "results": summaries,
              "limitations": ["Synonym matches do not establish an assay measurement row.",
                              "Numeric equality alone does not prove a patent example or endpoint."]}
    data = json_bytes(report)
    write_once(args.output_dir / "summary.json", data)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

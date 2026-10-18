"""Checkpointed PubChem name lookup for all archived S1PR1 assay source IDs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
import zipfile

from query_pubchem_sample_synonyms import parse_synonyms, json_bytes, write_once


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--expected-archive-sha256", required=True)
    parser.add_argument("--assay-id", default="CHEMBL5734042")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-new", type=int, default=294)
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args()
    archive_hash = sha256(args.archive.read_bytes())
    if archive_hash != args.expected_archive_sha256.lower():
        raise ValueError("Archived run hash mismatch")
    with zipfile.ZipFile(args.archive) as archive:
        raw = archive.read("run/evidence/E0174_thin_target_window.json")
    window = json.loads(raw)
    if not window["complete"]:
        raise ValueError("Target-window source is partial")
    records = [item for item in window["records"] if item["assay_chembl_id"] == args.assay_id]
    ids = sorted({item["molecule_chembl_id"] for item in records if item.get("molecule_chembl_id")})
    if len(records) != 295 or len(ids) != 294:
        raise ValueError("Source assay counts changed")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    new = 0
    status_counts = {}
    for position, identifier in enumerate(ids, 1):
        path = args.output_dir / (identifier + ".json")
        if path.exists():
            receipt = json.loads(path.read_bytes())
            if receipt["molecule_chembl_id"] != identifier or receipt["archive_sha256"] != archive_hash:
                raise ValueError(f"Existing receipt mismatch: {identifier}")
        elif new >= args.max_new:
            continue
        else:
            url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/" + quote(identifier) + "/synonyms/JSON"
            try:
                with urlopen(Request(url, headers={"User-Agent": "agentic-screening-source-review/1.0"}),
                             timeout=args.timeout) as response:
                    body, status = response.read(), response.status
            except HTTPError as exc:
                body, status = exc.read(), exc.code
            except (URLError, TimeoutError) as exc:
                print(json.dumps({"failed_request": identifier, "error": str(exc),
                                  "completed_new": new}), flush=True)
                break
            parsed = parse_synonyms(body, identifier) if status == 200 else None
            receipt = {"schema": "s1pr1_all_pubchem_source_name_receipt_v1",
                       "archive_sha256": archive_hash, "source_window_sha256": sha256(raw),
                       "assay_id": args.assay_id, "molecule_chembl_id": identifier,
                       "url": url, "http_status": status, "response_sha256": sha256(body),
                       "parsed": parsed, "interpretation": "name_cross_reference_only_not_assay_method_proof"}
            write_once(path, json_bytes(receipt))
            new += 1
            if new % 25 == 0:
                print(json.dumps({"completed_new": new, "last_id": identifier}), flush=True)
            time.sleep(0.4)
        status = receipt["http_status"]
        status_counts[str(status)] = status_counts.get(str(status), 0) + 1
        if status == 429:
            print(json.dumps({"stopped_on_rate_limit": identifier, "completed_new": new}), flush=True)
            break
    saved = list(args.output_dir.glob("CHEMBL*.json"))
    print(json.dumps({"archive_sha256": archive_hash, "assay_id": args.assay_id,
                      "source_records": len(records), "source_ids": len(ids),
                      "new_receipts": new, "saved_receipts": len(saved),
                      "status_counts_this_pass": status_counts,
                      "all_ids_covered": len(saved) == len(ids)}), flush=True)


if __name__ == "__main__":
    main()

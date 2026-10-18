"""Save primary PubChem BioAssay evidence with URL and byte-level receipts."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aid", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.aid <= 10_000_000:
        raise ValueError("Invalid PubChem AID")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    receipts = []
    for name, path in (("description.json", "description/JSON"), ("concise.csv", "concise/CSV")):
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/assay/aid/{args.aid}/{path}"
        request = Request(url, headers={"User-Agent": "agentic-screening-source-audit/1.0"})
        with urlopen(request, timeout=120) as response:
            if response.status != 200 or response.geturl() != url:
                raise ValueError("PubChem response status or URL changed")
            payload = response.read(20_000_001)
            if len(payload) > 20_000_000:
                raise ValueError("PubChem response exceeds declared size cap")
            mime = response.headers.get("Content-Type")
        output = args.output_dir / name
        output.write_bytes(payload)
        receipts.append({"filename": name, "url": url, "http_status": 200,
                         "content_type": mime, "bytes": len(payload),
                         "sha256": hashlib.sha256(payload).hexdigest()})
    (args.output_dir / "receipt.json").write_text(
        json.dumps({"schema": "pubchem_primary_assay_fetch_v1", "aid": args.aid,
                    "source_review_complete": False, "receipts": receipts}, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": "primary_assay_data_saved", "aid": args.aid,
                      "output_dir": str(args.output_dir), "receipts": receipts}, indent=2))


if __name__ == "__main__":
    main()

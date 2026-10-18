"""Save a full PubChem AID record to preserve per-readout qualifiers."""
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
        raise ValueError("Invalid AID")
    if not args.output_dir.is_dir():
        raise FileNotFoundError("Expected existing source-audit directory")
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/assay/aid/{args.aid}/JSON"
    with urlopen(Request(url, headers={"User-Agent": "agentic-screening-source-audit/1.0"}), timeout=120) as response:
        if response.status != 200 or response.geturl() != url:
            raise ValueError("PubChem response status or URL changed")
        raw = response.read(50_000_001)
        if len(raw) > 50_000_000:
            raise ValueError("Full AID exceeds 50 MB size cap")
        mime = response.headers.get("Content-Type")
    path = args.output_dir / "full.json"
    with path.open("xb") as output:
        output.write(raw)
    receipt = {"schema": "pubchem_full_assay_fetch_v1", "aid": args.aid,
               "url": url, "http_status": 200, "content_type": mime,
               "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    (args.output_dir / "full_receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()

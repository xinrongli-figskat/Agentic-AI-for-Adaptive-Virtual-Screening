"""Save a PubChem assay-summary receipt for the locked Table 3 supplement."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    selected = json.loads(args.selection.read_bytes())["selected"]
    cids = [str(row["pubchem_cid"]) for row in selected]
    if len(cids) != 4 or len(set(cids)) != 4:
        raise ValueError("Expected four distinct selected CIDs")
    url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/" + ",".join(cids) + "/assaysummary/JSON"
    request = Request(url, headers={"User-Agent": "agentic-screening-source-review/1.0"})
    with urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise ValueError(f"PubChem returned {response.status}")
        body = response.read()
    payload = json.loads(body)
    if "Table" not in payload:
        raise ValueError("Unexpected PubChem response")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        if args.output.read_bytes() != body:
            raise FileExistsError("Existing PubChem receipt differs")
    else:
        args.output.write_bytes(body)
    print(json.dumps({"url": url, "cid_count": len(cids), "response_sha256": hashlib.sha256(body).hexdigest(),
                      "saved": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()

"""Pre-label environment and public-feature lock for D7-C2/C3.

Reads only public candidate structures. It does not open oracle label files.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PACKAGES = HERE / "runtime_packages"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(PACKAGES))

import numpy as np
import rdkit
from rdkit import rdBase
import scipy
import sklearn

from c1_surrogates import SurrogateBank

TNAP = ROOT / "data/benchmarks/tnap_chembl1738510_v1"
DYRK3_BACKUP = ROOT / ".sync_audit/backup_20261015_bbea8ee9/remote_snapshot.zip"
DYRK3_PUBLIC = "data/campaign_public/prefreeze_20261014T145140Z_6402306a507c6fd5/candidates.jsonl"
DYRK3_MANIFEST = "data/curation_private/frozen_dyrk3_v1/manifest.json"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_jsonl(blob: bytes):
    rows = [json.loads(line) for line in blob.splitlines() if line.strip()]
    if any(set(row) != {"compound_key", "standardized_smiles"} for row in rows):
        raise ValueError("Public candidate schema does not match the locked C1 interface")
    return rows


def main() -> None:
    tnap_manifest = json.loads((TNAP / "manifest.json").read_text(encoding="utf-8"))
    tnap_public_bytes = (TNAP / "public/candidates.jsonl").read_bytes()
    if sha(tnap_public_bytes) != tnap_manifest["public"]["sha256"]:
        raise ValueError("TNAP public candidate hash mismatch")
    tnap_rows = load_jsonl(tnap_public_bytes)

    with zipfile.ZipFile(DYRK3_BACKUP) as archive:
        dyrk3_public_bytes = archive.read(DYRK3_PUBLIC)
        dyrk3_manifest_bytes = archive.read(DYRK3_MANIFEST)
    dyrk3_manifest = json.loads(dyrk3_manifest_bytes)
    if sha(dyrk3_public_bytes) != dyrk3_manifest["data_sha256"]["public_candidates"]:
        raise ValueError("DYRK3 backup public candidate hash mismatch")
    dyrk3_rows = load_jsonl(dyrk3_public_bytes)

    if rdBase.rdkitVersion != "2026.09.1":
        raise RuntimeError(f"D7-C1 RDKit lock mismatch: {rdBase.rdkitVersion}")
    # Descriptor and fingerprint feature construction uses public structures only.
    banks = {
        "TNAP": SurrogateBank(tnap_rows),
        "DYRK3": SurrogateBank(dyrk3_rows),
    }
    descriptor_names = list(banks["TNAP"].descriptor_names)
    if descriptor_names != list(banks["DYRK3"].descriptor_names):
        raise ValueError("RDKit descriptor list differs across pools")
    descriptor_payload = ("\n".join(descriptor_names) + "\n").encode("utf-8")
    expected_environment = {
        "python": "3.12",
        "rdkit": "2026.09.1",
        "scikit-learn": importlib.metadata.version("scikit-learn"),
        "scipy": importlib.metadata.version("scipy"),
        "numpy": np.__version__,
    }
    result = {
        "status": "PRE_LABEL_ENVIRONMENT_LOCKED",
        "post_exposure": True,
        "utc": datetime.now(timezone.utc).isoformat(),
        "labels_read": False,
        "C1_code_sha256": sha((HERE / "c1_surrogates.py").read_bytes()),
        "C1_spec_sha256": sha((HERE / "C1_SPEC.md").read_bytes()),
        "runtime": {"python": sys.version, "executable": sys.executable, **expected_environment},
        "descriptor_list_count": len(descriptor_names),
        "descriptor_list_sha256": sha(descriptor_payload),
        "descriptor_names": descriptor_names,
        "pools": {
            "TNAP": {
                "candidate_count": len(tnap_rows),
                "public_candidates_sha256": sha(tnap_public_bytes),
                "feature_count": {name: int(values.shape[1]) for name, values in banks["TNAP"].features.items()},
                "incumbent_fingerprint_count": len(banks["TNAP"].incumbent.fingerprints),
            },
            "DYRK3": {
                "candidate_count": len(dyrk3_rows),
                "public_candidates_sha256": sha(dyrk3_public_bytes),
                "public_manifest_sha256": sha(dyrk3_manifest_bytes),
                "feature_count": {name: int(values.shape[1]) for name, values in banks["DYRK3"].features.items()},
                "incumbent_fingerprint_count": len(banks["DYRK3"].incumbent.fingerprints),
                "input_origin": "hash-verified backup archive; no live frozen directory required",
            },
        },
    }
    out = HERE / "C2_ENV_LOCK.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "descriptor_names"}, ensure_ascii=False, indent=2))
    print("descriptor_names_sha256:", result["descriptor_list_sha256"])
    print("environment_lock_sha256:", sha(out.read_bytes()))


if __name__ == "__main__":
    main()

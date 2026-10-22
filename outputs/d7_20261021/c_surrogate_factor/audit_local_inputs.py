"""Read-only local D7-C input audit; never exports labels or outcomes."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "local_input_audit.json"
BACKUP = ROOT / ".sync_audit/backup_20261015_bbea8ee9/remote_snapshot.zip"
D5 = ROOT / ".sync_audit/d5_20261020/d5_e_menu_private_20261020.zip"
TNAP = ROOT / "data/benchmarks/tnap_chembl1738510_v1"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def keys(blob):
    return [json.loads(line)["compound_key"] for line in blob.splitlines() if line]


def main():
    result = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "scope": "local_read_only_no_network_no_campaign",
        "python": sys.executable,
        "dependencies": {name: importlib.util.find_spec(name) is not None
                         for name in ("rdkit", "sklearn", "numpy", "scipy")},
    }
    result["d5_archive"] = {
        "present": D5.is_file(),
        "sha256": sha(D5.read_bytes()) if D5.is_file() else None,
        "expected_sha256": "2b812fc95cac56d225d5b3034940598ce05df12180bb403d7e17aeb81ce9440a",
    }
    result["d5_archive"]["match"] = result["d5_archive"]["sha256"] == result["d5_archive"]["expected_sha256"]

    tnap_manifest_path = TNAP / "manifest.json"
    if tnap_manifest_path.is_file():
        manifest = json.loads(tnap_manifest_path.read_text(encoding="utf-8"))
        public = (TNAP / "public/candidates.jsonl").read_bytes()
        private = (TNAP / "curation_private_labels/oracle_labels.jsonl").read_bytes()
        pkeys, lkeys = keys(public), keys(private)
        result["tnap"] = {
            "manifest_present": True,
            "public_sha256": sha(public),
            "public_hash_match": sha(public) == manifest["public"]["sha256"],
            "private_sha256": sha(private),
            "private_hash_match": sha(private) == manifest["private"]["sha256"],
            "candidate_count": len(pkeys),
            "label_count": len(lkeys),
            "same_distinct_keys": len(pkeys) == len(set(pkeys)) == len(lkeys) == len(set(lkeys)) and set(pkeys) == set(lkeys),
            "public_schema": sorted(json.loads(public.splitlines()[0])),
        }
    else:
        result["tnap"] = {"manifest_present": False}

    result["dyrk3_live_frozen_manifest_present"] = (ROOT / "data/curation_private/frozen_dyrk3_v1/manifest.json").is_file()
    result["chembl_sqlite_present"] = (ROOT / "data/source_dbs/chembl_37/extracted/chembl_37.db").is_file()
    if BACKUP.is_file():
        with zipfile.ZipFile(BACKUP) as archive:
            mbytes = archive.read("data/curation_private/frozen_dyrk3_v1/manifest.json")
            manifest = json.loads(mbytes)
            public = archive.read("data/campaign_public/prefreeze_20261014T145140Z_6402306a507c6fd5/candidates.jsonl")
            private = archive.read("data/curation_private/prefreeze_20261014T145140Z_6402306a507c6fd5/oracle_labels.jsonl")
            pkeys, lkeys = keys(public), keys(private)
            result["dyrk3_backup"] = {
                "archive_present": True,
                "manifest_sha256": sha(mbytes),
                "manifest_matches_preflight": sha(mbytes) == "3866c7bfc99e92b8e0d6f92b98955d5e68a7ae202f609eac90d0e7a201f98235",
                "public_hash_match": sha(public) == manifest["data_sha256"]["public_candidates"],
                "private_hash_match": sha(private) == manifest["data_sha256"]["private_labels"],
                "candidate_count": len(pkeys),
                "label_count": len(lkeys),
                "same_distinct_keys": len(pkeys) == len(set(pkeys)) == len(lkeys) == len(set(lkeys)) and set(pkeys) == set(lkeys),
                "public_schema": sorted(json.loads(public.splitlines()[0])),
            }
    else:
        result["dyrk3_backup"] = {"archive_present": False}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

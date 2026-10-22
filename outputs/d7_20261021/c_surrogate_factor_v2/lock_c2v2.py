"""Lock the fifth C2-v2 proxy before computing its label-dependent scores."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "outputs/d7_20261021/c_surrogate_factor/runtime_packages"))
import numpy as np
import sklearn
import scipy
from rdkit import rdBase

ENV_LOCK = ROOT / "outputs/d7_20261021/c_surrogate_factor/C2_ENV_LOCK.json"
C1_CODE = ROOT / "outputs/d7_20261021/c_surrogate_factor/c1_surrogates.py"
C1_SPEC = ROOT / "outputs/d7_20261021/c_surrogate_factor/C1_SPEC.md"
TOOLS = ROOT / "outputs/campaign_v0/numerical_tools.py"
OLD_SUMMARY = ROOT / "outputs/d7_20261021/c_surrogate_factor/C2_PUBLIC_SUMMARY.json"
TNAP_PUBLIC = ROOT / "data/benchmarks/tnap_chembl1738510_v1/public/candidates.jsonl"
DYRK3_ARCHIVE = ROOT / ".sync_audit/backup_20261015_bbea8ee9/remote_snapshot.zip"
DYRK3_PUBLIC = "data/campaign_public/prefreeze_20261014T145140Z_6402306a507c6fd5/candidates.jsonl"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main():
    env_bytes = ENV_LOCK.read_bytes()
    env = json.loads(env_bytes)
    if env.get("labels_read") is not False or env.get("descriptor_list_sha256") != "1f99f08c69f76b679316a7ea5cb57d6ac6bddf6e43ceea0fae88fd2b9e3ac0aa":
        raise ValueError("C2 v1 environment/descriptor lock mismatch")
    locked_runtime = env["runtime"]
    runtime = {"python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
               "rdkit": rdBase.rdkitVersion, "scikit-learn": sklearn.__version__,
               "scipy": scipy.__version__, "numpy": np.__version__}
    for name in ("rdkit", "scikit-learn", "scipy", "numpy"):
        if runtime[name] != locked_runtime[name]:
            raise ValueError(f"Runtime mismatch for {name}: {runtime[name]} != {locked_runtime[name]}")

    feature_spec = {"name": "S_morgan_gbdt", "representation": "Morgan bit fingerprint",
                    "radius": 2, "fp_size": 2048, "include_chirality": True,
                    "feature_source": "same NumericalTools fingerprints as S_incumbent",
                    "model": "GradientBoostingClassifier", "n_estimators": 200,
                    "max_depth": 3, "learning_rate": 0.1, "random_state": 0,
                    "cv": {"type": "StratifiedKFold", "n_splits": 5,
                           "shuffle": True, "random_state": 0},
                    "metrics": ["pooled_ROC_AUC", "EF1_percent"]}
    feature_spec_bytes = json.dumps(feature_spec, sort_keys=True, separators=(",", ":")).encode()
    tnap = TNAP_PUBLIC.read_bytes()
    with ZipFile(DYRK3_ARCHIVE) as z:
        dyrk3 = z.read(DYRK3_PUBLIC)
        dmanifest = z.read("data/curation_private/frozen_dyrk3_v1/manifest.json")
    dmanifest_obj = json.loads(dmanifest)
    if sha(dyrk3) != dmanifest_obj["data_sha256"]["public_candidates"]:
        raise ValueError("DYRK3 backup public pool hash mismatch")
    lock = {"status": "C2V2_PRE_SCORE_LOCKED", "post_exposure": True,
            "utc": datetime.now(timezone.utc).isoformat(), "labels_read": False,
            "runtime": runtime, "inherited_C2_ENV_LOCK_sha256": sha(env_bytes),
            "descriptor_name_set_sha256": env["descriptor_list_sha256"],
            "feature_spec": feature_spec, "feature_spec_sha256": sha(feature_spec_bytes),
            "C1_code_sha256": sha(C1_CODE.read_bytes()), "C1_spec_sha256": sha(C1_SPEC.read_bytes()),
            "NumericalTools_sha256": sha(TOOLS.read_bytes()),
            "C2v1_public_summary_sha256": sha(OLD_SUMMARY.read_bytes()),
            "TNAP_public_sha256": sha(tnap), "DYRK3_backup_public_sha256": sha(dyrk3),
            "DYRK3_manifest_sha256": sha(dmanifest),
            "ranking_rule": "sort all five proxies by observed TNAP ROC-AUC ascending; fixed before any C3 campaign",
            "tier_b_v2": {"minimum_TNAP_AUC_span": 0.05,
                           "S_morgan_gbdt_outlier_margin": 0.15,
                           "reference_range": "min/max of the four pre-existing C2-v1 TNAP ROC-AUC values"}}
    path = HERE / "C2V2_ENV_LOCK.json"
    path.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": lock["status"], "labels_read": False,
                      "runtime": runtime, "feature_spec_sha256": lock["feature_spec_sha256"],
                      "lock_sha256": sha(path.read_bytes())}, indent=2))


if __name__ == "__main__":
    main()

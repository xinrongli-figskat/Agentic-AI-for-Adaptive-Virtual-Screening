"""Seal local D7-C1 work without opening any hidden outcomes."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    compile((BASE / "c1_surrogates.py").read_text(encoding="utf-8"), "c1_surrogates.py", "exec")
    audit = json.loads((BASE / "local_input_audit.json").read_text(encoding="utf-8"))
    assert all(audit["tnap"][name] for name in ("public_hash_match", "private_hash_match", "same_distinct_keys"))
    assert all(audit["dyrk3_backup"][name] for name in
               ("manifest_matches_preflight", "public_hash_match", "private_hash_match", "same_distinct_keys"))
    assert audit["d5_archive"]["match"]
    assert not audit["dependencies"]["rdkit"] and not audit["dependencies"]["sklearn"]
    refs = {
        "original_card": ROOT / "outputs/d7_20261021/task_card_D7.md",
        "addendum": ROOT / "outputs/d7_20261021/task_card_D7_addendum_20261021.md",
        "frozen_knn_source_local_copy": ROOT / "outputs/campaign_v0/numerical_tools.py",
        "surrogate_code": BASE / "c1_surrogates.py",
        "surrogate_spec": BASE / "C1_SPEC.md",
        "local_input_audit": BASE / "local_input_audit.json",
    }
    lock = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "status": "C1_CODE_AND_SPEC_LOCKED_EXECUTION_UNVERIFIED",
        "post_exposure": True,
        "scope": "TNAP and DYRK3 frozen human-target pools only",
        "inputs": {name: sha(path) for name, path in refs.items()},
        "c2_admitted_locally": False,
        "reason": "RDKit, scikit-learn, and SciPy absent; remote 11-input preflight cannot be reproduced locally",
        "glm_calls": 0,
        "cpu_campaigns": 0,
    }
    assert lock["inputs"]["frozen_knn_source_local_copy"] == "00aba0779ea32c3d1f0514a783af42152fb9514665119a51907c491bd66e4749"
    write_json(BASE / "C1_LOCK.json", lock)
    (BASE / "STATUS_LOCAL_C1").write_text("C1_SPEC_LOCKED_C2_C3_BLOCKED_LOCAL_DEPENDENCIES\n", encoding="utf-8")
    (BASE / "BLOCKED_LOCAL_C2_C3.md").write_text(
        "# D7-C local execution block\n\n"
        "C1 code and specification were locked before any C2 result. Only syntax was checked. "
        "The locally available TNAP pool (462) and DYRK3 backup pool (231) passed "
        "public/private hash and identity checks. The D5 private archive passed SHA-256.\n\n"
        "This Windows runtime lacks RDKit, scikit-learn and SciPy. The live DYRK3 "
        "frozen directory and 30 GB ChEMBL SQLite are also absent. The recorded D7 "
        "11-input PASS is from the remote host. Under the current local-only scope, "
        "do not use SSH or network to fill these gaps. C2 five-fold ROC-AUC/EF1 "
        "and C3 1,600 CPU campaigns have not been run. No surrogate strength order "
        "or C4 eligibility can be inferred from local evidence. Running TNAP alone "
        "would not satisfy the two-pool preregistered factor experiment.\n\n"
        "To resume in an authorized environment: verify all eleven frozen input hashes, "
        "run the locked code with RDKit 2026.09.1 and scikit-learn/SciPy available, "
        "record exact descriptor names and dependency versions before reading C2 "
        "labels, then compute C2 privately. If either pool violates the expected "
        "strict ROC-AUC order, apply the Tier B stop without C3 or C4.\n",
        encoding="utf-8",
    )
    (BASE / "RUN_LOG_LOCAL_C1.md").write_text(
        "# D7-C local continuation log\n\n"
        f"- {lock['utc']}: Local C1 code/specification sealed. Syntax check passed; import/model tests unavailable.\n"
        "- Read-only input audit: TNAP 462 and archived DYRK3 231, both candidate/label hashes and keys match frozen manifests. D5 private archive hash matches.\n"
        "- No C2, C3 or C4 results; no network, SSH, GPU, GLM, wet experiments or model downloads.\n",
        encoding="utf-8",
    )
    members = ("audit_local_inputs.py", "local_input_audit.json", "c1_surrogates.py", "C1_SPEC.md",
               "C1_LOCK.json", "STATUS_LOCAL_C1", "BLOCKED_LOCAL_C2_C3.md", "RUN_LOG_LOCAL_C1.md",
               "seal_local_c1.py")
    write_json(BASE / "MANIFEST_LOCAL_C1.json", {
        "utc": datetime.now(timezone.utc).isoformat(),
        "status": lock["status"],
        "files": {name: sha(BASE / name) for name in members},
        "historical_manifest_unchanged": True,
    })
    print(json.dumps({"status": lock["status"], "lock_sha256": sha(BASE / "C1_LOCK.json"),
                      "manifest_sha256": sha(BASE / "MANIFEST_LOCAL_C1.json"),
                      "c2_admitted_locally": False}, indent=2))


if __name__ == "__main__":
    main()

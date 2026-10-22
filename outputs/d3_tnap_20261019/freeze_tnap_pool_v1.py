"""D3-3 immutable-by-version TNAP pool snapshot and hash receipt."""
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STAGE = ROOT / "outputs/d3_tnap_20261019"
POOL = ROOT / "data/benchmarks/tnap_chembl1738510_v1"
FREEZE = STAGE / "freeze_tnap_v1"
PRIVATE_FREEZE = STAGE / "freeze_tnap_v1_private_labels"
EXPECTED_POOL_MANIFEST = "c4206075c51db7c9fc14a9ab910b87c91adb82f5fd468dba74edba244d27feb1"
EXPECTED_STAGE_MANIFEST = "332c981f2f3a8876afdca619267838b2c12d8b239686e3eef6b35db9c3c938ab"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def copy_and_record(src, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    assert sha(dest) == sha(src)
    return {"source": str(src), "snapshot": str(dest), "sha256": sha(dest), "bytes": dest.stat().st_size}


def main():
    if FREEZE.exists() or PRIVATE_FREEZE.exists():
        raise RuntimeError("TNAP v1 freeze already exists; a change needs a new version")
    assert sha(POOL / "manifest.json") == EXPECTED_POOL_MANIFEST
    assert sha(STAGE / "d3_2_pool/MANIFEST.json") == EXPECTED_STAGE_MANIFEST
    manifest = json.loads((POOL / "manifest.json").read_text())
    assert sha(POOL / "public/candidates.jsonl") == manifest["public"]["sha256"]
    assert sha(POOL / "curation_private_labels/oracle_labels.jsonl") == manifest["private"]["sha256"]
    assert sha(STAGE / "d3_2_pool/pool_card.md") == manifest["pool_card_sha256"]
    assert sha(STAGE / "build_tnap_pool_v1.py") == manifest["build_code_sha256"]
    files = [
        copy_and_record(POOL / "public/candidates.jsonl", FREEZE / "public/candidates.jsonl"),
        copy_and_record(POOL / "curation_private_labels/oracle_labels.jsonl", PRIVATE_FREEZE / "oracle_labels.jsonl"),
        copy_and_record(POOL / "manifest.json", FREEZE / "pool_manifest.json"),
        copy_and_record(STAGE / "d3_2_pool/pool_card.md", FREEZE / "pool_card.md"),
        copy_and_record(STAGE / "d3_2_pool/qualification.json", FREEZE / "qualification.json"),
        copy_and_record(STAGE / "build_tnap_pool_v1.py", FREEZE / "code_snapshot/build_tnap_pool_v1.py"),
        copy_and_record(STAGE / "revision_v3_20261019/run_h3_h7_v3.py", FREEZE / "code_snapshot/run_h3_h7_v3.py"),
        copy_and_record(ROOT / "data/curation_private/p5_init_gate_private_20261018/init_gate_function.py", FREEZE / "code_snapshot/init_gate_function.py"),
        copy_and_record(STAGE / "revision_v3_20261019/homogeneity_measurement_rule_v3.md", FREEZE / "rules/homogeneity_measurement_rule_v3.md"),
        copy_and_record(STAGE / "d3_coldstart_decision_spec.md", FREEZE / "rules/d3_coldstart_decision_spec.md"),
    ]
    now = datetime.now(timezone.utc).isoformat()
    receipt = {"schema": "tnap_v1_freeze_receipt_v1", "frozen_at_utc": now,
               "pool_id": "tnap_chembl1738510_v1", "post_exposure": True,
               "source_gap_class": "limited", "qualification_checks_all_pass": True,
               "public_pool_path": str(FREEZE / "public/candidates.jsonl"),
               "private_label_path": str(PRIVATE_FREEZE / "oracle_labels.jsonl"),
               "pool_manifest_sha256": EXPECTED_POOL_MANIFEST,
               "d3_2_stage_manifest_sha256": EXPECTED_STAGE_MANIFEST,
               "no_changes_after_freeze": True, "glm_calls": 0, "files": files}
    receipt_path = FREEZE / "freeze_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (FREEZE / "STATUS").write_text("done\n", encoding="utf-8", newline="\n")
    (FREEZE / "RUN_LOG.md").write_text(f"{now}: TNAP v1 pool frozen; receipt SHA256 {sha(receipt_path)}; GLM calls 0. Any curation change requires v2.\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": "frozen", "frozen_at_utc": now,
                      "freeze_receipt_sha256": sha(receipt_path), "files": len(files)}))


if __name__ == "__main__":
    main()

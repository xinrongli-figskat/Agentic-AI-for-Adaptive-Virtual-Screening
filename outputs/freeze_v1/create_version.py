"""Create a versioned DYRK3 v1 manifest after verifying pre-freeze evidence."""

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path

from oracle_boundary_v0.oracle_boundary import read_json, sha256_file, verify_prepared
from campaign_v0.glm_api import MODEL_REQUEST_SETTINGS


POOL_ID = "6402306a507c6fd5"
PUBLIC_SHA = "0e1d745fe49c9d5f1aeed732f54388ece05b56f5670c424db92e4c7711943800"
PRIVATE_SHA = "eaa0c992023e51740c81f14a42960d382e6f5c9e1dfa8d1f587fdff5fa03a0b6"
FROZEN_MODEL = "glm-5.3-flash"
SOURCE_FILES = (
    "oracle_boundary_v0/oracle_boundary.py", "oracle_boundary_v0/verify_prepared.py",
    "campaign_v0/numerical_tools.py", "campaign_v0/campaign_core.py",
    "campaign_v0/llm_controller.py", "campaign_v0/glm_api.py",
    "campaign_v0/evaluation.py", "campaign_v0/evaluate_frozen.py",
    "campaign_v0/real_campaign.py",
    "freeze_v1/create_version.py",
)


def create_version(project_root, public_dir, private_dir, *, check_only=False):
    project_root, public_dir, private_dir = (Path(x).resolve() for x in
                                             (project_root, public_dir, private_dir))
    checked = verify_prepared(public_dir, private_dir)
    receipt = read_json(private_dir / "private_receipt.json")
    if checked["pool_id"] != POOL_ID or checked["public_sha256"] != PUBLIC_SHA or \
       receipt["private_labels_sha256"] != PRIVATE_SHA or \
       receipt["class_counts"] != {"hit_support": 116, "nonhit_support": 115} or \
       receipt["excluded_unknown_count"] != 1 or \
       receipt["chembl_release"] != "ChEMBL_37":
        raise ValueError("Pre-freeze evidence is not the declared DYRK3 pool")
    source_hashes = {}
    for name in SOURCE_FILES:
        path = project_root / name
        if not path.is_file():
            raise FileNotFoundError(path)
        source_hashes[str(path)] = sha256_file(path)
    protocol_source = project_root / "freeze_v1" / "protocol_decisions.md"
    protocol_bytes = protocol_source.read_bytes()
    if not protocol_bytes:
        raise ValueError("Missing protocol decisions")
    frozen_dir = private_dir.parent / "frozen_dyrk3_v1"
    if frozen_dir.exists():
        raise FileExistsError("Frozen version already exists; never overwrite it")
    campaign_spec = {"seeds": [0, 1, 2, 3, 4], "total_budget": 50,
                     "initialization_queries": 10, "batch_size": 10,
                     "representations": ["bit", "count"],
                     "model": FROZEN_MODEL,
                     "thinking": MODEL_REQUEST_SETTINGS[FROZEN_MODEL]["thinking"]["type"],
                     "reasoning_effort": MODEL_REQUEST_SETTINGS[FROZEN_MODEL]["reasoning_effort"],
                     "max_output_tokens": MODEL_REQUEST_SETTINGS[FROZEN_MODEL]["max_tokens"],
                     "api_timeout_seconds": 120, "do_sample": False,
                     "policies": ["knn_greedy", "knn_diverse", "uniform_random"],
                     "primary_metric": "H@50"}
    if check_only:
        return {"status": "ready_to_freeze_no_files_written",
                "would_create": str(frozen_dir), "pool_id": POOL_ID,
                "candidate_count": checked["candidate_count"],
                "public_sha256": PUBLIC_SHA, "private_label_sha256": PRIVATE_SHA,
                "protocol_decisions_sha256": hashlib.sha256(protocol_bytes).hexdigest(),
                "source_file_count": len(source_hashes), "campaign_spec": campaign_spec}
    frozen_dir.mkdir(mode=0o700)
    os.chmod(frozen_dir, 0o700)
    for name in SOURCE_FILES:
        snapshot_path = frozen_dir / "source_snapshot" / name
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(project_root / name, snapshot_path)
        if sha256_file(snapshot_path) != source_hashes[str(project_root / name)]:
            raise ValueError("Source snapshot hash mismatch")
        os.chmod(snapshot_path, 0o400)
    (frozen_dir / "protocol_decisions.md").write_bytes(protocol_bytes)
    os.chmod(frozen_dir / "protocol_decisions.md", 0o400)
    manifest = {
        "status": "frozen_dyrk3_v1", "pool_id": POOL_ID,
        "project_root": str(project_root),
        "target_chembl_id": "CHEMBL4575", "assay_chembl_id": "CHEMBL5363961",
        "chembl_release": "ChEMBL_37", "public_dir": str(public_dir),
        "private_dir": str(private_dir),
        "source_audit_run": receipt["source_audit_run"],
        "source_summary_sha256": receipt["source_summary_sha256"],
        "rdkit_version_at_curation": receipt["rdkit_version"],
        "run_root": str(private_dir.parent / "runs_dyrk3_v1"),
        "data_sha256": {"public_candidates": PUBLIC_SHA, "private_labels": PRIVATE_SHA,
                        "source_audit_manifest": receipt["source_audit_manifest_sha256"],
                        "qualification_decision": receipt["qualification_sha256"],
                        "pre_freeze_protocol": receipt["protocol_draft_sha256"]},
        "protocol_decisions_sha256": sha256_file(frozen_dir / "protocol_decisions.md"),
        "source_sha256": source_hashes,
        "campaign_spec": campaign_spec,
    }
    manifest_path = frozen_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True,
                                        indent=2) + "\n", encoding="utf-8")
    os.chmod(manifest_path, 0o400)
    return {"frozen_dir": str(frozen_dir), "manifest_sha256": sha256_file(manifest_path),
            "pool_id": POOL_ID, "public_sha256": PUBLIC_SHA,
            "private_label_sha256": PRIVATE_SHA, "source_file_count": len(source_hashes),
            "status": manifest["status"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--public-dir", type=Path, required=True)
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--check-only", action="store_true",
                        help="Verify evidence and show the planned spec without writing a frozen version")
    args = parser.parse_args()
    print(json.dumps(create_version(args.project_root, args.public_dir, args.private_dir,
                                    check_only=args.check_only),
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

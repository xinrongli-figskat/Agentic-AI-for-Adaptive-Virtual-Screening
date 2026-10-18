"""Verify a DYRK3 audit and export separate public/private pre-freeze inputs.

This is deliberately NOT a campaign or a final freeze. No network or LLM calls.
"""

import argparse
import hashlib
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


EXPECTED_TARGET = "CHEMBL4575"
EXPECTED_ASSAY = "CHEMBL5363961"


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    return sha256_bytes(path.read_bytes())


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def jsonl_bytes(rows):
    return b"".join(json_bytes(row) for row in rows)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify_audit(run):
    require(run.is_dir(), "Audit directory does not exist")
    manifest = read_json(run / "OUTPUT_SHA256_MANIFEST.json")
    require(isinstance(manifest, dict) and manifest, "Missing audit hash manifest")
    for name, expected in manifest.items():
        require(Path(name).name == name, "Unexpected path in audit manifest")
        require(sha256_file(run / name) == expected, "Audit hash mismatch: " + name)
    metadata = read_json(run / "run_metadata.json")
    summary = read_json(run / "summary.json")
    policy = read_json(run / "audit_policy.json")
    criteria = read_json(run / "discovery_criteria_snapshot.json")
    require(metadata.get("completed") is True, "Audit is incomplete")
    require((summary.get("target_chembl_id"), summary.get("assay_chembl_id")) ==
            (EXPECTED_TARGET, EXPECTED_ASSAY), "Unexpected target or assay")
    require((policy.get("target_chembl_id"), policy.get("assay_chembl_id")) ==
            (EXPECTED_TARGET, EXPECTED_ASSAY), "Audit policy does not match summary")
    require(policy.get("hit_threshold_nM") == "1000" and criteria.get("hit_threshold_nM") == "1000",
            "1000 nM threshold was not preserved")
    require(criteria.get("exclude_flagged_potential_duplicates_from_signals") is True,
            "Potential duplicate exclusion was not preserved")
    require(metadata.get("chembl_db_version") == "ChEMBL_37", "Unexpected ChEMBL release")
    require(summary.get("selected_assay_records") == 232 and summary.get("standardized_identity_count") == 232,
            "Audit record or standardized-identity count changed")
    return metadata, summary, policy


def build_rows(run, summary):
    compounds = read_json(run / "compound_audit.json")
    records = read_json(run / "records_audit.json")
    require(len(compounds) == 232 and len(records) == 232, "Audit row counts changed")
    by_activity = {str(r["activity_id"]): r for r in records}
    require(len(by_activity) == len(records), "Duplicate activity IDs")
    public, private, excluded = [], [], []
    keys, structures = set(), set()
    for c in sorted(compounds, key=lambda row: row["compound_key"]):
        key, smiles = c["compound_key"], c["standardized_smiles"]
        require(key not in keys and smiles not in structures, "Duplicate compound key or structure")
        require(key == "cmp_" + sha256_bytes(smiles.encode("utf-8")), "Compound key does not match structure")
        keys.add(key)
        structures.add(smiles)
        source_rows = [by_activity[str(i)] for i in c["activity_ids"]]
        require(source_rows and all(r["assay_chembl_id"] == EXPECTED_ASSAY for r in source_rows),
                "Missing or out-of-assay source record")
        if not c["usable_for_prototype_review"]:
            excluded.append({"compound_key": key, "smiles": smiles,
                             "molecule_chembl_ids": c["molecule_chembl_ids"],
                             "activity_ids": c["activity_ids"], "state": c["provisional_state"],
                             "reason": c["decision_reason"],
                             "source_potential_duplicate": [r.get("potential_duplicate") for r in source_rows]})
            continue
        state = c["provisional_state"]
        require(state in ("hit_support", "nonhit_support") and not c["review_flags"],
                "Usable compound has unsupported or flagged state")
        signals = {r["record_signal"] for r in source_rows} - {"unknown"}
        require(signals == {state}, "Frozen support disagrees with source records")
        public.append({"compound_key": key, "standardized_smiles": smiles})
        private.append({"compound_key": key, "outcome": 1 if state == "hit_support" else 0,
                        "evidence_state": state, "activity_ids": c["activity_ids"],
                        "molecule_chembl_ids": c["molecule_chembl_ids"],
                        "document_chembl_ids": c["document_chembl_ids"],
                        "exact_min_nM": c.get("exact_min_nM"),
                        "exact_max_nM": c.get("exact_max_nM")})
    counts = Counter(r["evidence_state"] for r in private)
    require(len(public) == 231 and counts == {"hit_support": 116, "nonhit_support": 115},
            "Usable class counts changed")
    require(len(excluded) == 1 and excluded[0]["state"] == "unknown" and
            excluded[0]["molecule_chembl_ids"] == ["CHEMBL1802358"] and
            excluded[0]["source_potential_duplicate"] == [1],
            "Potential duplicate disposition changed")
    require(summary.get("usable_support_counts") == dict(counts), "Summary differs from exported classes")
    return public, private, excluded


def export(run, qualification, protocol, public_root, private_root):
    run, public_root, private_root = run.resolve(), public_root.resolve(), private_root.resolve()
    require(not (public_root == private_root or public_root.is_relative_to(private_root) or
                 private_root.is_relative_to(public_root)), "Public and private roots must be separate")
    require(not (public_root.is_relative_to(run) or private_root.is_relative_to(run)),
            "Output roots cannot be inside the audit run")
    metadata, summary, policy = verify_audit(run)
    public_rows, private_rows, excluded = build_rows(run, summary)
    qual_bytes, protocol_bytes = qualification.read_bytes(), protocol.read_bytes()
    require(qual_bytes and protocol_bytes, "Missing qualification or protocol document")
    public_bytes, private_bytes = jsonl_bytes(public_rows), jsonl_bytes(private_rows)
    public_sha, private_sha = sha256_bytes(public_bytes), sha256_bytes(private_bytes)
    qualification_sha, protocol_sha = sha256_bytes(qual_bytes), sha256_bytes(protocol_bytes)
    source_sha = sha256_file(run / "summary.json")
    pool_id = sha256_bytes((public_sha + qualification_sha + source_sha).encode("ascii"))[:16]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    folder = "prefreeze_" + stamp + "_" + pool_id
    public_dir, private_dir = public_root / folder, private_root / folder
    require(not public_dir.exists() and not private_dir.exists(), "Pre-freeze export already exists")
    public_dir.mkdir(parents=True)
    private_dir.mkdir(mode=0o700, parents=True)
    os.chmod(private_dir, 0o700)
    (public_dir / "candidates.jsonl").write_bytes(public_bytes)
    (private_dir / "oracle_labels.jsonl").write_bytes(private_bytes)
    (private_dir / "excluded_unknown.json").write_bytes(json_bytes(excluded))
    (private_dir / "qualification_decision.md").write_bytes(qual_bytes)
    (private_dir / "protocol_pre_freeze.md").write_bytes(protocol_bytes)
    for name in ("oracle_labels.jsonl", "excluded_unknown.json", "qualification_decision.md", "protocol_pre_freeze.md"):
        os.chmod(private_dir / name, 0o600)
    public_receipt = {
        "status": "pre_freeze_export_not_campaign_ready", "pool_id": pool_id,
        "target_chembl_id": EXPECTED_TARGET, "assay_chembl_id": EXPECTED_ASSAY,
        "compound_count": len(public_rows), "candidates_sha256": public_sha,
        "contains_outcomes": False,
    }
    private_receipt = {
        "status": "pre_freeze_export_not_campaign_ready", "pool_id": pool_id,
        "source_audit_run": str(run), "source_summary_sha256": source_sha,
        "source_audit_manifest_sha256": sha256_file(run / "OUTPUT_SHA256_MANIFEST.json"),
        "chembl_release": metadata["chembl_db_version"], "rdkit_version": metadata["rdkit_version"],
        "assay_chembl_id": EXPECTED_ASSAY, "hit_threshold_nM": policy["hit_threshold_nM"],
        "public_candidates_sha256": public_sha, "private_labels_sha256": private_sha,
        "qualification_sha256": qualification_sha, "protocol_draft_sha256": protocol_sha,
        "usable_compounds": len(public_rows), "class_counts": dict(Counter(r["evidence_state"] for r in private_rows)),
        "excluded_unknown_count": len(excluded),
        "remaining_before_campaign": ["finalize controller/tool configuration and sensitivity rules",
                                      "freeze complete protocol with hashes", "synthetic-oracle isolation test"],
    }
    (public_dir / "public_receipt.json").write_bytes(json_bytes(public_receipt))
    (private_dir / "private_receipt.json").write_bytes(json_bytes(private_receipt))
    os.chmod(private_dir / "private_receipt.json", 0o600)
    require(sha256_file(public_dir / "candidates.jsonl") == public_sha and
            sha256_file(private_dir / "oracle_labels.jsonl") == private_sha,
            "Exported data did not match the computed hashes")
    return {"status": public_receipt["status"], "pool_id": pool_id,
            "public_dir": str(public_dir), "private_dir": str(private_dir),
            "compound_count": len(public_rows), "class_counts": private_receipt["class_counts"],
            "excluded_unknown_count": len(excluded), "public_sha256": public_sha,
            "private_label_sha256": private_sha}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-run", required=True, type=Path)
    parser.add_argument("--qualification", required=True, type=Path)
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--public-root", required=True, type=Path)
    parser.add_argument("--private-root", required=True, type=Path)
    args = parser.parse_args()
    result = export(args.audit_run, args.qualification, args.protocol, args.public_root, args.private_root)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

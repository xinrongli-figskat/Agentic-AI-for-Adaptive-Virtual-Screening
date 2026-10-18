"""Read-only follow-up for one completed DYRK3 assay audit.

This is a curation diagnostic. Its outputs include labels and must never be
mounted into a campaign agent's workspace.
"""

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from rdkit import Chem, DataStructs, rdBase
from rdkit.Chem import rdFingerprintGenerator, rdMolDescriptors


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect(audit_run):
    metadata = read_json(audit_run / "run_metadata.json")
    summary = read_json(audit_run / "summary.json")
    policy = read_json(audit_run / "audit_policy.json")
    manifest = read_json(audit_run / "OUTPUT_SHA256_MANIFEST.json")
    if not metadata.get("completed"):
        raise ValueError("Audit run is incomplete")
    for name, expected in manifest.items():
        if Path(name).name != name or digest(audit_run / name) != expected:
            raise ValueError("Audit file is missing or hash differs: " + name)
    if summary["target_chembl_id"] != policy["target_chembl_id"] or summary["assay_chembl_id"] != policy["assay_chembl_id"]:
        raise ValueError("Audit summary and policy disagree")
    if (summary["target_chembl_id"], summary["assay_chembl_id"]) != ("CHEMBL4575", "CHEMBL5363961"):
        raise ValueError("This diagnostic is scoped to the reviewed DYRK3 assay")

    compounds = read_json(audit_run / "compound_audit.json")
    records = read_json(audit_run / "records_audit.json")
    if len(compounds) != summary["standardized_identity_count"] or len(records) != summary["selected_assay_records"]:
        raise ValueError("Audit row counts differ from summary")
    by_activity = {str(r["activity_id"]): r for r in records}
    if len(by_activity) != len(records):
        raise ValueError("Duplicate activity IDs in audit")

    unresolved = []
    for compound in compounds:
        if compound["usable_for_prototype_review"]:
            continue
        support = []
        for activity_id in compound["activity_ids"]:
            r = by_activity[str(activity_id)]
            support.append({key: r.get(key) for key in (
                "activity_id", "molecule_chembl_id", "assay_chembl_id", "document_chembl_id",
                "standard_type", "standard_relation", "standard_value", "standard_units",
                "normalized_value_nM", "activity_comment", "data_validity_comment",
                "potential_duplicate", "record_signal", "record_reason", "source_smiles",
            )})
        unresolved.append({key: compound.get(key) for key in (
            "compound_key", "standardized_smiles", "molecule_chembl_ids", "activity_ids",
            "provisional_state", "review_flags", "decision_reason", "record_reason_counts",
        )} | {"source_records": support})

    settings = policy["diversity_policy"]
    generator = rdFingerprintGenerator.GetMorganGenerator(
        radius=settings["radius"], fpSize=settings["bits"], includeChirality=settings["include_chirality"]
    )
    groups = defaultdict(list)
    usable = [c for c in compounds if c["usable_for_prototype_review"]]
    for c in usable:
        mol = Chem.MolFromSmiles(c["standardized_smiles"])
        if mol is None:
            raise ValueError("Previously audited SMILES no longer parses: " + c["compound_key"])
        fp = generator.GetFingerprint(mol)
        count_fp = generator.GetSparseCountFingerprint(mol)
        groups[DataStructs.BitVectToBinaryText(fp)].append({
            "compound_key": c["compound_key"],
            "molecule_chembl_ids": c["molecule_chembl_ids"],
            "activity_ids": c["activity_ids"],
            "standardized_smiles": c["standardized_smiles"],
            "stereo_and_isotope_agnostic_smiles": c.get("stereo_and_isotope_agnostic_smiles"),
            "molecular_formula": rdMolDescriptors.CalcMolFormula(mol),
            "provisional_state": c["provisional_state"],
            "sparse_count_fingerprint_sha256": hashlib.sha256(
                repr(sorted(count_fp.GetNonzeroElements().items())).encode("utf-8")
            ).hexdigest(),
        })
    identical_fp_groups = []
    for bittext, members in groups.items():
        if len(members) < 2:
            continue
        identical_fp_groups.append({
            "bit_fingerprint_sha256": hashlib.sha256(bittext).hexdigest(),
            "size": len(members),
            "different_standardized_structures": len({m["standardized_smiles"] for m in members}),
            "class_counts": {s: sum(m["provisional_state"] == s for m in members)
                             for s in ("hit_support", "nonhit_support")},
            "same_sparse_count_fingerprint": len({m["sparse_count_fingerprint_sha256"] for m in members}) == 1,
            "members": members,
        })
    identical_fp_groups.sort(key=lambda g: (-g["size"], g["bit_fingerprint_sha256"]))
    mixed = sum(len([v for v in g["class_counts"].values() if v]) > 1 for g in identical_fp_groups)
    return {
        "purpose": "curation_edge_inspection_only",
        "source_audit_run": str(audit_run.resolve()),
        "source_summary_sha256": digest(audit_run / "summary.json"),
        "rdkit_version": rdBase.rdkitVersion,
        "fingerprint_settings": {key: settings[key] for key in ("fingerprint", "radius", "bits", "include_chirality")},
        "usable_compounds": len(usable),
        "unresolved_compounds": unresolved,
        "identical_bit_fingerprint_group_count": len(identical_fp_groups),
        "compounds_in_identical_bit_fingerprint_groups": sum(g["size"] for g in identical_fp_groups),
        "groups_with_both_support_classes": mixed,
        "identical_bit_fingerprint_groups": identical_fp_groups,
        "interpretation_limits": [
            "A matching finite Morgan bit fingerprint does not mean the chemical structures are identical.",
            "These labels are curation evidence; no campaign result or direct-binding claim is made.",
            "Sparse-count comparison is diagnostic only and does not resolve chemical identity or measurement conflicts.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-run", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = inspect(args.audit_run)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = args.output_dir / ("edge_inspection_" + stamp + "_" + result["source_summary_sha256"][:8])
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / "edge_inspection.json", result)
    preview = {
        "source_audit_run": result["source_audit_run"],
        "usable_compounds": result["usable_compounds"],
        "unresolved_compounds": result["unresolved_compounds"],
        "identical_bit_fingerprint_group_count": result["identical_bit_fingerprint_group_count"],
        "compounds_in_identical_bit_fingerprint_groups": result["compounds_in_identical_bit_fingerprint_groups"],
        "groups_with_both_support_classes": result["groups_with_both_support_classes"],
        "first_three_fingerprint_groups": result["identical_bit_fingerprint_groups"][:3],
    }
    write_json(out / "console_preview.json", preview)
    print(json.dumps(preview, indent=2, ensure_ascii=False))
    print("Output directory:", out)


if __name__ == "__main__":
    main()

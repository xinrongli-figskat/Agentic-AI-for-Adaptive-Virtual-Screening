"""Read-only structural preview of the archived S1PR1 assay window.

This operates on source molecule IDs and raw ChEMBL SMILES. It does not apply
the formal standardization/measurement audit and cannot qualify a benchmark.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import zipfile

from verify_task1_v4_archive import verify


def calculate(archive: Path, expected_sha256: str) -> dict:
    from rdkit import Chem, DataStructs, rdBase
    from rdkit.Chem import rdFingerprintGenerator
    from rdkit.Chem.Scaffolds import MurckoScaffold
    from rdkit.ML.Cluster import Butina

    verified = verify(archive, expected_sha256)
    with zipfile.ZipFile(archive) as bundle:
        state = json.loads(bundle.read("run/state.json"))
        entry = state["evidence"]["E0174"]
        content = bundle.read("run/" + entry["path"])
        if hashlib.sha256(content).hexdigest() != entry["sha256"]:
            raise ValueError("Archived target window hash mismatch")
        window = json.loads(content)
        rows = [row for row in window["records"] if row.get("assay_chembl_id") == "CHEMBL5734042"]
    if not window["complete"] or window["target_id"] != "CHEMBL4333":
        raise ValueError("Unexpected target window")
    smiles_by_id: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        identifier, smiles = row.get("molecule_chembl_id"), row.get("canonical_smiles")
        if identifier and smiles:
            smiles_by_id[identifier].add(smiles)
    ambiguous_ids = sorted(key for key, values in smiles_by_id.items() if len(values) != 1)
    generator = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048, includeChirality=True)
    entries = []
    invalid_ids = []
    scaffolds = Counter()
    for identifier in sorted(smiles_by_id):
        if identifier in ambiguous_ids:
            continue
        smiles = next(iter(smiles_by_id[identifier]))
        molecule = Chem.MolFromSmiles(smiles)
        if molecule is None:
            invalid_ids.append(identifier)
            continue
        scaffold = MurckoScaffold.MurckoScaffoldSmiles(mol=molecule, includeChirality=False)
        scaffolds[scaffold or "<acyclic>" ] += 1
        entries.append((identifier, generator.GetFingerprint(molecule)))
    distances = []
    for index in range(1, len(entries)):
        distances.extend(1 - value for value in DataStructs.BulkTanimotoSimilarity(
            entries[index][1], [fingerprint for _, fingerprint in entries[:index]]))
    clusters = Butina.ClusterData(distances, len(entries), 0.3, isDistData=True, reordering=True) if entries else []
    largest = max((len(cluster) for cluster in clusters), default=0)
    return {
        "status": "raw_smiles_preliminary_structure_preview_not_curated_pool",
        "archive_sha256": verified["sha256"],
        "target_id": "CHEMBL4333", "assay_id": "CHEMBL5734042",
        "source_activity_records": len(rows), "source_molecule_ids": len(smiles_by_id),
        "ambiguous_smiles_source_ids": ambiguous_ids,
        "invalid_smiles_source_ids": invalid_ids,
        "valid_distinct_source_ids": len(entries),
        "exact_murcko_scaffold_bucket_count_including_acyclic": len(scaffolds),
        "largest_exact_scaffold_bucket_size": max(scaffolds.values(), default=0),
        "largest_exact_scaffold_bucket_fraction": (max(scaffolds.values()) / len(entries) if entries else None),
        "top_scaffold_bucket_sizes": [count for _, count in scaffolds.most_common(10)],
        "butina_tanimoto_similarity_threshold": 0.7,
        "butina_cluster_count": len(clusters),
        "largest_butina_cluster_size": largest,
        "largest_butina_cluster_fraction": (largest / len(entries) if entries else None),
        "rdkit_version": rdBase.rdkitVersion,
        "limitations": [
            "Raw canonical_smiles are not cleaned or reconciled by the formal assay audit.",
            "Source IDs may merge or split during standardized-structure identity checks.",
            "No source/endpoint resolution, measurement reconciliation, or campaign qualification is implied.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = calculate(args.archive, args.expected_sha256)
    data = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        if args.output.read_bytes() != data:
            raise FileExistsError("Existing preview differs; do not overwrite it")
    else:
        with args.output.open("xb") as handle:
            handle.write(data)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

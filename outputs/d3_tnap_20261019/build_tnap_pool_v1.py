"""D3-2: independently qualify TNAP and export a label-separated pool.

Run only on the curation host. Never import private labels into campaign code.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from rdkit import Chem, DataStructs
from rdkit.Chem import rdFingerprintGenerator
from rdkit.Chem.Scaffolds import MurckoScaffold
from rdkit.ML.Cluster import Butina

PROJECT = Path(__file__).resolve().parents[2]
CURATION = PROJECT / "data/curation_private/chembl37_batch_curations/chembl37_batch_curation_d1d3b87ef2b3ea4e/CHEMBL1738510"
GATE = PROJECT / "data/curation_private/p5_init_gate_private_20261018/init_gate_function.py"
V3 = PROJECT / "outputs/d3_tnap_20261019/revision_v3_20261019"
STAGE = PROJECT / "outputs/d3_tnap_20261019/d3_2_pool"
POOL = PROJECT / "data/benchmarks/tnap_chembl1738510_v1"
PUBLIC = POOL / "public"
PRIVATE = POOL / "curation_private_labels"
SOURCE_HASHES = {
    "compounds_private.json": "db688a4a9814d9fb2dd7238a39075ee41f72d1da7c3ba4934ec8835bd2285c73",
    "summary.json": "87e9417e040ee9a303998436b11eccc50b1c5b0cb780b90b60194756b2978585",
    "diversity.json": "8a4ede024dcc3cc0047f04488438bfc22ccb9fddb116df455081bb12ec663a8c",
    "policy_snapshot.json": "45720302d6d68869c2c1f6ba9d9986d2ea72dc39efeea40eeb2c727cc8584210",
}
DB_SHA256 = "4be13df3b68e25dcd0bff44bf094033b5aebe98f415acdc8c1cdf380e0c15142"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def main():
    if STAGE.exists() or POOL.exists():
        raise RuntimeError("D3-2 outputs already exist; never overwrite a pool version")
    for name, expected in SOURCE_HASHES.items():
        assert sha(CURATION / name) == expected, f"Curation input hash mismatch: {name}"
    v3_manifest = json.loads((V3 / "MANIFEST.json").read_text(encoding="utf-8"))
    assert v3_manifest["status"] == "done" and v3_manifest["source_gap_class"] == "limited"
    assert sha(V3 / "MANIFEST.json") == "55be8d5e7c86860d15b476c08c4176d7de57b81c60b865fc7c6c5b53e0c8a35a"
    summary = json.loads((CURATION / "summary.json").read_text())
    old_diversity = json.loads((CURATION / "diversity.json").read_text())
    all_compounds = json.loads((CURATION / "compounds_private.json").read_text())
    selected = sorted((c for c in all_compounds if c["usable_for_prototype_review"]), key=lambda c: c["compound_key"])
    assert len({c["compound_key"] for c in selected}) == len(selected)
    states = Counter(c["provisional_state"] for c in selected)
    assert set(states) == {"hit_support", "nonhit_support"}
    N, K = len(selected), states["hit_support"]
    assert (N, K, states["nonhit_support"]) == (462, 53, 409)
    assert sum(1 for c in all_compounds if not c["usable_for_prototype_review"]) == 3
    generator = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048, includeChirality=True)
    molecules = [Chem.MolFromSmiles(c["standardized_smiles"]) for c in selected]
    assert all(m is not None for m in molecules)
    fps = [generator.GetFingerprint(m) for m in molecules]
    distances = []
    for i in range(1, N):
        distances.extend(1.0 - sim for sim in DataStructs.BulkTanimotoSimilarity(fps[i], fps[:i]))
    clusters = Butina.ClusterData(distances, N, 0.3, isDistData=True, reordering=True)
    scaffolds = [MurckoScaffold.MurckoScaffoldSmiles(mol=m, includeChirality=False) for m in molecules]
    scaffold_buckets = len(set(scaffolds))
    cluster_fraction = max(map(len, clusters)) / N
    assert abs(cluster_fraction - old_diversity["largest_cluster_fraction"]) < 1e-12
    assert scaffold_buckets == old_diversity["scaffold_count_including_acyclic_bucket"]
    spec = importlib.util.spec_from_file_location("p5_init_gate", GATE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    gate = module.p_single_class(N, K, 10)
    assert abs(gate["p_no_hit"] - 0.29191094238049553) < 1e-10
    assert abs(gate["p_single_class"] - 0.29191094255667377) < 1e-10
    checks = {
        "usable_compounds_ge_250": N >= 250,
        "hits_ge_30": K >= 30,
        "measured_nonhits_ge_100": states["nonhit_support"] >= 100,
        "mapping_confidence_ge_9": bool(summary["qualification"]["checks"]["mapping_confidence"]),
        "scaffold_buckets_ge_10": scaffold_buckets >= 10,
        "largest_butina_cluster_le_025": cluster_fraction <= 0.25,
        "query_fraction_le_020": 50 / N <= 0.20,
        "p_single_class10_le_05": gate["p_single_class"] <= 0.5,
    }
    assert summary["qualification"]["checks"]["complete_assay_endpoint_scope"]
    assert summary["qualification"]["checks"]["single_protein_mapping"]
    assert summary["qualification"]["checks"]["assay_type_B"]
    result = {
        "schema": "tnap_d3_2_qualification_v1", "assay_id": "CHEMBL1738510",
        "source_gap_class": "limited", "post_exposure": True,
        "N": N, "hits": K, "measured_nonhits": states["nonhit_support"],
        "unknown_standardized_identities": len(all_compounds) - N,
        "threshold_conflict_identities": sum(c["provisional_state"] == "threshold_disagreement" for c in all_compounds),
        "scaffold_buckets": scaffold_buckets, "largest_butina_cluster_size": max(map(len, clusters)),
        "largest_butina_cluster_fraction": cluster_fraction, "butina_cluster_count": len(clusters),
        "query_fraction": 50 / N, **gate, "random_expected_H50": 50 * K / N,
        "checks": checks, "all_checks_pass": all(checks.values()),
        "exception_accepted": [], "glm_calls": 0,
        "structure_label_association_used_for_admission": False,
    }
    STAGE.mkdir(parents=True)
    dump(STAGE / "qualification.json", result)
    if not result["all_checks_pass"]:
        (STAGE / "STATUS").write_text("blocked\n", encoding="utf-8")
        raise RuntimeError("TNAP qualification failed; no pool files written")
    PUBLIC.mkdir(parents=True)
    PRIVATE.mkdir(parents=True)
    public_path = PUBLIC / "candidates.jsonl"
    private_path = PRIVATE / "oracle_labels.jsonl"
    with public_path.open("w", encoding="utf-8", newline="\n") as pub, private_path.open("w", encoding="utf-8", newline="\n") as priv:
        for c in selected:
            pub.write(json.dumps({"compound_key": c["compound_key"], "standardized_smiles": c["standardized_smiles"]}, sort_keys=True) + "\n")
            priv.write(json.dumps({"compound_key": c["compound_key"], "outcome": int(c["provisional_state"] == "hit_support")}, sort_keys=True) + "\n")
    for line in public_path.read_text().splitlines():
        assert set(json.loads(line)) == {"compound_key", "standardized_smiles"}
    assert len(public_path.read_text().splitlines()) == len(private_path.read_text().splitlines()) == N
    pool_card = f"""# TNAP CHEMBL1738510 pool card v1

Post-exposure, single-assay, measured-label feasibility pool. Source: PubChem AID 1056, ChEMBL src_id=7, 485/485 record-level aligned to selected `IC50_Mean` (tid=2) and qualifier (tid=1). Target: human TNAP, UniProt P05186. The biochemical endpoint is cell-free TNAP enzyme activity inhibition measured with CDP-star chemiluminescence; it is not direct-binding evidence. Protein construct remains unspecified, so source status is **limited**.

Fixed hit threshold: IC50 ≤1000 nM using the saved relation/censor rules. Of 465 standardized identities, 462 are usable: 53 measured hits and 409 measured nonhits. Two unusable identities have exact/censored disagreement and one has a threshold conflict; none is silently counted as a nonhit. PubChem's Active call (roughly 100 µM) is not reused as this project's 1 µM label. 485 source records reconcile to 462 usable compounds by 20 merged duplicate records plus 2 exact/censor disagreements plus 1 threshold conflict (23 record-to-usable difference, not 23 excluded compounds).

D3-1 v3 H3 classified all 494 auxiliary tids into six same-protocol families with zero unmatched. H1/H2 passed 485/485 in v2; reconciliation remained unchanged. V3 rule SHA-256 `{sha(V3 / 'homogeneity_measurement_rule_v3.md')}`; v3 manifest SHA-256 `{sha(V3 / 'MANIFEST.json')}`. The original and v2 failed assertions remain archived.

Measurement depth varies by source row: 1–21 per-range fitted IC50 curves, median 1. Depth is associated with the usable hit label (auxiliary-tid proxy AUC 0.8785, point-biserial r 0.4949). Single-fit exact IC50 values were supported by available 7–10 point dose-response series (73/73 source rows); the depth proxy is **not** the number of concentration points or verified independent experiment repeats. This pool compares deeply characterized actives with thinly measured nonhits rather than compounds under uniform measurement effort. The association is an interpretation and selection-bias limitation, not an oracle label leak or causal proof. None of 13 exact near-threshold usable compounds had depth 1.

Structure: Morgan radius 2, 2048 bit, chirality; Butina Tanimoto cutoff 0.7, reordering=True. N={N}, hit prevalence={K/N:.4%}; largest cluster {max(map(len,clusters))}/{N}={cluster_fraction:.4%}; {scaffold_buckets} Bemis–Murcko scaffold buckets. Query fraction 50/{N}={50/N:.4%}. Exact 10-query p(no hit)={gate['p_no_hit']:.6f}, p(all hit)={gate['p_all_hit']:.12g}, p(single class)={gate['p_single_class']:.6f}; random expected H@50={50*K/N:.4f}. All frozen numerical gates passed; `exception_accepted=[]`.

Pool admission uses only source assessment and predeclared marginal/count/diversity gates. Structure–label predictive association is **not** an admission gate; it belongs to subsequent evaluation. Public candidates contain structure and key only. Labels remain in the separate private file and must be revealed only by the batch oracle. No GLM has been called for D3.
"""
    (STAGE / "pool_card.md").write_text(pool_card, encoding="utf-8", newline="\n")
    now = datetime.now(timezone.utc).isoformat()
    manifest = {
        "schema": "tnap_pool_manifest_v1", "created_utc": now,
        "database_sha256": DB_SHA256,
        "source_curation_hashes": SOURCE_HASHES,
        "source_gap_rule_sha256": sha(V3 / "homogeneity_measurement_rule_v3.md"),
        "source_review_manifest_sha256": sha(V3 / "MANIFEST.json"),
        "qualification_sha256": sha(STAGE / "qualification.json"),
        "pool_card_sha256": sha(STAGE / "pool_card.md"),
        "build_code_sha256": sha(Path(__file__)),
        "exact_gate_helper_sha256": sha(GATE),
        "public": {"path": str(public_path), "sha256": sha(public_path), "count": N},
        "private": {"path": str(private_path), "sha256": sha(private_path), "count": N},
        "label_fields_absent_from_public": True,
        "glm_calls": 0,
    }
    dump(POOL / "manifest.json", manifest)
    (STAGE / "STATUS").write_text("done\n", encoding="utf-8", newline="\n")
    (STAGE / "RUN_LOG.md").write_text(f"{now}: Built pool only after all D3-2 gates passed. Public SHA256 {sha(public_path)}; private SHA256 {sha(private_path)}. No GLM calls.\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": "done", "N": N, "hits": K, "measured_nonhits": N-K,
                      "qualification_checks": checks, "pool_manifest_sha256": sha(POOL / "manifest.json")}, ensure_ascii=False))


if __name__ == "__main__":
    main()

"""Post-exposure D1 analysis of frozen DYRK3 v1; never calls GLM.

Structure descriptors are computed and saved before private labels are loaded.
All compound-level outcomes and evaluation results stay in a *_private_ directory.
"""
import csv
import hashlib
import json
import math
import os
import platform
import random
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import scipy
from scipy.stats import pointbiserialr, rankdata
from rdkit import Chem, DataStructs, rdBase
from rdkit.Chem import rdFingerprintGenerator
from rdkit.ML.Cluster import Butina

ROOT = Path(os.environ.get("D1_PROJECT_ROOT", "/driveA/xinrong/agentic-screening"))
sys.path.insert(0, str(ROOT))
from oracle_boundary_v0.oracle_boundary import BatchOracle, read_jsonl

FROZEN = ROOT / "data/curation_private/frozen_dyrk3_v1"
R5 = ROOT / "data/curation_private/r5_cpu_controls_private_20261018"
OUT = ROOT / "outputs/d_discrimination_20261018"
PRIVATE = OUT / "d1_descriptor_association_private_"
ARMS = OUT / "d1_arms"
SHA_FROZEN = "3866c7bfc99e92b8e0d6f92b98955d5e68a7ae202f609eac90d0e7a201f98235"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def write_csv(path, rows, columns):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def frozen_candidates():
    assert sha(FROZEN / "manifest.json") == SHA_FROZEN
    manifest = json.loads((FROZEN / "manifest.json").read_text())
    candidates = read_jsonl(Path(manifest["public_dir"]) / "candidates.jsonl")
    assert len(candidates) == 231
    assert all(set(row) == {"compound_key", "standardized_smiles"} for row in candidates)
    assert len({row["compound_key"] for row in candidates}) == 231
    return sorted(candidates, key=lambda row: row["compound_key"]), manifest


def descriptors(candidates, representation):
    """This function only accepts public candidates. No label path or outcome argument."""
    keys = [row["compound_key"] for row in candidates]
    gen = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048, includeChirality=True)
    fps = []
    for row in candidates:
        mol = Chem.MolFromSmiles(row["standardized_smiles"])
        if mol is None:
            raise ValueError("Invalid public SMILES for " + row["compound_key"])
        fps.append(gen.GetFingerprint(mol) if representation == "bit" else gen.GetSparseCountFingerprint(mol))
    n = len(keys)
    sims = np.eye(n, dtype=float)
    distances = []
    for i in range(1, n):
        values = DataStructs.BulkTanimotoSimilarity(fps[i], fps[:i])
        distances.extend(1 - value for value in values)
        sims[i, :i] = values
        sims[:i, i] = values
    clusters = Butina.ClusterData(distances, n, 1 - 0.7, isDistData=True, reordering=True)
    assigned = {}
    for ci, members in enumerate(clusters):
        for index in members:
            assert index not in assigned
            assigned[index] = (ci, members)
    assert len(assigned) == n
    rows = []
    for i, key in enumerate(keys):
        neighbors = sorted(((-float(sims[i, j]), keys[j]) for j in range(n) if j != i))
        top5 = [-value for value, _ in neighbors[:5]]
        ci, members = assigned[i]
        others = [j for j in members if j != i]
        rows.append({
            "compound_key": key,
            "representation": representation,
            "mean_tanimoto_k5": sum(top5) / 5,
            "butina_cluster_size": len(members),
            "cluster_centrality": float(np.mean([sims[i, j] for j in others])) if others else 0.0,
            "degree_t07": int(sum(sims[i, j] >= 0.7 for j in range(n) if j != i)),
            "cluster_id": f"cluster_{ci+1:04d}",
        })
    return rows


def tie_hash(seed, round_number, key):
    return hashlib.sha256(f"structprior|{seed}|{round_number}|{key}".encode()).digest()


def select_structure_batch(scores, queried, seed, round_number, wanted=10):
    """Pure selector: no revealed values, outcome, labels or oracle reference."""
    available = set(scores) - set(queried)
    assert len(available) >= wanted
    return sorted(available, key=lambda key: (-scores[key], tie_hash(seed, round_number, key), key))[:wanted]


def structure_run(candidates, labels, descriptor_rows, seed):
    scores = {row["compound_key"]: row["mean_tanimoto_k5"] for row in descriptor_rows}
    oracle = BatchOracle(candidates, labels, seed=seed, total_budget=50,
                         initialization_queries=10, batch_size=10)
    first = oracle.proposed_initial_ids()
    oracle.query_batch_tool({"compound_keys": first})
    selections = [first]
    queried = set(first)
    for rnd in range(1, 5):
        chosen = select_structure_batch(scores, queried, seed, rnd)
        oracle.query_batch_tool({"compound_keys": chosen})
        selections.append(chosen)
        queried.update(chosen)
    assert len(queried) == 50
    return selections


def auc(y, scores):
    y = np.asarray(y, dtype=int)
    scores = np.asarray(scores, dtype=float)
    positives = int(y.sum())
    negatives = len(y) - positives
    if not positives or not negatives:
        return None
    ranks = rankdata(scores, method="average")
    return float((ranks[y == 1].sum() - positives * (positives + 1) / 2) / (positives * negatives))


def paired_interval(diff, seed=20261018, draws=10000):
    rng = random.Random(seed)
    means = sorted(statistics.mean(rng.choice(diff) for _ in diff) for _ in range(draws))
    return statistics.mean(diff), means[249], means[9750]


def manifest(directory):
    files = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name != "MANIFEST.json":
            files.append({"path": path.relative_to(directory).as_posix(),
                          "bytes": path.stat().st_size, "sha256": sha(path)})
    (directory / "MANIFEST.json").write_text(json.dumps({"files": files, "self_excluded": True}, indent=2) + "\n")


def main():
    started = utc()
    spec = OUT / "d1_descriptor_spec.md"
    expected = "2b59e83b01f35ed5cd43505518517ad25920beee8bc06f83f4afab08706708c3"
    assert sha(spec) == expected, "Pre-registered descriptor specification changed"
    # The active remote R5 result directory stores runs and summaries; its code
    # snapshot is the byte-identical copy in this new arm directory.
    assert sha(ARMS / "run_controls.py") == "efc8a414949caf669047119d3b10ea65b0772c0a03c281503b4b740d34122bd0"
    preexisting = {str(p): sha(p) for p in [ARMS / "run_controls.py", R5 / "control_summary.csv",
        ROOT / "campaign_v0/numerical_tools.py", ROOT / "campaign_v0/campaign_core.py"]}
    candidates, frozen = frozen_candidates()
    ARMS.mkdir(parents=True, exist_ok=True)
    PRIVATE.mkdir(parents=True, exist_ok=False)
    # Save strictly public structure-only descriptors before loading labels.
    rows = {rep: descriptors(candidates, rep) for rep in ("bit", "count")}
    for rep in rows:
        write_csv(ARMS / f"descriptors_{rep}.csv", rows[rep], list(rows[rep][0]))
    geometry_finished = utc()
    geometry_hashes = {rep: sha(ARMS / f"descriptors_{rep}.csv") for rep in rows}
    (ARMS / "structure_only_receipt.json").write_text(json.dumps({
        "finished_utc": geometry_finished, "candidate_count": 231,
        "descriptor_sha256": geometry_hashes, "labels_loaded": False,
    }, indent=2) + "\n")
    # Private evaluation begins here.
    labelrows = read_jsonl(Path(frozen["private_dir"]) / "oracle_labels.jsonl")
    labels = {row["compound_key"]: row["outcome"] for row in labelrows}
    assert set(labels) == {row["compound_key"] for row in candidates}
    assert sum(labels.values()) == 116
    base_runs = list(csv.DictReader((R5 / "control_summary.csv").open(newline="", encoding="utf-8")))
    existing = {(r["controller"], r["representation"], int(r["seed"])): int(r["H50_true"])
                for r in base_runs}
    assert len(existing) == 280
    associations, cluster_rows, run_rows, independence = [], [], [], []
    fieldnames = ("mean_tanimoto_k5", "butina_cluster_size", "cluster_centrality", "degree_t07")
    public_keys = [row["compound_key"] for row in candidates]
    y = [labels[key] for key in public_keys]
    for rep in ("bit", "count"):
        dr = rows[rep]
        for field in fieldnames:
            values = [float(row[field]) for row in dr]
            rank = sorted(range(231), key=lambda i: (-values[i], public_keys[i]))
            observed_auc = auc(y, values)
            corr = float(pointbiserialr(y, values).statistic) if np.std(values) else None
            rng = np.random.default_rng(20261018)
            boot = []
            ya, va = np.asarray(y), np.asarray(values)
            for _ in range(10000):
                idx = rng.integers(0, 231, 231)
                a = auc(ya[idx], va[idx])
                if a is not None:
                    boot.append(a)
            boot.sort()
            associations.append({"representation": rep, "descriptor": field, "n": 231,
                                 "hits": 116, "roc_auc": observed_auc, "auc_bootstrap_low": boot[int(.025 * len(boot))],
                                 "auc_bootstrap_high": boot[int(.975 * len(boot))],
                                 "point_biserial_r": corr,
                                 "H50_descending": sum(y[i] for i in rank[:50])})
        groups = {}
        for row in dr:
            groups.setdefault(row["cluster_id"], []).append(row["compound_key"])
        for cid, members in sorted(groups.items()):
            cluster_rows.append({"representation": rep, "cluster_id": cid, "size": len(members),
                                 "hits": sum(labels[k] for k in members),
                                 "hit_rate": sum(labels[k] for k in members) / len(members)})
        top = sorted(dr, key=lambda r: (-r["butina_cluster_size"], r["compound_key"]))[:math.ceil(231 / 4)]
        (PRIVATE / f"dense_group_{rep}.json").write_text(json.dumps({
            "definition": "top ceil(N/4) compounds by Butina cluster size", "n": len(top),
            "hit_count": sum(labels[r["compound_key"]] for r in top),
            "hit_rate": sum(labels[r["compound_key"]] for r in top) / len(top),
            "pool_hit_rate": 116 / 231,
        }, indent=2) + "\n")
        for seed in range(20):
            sequence = structure_run(candidates, labels, dr, seed)
            inverted = {k: 1 - v for k, v in labels.items()}
            assert sequence == structure_run(candidates, inverted, dr, seed), "Outcome changed structure-only selection"
            ids = [key for batch in sequence for key in batch]
            assert len(ids) == len(set(ids)) == 50
            # Compare every existing arm's recorded initialization, not just one reference.
            for mode in ("fixed", "random", "fixed_schedule", "rule_adaptive", "random_mixture", "matched_proportion", "label_shuffle"):
                old = json.loads((R5 / "runs" / f"{mode}_{rep}_seed{seed}.json").read_text())
                assert sequence[0] == old["result"]["trajectory"][0]["selection"], (mode, rep, seed)
            run_rows.append({"controller": "structure_prior", "representation": rep,
                             "seed": seed, "H50_true": sum(labels[k] for k in ids),
                             "initialization_hits": sum(labels[k] for k in sequence[0]),
                             "selected_keys": json.dumps(ids)})
            independence.append({"representation": rep, "seed": seed,
                                 "outcome_invariance_pass": True, "matched_initialization_pass": True})
    write_csv(PRIVATE / "descriptor_association.csv", associations, list(associations[0]))
    write_csv(PRIVATE / "cluster_hit_rates.csv", cluster_rows, list(cluster_rows[0]))
    write_csv(PRIVATE / "structure_prior_runs.csv", run_rows, list(run_rows[0]))
    write_csv(ARMS / "independence_tests.csv", independence, list(independence[0]))
    indexed = dict(existing)
    indexed.update({(r["controller"], r["representation"], int(r["seed"])): int(r["H50_true"])
                    for r in run_rows})
    comparisons = []
    pairs = [("structure_prior", "random"), ("label_shuffle", "structure_prior"),
             ("fixed", "label_shuffle"), ("fixed", "structure_prior"), ("fixed", "random")]
    for mode in ("random_mixture", "matched_proportion", "fixed_schedule", "rule_adaptive"):
        for floor in ("random", "structure_prior", "label_shuffle"):
            pairs.append((mode, floor))
    for rep in ("bit", "count"):
        for numerator, denominator in pairs:
            diffs = [indexed[(numerator, rep, seed)] - indexed[(denominator, rep, seed)] for seed in range(20)]
            mean, low, high = paired_interval(diffs)
            comparisons.append({"representation": rep, "numerator": numerator, "denominator": denominator,
                "n_paired_seeds": 20, "mean_difference_H50": mean, "bootstrap_95_low": low,
                "bootstrap_95_high": high, "primary": numerator == "fixed" and denominator == "label_shuffle",
                "post_exposure_descriptive": True})
    write_csv(PRIVATE / "paired_decomposition.csv", comparisons, list(comparisons[0]))
    # Existing GLM seeds 0-4 only; power-limited, separate from the 20-seed table.
    glm_rows = []
    for rep in ("bit", "count"):
        for seed in range(5):
            path = ROOT / "data/curation_private/runs_dyrk3_v1" / f"llm_{rep}_seed{seed}" / "run.json"
            run = json.loads(path.read_text())["result"]
            for floor in ("random", "structure_prior", "label_shuffle"):
                glm_rows.append({"representation": rep, "seed": seed, "floor": floor,
                                 "glm_H50": run["hits_at_budget"],
                                 "floor_H50": indexed[(floor, rep, seed)],
                                 "paired_difference": run["hits_at_budget"] - indexed[(floor, rep, seed)]})
    write_csv(PRIVATE / "glm_five_seed_context.csv", glm_rows, list(glm_rows[0]))
    assert preexisting == {path: sha(path) for path in preexisting}, "Frozen or R5 input changed"
    (ARMS / "STATUS").write_text("done\n")
    (PRIVATE / "STATUS").write_text("done\n")
    log = (f"Start UTC: {started}\nEnd UTC: {utc()}\n"
           f"Specification SHA-256: {expected}\nSpecification locked before results: true\n"
           f"Structure-only stage ended UTC: {geometry_finished}\n"
           f"Python {platform.python_version()}; NumPy {np.__version__}; SciPy {scipy.__version__}; RDKit {rdBase.rdkitVersion}\n"
           f"Code SHA-256: {sha(__file__)}\nCopied R5 code SHA-256: {sha(ARMS/'run_controls.py')}\n"
           f"Frozen manifest SHA-256: {sha(FROZEN/'manifest.json')}\n"
           "Seeds: 0-19; paired/bootstrap seed: 20261018; 10000 draws\nGLM calls: 0\n"
           "Post-exposure descriptive analysis; no new benchmark or campaign.\n")
    (ARMS / "RUN_LOG.md").write_text(log)
    (PRIVATE / "RUN_LOG.md").write_text(log)
    manifest(ARMS)
    manifest(PRIVATE)
    print(json.dumps({"status": "done", "association_rows": len(associations),
        "cluster_rows": len(cluster_rows), "structure_runs": len(run_rows),
        "comparison_rows": len(comparisons), "glm_context_rows": len(glm_rows),
        "structure_only_receipt_sha256": sha(ARMS / "structure_only_receipt.json"),
        "private_manifest_sha256": sha(PRIVATE / "MANIFEST.json")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
